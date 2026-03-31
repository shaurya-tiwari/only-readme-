"""
Claims API for history, review queue, and admin resolution.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.payout_executor import payout_executor
from backend.core.session_auth import require_admin_session
from backend.database import get_db
from backend.db.models import AuditLog, Claim, Event, TrustScore, Worker
from backend.schemas.claim import ClaimResolveRequest

router = APIRouter(prefix="/api/claims", tags=["Claims"])


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
        "decision_breakdown": claim.decision_breakdown,
        "status": claim.status,
        "rejection_reason": claim.rejection_reason,
        "review_deadline": claim.review_deadline.isoformat() if claim.review_deadline else None,
        "reviewed_by": claim.reviewed_by,
        "reviewed_at": claim.reviewed_at.isoformat() if claim.reviewed_at else None,
        "created_at": claim.created_at.isoformat() if claim.created_at else None,
        "payout_info": payout_info,
    }


@router.get("/worker/{worker_id}")
async def get_worker_claims(worker_id: UUID, status_filter: Optional[str] = None, days: int = 30, db: AsyncSession = Depends(get_db)):
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
async def get_claim_detail(claim_id: UUID, db: AsyncSession = Depends(get_db)):
    claim = (
        await db.execute(
            select(Claim)
            .options(selectinload(Claim.payout), selectinload(Claim.worker), selectinload(Claim.event))
            .where(Claim.id == claim_id)
        )
    ).scalar_one_or_none()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found.")

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
    claims_data = []
    overdue_count = 0
    for claim in claims:
        is_overdue = bool(claim.review_deadline and claim.review_deadline < now)
        overdue_count += 1 if is_overdue else 0
        claims_data.append(
            {
                **serialize_claim_summary(claim),
                "zone": claim.event.zone if claim.event else None,
                "event_type": claim.event.event_type if claim.event else None,
                "is_overdue": is_overdue,
            }
        )
    return {"total_pending": len(claims_data), "overdue_count": overdue_count, "claims": claims_data}


@router.post("/resolve/{claim_id}")
async def resolve_delayed_claim(
    claim_id: UUID,
    request: ClaimResolveRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin_session),
):
    claim = (
        await db.execute(select(Claim).options(selectinload(Claim.worker), selectinload(Claim.policy)).where(Claim.id == claim_id))
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

    if request.decision == "approve":
        claim.status = "approved"
        payout_result = await payout_executor.execute(db, claim, claim.worker, claim.policy.plan_name if claim.policy else "smart_protect", float(claim.calculated_payout or 0))
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
async def get_claim_stats(days: int = 7, city: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    cutoff = utc_now_naive() - timedelta(days=days)
    query = select(Claim).where(Claim.created_at >= cutoff)
    if city:
        query = query.join(Event).where(Event.city == city.lower())
    claims = (await db.execute(query)).scalars().all()
    total = len(claims)
    approved = sum(1 for claim in claims if claim.status == "approved")
    delayed = sum(1 for claim in claims if claim.status == "delayed")
    rejected = sum(1 for claim in claims if claim.status == "rejected")
    fraud_flagged = sum(1 for claim in claims if float(claim.fraud_score or 0) >= 0.4)
    total_payout = sum(float(claim.final_payout or 0) for claim in claims if claim.status == "approved")
    avg_final_score = round(sum(float(claim.final_score or 0) for claim in claims) / max(1, total), 3)
    avg_fraud_score = round(sum(float(claim.fraud_score or 0) for claim in claims) / max(1, total), 3)
    by_trigger = {}
    for claim in claims:
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
        "fraud_rate": round(fraud_flagged / max(1, total) * 100, 1),
        "avg_final_score": avg_final_score,
        "avg_fraud_score": avg_fraud_score,
        "by_trigger": by_trigger,
        "total_payout": round(total_payout, 2),
    }
