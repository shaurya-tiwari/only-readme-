"""
Events API for viewing detected disruption events.
"""

from datetime import timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.db.models import Claim, Event
from backend.utils.time import utc_now_naive

router = APIRouter(prefix="/api/events", tags=["Events"])


def serialize_event(event: Event, claims_count: int, include_metadata: bool = False) -> dict:
    end = event.ended_at or utc_now_naive()
    duration = round((end - event.started_at).total_seconds() / 3600, 1) if event.started_at else None
    payload = {
        "id": str(event.id),
        "event_type": event.event_type,
        "zone": event.zone,
        "city": event.city,
        "started_at": event.started_at.isoformat() if event.started_at else None,
        "ended_at": event.ended_at.isoformat() if event.ended_at else None,
        "severity": float(event.severity) if event.severity is not None else None,
        "raw_value": float(event.raw_value) if event.raw_value is not None else None,
        "threshold": float(event.threshold) if event.threshold is not None else None,
        "disruption_score": float(event.disruption_score) if event.disruption_score is not None else None,
        "event_confidence": float(event.event_confidence) if event.event_confidence is not None else None,
        "api_source": event.api_source,
        "status": event.status,
        "created_at": event.created_at.isoformat() if event.created_at else None,
        "duration_hours": duration,
        "claims_generated": claims_count,
    }
    if include_metadata:
        payload["metadata_json"] = event.metadata_json
    return payload


async def _claim_counts_by_event(db: AsyncSession, event_ids: list[UUID]) -> dict[UUID, int]:
    if not event_ids:
        return {}
    rows = (
        await db.execute(
            select(Claim.event_id, func.count(Claim.id))
            .where(Claim.event_id.in_(event_ids))
            .group_by(Claim.event_id)
        )
    ).all()
    return {event_id: count for event_id, count in rows}


@router.get("/active")
async def get_active_events(city: Optional[str] = None, zone: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    query = select(Event).where(Event.status == "active")
    if city:
        query = query.where(Event.city == city.lower())
    if zone:
        query = query.where(Event.zone == zone.lower())
    events = (await db.execute(query.order_by(desc(Event.started_at)))).scalars().all()
    claim_counts = await _claim_counts_by_event(db, [event.id for event in events])
    event_list = []
    for event in events:
        claims_count = claim_counts.get(event.id, 0)
        event_list.append(serialize_event(event, claims_count))
    return {"total": len(event_list), "active_count": len(event_list), "events": event_list}


@router.get("/history")
async def get_event_history(
    city: Optional[str] = None,
    zone: Optional[str] = None,
    days: int = 7,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    cutoff = utc_now_naive() - timedelta(days=days)
    query = select(Event).where(Event.created_at >= cutoff)
    if city:
        query = query.where(Event.city == city.lower())
    if zone:
        query = query.where(Event.zone == zone.lower())

    events = (await db.execute(query.order_by(desc(Event.started_at)).offset(skip).limit(limit))).scalars().all()
    count_query = select(func.count(Event.id)).where(Event.created_at >= cutoff)
    if city:
        count_query = count_query.where(Event.city == city.lower())
    if zone:
        count_query = count_query.where(Event.zone == zone.lower())
    total = (await db.execute(count_query)).scalar()

    claim_counts = await _claim_counts_by_event(db, [event.id for event in events])
    event_list = []
    for event in events:
        claims_count = claim_counts.get(event.id, 0)
        event_list.append(serialize_event(event, claims_count, include_metadata=True))

    return {"total": total, "period_days": days, "events": event_list}


@router.get("/detail/{event_id}")
async def get_event_detail(event_id: UUID, db: AsyncSession = Depends(get_db)):
    event = (
        await db.execute(select(Event).options(selectinload(Event.claims)).where(Event.id == event_id))
    ).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")

    claims_data = [
        {
            "id": str(claim.id),
            "worker_id": str(claim.worker_id),
            "status": claim.status,
            "final_score": float(claim.final_score) if claim.final_score else None,
            "fraud_score": float(claim.fraud_score) if claim.fraud_score else None,
            "final_payout": float(claim.final_payout) if claim.final_payout else None,
            "created_at": claim.created_at.isoformat() if claim.created_at else None,
        }
        for claim in event.claims
    ]
    return {
        **serialize_event(event, len(claims_data), include_metadata=True),
        "metadata": event.metadata_json,
        "claims": claims_data,
        "total_claims": len(claims_data),
        "approved_claims": sum(1 for claim in event.claims if claim.status == "approved"),
        "delayed_claims": sum(1 for claim in event.claims if claim.status == "delayed"),
        "rejected_claims": sum(1 for claim in event.claims if claim.status == "rejected"),
        "total_payout": round(sum(float(claim.final_payout or 0) for claim in event.claims if claim.status == "approved"), 2),
    }


@router.get("/zone/{zone_name}")
async def get_zone_events(
    zone_name: str,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    query = select(Event).where(Event.zone == zone_name.lower())
    if active_only:
        query = query.where(Event.status == "active")

    events = (await db.execute(query.order_by(desc(Event.started_at)).limit(50))).scalars().all()
    claim_counts = await _claim_counts_by_event(db, [event.id for event in events])
    event_list = []
    for event in events:
        claims_count = claim_counts.get(event.id, 0)
        event_list.append(serialize_event(event, claims_count))

    return {
        "zone": zone_name,
        "active_only": active_only,
        "total": len(event_list),
        "events": event_list,
    }
