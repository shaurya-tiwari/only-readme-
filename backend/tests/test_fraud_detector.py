"""
Direct tests for Sprint 2 fraud detection.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend.core.fraud_detector import fraud_detector
from backend.database import async_session_factory
from backend.db.models import Event, Policy, TrustScore, Worker, WorkerActivity


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def create_worker_policy_event(profile: str):
    now = utc_now_naive()

    async with async_session_factory() as db:
        worker = Worker(
            name=f"{profile.title()} Worker",
            phone=f"+91990000{1 if profile == 'legit' else 2 if profile == 'fraud' else 3:04d}",
            city="delhi",
            zone="south_delhi",
            platform="zomato",
            self_reported_income=Decimal("900") if profile == "legit" else Decimal("2500"),
            working_hours=Decimal("8"),
            consent_given=True,
            consent_timestamp=now - timedelta(days=30 if profile == "legit" else 2),
            status="active",
            created_at=now - timedelta(days=30 if profile == "legit" else 2),
            device_fingerprint="device_ok" if profile == "legit" else None,
            ip_address="10.0.0.21" if profile == "legit" else None,
        )
        db.add(worker)
        await db.flush()

        db.add(
            TrustScore(
                worker_id=worker.id,
                score=Decimal("0.750") if profile == "legit" else Decimal("0.100"),
                total_claims=10 if profile == "legit" else 0,
                approved_claims=9 if profile == "legit" else 0,
                fraud_flags=0,
                account_age_days=30 if profile == "legit" else 2,
                device_stability=Decimal("0.900") if profile == "legit" else Decimal("0.300"),
                last_updated=now,
            )
        )

        policy = Policy(
            worker_id=worker.id,
            plan_name="smart_protect",
            plan_display_name="Smart Protect",
            base_price=Decimal("39"),
            plan_factor=Decimal("1.5"),
            risk_score_at_purchase=Decimal("0.450"),
            weekly_premium=Decimal("39"),
            coverage_cap=Decimal("600"),
            triggers_covered=["rain", "traffic", "platform_outage", "social"],
            status="active",
            purchased_at=now - timedelta(days=1),
            activates_at=now - timedelta(hours=1),
            expires_at=now + timedelta(days=6),
            created_at=now - timedelta(days=1),
        )
        db.add(policy)

        event = Event(
            event_type="rain",
            zone="south_delhi",
            city="delhi",
            started_at=now - timedelta(minutes=10),
            severity=Decimal("1.600"),
            raw_value=Decimal("48.0"),
            threshold=Decimal("25.0"),
            disruption_score=Decimal("0.780"),
            event_confidence=Decimal("0.900"),
            api_source="openweather",
            status="active",
            created_at=now - timedelta(minutes=10),
            updated_at=now - timedelta(minutes=10),
        )
        db.add(event)
        await db.flush()

        if profile == "legit":
            for i in range(6):
                db.add(
                    WorkerActivity(
                        worker_id=worker.id,
                        zone="south_delhi",
                        latitude=Decimal("28.5200000") + Decimal(str(i * 0.002)),
                        longitude=Decimal("77.2200000") + Decimal(str(i * 0.003)),
                        speed_kmh=Decimal(str(14 + i * 2)),
                        has_delivery_stop=True,
                        recorded_at=now - timedelta(hours=2) + timedelta(minutes=i * 20),
                    )
                )

        await db.commit()
        return worker.id


@pytest.mark.asyncio
async def test_legitimate_profile_gets_low_fraud_score():
    worker_id = await create_worker_policy_event("legit")

    async with async_session_factory() as db:
        worker = await db.get(Worker, worker_id)
        policy = (await db.execute(select(Policy).where(Policy.worker_id == worker_id))).scalar_one()
        event = (await db.execute(select(Event))).scalar_one()

        result = await fraud_detector.compute_fraud_score(db, worker, event, policy, trust_score=0.75)

    assert result["adjusted_fraud_score"] < 0.2
    assert result["flags"] == []
    assert result["is_high_risk"] is False


@pytest.mark.asyncio
async def test_suspicious_profile_gets_flagged_and_scored_high():
    worker_id = await create_worker_policy_event("fraud")

    async with async_session_factory() as db:
        worker = await db.get(Worker, worker_id)
        policy = (await db.execute(select(Policy).where(Policy.worker_id == worker_id))).scalar_one()
        event = (await db.execute(select(Event))).scalar_one()

        result = await fraud_detector.compute_fraud_score(db, worker, event, policy, trust_score=0.1)

    assert result["adjusted_fraud_score"] >= 0.38
    assert "movement" in result["flags"]
    assert "income_inflation" in result["flags"]
    assert "pre_activity" in result["flags"]
