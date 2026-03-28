"""
Policies API
Handles plan listing, policy purchase, and policy management.

Endpoints:
    GET  /api/policies/plans/{worker_id}    -> List plans with premiums for worker
    POST /api/policies/create               -> Purchase a weekly plan
    GET  /api/policies/active/{worker_id}   -> Get active policy
    GET  /api/policies/history/{worker_id}  -> Get policy history
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.core.premium_calculator import premium_calculator
from backend.database import get_db
from backend.db.models import AuditLog, Policy, Worker
from backend.schemas.policy import (
    PlanListResponse,
    PolicyCreateRequest,
    PolicyCreateResponse,
    PolicyHistoryResponse,
    PolicyResponse,
    PremiumCalculation,
)

router = APIRouter(prefix="/api/policies", tags=["Policies"])


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/plans/{worker_id}")
async def list_plans(
    worker_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    List all available plans with premiums calculated for a specific worker.
    Uses the worker's current risk score.
    """

    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found.",
        )

    risk_score = float(worker.risk_score) if worker.risk_score else 0.50
    plans, recommended = premium_calculator.calculate_all_plans(risk_score)

    return {
        "worker_id": str(worker.id),
        "worker_name": worker.name,
        "city": worker.city,
        "risk_score": risk_score,
        "plans": plans,
        "recommended": recommended,
        "activation_delay_hours": settings.ACTIVATION_DELAY_HOURS,
        "policy_duration_days": settings.POLICY_DURATION_DAYS,
        "note": f"All plans activate {settings.ACTIVATION_DELAY_HOURS} hours "
        f"after purchase and last {settings.POLICY_DURATION_DAYS} days.",
    }


@router.post("/create", response_model=PolicyCreateResponse, status_code=201)
async def create_policy(
    request: PolicyCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Purchase a weekly insurance plan.

    Steps:
    1. Validate worker exists and is active
    2. Check for existing active policy (one at a time)
    3. Calculate premium based on current risk score
    4. Create policy with 24-hour activation delay
    5. Log in audit trail
    """

    result = await db.execute(
        select(Worker)
        .options(selectinload(Worker.policies))
        .where(Worker.id == request.worker_id)
    )
    worker = result.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found.",
        )

    if worker.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Worker account is {worker.status}. Cannot purchase a plan.",
        )

    if not worker.consent_given:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Worker must give consent before purchasing a plan.",
        )

    plan_def = settings.PLAN_DEFINITIONS.get(request.plan_name)
    if not plan_def:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown plan: {request.plan_name}. "
            f"Available plans: {', '.join(settings.PLAN_DEFINITIONS.keys())}",
        )

    now = utc_now_naive()
    for existing_policy in worker.policies:
        if existing_policy.status in ("active", "pending") and existing_policy.expires_at > now:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Worker already has an active/pending policy "
                f"({existing_policy.plan_display_name}) "
                f"expiring at {existing_policy.expires_at.isoformat()}. "
                f"Wait for it to expire or cancel it first.",
            )

    risk_score = float(worker.risk_score) if worker.risk_score else 0.50

    previous_premium = None
    expired_policies = [
        p for p in worker.policies if p.status == "expired" and p.plan_name == request.plan_name
    ]
    if expired_policies:
        latest = max(expired_policies, key=lambda p: p.expires_at)
        previous_premium = float(latest.weekly_premium)

    premium_result = premium_calculator.calculate(
        plan_name=request.plan_name,
        risk_score=risk_score,
        previous_premium=previous_premium,
    )

    purchased_at = utc_now_naive()
    activates_at = purchased_at + timedelta(hours=settings.ACTIVATION_DELAY_HOURS)
    expires_at = activates_at + timedelta(days=settings.POLICY_DURATION_DAYS)

    policy = Policy(
        worker_id=worker.id,
        plan_name=request.plan_name,
        plan_display_name=plan_def["display_name"],
        base_price=plan_def["base_price"],
        plan_factor=plan_def["plan_factor"],
        risk_score_at_purchase=risk_score,
        weekly_premium=premium_result["final_premium"],
        coverage_cap=plan_def["coverage_cap"],
        triggers_covered=plan_def["triggers_covered"],
        status="pending",
        purchased_at=purchased_at,
        activates_at=activates_at,
        expires_at=expires_at,
    )
    db.add(policy)
    await db.flush()

    audit = AuditLog(
        entity_type="policy",
        entity_id=policy.id,
        action="purchased",
        details={
            "plan_name": request.plan_name,
            "worker_id": str(worker.id),
            "risk_score": risk_score,
            "premium": premium_result["final_premium"],
            "coverage_cap": plan_def["coverage_cap"],
            "activates_at": activates_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "previous_premium": previous_premium,
            "premium_capped": premium_result["premium_capped"],
        },
    )
    db.add(audit)

    premium_calc = PremiumCalculation(
        base_price=premium_result["base_price"],
        plan_factor=premium_result["plan_factor"],
        risk_score=premium_result["risk_score"],
        raw_premium=premium_result["raw_premium"],
        final_premium=premium_result["final_premium"],
        formula=premium_result["formula"],
    )

    policy_response = PolicyResponse(
        id=policy.id,
        worker_id=policy.worker_id,
        plan_name=policy.plan_name,
        plan_display_name=policy.plan_display_name,
        weekly_premium=float(policy.weekly_premium),
        coverage_cap=float(policy.coverage_cap),
        triggers_covered=policy.triggers_covered,
        status=policy.status,
        purchased_at=policy.purchased_at,
        activates_at=policy.activates_at,
        expires_at=policy.expires_at,
        is_active=False,
        premium_calculation=premium_calc,
    )

    await db.commit()

    return PolicyCreateResponse(
        policy=policy_response,
        premium_calculation=premium_calc,
        message=(
            f"Plan '{plan_def['display_name']}' purchased successfully for "
            f"INR {premium_result['final_premium']}/week."
        ),
        activation_note=(
            f"Your coverage will activate at {activates_at.strftime('%B %d, %Y %I:%M %p')} "
            f"({settings.ACTIVATION_DELAY_HOURS} hours from now). "
            f"This waiting period prevents adverse selection."
        ),
    )


@router.get("/active/{worker_id}")
async def get_active_policy(
    worker_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the currently active policy for a worker."""

    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found.",
        )

    now = utc_now_naive()

    policy_result = await db.execute(
        select(Policy).where(
            and_(
                Policy.worker_id == worker_id,
                Policy.status == "active",
                Policy.activates_at <= now,
                Policy.expires_at >= now,
            )
        )
    )
    policy = policy_result.scalar_one_or_none()

    pending_result = await db.execute(
        select(Policy).where(
            and_(
                Policy.worker_id == worker_id,
                Policy.status == "pending",
                Policy.activates_at > now,
            )
        )
    )
    pending = pending_result.scalar_one_or_none()

    activate_result = await db.execute(
        select(Policy).where(
            and_(
                Policy.worker_id == worker_id,
                Policy.status == "pending",
                Policy.activates_at <= now,
                Policy.expires_at >= now,
            )
        )
    )
    to_activate = activate_result.scalar_one_or_none()

    if to_activate:
        to_activate.status = "active"
        policy = to_activate
        await db.flush()
        await db.commit()

    response = {
        "worker_id": str(worker_id),
        "has_active_policy": policy is not None,
        "active_policy": None,
        "pending_policy": None,
    }

    if policy:
        response["active_policy"] = {
            "id": str(policy.id),
            "plan_name": policy.plan_name,
            "display_name": policy.plan_display_name,
            "weekly_premium": float(policy.weekly_premium),
            "coverage_cap": float(policy.coverage_cap),
            "triggers_covered": policy.triggers_covered,
            "status": policy.status,
            "activates_at": policy.activates_at.isoformat(),
            "expires_at": policy.expires_at.isoformat(),
            "hours_remaining": max(0, (policy.expires_at - now).total_seconds() / 3600),
        }

    if pending:
        response["pending_policy"] = {
            "id": str(pending.id),
            "plan_name": pending.plan_name,
            "display_name": pending.plan_display_name,
            "activates_at": pending.activates_at.isoformat(),
            "hours_until_activation": max(
                0, (pending.activates_at - now).total_seconds() / 3600
            ),
        }

    return response


@router.get("/history/{worker_id}")
async def get_policy_history(
    worker_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get complete policy history for a worker."""

    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found.",
        )

    policies_result = await db.execute(
        select(Policy).where(Policy.worker_id == worker_id).order_by(Policy.purchased_at.desc())
    )
    policies = policies_result.scalars().all()

    now = utc_now_naive()
    for policy in policies:
        if policy.status in ("active", "pending") and policy.expires_at < now:
            policy.status = "expired"

    await db.flush()
    await db.commit()

    total_premiums = sum(float(policy.weekly_premium) for policy in policies)
    policy_list = [
        PolicyResponse(
            id=policy.id,
            worker_id=policy.worker_id,
            plan_name=policy.plan_name,
            plan_display_name=policy.plan_display_name,
            weekly_premium=float(policy.weekly_premium),
            coverage_cap=float(policy.coverage_cap),
            triggers_covered=policy.triggers_covered,
            status=policy.status,
            purchased_at=policy.purchased_at,
            activates_at=policy.activates_at,
            expires_at=policy.expires_at,
            is_active=policy.status == "active" and policy.activates_at <= now <= policy.expires_at,
        )
        for policy in policies
    ]

    return PolicyHistoryResponse(
        worker_id=worker_id,
        total_policies=len(policies),
        total_premiums_paid=total_premiums,
        policies=policy_list,
    )


@router.post("/expire-old")
async def expire_old_policies(
    db: AsyncSession = Depends(get_db),
):
    """
    Admin utility: expire all policies past their expiry date.
    In production, this would be a scheduled job.
    """
    now = utc_now_naive()

    result = await db.execute(
        select(Policy).where(
            and_(
                Policy.status.in_(["active", "pending"]),
                Policy.expires_at < now,
            )
        )
    )
    expired = result.scalars().all()

    count = 0
    for policy in expired:
        policy.status = "expired"
        count += 1

    await db.flush()
    await db.commit()

    return {
        "message": f"Expired {count} policies.",
        "expired_count": count,
    }


@router.post("/activate-pending")
async def activate_pending_policies(
    db: AsyncSession = Depends(get_db),
):
    """
    Admin utility: activate all pending policies past their activation time.
    In production, this would be a scheduled job.
    """
    now = utc_now_naive()

    result = await db.execute(
        select(Policy).where(
            and_(
                Policy.status == "pending",
                Policy.activates_at <= now,
                Policy.expires_at > now,
            )
        )
    )
    to_activate = result.scalars().all()

    count = 0
    for policy in to_activate:
        policy.status = "active"
        count += 1

    await db.flush()
    await db.commit()

    return {
        "message": f"Activated {count} policies.",
        "activated_count": count,
    }
