"""Decision-memory logging and replay helpers for Phase 3."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.decision_engine import decision_engine
from backend.db.models import Claim, DecisionLog, Event, Policy, Worker
from backend.utils.time import utc_now_naive


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _fraud_model_payload(claim: Claim, fraud_result: dict[str, Any] | None) -> dict[str, Any]:
    decision_breakdown = claim.decision_breakdown if isinstance(claim.decision_breakdown, dict) else {}
    stored_payload = decision_breakdown.get("fraud_model") if isinstance(decision_breakdown, dict) else {}
    stored_payload = stored_payload if isinstance(stored_payload, dict) else {}
    if fraud_result:
        return {
            **stored_payload,
            "rule_fraud_score": fraud_result.get("rule_fraud_score", stored_payload.get("rule_fraud_score")),
            "ml_fraud_score": fraud_result.get("ml_fraud_score", stored_payload.get("ml_fraud_score")),
            "fraud_probability": fraud_result.get("fraud_probability", stored_payload.get("fraud_probability")),
            "confidence": fraud_result.get("ml_confidence", stored_payload.get("confidence")),
            "model_version": fraud_result.get("model_version", stored_payload.get("model_version", "rule-based")),
            "fallback_used": fraud_result.get("fallback_used", stored_payload.get("fallback_used", False)),
            "top_factors": fraud_result.get("top_factors", stored_payload.get("top_factors", [])),
        }
    return stored_payload


def _signal_snapshot_refs(event: Event | None) -> list[str]:
    metadata = event.metadata_json if event and isinstance(event.metadata_json, dict) else {}
    refs = metadata.get("signal_snapshot_ids") or metadata.get("signal_snapshot_refs") or []
    return [str(ref) for ref in refs if ref]


def _resolve_traffic_source(
    *,
    claim: Claim | None = None,
    event: Event | None = None,
    explicit_source: str | None = None,
) -> str:
    if explicit_source:
        return str(explicit_source)
    decision_breakdown = claim.decision_breakdown if claim and isinstance(claim.decision_breakdown, dict) else {}
    if decision_breakdown.get("traffic_source"):
        return str(decision_breakdown["traffic_source"])
    metadata = event.metadata_json if event and isinstance(event.metadata_json, dict) else {}
    if metadata.get("traffic_source"):
        return str(metadata["traffic_source"])
    return "baseline"


def _build_feature_snapshot(
    *,
    claim: Claim,
    worker: Worker | None,
    policy: Policy | None,
    event: Event | None,
    fraud_result: dict[str, Any] | None,
    payout_calc: dict[str, Any] | None,
    feedback_result: dict[str, Any] | None,
) -> dict[str, Any]:
    decision_breakdown = claim.decision_breakdown if isinstance(claim.decision_breakdown, dict) else {}
    inputs = decision_breakdown.get("inputs") if isinstance(decision_breakdown.get("inputs"), dict) else {}
    payout_breakdown = decision_breakdown.get("payout_breakdown") if isinstance(decision_breakdown.get("payout_breakdown"), dict) else {}
    breakdown = decision_breakdown.get("breakdown") if isinstance(decision_breakdown.get("breakdown"), dict) else {}
    rule_metadata = breakdown.get("rule_metadata") if isinstance(breakdown.get("rule_metadata"), dict) else {}

    frozen_fraud_result = {
        "adjusted_fraud_score": _to_float(claim.fraud_score),
        "raw_fraud_score": _to_float(
            (fraud_result or {}).get("raw_fraud_score"),
            _to_float(inputs.get("raw_fraud_score"), _to_float(claim.fraud_score)),
        ),
        "flags": list((fraud_result or {}).get("flags") or inputs.get("fraud_flags") or []),
        "ml_confidence": (fraud_result or {}).get("ml_confidence"),
        "fallback_used": (fraud_result or {}).get("fallback_used", False),
        "model_version": _fraud_model_payload(claim, fraud_result).get("model_version", "rule-based"),
        "fraud_probability": _fraud_model_payload(claim, fraud_result).get("fraud_probability"),
        "top_factors": _fraud_model_payload(claim, fraud_result).get("top_factors", []),
    }

    decision_inputs = {
        "disruption_score": _to_float(claim.disruption_score),
        "event_confidence": _to_float(claim.event_confidence),
        "trust_score": _to_float(claim.trust_score),
        "payout_amount": _to_float(claim.final_payout, _to_float(claim.calculated_payout)),
        "fraud_result": frozen_fraud_result,
        "feedback_result": feedback_result or decision_breakdown.get("review_feedback") or {},
    }

    return _json_safe(
        {
            "decision_inputs": decision_inputs,
            "claim_features": {
                "trigger_type": claim.trigger_type,
                "disruption_hours": claim.disruption_hours,
                "income_per_hour": claim.income_per_hour,
                "peak_multiplier": claim.peak_multiplier,
                "calculated_payout": claim.calculated_payout,
                "final_payout": claim.final_payout,
                "covered_triggers": decision_breakdown.get("covered_triggers") or [],
                "incident_triggers": decision_breakdown.get("incident_triggers") or [],
                "surface": rule_metadata.get("surface"),
                "risk_expectation": rule_metadata.get("risk_expectation"),
            },
            "worker_context": {
                "worker_id": worker.id if worker else claim.worker_id,
                "name": worker.name if worker else None,
                "city": worker.city if worker else None,
                "zone": worker.zone if worker else None,
                "platform": worker.platform if worker else None,
                "risk_score": worker.risk_score if worker else None,
            },
            "policy_context": {
                "policy_id": policy.id if policy else claim.policy_id,
                "plan_name": policy.plan_name if policy else None,
                "weekly_premium": policy.weekly_premium if policy else None,
                "coverage_cap": policy.coverage_cap if policy else None,
            },
            "event_context": {
                "event_id": event.id if event else claim.event_id,
                "event_type": event.event_type if event else claim.trigger_type,
                "city": event.city if event else None,
                "zone": event.zone if event else None,
                "started_at": event.started_at if event else None,
                "api_source": event.api_source if event else None,
                "metadata": event.metadata_json if event else None,
            },
            "payout_breakdown": payout_calc or payout_breakdown or {},
        }
    )


def _build_output_snapshot(
    *,
    claim: Claim,
    payout_result: dict[str, Any] | None = None,
    resolution_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision_breakdown = claim.decision_breakdown if isinstance(claim.decision_breakdown, dict) else {}
    return _json_safe(
        {
            "decision": {
                "decision": decision_breakdown.get("decision", claim.status),
                "explanation": decision_breakdown.get("explanation"),
                "policy_layer": decision_breakdown.get("policy_layer"),
                "rule_id": decision_breakdown.get("rule_id"),
                "decision_confidence": decision_breakdown.get("decision_confidence"),
                "decision_confidence_band": decision_breakdown.get("decision_confidence_band"),
                "primary_reason": decision_breakdown.get("primary_reason"),
                "review_deadline": decision_breakdown.get("review_deadline"),
            },
            "claim_status": claim.status,
            "payout_result": payout_result or {},
            "resolution_payload": resolution_payload or {},
        }
    )


def _build_context_snapshot(
    *,
    claim: Claim,
    event: Event | None,
    traffic_source: str | None = None,
    review_reason: str | None = None,
    reviewed_by: str | None = None,
    label_source: str | None = None,
) -> dict[str, Any]:
    decision_breakdown = claim.decision_breakdown if isinstance(claim.decision_breakdown, dict) else {}
    return _json_safe(
        {
            "source_mode": settings.SIGNAL_SOURCE_MODE,
            "traffic_source": _resolve_traffic_source(claim=claim, event=event, explicit_source=traffic_source),
            "pressure_profile": (event.metadata_json or {}).get("pressure_profile") if event and isinstance(event.metadata_json, dict) else None,
            "decision_memory_enabled": settings.ENABLE_DECISION_MEMORY,
            "review_reason": review_reason,
            "reviewed_by": reviewed_by,
            "label_source": label_source,
            "fraud_model": decision_breakdown.get("fraud_model") or {},
            "review_feedback": decision_breakdown.get("review_feedback") or {},
            "covered_triggers": decision_breakdown.get("covered_triggers") or [],
            "incident_triggers": decision_breakdown.get("incident_triggers") or [],
            "scenario_name": (event.metadata_json or {}).get("scenario_name") if event and isinstance(event.metadata_json, dict) else None,
            "event_metadata": event.metadata_json if event else None,
        }
    )


def _label_for_resolution(status: str, label_source: str | None) -> str | None:
    if not label_source:
        return None
    if status == "approved":
        return "legit"
    if status == "rejected":
        return "fraud"
    return None


async def record_claim_decision(
    *,
    db: AsyncSession,
    claim: Claim,
    worker: Worker | None,
    policy: Policy | None,
    event: Event | None,
    fraud_result: dict[str, Any] | None,
    payout_calc: dict[str, Any] | None,
    feedback_result: dict[str, Any] | None,
    traffic_source: str | None = None,
) -> DecisionLog | None:
    if not settings.ENABLE_DECISION_MEMORY:
        return None

    fraud_model = _fraud_model_payload(claim, fraud_result)
    decision_breakdown = claim.decision_breakdown if isinstance(claim.decision_breakdown, dict) else {}
    entry = DecisionLog(
        claim_id=claim.id,
        worker_id=claim.worker_id,
        policy_id=claim.policy_id,
        event_id=claim.event_id,
        lifecycle_stage="claim_created",
        decision_source="system",
        system_decision=decision_breakdown.get("decision", claim.status),
        resulting_status=claim.status,
        final_label=None,
        label_source=None,
        review_reason=None,
        reviewed_by=None,
        payout_amount=Decimal(str(_to_float(claim.final_payout, _to_float(claim.calculated_payout)))),
        review_wait_hours=Decimal("0.00"),
        fraud_score=Decimal(str(_to_float(claim.fraud_score))),
        trust_score=Decimal(str(_to_float(claim.trust_score))),
        final_score=Decimal(str(_to_float(claim.final_score))),
        decision_confidence=Decimal(str(_to_float(decision_breakdown.get("decision_confidence")))),
        model_versions={
            "fraud_model": fraud_model.get("model_version", "rule-based"),
        },
        decision_policy_version=decision_breakdown.get("decision_policy_version", settings.DECISION_POLICY_VERSION),
        signal_snapshot_refs=_signal_snapshot_refs(event),
        feature_snapshot=_build_feature_snapshot(
            claim=claim,
            worker=worker,
            policy=policy,
            event=event,
            fraud_result=fraud_result,
            payout_calc=payout_calc,
            feedback_result=feedback_result,
        ),
        output_snapshot=_build_output_snapshot(claim=claim),
        context_snapshot=_build_context_snapshot(claim=claim, event=event, traffic_source=traffic_source),
        created_at=utc_now_naive(),
    )
    db.add(entry)
    return entry


async def record_claim_resolution(
    *,
    db: AsyncSession,
    claim: Claim,
    event: Event | None,
    decision_source: str,
    reviewed_by: str | None,
    review_reason: str | None,
    label_source: str | None,
    traffic_source: str | None = None,
    payout_result: dict[str, Any] | None = None,
    resolution_payload: dict[str, Any] | None = None,
) -> DecisionLog | None:
    if not settings.ENABLE_DECISION_MEMORY:
        return None

    decision_breakdown = claim.decision_breakdown if isinstance(claim.decision_breakdown, dict) else {}
    system_decision = decision_breakdown.get("decision", "delayed")
    hours_waiting = 0.0
    if claim.created_at:
        hours_waiting = max(0.0, (utc_now_naive() - claim.created_at).total_seconds() / 3600)
    entry = DecisionLog(
        claim_id=claim.id,
        worker_id=claim.worker_id,
        policy_id=claim.policy_id,
        event_id=claim.event_id,
        lifecycle_stage="manual_resolution" if decision_source == "admin" else "backfill_resolution",
        decision_source=decision_source,
        system_decision=system_decision,
        resulting_status=claim.status,
        final_label=_label_for_resolution(claim.status, label_source),
        label_source=label_source,
        review_reason=review_reason,
        reviewed_by=reviewed_by,
        payout_amount=Decimal(str(_to_float(claim.final_payout, _to_float(claim.calculated_payout)))),
        review_wait_hours=Decimal(str(round(hours_waiting, 2))),
        fraud_score=Decimal(str(_to_float(claim.fraud_score))),
        trust_score=Decimal(str(_to_float(claim.trust_score))),
        final_score=Decimal(str(_to_float(claim.final_score))),
        decision_confidence=Decimal(str(_to_float(decision_breakdown.get("decision_confidence")))),
        model_versions={
            "fraud_model": _fraud_model_payload(claim, None).get("model_version", "rule-based"),
        },
        decision_policy_version=decision_breakdown.get("decision_policy_version", settings.DECISION_POLICY_VERSION),
        signal_snapshot_refs=_signal_snapshot_refs(event),
        feature_snapshot=_build_feature_snapshot(
            claim=claim,
            worker=getattr(claim, "worker", None),
            policy=getattr(claim, "policy", None),
            event=event,
            fraud_result=None,
            payout_calc=None,
            feedback_result=None,
        ),
        output_snapshot=_build_output_snapshot(
            claim=claim,
            payout_result=payout_result,
            resolution_payload=resolution_payload,
        ),
        context_snapshot=_build_context_snapshot(
            claim=claim,
            event=event,
            traffic_source=traffic_source,
            review_reason=review_reason,
            reviewed_by=reviewed_by,
            label_source=label_source,
        ),
        created_at=utc_now_naive(),
    )
    db.add(entry)
    return entry


def serialize_decision_log(entry: DecisionLog) -> dict[str, Any]:
    return _json_safe(
        {
            "id": entry.id,
            "claim_id": entry.claim_id,
            "worker_id": entry.worker_id,
            "policy_id": entry.policy_id,
            "event_id": entry.event_id,
            "lifecycle_stage": entry.lifecycle_stage,
            "decision_source": entry.decision_source,
            "system_decision": entry.system_decision,
            "resulting_status": entry.resulting_status,
            "final_label": entry.final_label,
            "label_source": entry.label_source,
            "review_reason": entry.review_reason,
            "reviewed_by": entry.reviewed_by,
            "payout_amount": entry.payout_amount,
            "review_wait_hours": entry.review_wait_hours,
            "fraud_score": entry.fraud_score,
            "trust_score": entry.trust_score,
            "final_score": entry.final_score,
            "decision_confidence": entry.decision_confidence,
            "model_versions": entry.model_versions,
            "decision_policy_version": entry.decision_policy_version,
            "signal_snapshot_refs": entry.signal_snapshot_refs,
            "feature_snapshot": entry.feature_snapshot,
            "output_snapshot": entry.output_snapshot,
            "context_snapshot": entry.context_snapshot,
            "created_at": entry.created_at,
        }
    )


def replay_decision_log(entry: DecisionLog) -> dict[str, Any]:
    feature_snapshot = entry.feature_snapshot or {}
    decision_inputs = feature_snapshot.get("decision_inputs") or {}
    fraud_result = decision_inputs.get("fraud_result") or {}
    return decision_engine.decide(
        disruption_score=_to_float(decision_inputs.get("disruption_score")),
        event_confidence=_to_float(decision_inputs.get("event_confidence")),
        fraud_result={
            "adjusted_fraud_score": _to_float(fraud_result.get("adjusted_fraud_score")),
            "raw_fraud_score": _to_float(fraud_result.get("raw_fraud_score")),
            "flags": list(fraud_result.get("flags") or []),
            "ml_confidence": fraud_result.get("ml_confidence"),
            "fallback_used": fraud_result.get("fallback_used", False),
            "model_version": fraud_result.get("model_version"),
            "fraud_probability": fraud_result.get("fraud_probability"),
            "top_factors": fraud_result.get("top_factors", []),
        },
        trust_score=_to_float(decision_inputs.get("trust_score")),
        feedback_result=decision_inputs.get("feedback_result") or {},
        payout_amount=_to_float(decision_inputs.get("payout_amount")),
    )


async def export_decision_logs(
    db: AsyncSession,
    *,
    resolved_only: bool = False,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    query = select(DecisionLog).order_by(DecisionLog.created_at.asc())
    if resolved_only:
        query = query.where(DecisionLog.final_label.is_not(None))
    if limit:
        query = query.limit(limit)
    rows = (await db.execute(query)).scalars().all()
    return [serialize_decision_log(row) for row in rows]


async def fetch_decision_log_by_claim(
    db: AsyncSession,
    claim_id: UUID,
) -> list[DecisionLog]:
    return (
        await db.execute(
            select(DecisionLog)
            .where(DecisionLog.claim_id == claim_id)
            .order_by(DecisionLog.created_at.asc())
        )
    ).scalars().all()


def default_export_path() -> Path:
    return Path("logs") / "decision_memory"
