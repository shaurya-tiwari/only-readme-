"""
Analytics API for admin dashboard metrics and operational summaries.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.session_auth import require_admin_session
from backend.core.trigger_scheduler import trigger_scheduler
from backend.database import get_db
from backend.db.models import AuditLog, Event, Payout, Policy, Worker, WorkerActivity

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def forecast_band(score: float) -> str:
    if score < 0.3:
        return "low"
    if score < 0.55:
        return "guarded"
    if score < 0.75:
        return "elevated"
    return "critical"


@router.get("/admin-overview")
async def get_admin_overview(
    days: int = 14,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin_session),
):
    now = utc_now_naive()
    cutoff = now - timedelta(days=days)
    recent_activity_cutoff = now - timedelta(hours=6)

    active_policies = (
        await db.execute(
            select(Policy).where(
                Policy.status == "active",
                Policy.activates_at <= now,
                Policy.expires_at >= now,
            )
        )
    ).scalars().all()

    policies_by_plan: dict[str, int] = {}
    policies_by_city: dict[str, int] = {}
    premiums_in_force = 0.0
    for policy in active_policies:
        policies_by_plan[policy.plan_name] = policies_by_plan.get(policy.plan_name, 0) + 1
        worker = (
            await db.execute(select(Worker.city).where(Worker.id == policy.worker_id))
        ).scalar_one_or_none()
        if worker:
            policies_by_city[worker] = policies_by_city.get(worker, 0) + 1
        premiums_in_force += float(policy.weekly_premium or 0)

    payouts_total = (
        await db.execute(
            select(func.coalesce(func.sum(Payout.amount), 0)).where(Payout.initiated_at >= cutoff)
        )
    ).scalar_one()
    payouts_total = float(payouts_total or 0)

    active_workers = (
        await db.execute(select(func.count(Worker.id)).where(Worker.status == "active"))
    ).scalar_one()
    recent_activity_points = (
        await db.execute(
            select(func.count(WorkerActivity.id)).where(WorkerActivity.recorded_at >= recent_activity_cutoff)
        )
    ).scalar_one()
    worker_activity_index = round((recent_activity_points / max(1, active_workers)) * 10, 1)

    recent_duplicate_logs = (
        await db.execute(
            select(AuditLog)
            .where(
                AuditLog.created_at >= cutoff,
                AuditLog.action.in_(["duplicate_detected", "event_extended"]),
            )
            .order_by(AuditLog.created_at.desc())
            .limit(12)
        )
    ).scalars().all()

    duplicate_claim_log = [
        {
            "id": str(log.id),
            "entity_type": log.entity_type,
            "entity_id": str(log.entity_id),
            "action": log.action,
            "details": log.details or {},
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in recent_duplicate_logs
    ]

    active_events_by_city = (
        await db.execute(
            select(Event.city, func.count(Event.id))
            .where(Event.status == "active")
            .group_by(Event.city)
        )
    ).all()
    active_city_counts = {city: count for city, count in active_events_by_city}

    forecast = []
    for city, profile in settings.CITY_RISK_PROFILES.items():
        base = float(profile["base_risk"])
        active_pressure = min(0.25, 0.05 * active_city_counts.get(city, 0))
        projected_score = round(min(1.0, base + active_pressure), 3)
        forecast.append(
            {
                "city": city,
                "base_risk": base,
                "active_incidents": active_city_counts.get(city, 0),
                "projected_risk": projected_score,
                "band": forecast_band(projected_score),
            }
        )

    return {
        "period_days": days,
        "active_policies_total": len(active_policies),
        "active_policies_by_plan": policies_by_plan,
        "active_policies_by_city": policies_by_city,
        "premiums_in_force": round(premiums_in_force, 2),
        "payouts_in_window": round(payouts_total, 2),
        "loss_ratio": round((payouts_total / max(1.0, premiums_in_force)) * 100, 1),
        "worker_activity_index": worker_activity_index,
        "duplicate_claim_log": duplicate_claim_log,
        "scheduler": trigger_scheduler.state,
        "next_week_forecast": forecast,
    }
