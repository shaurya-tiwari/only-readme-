"""Deterministic demo scenarios used by the product demo surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import time
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.core.claim_processor import claim_processor
from backend.core.location_service import location_service
from backend.core.password_auth import hash_password
from backend.core.premium_calculator import premium_calculator
from backend.core.risk_scorer import risk_scorer
from backend.core.trigger_engine import trigger_engine
from backend.db.models import AuditLog, Claim, Event, Policy, TrustScore, Worker, WorkerActivity
from backend.utils.time import utc_now_naive


@dataclass(frozen=True)
class DemoScenario:
    title: str
    city: str
    zone: str
    worker_name: str
    profile: str
    income: int
    plan_name: str
    platform: str
    simulator_scenario: str
    expected_path: str
    summary: str


DEMO_PASSWORD = "rideshield-demo"

DEMO_SCENARIOS: dict[str, DemoScenario] = {
    "clean_legit": DemoScenario(
        title="Automatic rain payout",
        city="delhi",
        zone="south_delhi",
        worker_name="Rahul Kumar",
        profile="legit",
        income=900,
        plan_name="smart_protect",
        platform="zomato",
        simulator_scenario="heavy_rain",
        expected_path="Claim is created and payout is released automatically.",
        summary="Stable worker, covered rain disruption, and clean payout path.",
    ),
    "borderline_review": DemoScenario(
        title="Borderline manual review",
        city="delhi",
        zone="east_delhi",
        worker_name="Arun Patel",
        profile="edge",
        income=800,
        plan_name="assured_plan",
        platform="zomato",
        simulator_scenario="platform_outage",
        expected_path="Claim is held for review because the disruption is real but the evidence mix is incomplete.",
        summary="Platform drop with weaker history and a guarded review lane.",
    ),
    "suspicious_activity": DemoScenario(
        title="Suspicious activity check",
        city="delhi",
        zone="south_delhi",
        worker_name="Vikram Singh",
        profile="fraud",
        income=2500,
        plan_name="smart_protect",
        platform="zomato",
        simulator_scenario="heavy_rain",
        expected_path="Claim is blocked from instant payout because the account pattern is not trusted.",
        summary="Real disruption signal, but the account pattern looks unsafe.",
    ),
    "gps_spoofing_attack": DemoScenario(
        title="GPS spoofing detection",
        city="delhi",
        zone="south_delhi",
        worker_name="Deepak Sharma",
        profile="spoof",
        income=1200,
        plan_name="smart_protect",
        platform="zomato",
        simulator_scenario="heavy_rain",
        expected_path="Claim is flagged and routed to review due to impossible GPS movement patterns.",
        summary="Real disruption signal but GPS data reveals teleportation-class movement anomalies.",
    ),
}


def unique_demo_phone(offset: int = 0) -> str:
    return f"+91{(int(time.time()) % 10000000000) + offset:010d}"


async def enrich_worker_for_demo(worker_id: str, zone: str, profile: str, db: AsyncSession | None = None) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    worker_uuid = UUID(worker_id)

    async def _apply(session: AsyncSession) -> None:
        worker = await session.get(Worker, worker_uuid)
        if not worker:
            return

        trust = next(
            iter(
                (
                    await session.execute(
                        select(TrustScore).where(TrustScore.worker_id == worker.id)
                    )
                ).scalars().all()
            ),
            None,
        )

        if trust is None:
            trust = TrustScore(worker_id=worker.id)
            session.add(trust)

        if profile == "legit":
            worker.created_at = now - timedelta(days=30)
            worker.device_fingerprint = "rahul_device_android_01"
            worker.ip_address = "10.10.0.21"
            trust.score = Decimal("0.750")
            trust.total_claims = 12
            trust.approved_claims = 10
            trust.fraud_flags = 0
            trust.account_age_days = 30
            trust.device_stability = Decimal("0.900")

            for i in range(8):
                session.add(
                    WorkerActivity(
                        worker_id=worker.id,
                        zone=zone,
                        latitude=Decimal("28.5200000") + Decimal(str(i * 0.002)),
                        longitude=Decimal("77.2200000") + Decimal(str(i * 0.003)),
                        speed_kmh=Decimal(str(14 + i * 3)),
                        has_delivery_stop=True,
                        recorded_at=now - timedelta(hours=4) + timedelta(minutes=i * 25),
                    )
                )
        elif profile == "fraud":
            worker.created_at = now - timedelta(days=2)
            worker.device_fingerprint = None
            worker.ip_address = None
            trust.score = Decimal("0.100")
            trust.total_claims = 0
            trust.approved_claims = 0
            trust.fraud_flags = 0
            trust.account_age_days = 2
            trust.device_stability = Decimal("0.300")
        elif profile == "edge":
            worker.created_at = now - timedelta(days=5)
            worker.device_fingerprint = "arun_device_android_01"
            worker.ip_address = "10.10.0.88"
            trust.score = Decimal("0.150")
            trust.total_claims = 0
            trust.approved_claims = 0
            trust.fraud_flags = 0
            trust.account_age_days = 5
            trust.device_stability = Decimal("0.500")
            session.add(
                WorkerActivity(
                    worker_id=worker.id,
                    zone=zone,
                    latitude=Decimal("28.6300000"),
                    longitude=Decimal("77.3000000"),
                    speed_kmh=Decimal("12.0"),
                    has_delivery_stop=True,
                    recorded_at=now - timedelta(hours=3),
                )
            )
        elif profile == "spoof":
            worker.created_at = now - timedelta(days=10)
            worker.device_fingerprint = "deepak_device_android_01"
            worker.ip_address = "10.10.0.55"
            trust.score = Decimal("0.400")
            trust.total_claims = 3
            trust.approved_claims = 2
            trust.fraud_flags = 0
            trust.account_age_days = 10
            trust.device_stability = Decimal("0.600")

            # Inject spoofed GPS records through the simulation module
            from simulations.location_spoof_mock import spoof_simulator
            await spoof_simulator.inject_teleportation_attack(
                session, worker.id, zone, intensity="high"
            )

        trust.last_updated = now
        await session.commit()

    if db is not None:
        await _apply(db)
        return

    from backend.database import async_session_factory

    async with async_session_factory() as session:
        await _apply(session)


async def _create_demo_worker(
    db: AsyncSession,
    *,
    scenario: DemoScenario,
    phone: str,
) -> Worker:
    zone_record = await location_service.resolve_zone(db, scenario.city, scenario.zone)
    risk_result = risk_scorer.calculate_risk_score(city=scenario.city, zone=zone_record.slug)

    worker = Worker(
        name=scenario.worker_name,
        phone=phone,
        password_hash=hash_password(DEMO_PASSWORD),
        city_id=zone_record.city_id,
        zone_id=zone_record.id,
        city=scenario.city,
        zone=zone_record.slug,
        platform=scenario.platform,
        self_reported_income=scenario.income,
        working_hours=8,
        consent_given=True,
        consent_timestamp=utc_now_naive(),
        risk_score=risk_result["risk_score"],
        ip_address="127.0.0.1",
        status="active",
    )
    db.add(worker)
    await db.flush()

    db.add(
        TrustScore(
            worker_id=worker.id,
            score=0.100,
            total_claims=0,
            approved_claims=0,
            fraud_flags=0,
            account_age_days=0,
            device_stability=0.500,
        )
    )
    db.add(
        AuditLog(
            entity_type="worker",
            entity_id=worker.id,
            action="registered",
            details={
                "city": scenario.city,
                "zone": zone_record.slug,
                "platform": scenario.platform,
                "risk_score": risk_result["risk_score"],
                "consent_given": True,
                "source": "demo_scenario",
            },
            performed_by="system",
        )
    )
    await db.commit()
    return worker


async def _create_demo_policy(db: AsyncSession, worker_id: UUID, plan_name: str) -> Policy:
    result = await db.execute(
        select(Worker)
        .options(selectinload(Worker.policies))
        .where(Worker.id == worker_id)
    )
    worker = result.scalar_one()
    plan_def = settings.PLAN_DEFINITIONS[plan_name]

    risk_result = risk_scorer.calculate_risk_score(city=worker.city, zone=worker.zone)
    premium_result = premium_calculator.calculate(
        plan_name=plan_name,
        risk_score=risk_result["risk_score"],
        previous_premium=None,
        risk_meta=risk_result["breakdown"],
    )

    now = utc_now_naive()
    policy = Policy(
        worker_id=worker.id,
        plan_name=plan_name,
        plan_display_name=plan_def["display_name"],
        base_price=plan_def["base_price"],
        plan_factor=plan_def["plan_factor"],
        risk_score_at_purchase=risk_result["risk_score"],
        weekly_premium=premium_result["final_premium"],
        coverage_cap=plan_def["coverage_cap"],
        triggers_covered=plan_def["triggers_covered"],
        status="active",
        purchased_at=now,
        activates_at=now,
        expires_at=now + timedelta(days=settings.POLICY_DURATION_DAYS),
    )
    db.add(policy)
    await db.flush()
    db.add(
        AuditLog(
            entity_type="policy",
            entity_id=policy.id,
            action="purchased",
            details={
                "plan_name": plan_name,
                "worker_id": str(worker.id),
                "premium": premium_result["final_premium"],
                "source": "demo_scenario",
            },
            performed_by="system",
        )
    )
    await db.commit()
    return policy


async def run_demo_scenario(db: AsyncSession, scenario_id: str) -> dict:
    if scenario_id not in DEMO_SCENARIOS:
        raise ValueError(f"Unknown demo scenario: {scenario_id}")

    scenario = DEMO_SCENARIOS[scenario_id]
    phone = unique_demo_phone(offset=list(DEMO_SCENARIOS.keys()).index(scenario_id))
    worker = await _create_demo_worker(db, scenario=scenario, phone=phone)
    await _create_demo_policy(db, worker.id, scenario.plan_name)
    await enrich_worker_for_demo(str(worker.id), scenario.zone, scenario.profile, db=db)

    demo_run_id = f"demo-{scenario_id}-{int(time.time())}"
    trigger_result = await claim_processor.run_trigger_cycle(
        db=db,
        zones=[scenario.zone],
        city=scenario.city,
        scenario=scenario.simulator_scenario,
        demo_run_id=demo_run_id,
    )

    if trigger_result["claims_generated"] == 0:
        await _force_demo_claim_generation(db, worker, scenario, trigger_result)

    claim_result = await db.execute(
        select(Claim)
        .where(Claim.worker_id == worker.id)
        .order_by(Claim.created_at.desc())
    )
    claims = claim_result.scalars().all()
    latest_claim = claims[0] if claims else None

    return {
        **trigger_result,
        "demo_scenario": scenario_id,
        "title": scenario.title,
        "summary": scenario.summary,
        "expected_path": scenario.expected_path,
        "city": scenario.city,
        "zone": scenario.zone,
        "scenario": scenario.simulator_scenario,
        "worker": {
            "id": str(worker.id),
            "name": worker.name,
            "phone": worker.phone,
            "profile": scenario.profile,
        },
        "latest_claim_status": latest_claim.status if latest_claim else None,
    }


async def _force_demo_claim_generation(
    db: AsyncSession,
    worker: Worker,
    scenario: DemoScenario,
    trigger_result: dict,
) -> None:
    zone_record = await location_service.resolve_zone(db, scenario.city, scenario.zone)
    thresholds = trigger_engine.thresholds_for_zone(zone_record)
    zone_result = trigger_result.get("details", [{}])[0] if trigger_result.get("details") else {}
    signals = zone_result.get("signals") or {}
    fired_triggers = zone_result.get("triggers_fired") or trigger_engine.evaluate_thresholds(signals, thresholds=thresholds)
    if not fired_triggers:
        return

    event = (
        await db.execute(
            select(Event)
            .where(and_(Event.zone_id == zone_record.id, Event.status == "active"))
            .order_by(Event.started_at.desc())
        )
    ).scalars().first()
    if not event:
        return

    policy = (
        await db.execute(
            select(Policy).where(
                and_(
                    Policy.worker_id == worker.id,
                    Policy.status == "active",
                )
            )
        )
    ).scalars().first()
    if not policy:
        return

    trust = (
        await db.execute(select(TrustScore).where(TrustScore.worker_id == worker.id))
    ).scalars().first()
    covered_triggers = [trigger for trigger in fired_triggers if trigger in policy.triggers_covered]
    if not covered_triggers:
        return

    claim_result = await claim_processor._process_worker_claim(
        db=db,
        worker=worker,
        policy=policy,
        event=event,
        disruption_score=float(event.disruption_score or trigger_engine.calculate_disruption_score(signals, thresholds=thresholds)),
        event_confidence=float(event.event_confidence or trigger_engine.calculate_event_confidence(signals, fired_triggers, scenario.zone)),
        trust_score=float(trust.score) if trust else 0.1,
        covered_triggers=covered_triggers,
        fired_triggers=fired_triggers,
        traffic_source="scenario",
    )
    if not trigger_result.get("details"):
        trigger_result["details"] = [{"zone": scenario.zone, "claim_details": []}]

    zone_result = trigger_result["details"][0]
    zone_result.setdefault("claim_details", []).append(claim_result)
    zone_result["claims_processed"] = zone_result.get("claims_processed", 0) + 1
    trigger_result["claims_generated"] += 1
    if claim_result["status"] == "approved":
        zone_result["claims_approved"] = zone_result.get("claims_approved", 0) + 1
        zone_result["total_payout"] = zone_result.get("total_payout", 0) + claim_result.get("payout_amount", 0)
        trigger_result["claims_approved"] += 1
        trigger_result["total_payout"] += claim_result.get("payout_amount", 0)
    elif claim_result["status"] == "delayed":
        zone_result["claims_delayed"] = zone_result.get("claims_delayed", 0) + 1
        trigger_result["claims_delayed"] += 1
    elif claim_result["status"] == "rejected":
        zone_result["claims_rejected"] = zone_result.get("claims_rejected", 0) + 1
        trigger_result["claims_rejected"] += 1
