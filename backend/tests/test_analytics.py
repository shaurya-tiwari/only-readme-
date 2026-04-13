"""
Tests for admin analytics endpoints.
"""

from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.database import async_session_factory
from backend.db.models import Claim, DecisionLog, Event, Policy, Worker, Zone
from backend.core.location_service import location_service
from backend.api.analytics import (
    _build_decision_memory_summary,
    _build_false_review_pattern_summary,
    _build_source_comparison_summary,
    _build_policy_health_summary,
    _build_policy_replay_summary,
    _build_review_driver_summary,
)
from backend.utils.time import utc_now_naive


def _claim_stub(*, created_at: datetime, primary_reason: str, worker_id=None, zone: str = "south_delhi"):
    return SimpleNamespace(
        worker_id=worker_id or uuid4(),
        created_at=created_at,
        decision_breakdown={"primary_reason": primary_reason},
        event=SimpleNamespace(zone=zone),
    )


def test_review_driver_summary_falls_back_to_active_queue_when_recent_window_is_empty():
    active_queue_claims = [
        _claim_stub(created_at=datetime(2026, 4, 3, 10, 0), primary_reason="movement anomaly", worker_id=uuid4()),
        _claim_stub(created_at=datetime(2026, 4, 3, 10, 5), primary_reason="worker trust score", worker_id=uuid4(), zone="east_delhi"),
    ]

    summary = _build_review_driver_summary([], active_queue_claims, recent_window_hours=1)

    assert summary["source"] == "active_queue"
    assert summary["total_incidents"] == 2
    assert summary["drivers"]
    assert summary["insights"]["weak_signal_overlap_share"] == 50
    assert summary["insights"]["low_trust_share"] == 50


def test_review_driver_summary_counts_multiple_labels_per_incident():
    claim = SimpleNamespace(
        worker_id=uuid4(),
        created_at=datetime(2026, 4, 3, 10, 0),
        decision_breakdown={
            "primary_reason": "movement anomaly",
            "fraud_model": {
                "top_factors": [
                    {"label": "movement anomaly"},
                    {"label": "weak pre-event activity"},
                ]
            },
            "inputs": {
                "fraud_flags": ["movement", "pre_activity"],
                "event_confidence": 0.72,
            },
        },
        event=SimpleNamespace(zone="south_delhi"),
    )

    summary = _build_review_driver_summary([], [claim], recent_window_hours=1)

    labels = {driver["label"] for driver in summary["drivers"]}
    assert "movement anomaly" in labels
    assert "weak pre-event activity" in labels
    assert "event confidence" in labels
    assert summary["insights"]["weak_signal_overlap_share"] == 100


def test_false_review_pattern_summary_and_replay_summary_capture_delayed_to_legit_behavior():
    claim_id = uuid4()
    created_log = SimpleNamespace(
        claim_id=claim_id,
        lifecycle_stage="claim_created",
        system_decision="delayed",
        resulting_status="delayed",
        final_label=None,
        feature_snapshot={
            "decision_inputs": {
                "disruption_score": 0.55,
                "event_confidence": 0.63,
                "trust_score": 0.46,
                "payout_amount": 98,
                "fraud_result": {
                    "adjusted_fraud_score": 0.26,
                    "raw_fraud_score": 0.34,
                    "flags": ["movement", "pre_activity"],
                    "ml_confidence": 0.76,
                    "fallback_used": False,
                },
                "feedback_result": {},
            },
            "claim_features": {
                "surface": "gray_band_surface",
                "risk_expectation": "reduce_false_reviews",
            },
        },
        output_snapshot={
            "decision": {
                "primary_reason": "movement anomaly",
                "policy_layer": "micro_payout_safe_lane",
                "rule_id": "gray_band_low_risk_surface_approve",
            }
        },
        context_snapshot={"traffic_source": "scenario"},
        final_score=0.613,
        payout_amount=98,
        fraud_score=0.26,
        trust_score=0.46,
        decision_policy_version="decision-policy-v3-wave1",
        model_versions={"fraud_model": "fraud-model-v2"},
    )
    resolved_log = SimpleNamespace(
        claim_id=claim_id,
        lifecycle_stage="manual_resolution",
        system_decision="delayed",
        resulting_status="approved",
        final_label="legit",
        feature_snapshot={},
        output_snapshot={},
        context_snapshot={"traffic_source": "scenario"},
        final_score=0.613,
        payout_amount=98,
        fraud_score=0.26,
        trust_score=0.46,
    )

    decision_summary = _build_decision_memory_summary([created_log, resolved_log])
    pattern_summary = _build_false_review_pattern_summary([created_log, resolved_log])
    policy_health = _build_policy_health_summary([created_log, resolved_log])
    replay_summary = _build_policy_replay_summary([created_log, resolved_log])

    assert decision_summary["traffic_source_counts"]["scenario"] == 1
    assert pattern_summary["false_review_count"] == 1
    assert pattern_summary["score_band_distribution"]["0.60_0.65"] == 1
    assert pattern_summary["payout_band_distribution"]["75_125"] == 1
    assert pattern_summary["dominant_patterns"][0]["flags"] == ["movement", "pre_activity"]
    assert pattern_summary["surface_distribution"]["gray_band_surface"] == 1
    assert pattern_summary["traffic_source_distribution"]["scenario"] == 1
    assert pattern_summary["top_rules"][0]["rule_id"] == "gray_band_low_risk_surface_approve"
    assert policy_health["friction_score"] == 100.0
    assert policy_health["review_load"] == 100.0
    assert policy_health["top_friction_rules"][0]["rule_id"] == "gray_band_low_risk_surface_approve"
    assert policy_health["top_friction_surfaces"][0]["surface"] == "gray_band_surface"
    source_summary = _build_source_comparison_summary([created_log, resolved_log])
    assert source_summary["source_rows"]["scenario"]["claim_created_rows"] == 1
    assert source_summary["source_rows"]["scenario"]["false_review_rate"] == 100.0
    assert source_summary["source_contamination"]["simulated_share"] == 100.0
    assert source_summary["baseline_truth_mode"]["sources_used"] == ["baseline"]
    assert replay_summary["rows_replayed"] == 1
    assert replay_summary["transitions"]["delayed->approved"] == 1
    assert replay_summary["delayed_to_approved_count"] == 1
    assert replay_summary["surface_transitions"]["gray_band_surface"]["delayed->approved"] == 1
    assert replay_summary["source_transitions"]["scenario"]["delayed->approved"] == 1


@pytest.mark.asyncio
async def test_admin_overview_includes_decision_memory_summary(client, admin_cookies):
    baseline_response = await client.get("/api/analytics/admin-overview", cookies=admin_cookies)
    assert baseline_response.status_code == 200
    baseline_payload = baseline_response.json()["decision_memory_summary"]

    async with async_session_factory() as db:
        now = utc_now_naive()
        zone = (await db.execute(select(Zone).order_by(Zone.slug.asc()))).scalars().first()
        if zone is None:
            await location_service.ensure_bootstrap(db, strict_backfill=True)
            await db.commit()
            zone = (await db.execute(select(Zone).order_by(Zone.slug.asc()))).scalars().first()
        assert zone is not None
        zone_slug = zone.slug
        phone_suffix = str(uuid4().int)[-6:]

        worker_1 = Worker(
            name="Analytics Worker 1",
            phone=f"+9191{phone_suffix}11",
            city_id=zone.city_id,
            zone_id=zone.id,
            city="delhi",
            zone=zone_slug,
            platform="zomato",
            consent_given=True,
            status="active",
            created_at=now - timedelta(days=14),
        )
        worker_2 = Worker(
            name="Analytics Worker 2",
            phone=f"+9191{phone_suffix}12",
            city_id=zone.city_id,
            zone_id=zone.id,
            city="delhi",
            zone=zone_slug,
            platform="swiggy",
            consent_given=True,
            status="active",
            created_at=now - timedelta(days=14),
        )
        worker_3 = Worker(
            name="Analytics Worker 3",
            phone=f"+9191{phone_suffix}13",
            city_id=zone.city_id,
            zone_id=zone.id,
            city="delhi",
            zone=zone_slug,
            platform="blinkit",
            consent_given=True,
            status="active",
            created_at=now - timedelta(days=14),
        )
        db.add_all([worker_1, worker_2, worker_3])
        await db.flush()

        policy_1 = Policy(
            worker_id=worker_1.id,
            plan_name="smart_protect",
            plan_display_name="Smart Protect",
            base_price=Decimal("39"),
            plan_factor=Decimal("1.5"),
            risk_score_at_purchase=Decimal("0.620"),
            weekly_premium=Decimal("39"),
            coverage_cap=Decimal("600"),
            triggers_covered=["rain"],
            status="active",
            purchased_at=now - timedelta(days=1),
            activates_at=now - timedelta(hours=1),
            expires_at=now + timedelta(days=6),
            created_at=now - timedelta(days=1),
        )
        policy_2 = Policy(
            worker_id=worker_2.id,
            plan_name="smart_protect",
            plan_display_name="Smart Protect",
            base_price=Decimal("39"),
            plan_factor=Decimal("1.5"),
            risk_score_at_purchase=Decimal("0.620"),
            weekly_premium=Decimal("39"),
            coverage_cap=Decimal("600"),
            triggers_covered=["rain"],
            status="active",
            purchased_at=now - timedelta(days=1),
            activates_at=now - timedelta(hours=1),
            expires_at=now + timedelta(days=6),
            created_at=now - timedelta(days=1),
        )
        policy_3 = Policy(
            worker_id=worker_3.id,
            plan_name="assured_plan",
            plan_display_name="Assured Plan",
            base_price=Decimal("49"),
            plan_factor=Decimal("2.0"),
            risk_score_at_purchase=Decimal("0.710"),
            weekly_premium=Decimal("49"),
            coverage_cap=Decimal("800"),
            triggers_covered=["rain"],
            status="active",
            purchased_at=now - timedelta(days=1),
            activates_at=now - timedelta(hours=1),
            expires_at=now + timedelta(days=6),
            created_at=now - timedelta(days=1),
        )
        db.add_all([policy_1, policy_2, policy_3])
        await db.flush()

        event_1 = Event(
            event_type="rain",
            zone_id=zone.id,
            zone=zone_slug,
            city="delhi",
            started_at=now - timedelta(hours=2),
            severity=Decimal("1.200"),
            raw_value=Decimal("38.0"),
            threshold=Decimal("25.0"),
            disruption_score=Decimal("0.580"),
            event_confidence=Decimal("0.690"),
            api_source="mock_weather",
            status="active",
            metadata_json={},
        )
        event_2 = Event(
            event_type="rain",
            zone_id=zone.id,
            zone=zone_slug,
            city="delhi",
            started_at=now - timedelta(hours=2),
            severity=Decimal("1.400"),
            raw_value=Decimal("42.0"),
            threshold=Decimal("25.0"),
            disruption_score=Decimal("0.710"),
            event_confidence=Decimal("0.820"),
            api_source="mock_weather",
            status="active",
            metadata_json={},
        )
        event_3 = Event(
            event_type="rain",
            zone_id=zone.id,
            zone=zone_slug,
            city="delhi",
            started_at=now - timedelta(hours=2),
            severity=Decimal("0.500"),
            raw_value=Decimal("19.0"),
            threshold=Decimal("25.0"),
            disruption_score=Decimal("0.310"),
            event_confidence=Decimal("0.440"),
            api_source="mock_weather",
            status="active",
            metadata_json={},
        )
        db.add_all([event_1, event_2, event_3])
        await db.flush()

        claim_1 = Claim(worker_id=worker_1.id, policy_id=policy_1.id, event_id=event_1.id, trigger_type="rain", status="approved")
        claim_2 = Claim(worker_id=worker_2.id, policy_id=policy_2.id, event_id=event_2.id, trigger_type="rain", status="approved")
        claim_3 = Claim(worker_id=worker_3.id, policy_id=policy_3.id, event_id=event_3.id, trigger_type="rain", status="rejected")
        db.add_all([claim_1, claim_2, claim_3])
        await db.flush()

        db.add_all(
            [
                DecisionLog(
                    claim_id=claim_1.id,
                    worker_id=worker_1.id,
                    policy_id=policy_1.id,
                    event_id=event_1.id,
                    lifecycle_stage="claim_created",
                    decision_source="system",
                    system_decision="delayed",
                    resulting_status="delayed",
                    decision_policy_version="decision-policy-v3-wave1",
                    model_versions={"fraud_model": "fraud-model-v2"},
                    feature_snapshot={
                        "decision_inputs": {
                            "trust_score": 0.62,
                            "disruption_score": 0.58,
                            "event_confidence": 0.69,
                            "payout_amount": 86,
                            "fraud_result": {
                                "flags": ["movement", "pre_activity"],
                                "top_factors": [{"label": "movement anomaly"}],
                            },
                        }
                    },
                    output_snapshot={
                        "decision": {
                            "primary_reason": "movement anomaly",
                            "decision_confidence": 0.61,
                        }
                    },
                    context_snapshot={},
                    final_score=0.58,
                ),
                DecisionLog(
                    claim_id=claim_1.id,
                    worker_id=worker_1.id,
                    policy_id=policy_1.id,
                    event_id=event_1.id,
                    lifecycle_stage="manual_resolution",
                    decision_source="admin",
                    system_decision="delayed",
                    resulting_status="approved",
                    final_label="legit",
                    label_source="admin_review",
                    reviewed_by="reviewer_a",
                    decision_policy_version="decision-policy-v3-wave1",
                    model_versions={"fraud_model": "fraud-model-v2"},
                    feature_snapshot={"decision_inputs": {"fraud_result": {"flags": ["movement", "pre_activity"]}}},
                    output_snapshot={"decision": {"primary_reason": "movement anomaly"}},
                    context_snapshot={},
                    final_score=0.58,
                ),
                DecisionLog(
                    claim_id=claim_2.id,
                    worker_id=worker_2.id,
                    policy_id=policy_2.id,
                    event_id=event_2.id,
                    lifecycle_stage="claim_created",
                    decision_source="system",
                    system_decision="approved",
                    resulting_status="approved",
                    decision_policy_version="decision-policy-v3-wave1",
                    model_versions={"fraud_model": "fraud-model-v2"},
                    feature_snapshot={"decision_inputs": {"trust_score": 0.81, "fraud_result": {"flags": []}}},
                    output_snapshot={"decision": {"primary_reason": "signal alignment"}},
                    context_snapshot={},
                    final_score=0.71,
                ),
                DecisionLog(
                    claim_id=claim_3.id,
                    worker_id=worker_3.id,
                    policy_id=policy_3.id,
                    event_id=event_3.id,
                    lifecycle_stage="claim_created",
                    decision_source="system",
                    system_decision="rejected",
                    resulting_status="rejected",
                    decision_policy_version="decision-policy-v2",
                    model_versions={"fraud_model": "fraud-model-v1"},
                    feature_snapshot={"decision_inputs": {"trust_score": 0.15, "fraud_result": {"flags": ["timing"]}}},
                    output_snapshot={"decision": {"primary_reason": "policy timing risk"}},
                    context_snapshot={},
                    final_score=0.31,
                ),
            ]
        )
        await db.commit()

    response = await client.get("/api/analytics/admin-overview", cookies=admin_cookies)
    assert response.status_code == 200
    payload = response.json()

    decision_memory = payload["decision_memory_summary"]
    assert decision_memory["claim_created_rows"] >= baseline_payload["claim_created_rows"] + 3
    assert decision_memory["resolved_labels"] >= baseline_payload["resolved_labels"] + 1
    assert decision_memory["false_review_count"] >= baseline_payload["false_review_count"] + 1
    assert decision_memory["route_counts"]["delayed"] >= baseline_payload["route_counts"]["delayed"] + 1
    assert decision_memory["route_counts"]["approved"] >= baseline_payload["route_counts"]["approved"] + 1
    assert decision_memory["route_counts"]["rejected"] >= baseline_payload["route_counts"]["rejected"] + 1
    assert (
        decision_memory["score_band_distribution"]["review_band_low"]
        >= baseline_payload["score_band_distribution"]["review_band_low"] + 1
    )
    assert (
        decision_memory["score_band_distribution"]["approve_band"]
        >= baseline_payload["score_band_distribution"]["approve_band"] + 1
    )
    assert (
        decision_memory["score_band_distribution"]["reject_band"]
        >= baseline_payload["score_band_distribution"]["reject_band"] + 1
    )
    assert decision_memory["policy_versions"]["decision-policy-v3-wave1"] >= baseline_payload["policy_versions"].get(
        "decision-policy-v3-wave1", 0
    ) + 2
    assert decision_memory["fraud_model_versions"]["fraud-model-v2"] >= baseline_payload["fraud_model_versions"].get(
        "fraud-model-v2", 0
    ) + 2
    assert decision_memory["top_false_review_drivers"]
    assert any(driver["label"] == "movement anomaly" for driver in decision_memory["top_false_review_drivers"])


@pytest.mark.asyncio
async def test_admin_overview_requires_admin_token(client):
    response = await client.get("/api/analytics/admin-overview")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_overview_returns_scheduler_and_forecast(client):
    login_response = await client.post(
        "/api/auth/admin/login",
        json={"username": "admin", "password": "rideshield-test-admin-password"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["token"]

    overview_response = await client.get(
        "/api/analytics/admin-overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert overview_response.status_code == 200
    data = overview_response.json()

    assert "scheduler" in data
    assert "decision_health" in data
    assert "zero_touch_rate" in data["decision_health"]
    assert "review_driver_summary" in data
    assert "false_review_pattern_summary" in data
    assert "policy_replay_summary" in data
    assert "policy_health_summary" in data
    assert "source_comparison_summary" in data
    assert "drivers" in data["review_driver_summary"]
    assert "source" in data["review_driver_summary"]
    assert "insights" in data["review_driver_summary"]
    assert "next_week_forecast" in data
    assert isinstance(data["next_week_forecast"], list)


@pytest.mark.asyncio
async def test_models_endpoint_returns_status(client, admin_cookies):
    response = await client.get("/api/analytics/models", cookies=admin_cookies)
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert "risk_model" in data["models"]
    assert "fraud_model" in data["models"]
    assert "roc_auc" in data["models"]["fraud_model"]
