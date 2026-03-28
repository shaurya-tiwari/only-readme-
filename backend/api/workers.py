"""
Workers API
Handles registration, profile management, and risk scoring.

Endpoints:
    POST /api/workers/register  -> Register new worker
    GET  /api/workers/me/{id}   -> Get worker profile
    PUT  /api/workers/me/{id}   -> Update worker details
    GET  /api/workers/          -> List all workers (admin)
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.core.premium_calculator import premium_calculator
from backend.core.risk_scorer import risk_scorer
from backend.database import get_db
from backend.db.models import AuditLog, TrustScore, Worker
from backend.schemas.worker import (
    PlanOption,
    RiskScoreBreakdown,
    WorkerListResponse,
    WorkerProfileResponse,
    WorkerRegisterRequest,
    WorkerRegisterResponse,
    WorkerUpdateRequest,
)

router = APIRouter(prefix="/api/workers", tags=["Workers"])


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_active_policy(worker, now):
    for policy in worker.policies:
        if policy.status == "active" and policy.activates_at <= now <= policy.expires_at:
            return {
                "id": str(policy.id),
                "plan_name": policy.plan_display_name,
                "weekly_premium": float(policy.weekly_premium),
                "coverage_cap": float(policy.coverage_cap),
                "triggers_covered": policy.triggers_covered,
                "activates_at": policy.activates_at.isoformat(),
                "expires_at": policy.expires_at.isoformat(),
            }
    return None


@router.post("/register", response_model=WorkerRegisterResponse, status_code=201)
async def register_worker(
    request: WorkerRegisterRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new delivery worker."""

    existing = await db.execute(select(Worker).where(Worker.phone == request.phone))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A worker with this phone number is already registered.",
        )

    city_profile = settings.CITY_RISK_PROFILES.get(request.city)
    if not city_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"City '{request.city}' is not supported.",
        )

    if request.zone and request.zone not in city_profile["zones"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Zone '{request.zone}' is not valid for city '{request.city}'. "
            f"Valid zones: {', '.join(city_profile['zones'])}",
        )

    risk_result = risk_scorer.calculate_risk_score(city=request.city, zone=request.zone)
    client_ip = req.client.host if req.client else None

    worker = Worker(
        name=request.name,
        phone=request.phone,
        city=request.city,
        zone=request.zone,
        platform=request.platform,
        self_reported_income=request.self_reported_income,
        working_hours=request.working_hours,
        consent_given=request.consent_given,
        consent_timestamp=utc_now_naive(),
        risk_score=risk_result["risk_score"],
        ip_address=client_ip,
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
                "city": request.city,
                "zone": request.zone,
                "platform": request.platform,
                "risk_score": risk_result["risk_score"],
                "consent_given": True,
                "ip_address": client_ip,
            },
            performed_by="system",
        )
    )

    plans, recommended = premium_calculator.calculate_all_plans(risk_result["risk_score"])
    plan_options = [
        PlanOption(
            plan_name=plan["plan_name"],
            display_name=plan["display_name"],
            weekly_premium=plan["weekly_premium"],
            coverage_cap=plan["coverage_cap"],
            triggers_covered=plan["triggers_covered"],
            description=plan["description"],
            color=plan["color"],
            is_recommended=plan["is_recommended"],
        )
        for plan in plans
    ]

    await db.commit()

    return WorkerRegisterResponse(
        worker_id=worker.id,
        name=worker.name,
        city=worker.city,
        zone=worker.zone,
        platform=worker.platform,
        risk_score=risk_result["risk_score"],
        risk_breakdown=RiskScoreBreakdown(**risk_result["breakdown"]),
        available_plans=plan_options,
        recommended_plan=recommended,
        activation_delay_hours=settings.ACTIVATION_DELAY_HOURS,
        message=(
            f"Welcome to RideShield, {worker.name}! "
            f"Your risk score is {risk_result['risk_score']} "
            f"({risk_result['breakdown']['risk_level']}). "
            f"We recommend the {recommended.replace('_', ' ').title()} plan."
        ),
    )


@router.get("/me/{worker_id}", response_model=WorkerProfileResponse)
async def get_worker_profile(
    worker_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get complete worker profile with active policy and claim stats."""

    result = await db.execute(
        select(Worker)
        .options(
            selectinload(Worker.trust_score),
            selectinload(Worker.policies),
            selectinload(Worker.claims),
        )
        .where(Worker.id == worker_id)
    )
    worker = result.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found.",
        )

    now = utc_now_naive()
    active_policy = get_active_policy(worker, now)
    total_claims = len(worker.claims)
    total_payouts = sum(float(claim.final_payout or 0) for claim in worker.claims if claim.status == "approved")
    trust_val = float(worker.trust_score.score) if worker.trust_score else 0.1

    return WorkerProfileResponse(
        id=worker.id,
        name=worker.name,
        phone=worker.phone,
        city=worker.city,
        zone=worker.zone,
        platform=worker.platform,
        self_reported_income=float(worker.self_reported_income) if worker.self_reported_income else None,
        working_hours=float(worker.working_hours) if worker.working_hours else None,
        risk_score=float(worker.risk_score) if worker.risk_score else None,
        status=worker.status,
        consent_given=worker.consent_given,
        created_at=worker.created_at,
        trust_score=trust_val,
        active_policy=active_policy,
        total_claims=total_claims,
        total_payouts=total_payouts,
    )


@router.put("/me/{worker_id}", response_model=WorkerProfileResponse)
async def update_worker(
    worker_id: UUID,
    update: WorkerUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update worker details. Recalculates risk score if zone changes."""

    result = await db.execute(
        select(Worker)
        .options(
            selectinload(Worker.trust_score),
            selectinload(Worker.policies),
            selectinload(Worker.claims),
        )
        .where(Worker.id == worker_id)
    )
    worker = result.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found.",
        )

    recalculate_risk = False
    if update.zone is not None:
        city_profile = settings.CITY_RISK_PROFILES.get(worker.city)
        if update.zone not in city_profile["zones"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Zone '{update.zone}' is not valid for city '{worker.city}'.",
            )
        worker.zone = update.zone
        recalculate_risk = True

    if update.self_reported_income is not None:
        worker.self_reported_income = update.self_reported_income
    if update.working_hours is not None:
        worker.working_hours = update.working_hours

    if recalculate_risk:
        risk_result = risk_scorer.calculate_risk_score(city=worker.city, zone=worker.zone)
        worker.risk_score = risk_result["risk_score"]

    worker.updated_at = utc_now_naive()
    db.add(
        AuditLog(
            entity_type="worker",
            entity_id=worker.id,
            action="updated",
            details={
                "updates": update.model_dump(exclude_unset=True),
                "risk_recalculated": recalculate_risk,
            },
        )
    )
    await db.flush()
    await db.commit()
    return await get_worker_profile(worker_id, db)


@router.get("/", response_model=WorkerListResponse)
async def list_workers(
    city: Optional[str] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List all workers. Admin endpoint."""

    query = select(Worker).options(
        selectinload(Worker.trust_score),
        selectinload(Worker.policies),
        selectinload(Worker.claims),
    )
    if city:
        query = query.where(Worker.city == city.lower())
    if status_filter:
        query = query.where(Worker.status == status_filter)

    result = await db.execute(query.offset(skip).limit(limit))
    workers = result.scalars().all()

    count_query = select(func.count(Worker.id))
    if city:
        count_query = count_query.where(Worker.city == city.lower())
    if status_filter:
        count_query = count_query.where(Worker.status == status_filter)
    total = (await db.execute(count_query)).scalar()

    now = utc_now_naive()
    worker_responses = []
    for worker in workers:
        active_policy = get_active_policy(worker, now)
        total_claims = len(worker.claims)
        total_payouts = sum(
            float(claim.final_payout or 0) for claim in worker.claims if claim.status == "approved"
        )
        trust_val = float(worker.trust_score.score) if worker.trust_score else 0.1

        worker_responses.append(
            WorkerProfileResponse(
                id=worker.id,
                name=worker.name,
                phone=worker.phone,
                city=worker.city,
                zone=worker.zone,
                platform=worker.platform,
                self_reported_income=float(worker.self_reported_income) if worker.self_reported_income else None,
                working_hours=float(worker.working_hours) if worker.working_hours else None,
                risk_score=float(worker.risk_score) if worker.risk_score else None,
                status=worker.status,
                consent_given=worker.consent_given,
                created_at=worker.created_at,
                trust_score=trust_val,
                active_policy=active_policy,
                total_claims=total_claims,
                total_payouts=total_payouts,
            )
        )

    return WorkerListResponse(total=total, workers=worker_responses)


@router.get("/risk-score/{worker_id}")
async def get_risk_score(
    worker_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed risk score breakdown for a worker."""

    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found.",
        )

    risk_result = risk_scorer.calculate_risk_score(city=worker.city, zone=worker.zone)
    plans, recommended = premium_calculator.calculate_all_plans(risk_result["risk_score"])

    return {
        "worker_id": str(worker.id),
        "worker_name": worker.name,
        "city": worker.city,
        "zone": worker.zone,
        "risk_score": risk_result["risk_score"],
        "breakdown": risk_result["breakdown"],
        "premium_impact": {
            plan["plan_name"]: {
                "premium": plan["weekly_premium"],
                "formula": plan["premium_calculation"]["formula"],
            }
            for plan in plans
        },
        "recommended_plan": recommended,
    }
