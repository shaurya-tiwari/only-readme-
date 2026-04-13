"""Tests for Phase 3 decision-memory logging and replay."""

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from backend.core.claim_processor import claim_processor
from backend.core.decision_memory import export_decision_logs, replay_decision_log
from backend.database import async_session_factory
from backend.db.models import Claim, DecisionLog, Event, Policy, TrustScore, Worker, Zone
from backend.utils.time import utc_now_naive


async def create_worker_policy_event(phone: str) -> tuple:
    now = utc_now_naive()
    async with async_session_factory() as db:
        zone = (await db.execute(select(Zone).where(Zone.slug == "south_delhi"))).scalar_one()
        worker = Worker(
            name="Decision Memory Worker",
            phone=phone,
            city_id=zone.city_id,
            zone_id=zone.id,
            city="delhi",
            zone="south_delhi",
            platform="zomato",
            self_reported_income=Decimal("900"),
            working_hours=Decimal("9"),
            consent_given=True,
            consent_timestamp=now - timedelta(days=30),
            risk_score=Decimal("0.620"),
            status="active",
            created_at=now - timedelta(days=30),
        )
        db.add(worker)
        await db.flush()

        policy = Policy(
            worker_id=worker.id,
            plan_name="smart_protect",
            plan_display_name="Smart Protect",
            base_price=Decimal("39"),
            plan_factor=Decimal("1.5"),
            risk_score_at_purchase=Decimal("0.620"),
            weekly_premium=Decimal("39"),
            coverage_cap=Decimal("600"),
            triggers_covered=["rain", "traffic", "platform_outage"],
            status="active",
            purchased_at=now - timedelta(days=1),
            activates_at=now - timedelta(hours=1),
            expires_at=now + timedelta(days=6),
            created_at=now - timedelta(days=1),
        )
        db.add(policy)

        trust = TrustScore(
            worker_id=worker.id,
            score=Decimal("0.780"),
            total_claims=2,
            approved_claims=2,
            fraud_flags=0,
            account_age_days=30,
            device_stability=Decimal("0.910"),
            last_updated=now,
        )
        db.add(trust)

        event = Event(
            event_type="rain",
            zone_id=zone.id,
            zone="south_delhi",
            city="delhi",
            started_at=now - timedelta(minutes=12),
            severity=Decimal("1.400"),
            raw_value=Decimal("41.0"),
            threshold=Decimal("25.0"),
            disruption_score=Decimal("0.810"),
            event_confidence=Decimal("0.880"),
            api_source="mock_weather",
            status="active",
            metadata_json={"fired_triggers": ["rain", "traffic"], "demo_run_id": "wave1-memory"},
            created_at=now - timedelta(minutes=12),
            updated_at=now - timedelta(minutes=12),
        )
        db.add(event)
        await db.commit()
        return worker.id, policy.id, event.id


def setup_approved_claim_mocks(monkeypatch):
    async def fake_fraud(*args, **kwargs):
        return {
            "raw_fraud_score": 0.11,
            "adjusted_fraud_score": 0.06,
            "flags": ["movement"],
            "signals": {"movement": 0.41},
            "is_high_risk": False,
            "rule_fraud_score": 0.09,
            "ml_fraud_score": 0.12,
            "fraud_probability": 0.11,
            "ml_confidence": 0.92,
            "model_version": "fraud-model-test",
            "fallback_used": False,
            "top_factors": [{"label": "movement anomaly", "score": 0.11}],
        }

    def fake_decide(*args, **kwargs):
        return {
            "final_score": 0.902,
            "decision": "approved",
            "explanation": "Approved in test.",
            "decision_policy_version": "decision-policy-test",
            "decision_confidence": 0.83,
            "decision_confidence_band": "high",
            "primary_reason": "movement anomaly",
            "breakdown": {"automation_confidence": 0.88},
            "inputs": {"fraud_flags": ["movement"], "raw_fraud_score": 0.11},
            "review_deadline": None,
        }

    async def fake_income(*args, **kwargs):
        return {
            "income_per_hour": 105,
            "net_income_per_hour": 90,
            "operating_cost_factor": 0.85,
            "peak_multiplier": 1.2,
            "raw_payout": 252,
            "final_payout": 252,
        }

    async def fake_payout(*args, **kwargs):
        return {"payout_id": "test-payout", "amount": 252, "status": "completed"}

    monkeypatch.setattr("backend.core.claim_processor.fraud_detector.compute_fraud_score", fake_fraud)
    monkeypatch.setattr("backend.core.claim_processor.decision_engine.decide", fake_decide)
    monkeypatch.setattr("backend.core.claim_processor.income_verifier.calculate_payout", fake_income)
    monkeypatch.setattr("backend.core.claim_processor.payout_executor.execute", fake_payout)


def setup_delayed_claim_mocks(monkeypatch):
    async def fake_fraud(*args, **kwargs):
        return {
            "raw_fraud_score": 0.31,
            "adjusted_fraud_score": 0.22,
            "flags": ["movement", "pre_activity"],
            "signals": {"movement": 0.54, "pre_activity": 0.52},
            "is_high_risk": False,
            "rule_fraud_score": 0.28,
            "ml_fraud_score": 0.25,
            "fraud_probability": 0.27,
            "ml_confidence": 0.78,
            "model_version": "fraud-model-test",
            "fallback_used": False,
            "top_factors": [{"label": "movement anomaly", "score": 0.22}],
        }

    def fake_decide(*args, **kwargs):
        return {
            "final_score": 0.588,
            "decision": "delayed",
            "explanation": "Delayed in test.",
            "decision_policy_version": "decision-policy-test",
            "decision_confidence": 0.61,
            "decision_confidence_band": "moderate",
            "primary_reason": "movement anomaly",
            "breakdown": {"automation_confidence": 0.59},
            "inputs": {"fraud_flags": ["movement", "pre_activity"], "raw_fraud_score": 0.31},
            "review_deadline": utc_now_naive() + timedelta(hours=24),
        }

    async def fake_income(*args, **kwargs):
        return {
            "income_per_hour": 96,
            "net_income_per_hour": 82,
            "operating_cost_factor": 0.85,
            "peak_multiplier": 1.1,
            "raw_payout": 132,
            "final_payout": 132,
        }

    monkeypatch.setattr("backend.core.claim_processor.fraud_detector.compute_fraud_score", fake_fraud)
    monkeypatch.setattr("backend.core.claim_processor.decision_engine.decide", fake_decide)
    monkeypatch.setattr("backend.core.claim_processor.income_verifier.calculate_payout", fake_income)


@pytest.mark.asyncio
async def test_claim_creation_writes_decision_log(monkeypatch):
    worker_id, policy_id, event_id = await create_worker_policy_event("+919888111001")
    setup_approved_claim_mocks(monkeypatch)

    async with async_session_factory() as db:
        worker = await db.get(Worker, worker_id)
        policy = await db.get(Policy, policy_id)
        event = await db.get(Event, event_id)

        result = await claim_processor._process_worker_claim(
            db=db,
            worker=worker,
            policy=policy,
            event=event,
            disruption_score=0.81,
            event_confidence=0.88,
            trust_score=0.78,
            covered_triggers=["rain", "traffic"],
            fired_triggers=["rain", "traffic"],
        )
        await db.commit()

        claim = (await db.execute(select(Claim).where(Claim.worker_id == worker_id))).scalar_one()
        logs = (
            await db.execute(
                select(DecisionLog)
                .where(DecisionLog.claim_id == claim.id)
                .order_by(DecisionLog.created_at.asc())
            )
        ).scalars().all()

    assert result["status"] == "approved"
    assert len(logs) == 1
    created_log = logs[0]
    assert created_log.lifecycle_stage == "claim_created"
    assert created_log.decision_source == "system"
    assert created_log.system_decision == "approved"
    assert created_log.resulting_status == "approved"
    assert created_log.decision_policy_version == "decision-policy-test"
    assert created_log.model_versions["fraud_model"] == "fraud-model-test"
    assert created_log.feature_snapshot["decision_inputs"]["fraud_result"]["adjusted_fraud_score"] == 0.06
    assert created_log.output_snapshot["decision"]["decision"] == "approved"
    assert created_log.context_snapshot["traffic_source"] == "baseline"


@pytest.mark.asyncio
async def test_manual_resolution_writes_decision_memory_entry(client, admin_cookies, monkeypatch):
    worker_id, policy_id, event_id = await create_worker_policy_event("+919888111002")
    setup_delayed_claim_mocks(monkeypatch)

    async with async_session_factory() as db:
        worker = await db.get(Worker, worker_id)
        policy = await db.get(Policy, policy_id)
        event = await db.get(Event, event_id)
        result = await claim_processor._process_worker_claim(
            db=db,
            worker=worker,
            policy=policy,
            event=event,
            disruption_score=0.63,
            event_confidence=0.71,
            trust_score=0.78,
            covered_triggers=["rain", "traffic"],
            fired_triggers=["rain", "traffic"],
        )
        await db.commit()
        claim = (await db.execute(select(Claim).where(Claim.worker_id == worker_id))).scalar_one()

    assert result["status"] == "delayed"

    resolve_response = await client.post(
        f"/api/claims/resolve/{claim.id}",
        json={"decision": "approve", "reason": "Manual verification passed.", "reviewed_by": "wave3_admin"},
        cookies=admin_cookies,
    )
    assert resolve_response.status_code == 200

    async with async_session_factory() as db:
        logs = (
            await db.execute(
                select(DecisionLog)
                .where(DecisionLog.claim_id == claim.id)
                .order_by(DecisionLog.created_at.asc())
            )
        ).scalars().all()

    assert len(logs) == 2
    resolution_log = logs[-1]
    assert resolution_log.lifecycle_stage == "manual_resolution"
    assert resolution_log.decision_source == "admin"
    assert resolution_log.system_decision == "delayed"
    assert resolution_log.resulting_status == "approved"
    assert resolution_log.final_label == "legit"
    assert resolution_log.label_source == "admin_review"
    assert resolution_log.reviewed_by == "wave3_admin"
    assert float(resolution_log.review_wait_hours) >= 0.0
    assert resolution_log.context_snapshot["traffic_source"] == "baseline"


@pytest.mark.asyncio
async def test_decision_memory_replay_and_export_use_frozen_inputs(monkeypatch):
    worker_id, policy_id, event_id = await create_worker_policy_event("+919888111003")
    setup_approved_claim_mocks(monkeypatch)

    async with async_session_factory() as db:
        worker = await db.get(Worker, worker_id)
        policy = await db.get(Policy, policy_id)
        event = await db.get(Event, event_id)
        await claim_processor._process_worker_claim(
            db=db,
            worker=worker,
            policy=policy,
            event=event,
            disruption_score=0.81,
            event_confidence=0.88,
            trust_score=0.78,
            covered_triggers=["rain", "traffic"],
            fired_triggers=["rain", "traffic"],
        )
        await db.commit()

        log_entry = (
            await db.execute(select(DecisionLog).order_by(DecisionLog.created_at.asc()))
        ).scalars().first()
        exported = await export_decision_logs(db)

    replayed = replay_decision_log(log_entry)

    assert replayed["decision"] == log_entry.system_decision
    assert exported
    assert exported[0]["feature_snapshot"]["decision_inputs"]["trust_score"] == 0.78
    assert exported[0]["decision_policy_version"] == "decision-policy-test"
    assert exported[0]["context_snapshot"]["traffic_source"] == "baseline"


@pytest.mark.asyncio
async def test_claim_creation_can_persist_explicit_traffic_source(monkeypatch):
    worker_id, policy_id, event_id = await create_worker_policy_event("+919888111004")
    setup_approved_claim_mocks(monkeypatch)

    async with async_session_factory() as db:
        worker = await db.get(Worker, worker_id)
        policy = await db.get(Policy, policy_id)
        event = await db.get(Event, event_id)

        await claim_processor._process_worker_claim(
            db=db,
            worker=worker,
            policy=policy,
            event=event,
            disruption_score=0.81,
            event_confidence=0.88,
            trust_score=0.78,
            covered_triggers=["rain", "traffic"],
            fired_triggers=["rain", "traffic"],
            traffic_source="simulation_pressure",
        )
        await db.commit()

        claim = (await db.execute(select(Claim).where(Claim.worker_id == worker_id))).scalar_one()
        log_entry = (await db.execute(select(DecisionLog).where(DecisionLog.claim_id == claim.id))).scalars().one()

    assert claim.decision_breakdown["traffic_source"] == "simulation_pressure"
    assert log_entry.context_snapshot["traffic_source"] == "simulation_pressure"
