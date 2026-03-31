"""
Payouts API for history and admin statistics.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.db.models import Claim, Payout, Worker

router = APIRouter(prefix="/api/payouts", tags=["Payouts"])


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def serialize_payout(payout: Payout, worker_name: str | None = None) -> dict:
    return {
        "id": str(payout.id),
        "claim_id": str(payout.claim_id),
        "worker_id": str(payout.worker_id),
        "worker_name": worker_name,
        "amount": float(payout.amount),
        "channel": payout.channel,
        "transaction_id": payout.transaction_id,
        "status": payout.status,
        "initiated_at": payout.initiated_at.isoformat() if payout.initiated_at else None,
        "completed_at": payout.completed_at.isoformat() if payout.completed_at else None,
    }


@router.get("/worker/{worker_id}")
async def get_worker_payouts(worker_id: UUID, days: int = 30, db: AsyncSession = Depends(get_db)):
    worker = (await db.execute(select(Worker).where(Worker.id == worker_id))).scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found.")
    cutoff = utc_now_naive() - timedelta(days=days)
    payouts = (
        await db.execute(
            select(Payout).where(and_(Payout.worker_id == worker_id, Payout.initiated_at >= cutoff)).order_by(desc(Payout.initiated_at))
        )
    ).scalars().all()
    total_amount = sum(float(payout.amount) for payout in payouts)
    week_start = utc_now_naive() - timedelta(days=7)
    this_week = [payout for payout in payouts if payout.initiated_at >= week_start]
    last_payout = serialize_payout(payouts[0], worker.name) if payouts else None
    weekly_history = [
        {
            "date": payout.initiated_at.date().isoformat() if payout.initiated_at else None,
            "amount": float(payout.amount),
            "status": payout.status,
            "transaction_id": payout.transaction_id,
        }
        for payout in this_week
    ]
    return {
        "worker_id": str(worker_id),
        "worker_name": worker.name,
        "period_days": days,
        "total_payouts": len(payouts),
        "total_amount": round(total_amount, 2),
        "this_week_count": len(this_week),
        "this_week_amount": round(sum(float(payout.amount) for payout in this_week), 2),
        "last_payout": last_payout,
        "weekly_history": weekly_history,
        "payouts": [serialize_payout(payout, worker.name) for payout in payouts],
    }


@router.get("/detail/{payout_id}")
async def get_payout_detail(payout_id: UUID, db: AsyncSession = Depends(get_db)):
    payout = (await db.execute(select(Payout).where(Payout.id == payout_id))).scalar_one_or_none()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found.")
    claim = (await db.execute(select(Claim).where(Claim.id == payout.claim_id))).scalar_one_or_none()
    worker = (await db.execute(select(Worker).where(Worker.id == payout.worker_id))).scalar_one_or_none()
    return {
        **serialize_payout(payout, worker.name if worker else None),
        "claim_details": {
            "trigger_type": claim.trigger_type if claim else None,
            "disruption_hours": float(claim.disruption_hours) if claim and claim.disruption_hours else None,
            "final_score": float(claim.final_score) if claim and claim.final_score else None,
        } if claim else None,
    }


@router.get("/stats")
async def get_payout_stats(days: int = 7, db: AsyncSession = Depends(get_db)):
    cutoff = utc_now_naive() - timedelta(days=days)
    payouts = (await db.execute(select(Payout).where(Payout.initiated_at >= cutoff))).scalars().all()
    total_amount = sum(float(payout.amount) for payout in payouts)
    by_channel = {}
    for payout in payouts:
        bucket = by_channel.setdefault(payout.channel, {"count": 0, "amount": 0})
        bucket["count"] += 1
        bucket["amount"] += float(payout.amount)
    recent_payouts = [serialize_payout(payout) for payout in payouts[:10]]
    return {
        "period_days": days,
        "total_payouts": len(payouts),
        "total_amount": round(total_amount, 2),
        "avg_payout": round(total_amount / max(1, len(payouts)), 2),
        "by_channel": by_channel,
        "recent_payouts": recent_payouts,
    }
