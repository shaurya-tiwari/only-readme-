from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend.config import settings
from backend.core.forecast_engine import forecast_engine
from backend.core.payout_executor import payout_executor
from backend.core.rate_limit import InMemoryRateLimiter
from backend.database import async_session_factory
from backend.db.models import Claim, Event, Payout, Policy, Worker
from backend.utils.time import utc_now_naive


@pytest.mark.asyncio
async def test_expire_old_requires_admin_session(client):
    response = await client.post("/api/policies/expire-old")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_payout_executor_does_not_overwrite_claim_final_payout():
    now = utc_now_naive()

    async with async_session_factory() as db:
        worker = Worker(
            name="Audit Worker",
            phone="+919100000001",
            city="delhi",
            zone="south_delhi",
            platform="zomato",
            consent_given=True,
            status="active",
        )
        db.add(worker)
        await db.flush()

        policy = Policy(
            worker_id=worker.id,
            plan_name="smart_protect",
            plan_display_name="Smart Protect",
            base_price=Decimal("39.00"),
            plan_factor=Decimal("1.5"),
            risk_score_at_purchase=Decimal("0.500"),
            weekly_premium=Decimal("39.00"),
            coverage_cap=Decimal("600.00"),
            triggers_covered=["rain"],
            status="active",
            activates_at=now - timedelta(hours=1),
            expires_at=now + timedelta(days=7),
        )
        event = Event(
            event_type="rain",
            zone="south_delhi",
            city="delhi",
            started_at=now - timedelta(hours=2),
            status="active",
        )
        db.add_all([policy, event])
        await db.flush()

        claim = Claim(
            worker_id=worker.id,
            policy_id=policy.id,
            event_id=event.id,
            trigger_type="rain",
            calculated_payout=Decimal("450.00"),
            final_payout=Decimal("300.00"),
            status="approved",
        )
        db.add(claim)
        await db.flush()

        await payout_executor.execute(db, claim, worker, policy.plan_name, 450.0)
        await db.commit()
        await db.refresh(claim)

        payout = (await db.execute(select(Payout).where(Payout.claim_id == claim.id))).scalar_one()

    assert claim.final_payout == Decimal("300.00")
    assert payout.amount == Decimal("450.00")


@pytest.mark.asyncio
async def test_payout_executor_marks_failed_status_when_transfer_errors(monkeypatch):
    now = utc_now_naive()

    async with async_session_factory() as db:
        worker = Worker(
            name="Failed Payout Worker",
            phone="+919100000021",
            city="delhi",
            zone="south_delhi",
            platform="zomato",
            consent_given=True,
            status="active",
        )
        db.add(worker)
        await db.flush()

        policy = Policy(
            worker_id=worker.id,
            plan_name="smart_protect",
            plan_display_name="Smart Protect",
            base_price=Decimal("39.00"),
            plan_factor=Decimal("1.5"),
            risk_score_at_purchase=Decimal("0.500"),
            weekly_premium=Decimal("39.00"),
            coverage_cap=Decimal("600.00"),
            triggers_covered=["rain"],
            status="active",
            activates_at=now - timedelta(hours=1),
            expires_at=now + timedelta(days=7),
        )
        event = Event(
            event_type="rain",
            zone="south_delhi",
            city="delhi",
            started_at=now - timedelta(hours=2),
            status="active",
        )
        db.add_all([policy, event])
        await db.flush()

        claim = Claim(
            worker_id=worker.id,
            policy_id=policy.id,
            event_id=event.id,
            trigger_type="rain",
            calculated_payout=Decimal("450.00"),
            final_payout=Decimal("300.00"),
            status="approved",
        )
        db.add(claim)
        await db.flush()

        monkeypatch.setattr(
            payout_executor,
            "_simulate_transfer",
            lambda plan_name: (_ for _ in ()).throw(RuntimeError("simulated transfer error")),
        )

        result = await payout_executor.execute(db, claim, worker, policy.plan_name, 450.0)
        await db.commit()

        payout = (await db.execute(select(Payout).where(Payout.claim_id == claim.id))).scalar_one()

    assert result["status"] == "failed"
    assert payout.status == "failed"
    assert payout.transaction_id is None


@pytest.mark.asyncio
async def test_manual_claim_resolution_prefers_final_payout(client, admin_cookies, monkeypatch):
    register_response = await client.post(
        "/api/workers/register",
        json={
            "name": "Manual Review Worker",
            "phone": "+919100000002",
            "password": "manualreview123",
            "city": "delhi",
            "zone": "south_delhi",
            "platform": "zomato",
            "self_reported_income": 900,
            "working_hours": 9,
            "consent_given": True,
        },
    )
    assert register_response.status_code == 201
    worker_id = register_response.json()["worker_id"]

    create_policy_response = await client.post(
        "/api/policies/create",
        json={"worker_id": worker_id, "plan_name": "smart_protect"},
    )
    assert create_policy_response.status_code == 201

    captured = {}

    async def fake_execute(db, claim, worker, plan_name, amount):
        captured["amount"] = amount
        return {"amount": amount, "status": "completed"}

    monkeypatch.setattr("backend.api.claims.payout_executor.execute", fake_execute)

    now = utc_now_naive()
    async with async_session_factory() as db:
        worker = (await db.execute(select(Worker).where(Worker.phone == "+919100000002"))).scalar_one()
        policy = (await db.execute(select(Policy).where(Policy.worker_id == worker.id))).scalar_one()
        event = Event(
            event_type="rain",
            zone="south_delhi",
            city="delhi",
            started_at=now - timedelta(hours=2),
            status="active",
        )
        db.add(event)
        await db.flush()

        claim = Claim(
            worker_id=worker.id,
            policy_id=policy.id,
            event_id=event.id,
            trigger_type="rain",
            calculated_payout=Decimal("500.00"),
            final_payout=Decimal("300.00"),
            status="delayed",
        )
        db.add(claim)
        await db.commit()
        claim_id = claim.id

    response = await client.post(
        f"/api/claims/resolve/{claim_id}",
        json={"decision": "approve", "reviewed_by": "test_admin"},
        cookies=admin_cookies,
    )

    assert response.status_code == 200
    assert captured["amount"] == 300.0
    assert response.json()["claim"]["status"] == "approved"


@pytest.mark.asyncio
async def test_manual_claim_resolution_keeps_claim_approved_when_payout_fails(client, admin_cookies, monkeypatch):
    register_response = await client.post(
        "/api/workers/register",
        json={
            "name": "Manual Fail Worker",
            "phone": "+919100000022",
            "password": "manualreview123",
            "city": "delhi",
            "zone": "south_delhi",
            "platform": "zomato",
            "self_reported_income": 900,
            "working_hours": 9,
            "consent_given": True,
        },
    )
    worker_id = register_response.json()["worker_id"]

    create_policy_response = await client.post(
        "/api/policies/create",
        json={"worker_id": worker_id, "plan_name": "smart_protect"},
    )
    assert create_policy_response.status_code == 201

    async def exploding_execute(db, claim, worker, plan_name, amount):
        raise RuntimeError("manual resolution payout failure")

    monkeypatch.setattr("backend.api.claims.payout_executor.execute", exploding_execute)

    now = utc_now_naive()
    async with async_session_factory() as db:
        worker = (await db.execute(select(Worker).where(Worker.phone == "+919100000022"))).scalar_one()
        policy = (await db.execute(select(Policy).where(Policy.worker_id == worker.id))).scalar_one()
        event = Event(
            event_type="rain",
            zone="south_delhi",
            city="delhi",
            started_at=now - timedelta(hours=2),
            status="active",
        )
        db.add(event)
        await db.flush()

        claim = Claim(
            worker_id=worker.id,
            policy_id=policy.id,
            event_id=event.id,
            trigger_type="rain",
            calculated_payout=Decimal("500.00"),
            final_payout=Decimal("300.00"),
            status="delayed",
        )
        db.add(claim)
        await db.commit()
        claim_id = claim.id

    response = await client.post(
        f"/api/claims/resolve/{claim_id}",
        json={"decision": "approve", "reviewed_by": "test_admin"},
        cookies=admin_cookies,
    )

    assert response.status_code == 200
    assert response.json()["claim"]["status"] == "approved"
    assert response.json()["payout"]["status"] == "failed"

    async with async_session_factory() as db:
        payout = (await db.execute(select(Payout).where(Payout.claim_id == claim_id))).scalar_one()
        claim = (await db.execute(select(Claim).where(Claim.id == claim_id))).scalar_one()

    assert claim.status == "approved"
    assert payout.status == "failed"


@pytest.mark.asyncio
async def test_incident_pressure_uses_7d_and_30d_windows():
    now = utc_now_naive()

    async with async_session_factory() as db:
        db.add_all(
            [
                Event(
                    event_type="rain",
                    zone="south_delhi",
                    city="delhi",
                    started_at=now - timedelta(days=2),
                    status="active",
                ),
                Event(
                    event_type="rain",
                    zone="south_delhi",
                    city="delhi",
                    started_at=now - timedelta(days=10),
                    status="active",
                ),
                Event(
                    event_type="rain",
                    zone="south_delhi",
                    city="delhi",
                    started_at=now - timedelta(days=40),
                    status="active",
                ),
                Event(
                    event_type="rain",
                    zone="south_delhi",
                    city="delhi",
                    started_at=now - timedelta(days=3),
                    status="ended",
                ),
            ]
        )
        await db.commit()

        incidents_7d, incidents_30d = await forecast_engine._incident_pressure(db, "south_delhi")

    assert incidents_7d == 1
    assert incidents_30d == 3


@pytest.mark.asyncio
async def test_rate_limiter_cleanup_prunes_stale_keys(monkeypatch):
    limiter = InMemoryRateLimiter(cleanup_interval=1)

    monkeypatch.setattr(settings, "ENV", "dev")
    monkeypatch.setattr("backend.core.rate_limit.time.monotonic", lambda: 10.0)

    limiter._events["stale"] = [0.0]
    limiter._windows["stale"] = 1

    await limiter.hit("fresh", limit=5, window_seconds=60)

    assert "stale" not in limiter._events
    assert "fresh" in limiter._events
