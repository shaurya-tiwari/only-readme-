"""Claims API for history, review queue, and admin resolution."""

from datetime import timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.payout_executor import payout_executor
from backend.core.decision_memory import record_claim_resolution
from backend.core.session_auth import ensure_worker_access, require_admin_session, require_authenticated_session
from backend.database import get_db
from backend.db.models import AuditLog, Claim, Event, TrustScore, Worker
from backend.schemas.claim import ClaimResolveRequest
from backend.utils.time import utc_now_naive

router = APIRouter(prefix="/api/claims", tags=["Claims"])
REVIEW_QUEUE_HIGH_LOAD_THRESHOLD = 4


def _coerce_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _humanize_label(value: str | None) -> str:
    if not value:
        return "system signal"
    return " ".join(part.capitalize() for part in str(value).split("_") if part)


def _extract_fraud_model_payload(claim: Claim) -> dict:
    if not isinstance(claim.decision_breakdown, dict):
        return {}
    fraud_model = claim.decision_breakdown.get("fraud_model")
    return fraud_model if isinstance(fraud_model, dict) else {}


def _is_zero_touch_approved(claim: Claim) -> bool:
    return claim.status == "approved" and not claim.reviewed_by


def _build_review_context(claim: Claim, now) -> dict:
    decision_breakdown = claim.decision_breakdown if isinstance(claim.decision_breakdown, dict) else {}
    decision_components = decision_breakdown.get("breakdown") if isinstance(decision_breakdown.get("breakdown"), dict) else {}
    uncertainty = decision_breakdown.get("uncertainty") if isinstance(decision_breakdown.get("uncertainty"), dict) else {}
    fraud_model = _extract_fraud_model_payload(claim)
    fraud_probability = _coerce_float(fraud_model.get("fraud_probability"), _coerce_float(claim.fraud_score))
    payout_amount = _coerce_float(claim.final_payout, _coerce_float(claim.calculated_payout))
    payout_risk = round(payout_amount * max(0.0, min(1.0, fraud_probability)), 2)
    hours_waiting = round(max(0.0, (now - claim.created_at).total_seconds() / 3600), 1) if claim.created_at else 0.0
    hours_until_deadline = (
        round((claim.review_deadline - now).total_seconds() / 3600, 1)
        if claim.review_deadline
        else None
    )
    overdue_hours = (
        round(max(0.0, (now - claim.review_deadline).total_seconds() / 3600), 1)
        if claim.review_deadline
        else 0.0
    )
    is_overdue = bool(claim.review_deadline and claim.review_deadline < now)
    deadline_pressure = 0.35
    if hours_until_deadline is not None:
        deadline_pressure = 1.0 if is_overdue else max(0.0, 1 - min(max(hours_until_deadline, 0.0), 24.0) / 24.0)

    urgency_score = round(
        min(
            1.0,
            max(
                0.0,
                (0.45 * deadline_pressure)
                + (0.30 * min(payout_risk / 120.0, 1.0))
                + (0.15 * max(0.0, min(1.0, fraud_probability)))
                + (0.10 * min(hours_waiting / 24.0, 1.0))
                + (0.15 if is_overdue else 0.0),
            ),
        ),
        3,
    )

    if is_overdue or urgency_score >= 0.72:
        urgency_band = "critical"
    elif urgency_score >= 0.48:
        urgency_band = "warning"
    else:
        urgency_band = "steady"

    event_confidence = _coerce_float(claim.event_confidence)
    trust_score = _coerce_float(claim.trust_score, 0.5)
    stored_decision_confidence = decision_breakdown.get("decision_confidence")
    if stored_decision_confidence is None:
        decision_confidence = round(
            min(
                1.0,
                max(
                    0.0,
                    (0.55 * event_confidence)
                    + (0.25 * trust_score)
                    + (0.20 * (1 - max(0.0, min(1.0, fraud_probability)))),
                ),
            ),
            3,
        )
    else:
        decision_confidence = _coerce_float(stored_decision_confidence)
    decision_confidence_band = decision_breakdown.get("decision_confidence_band")
    if not decision_confidence_band:
        if decision_confidence >= 0.72:
            decision_confidence_band = "high"
        elif decision_confidence >= 0.48:
            decision_confidence_band = "moderate"
        else:
            decision_confidence_band = "low"

    top_factors = fraud_model.get("top_factors") if isinstance(fraud_model.get("top_factors"), list) else []
    primary_factor = decision_breakdown.get("primary_reason") or (top_factors[0]["label"] if top_factors else None)
    secondary_factors = [factor.get("label") for factor in top_factors[1:3] if factor.get("label")]
    fraud_flags = []
    if isinstance(claim.decision_breakdown, dict):
        inputs = claim.decision_breakdown.get("inputs")
        if isinstance(inputs, dict) and isinstance(inputs.get("fraud_flags"), list):
            fraud_flags = [_humanize_label(flag) for flag in inputs["fraud_flags"][:3]]
    if not primary_factor and fraud_flags:
        primary_factor = fraud_flags[0]
        secondary_factors = fraud_flags[1:3]

    stored_priority_reason = decision_breakdown.get("priority_reason")
    if stored_priority_reason:
        priority_reason = stored_priority_reason
    elif is_overdue:
        priority_reason = "Overdue manual review"
    elif hours_until_deadline is not None and hours_until_deadline <= 6:
        priority_reason = "SLA breach risk"
    elif payout_risk >= 120:
        priority_reason = "High payout exposure"
    elif fraud_probability >= 0.35:
        priority_reason = "Elevated fraud pressure"
    else:
        priority_reason = "Resolve before backlog grows"

    return {
        "fraud_probability": fraud_probability,
        "payout_risk": payout_risk,
        "hours_waiting": hours_waiting,
        "hours_until_deadline": hours_until_deadline,
        "overdue_hours": overdue_hours,
        "urgency_score": urgency_score,
        "urgency_band": urgency_band,
        "priority_reason": priority_reason,
        "decision_confidence": decision_confidence,
        "decision_confidence_band": decision_confidence_band,
        "primary_factor": primary_factor,
        "secondary_factors": secondary_factors,
        "pattern_taxonomy": decision_components.get("pattern_taxonomy"),
        "uncertainty_case": uncertainty.get("case") or decision_components.get("uncertainty_case"),
    }


def serialize_claim_summary(claim: Claim) -> dict:
    payout_info = None
    if claim.payout:
        payout_info = {
            "id": str(claim.payout.id),
            "amount": float(claim.payout.amount),
            "channel": claim.payout.channel,
            "transaction_id": claim.payout.transaction_id,
            "status": claim.payout.status,
            "initiated_at": claim.payout.initiated_at.isoformat() if claim.payout.initiated_at else None,
            "completed_at": claim.payout.completed_at.isoformat() if claim.payout.completed_at else None,
        }

    fraud_model = None
    payout_breakdown = None
    decision_confidence = None
    decision_confidence_band = None
    if isinstance(claim.decision_breakdown, dict):
        fraud_model = claim.decision_breakdown.get("fraud_model")
        payout_breakdown = claim.decision_breakdown.get("payout_breakdown")
        decision_confidence = claim.decision_breakdown.get("decision_confidence")
        decision_confidence_band = claim.decision_breakdown.get("decision_confidence_band")

    return {
        "id": str(claim.id),
        "worker_id": str(claim.worker_id),
        "worker_name": claim.worker.name if getattr(claim, "worker", None) else None,
        "policy_id": str(claim.policy_id),
        "event_id": str(claim.event_id),
        "trigger_type": claim.trigger_type,
        "disruption_hours": float(claim.disruption_hours) if claim.disruption_hours is not None else None,
        "income_per_hour": float(claim.income_per_hour) if claim.income_per_hour is not None else None,
        "peak_multiplier": float(claim.peak_multiplier) if claim.peak_multiplier is not None else None,
        "calculated_payout": float(claim.calculated_payout) if claim.calculated_payout is not None else None,
        "final_payout": float(claim.final_payout) if claim.final_payout is not None else None,
        "disruption_score": float(claim.disruption_score) if claim.disruption_score is not None else None,
        "event_confidence": float(claim.event_confidence) if claim.event_confidence is not None else None,
        "fraud_score": float(claim.fraud_score) if claim.fraud_score is not None else None,
        "trust_score": float(claim.trust_score) if claim.trust_score is not None else None,
        "final_score": float(claim.final_score) if claim.final_score is not None else None,
        "decision_confidence": _coerce_float(decision_confidence) if decision_confidence is not None else None,
        "decision_confidence_band": decision_confidence_band,
        "decision_breakdown": claim.decision_breakdown,
        "fraud_model": fraud_model,
        "payout_breakdown": payout_breakdown,
        "status": claim.status,
        "rejection_reason": claim.rejection_reason,
        "review_deadline": claim.review_deadline.isoformat() if claim.review_deadline else None,
        "reviewed_by": claim.reviewed_by,
        "reviewed_at": claim.reviewed_at.isoformat() if claim.reviewed_at else None,
        "created_at": claim.created_at.isoformat() if claim.created_at else None,
        "payout_info": payout_info,
    }


@router.get("/worker/{worker_id}")
async def get_worker_claims(
    worker_id: UUID,
    status_filter: Optional[str] = None,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    session: dict = Depends(require_authenticated_session),
):
    ensure_worker_access(session, worker_id)
    worker = (await db.execute(select(Worker).where(Worker.id == worker_id))).scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found.")

    cutoff = utc_now_naive() - timedelta(days=days)
    query = select(Claim).options(selectinload(Claim.payout)).where(and_(Claim.worker_id == worker_id, Claim.created_at >= cutoff))
    if status_filter:
        query = query.where(Claim.status == status_filter)
    claims = (await db.execute(query.order_by(desc(Claim.created_at)))).scalars().all()

    claims_data = []
    total_payout = 0.0
    approved_count = delayed_count = rejected_count = 0
    for claim in claims:
        if claim.status == "approved":
            approved_count += 1
            total_payout += float(claim.final_payout or 0)
        elif claim.status == "delayed":
            delayed_count += 1
        elif claim.status == "rejected":
            rejected_count += 1
        claims_data.append(serialize_claim_summary(claim))

    return {
        "worker_id": str(worker_id),
        "worker_name": worker.name,
        "period_days": days,
        "total": len(claims_data),
        "approved": approved_count,
        "delayed": delayed_count,
        "rejected": rejected_count,
        "total_payout": round(total_payout, 2),
        "claims": claims_data,
    }


@router.get("/detail/{claim_id}")
async def get_claim_detail(
    claim_id: UUID,
    db: AsyncSession = Depends(get_db),
    session: dict = Depends(require_authenticated_session),
):
    claim = (
        await db.execute(
            select(Claim)
            .options(selectinload(Claim.payout), selectinload(Claim.worker), selectinload(Claim.event))
            .where(Claim.id == claim_id)
        )
    ).scalar_one_or_none()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found.")
    ensure_worker_access(session, claim.worker_id)

    event_info = None
    if claim.event:
        event_info = {
            "id": str(claim.event.id),
            "event_type": claim.event.event_type,
            "zone": claim.event.zone,
            "city": claim.event.city,
            "raw_value": float(claim.event.raw_value) if claim.event.raw_value else None,
            "threshold": float(claim.event.threshold) if claim.event.threshold else None,
            "severity": float(claim.event.severity) if claim.event.severity else None,
            "started_at": claim.event.started_at.isoformat() if claim.event.started_at else None,
        }

    return {
        **serialize_claim_summary(claim),
        "event": event_info,
        "payout": serialize_claim_summary(claim)["payout_info"],
    }


@router.get("/review-queue")
async def get_review_queue(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin_session),
):
    claims = (
        await db.execute(
            select(Claim).options(selectinload(Claim.worker), selectinload(Claim.event)).where(Claim.status == "delayed").order_by(Claim.review_deadline.asc())
        )
    ).scalars().all()
    now = utc_now_naive()
    review_candidates = []
    overdue_count = 0
    for claim in claims:
        is_overdue = bool(claim.review_deadline and claim.review_deadline < now)
        overdue_count += 1 if is_overdue else 0
        review_context = _build_review_context(claim, now)
        review_candidates.append(
            (
                review_context["urgency_score"],
                claim.review_deadline or now + timedelta(days=7),
                {
                    **serialize_claim_summary(claim),
                    "city": claim.event.city if claim.event else None,
                    "zone": claim.event.zone if claim.event else None,
                    "event_type": claim.event.event_type if claim.event else None,
                    "is_overdue": is_overdue,
                    **review_context,
                },
            )
        )
    claims_data = [
        payload
        for _, _, payload in sorted(
            review_candidates,
            key=lambda item: (-item[0], item[1], item[2]["created_at"] or ""),
        )
    ]
    total_pending = len(claims_data)
    high_load_mode = total_pending >= REVIEW_QUEUE_HIGH_LOAD_THRESHOLD
    return {
        "total_pending": total_pending,
        "overdue_count": overdue_count,
        "high_load_mode": high_load_mode,
        "high_load_threshold": REVIEW_QUEUE_HIGH_LOAD_THRESHOLD,
        "claims": claims_data,
    }


@router.post("/resolve/{claim_id}")
async def resolve_delayed_claim(
    claim_id: UUID,
    request: ClaimResolveRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin_session),
):
    claim = (
        await db.execute(
            select(Claim)
            .options(selectinload(Claim.worker), selectinload(Claim.policy), selectinload(Claim.event))
            .where(Claim.id == claim_id)
        )
    ).scalar_one_or_none()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found.")
    if claim.status != "delayed":
        raise HTTPException(status_code=400, detail=f"Claim is '{claim.status}', not 'delayed'.")

    now = utc_now_naive()
    claim.reviewed_by = request.reviewed_by
    claim.reviewed_at = now
    claim.updated_at = now
    payout_result = None

    previous_status = claim.status
    if request.decision == "approve":
        claim.status = "approved"
        payout_amount = claim.final_payout
        if payout_amount is None:
            payout_amount = claim.calculated_payout or 0
        try:
            payout_result = await payout_executor.execute(
                db,
                claim,
                claim.worker,
                claim.policy.plan_name if claim.policy else "smart_protect",
                float(payout_amount),
            )
        except Exception as exc:
            payout_result = await payout_executor.record_failed(
                db,
                claim,
                claim.worker,
                claim.policy.plan_name if claim.policy else "smart_protect",
                float(payout_amount),
                str(exc),
            )
        trust = (await db.execute(select(TrustScore).where(TrustScore.worker_id == claim.worker_id))).scalar_one_or_none()
        if trust:
            trust.approved_claims = (trust.approved_claims or 0) + 1
            trust.score = Decimal(str(min(1.0, float(trust.score) + 0.02)))
            trust.last_updated = now
    else:
        claim.status = "rejected"
        claim.rejection_reason = request.reason or "Manually rejected by admin after review."
        claim.final_payout = Decimal("0")

    db.add(
        AuditLog(
            entity_type="claim",
            entity_id=claim.id,
            action=f"resolved_{request.decision}",
            details={"reviewed_by": request.reviewed_by, "decision": request.decision, "reason": request.reason},
        )
    )
    await record_claim_resolution(
        db=db,
        claim=claim,
        event=claim.event,
        decision_source="admin",
        reviewed_by=request.reviewed_by,
        review_reason=request.reason,
        label_source="admin_review",
        payout_result=payout_result,
        resolution_payload={
            "previous_status": previous_status,
            "resolved_by": request.reviewed_by,
            "decision": request.decision,
            "reason": request.reason,
            "within_sla": now <= claim.review_deadline if claim.review_deadline else None,
        },
    )
    await db.flush()
    within_sla = None
    if claim.review_deadline:
        within_sla = now <= claim.review_deadline
    return {
        "claim_id": str(claim.id),
        "decision": request.decision,
        "status": claim.status,
        "reviewed_by": request.reviewed_by,
        "reviewed_at": now.isoformat(),
        "within_sla": within_sla,
        "payout": payout_result,
        "claim": serialize_claim_summary(claim),
    }


@router.get("/stats")
async def get_claim_stats(
    days: int = 7,
    city: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin_session),
):
    cutoff = utc_now_naive() - timedelta(days=days)
    query = select(Claim).where(Claim.created_at >= cutoff)
    if city:
        query = query.join(Event).where(Event.city == city.lower())
    claims = (await db.execute(query)).scalars().all()
    total = len(claims)
    approved = sum(1 for claim in claims if claim.status == "approved")
    delayed = sum(1 for claim in claims if claim.status == "delayed")
    rejected = sum(1 for claim in claims if claim.status == "rejected")
    auto_approved = 0
    fraud_flagged = sum(1 for claim in claims if float(claim.fraud_score or 0) >= 0.4)
    total_payout = sum(float(claim.final_payout or 0) for claim in claims if claim.status == "approved")
    avg_final_score = round(sum(float(claim.final_score or 0) for claim in claims) / max(1, total), 3)
    avg_fraud_score = round(sum(float(claim.fraud_score or 0) for claim in claims) / max(1, total), 3)
    by_trigger = {}
    for claim in claims:
        if _is_zero_touch_approved(claim):
            auto_approved += 1
        incident_triggers = (claim.decision_breakdown or {}).get("incident_triggers") or [claim.trigger_type]
        for trigger in incident_triggers:
            by_trigger[trigger] = by_trigger.get(trigger, 0) + 1
    return {
        "period_days": days,
        "total_claims": total,
        "approved": approved,
        "delayed": delayed,
        "rejected": rejected,
        "approval_rate": round(approved / max(1, total) * 100, 1),
        "delayed_rate": round(delayed / max(1, total) * 100, 1),
        "review_rate": round(delayed / max(1, total) * 100, 1),
        "auto_approved": auto_approved,
        "auto_approval_rate": round(auto_approved / max(1, total) * 100, 1),
        "zero_touch_approvals": auto_approved,
        "zero_touch_rate": round(auto_approved / max(1, total) * 100, 1),
        "high_load_mode": delayed >= REVIEW_QUEUE_HIGH_LOAD_THRESHOLD,
        "high_load_threshold": REVIEW_QUEUE_HIGH_LOAD_THRESHOLD,
        "fraud_rate": round(fraud_flagged / max(1, total) * 100, 1),
        "avg_final_score": avg_final_score,
        "avg_fraud_score": avg_fraud_score,
        "by_trigger": by_trigger,
        "total_payout": round(total_payout, 2),
    }
