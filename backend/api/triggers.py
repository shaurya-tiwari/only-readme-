"""
Triggers API for Sprint 2 demos and testing.
"""

from contextlib import contextmanager
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.claim_processor import claim_processor
from backend.core.demo_scenarios import (
    DEMO_SCENARIOS,
    _create_demo_policy,
    _create_demo_worker,
    enrich_worker_for_demo,
    run_demo_scenario,
    unique_demo_phone,
)
from backend.core.location_service import location_service
from backend.core.session_auth import require_admin_session
from backend.core.trigger_engine import trigger_engine
from backend.database import get_db
from backend.db.models import SignalSnapshot as SignalSnapshotModel
from backend.schemas.event import SignalSnapshot as SignalSnapshotSchema, TriggerCheckRequest, TriggerLabRequest
from backend.utils.time import utc_now_naive
from simulations.aqi_mock import aqi_simulator
from simulations.platform_mock import platform_simulator
from simulations.traffic_mock import traffic_simulator
from simulations.weather_mock import weather_simulator

router = APIRouter(prefix="/api/triggers", tags=["Triggers"])


@contextmanager
def _lab_overrides(signals: dict):
    weather_simulator.set_override(
        {
            "rainfall_mm_hr": signals.get("rain_mm_hr", 0),
            "temperature_c": signals.get("temperature_c", 30),
            "condition": "lab_override",
        }
    )
    aqi_simulator.set_override(
        {
            "aqi_value": signals.get("aqi_value", 120),
        }
    )
    traffic_simulator.set_override(
        {
            "congestion_index": signals.get("congestion_index", 0.35),
        }
    )
    platform_simulator.set_override(
        {
            "order_density_drop": signals.get("order_density_drop", 0.1),
        }
    )
    try:
        yield
    finally:
        weather_simulator.clear_override()
        aqi_simulator.clear_override()
        traffic_simulator.clear_override()
        platform_simulator.clear_override()


async def _seed_lab_worker(
    db: AsyncSession,
    *,
    city: str,
    zone: str,
    profile: str,
    plan_name: str,
    platform: str,
    self_reported_income: int,
    iteration: int,
):
    scenario_like = type(
        "ScenarioLike",
        (),
        {
            "city": city,
            "zone": zone,
            "worker_name": f"{city.title()} Lab Worker {iteration + 1}",
            "platform": platform,
            "income": self_reported_income,
        },
    )()
    worker = await _create_demo_worker(
        db,
        scenario=scenario_like,
        phone=unique_demo_phone(offset=iteration + 100),
    )
    await _create_demo_policy(db, worker.id, plan_name)
    await enrich_worker_for_demo(str(worker.id), zone, profile, db=db)
    return worker


@router.post("/check")
async def run_trigger_check(request: TriggerCheckRequest, db: AsyncSession = Depends(get_db)):
    city = request.city or "delhi"
    zones = request.zones or [zone.slug for zone in await location_service.get_active_zones(db, city_slug=city)]
    return await claim_processor.run_trigger_cycle(
        db=db,
        zones=zones,
        city=city,
        scenario=request.scenario,
        demo_run_id=request.demo_run_id,
    )


@router.get("/status")
async def get_trigger_status(city: str = "delhi", zones: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Return latest signal snapshots from DB. Never calls external APIs."""
    from sqlalchemy import select, and_, func
    from backend.db.models import SignalSnapshot

    zone_list = zones.split(",") if zones else [zone.slug for zone in await location_service.get_active_zones(db, city_slug=city)]
    snapshots = []

    # For each zone, fetch the latest snapshot per signal type from DB
    signal_types = ("weather", "aqi", "traffic", "platform", "social")
    for zone in zone_list:
        zone = zone.strip()
        signals = {}
        latest_timestamp = None
        for signal_type in signal_types:
            row = (
                await db.execute(
                    select(SignalSnapshot)
                    .where(
                        and_(
                            SignalSnapshot.zone == zone,
                            SignalSnapshot.signal_type == signal_type,
                        )
                    )
                    .order_by(SignalSnapshot.captured_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if row and row.normalized_metrics:
                metrics = row.normalized_metrics
                if signal_type == "weather":
                    signals["rain"] = float(metrics.get("rainfall_mm_hr", 0) or 0)
                    signals["heat"] = float(metrics.get("temperature_c", 0) or 0)
                elif signal_type == "aqi":
                    signals["aqi"] = int(metrics.get("aqi_value", 0) or 0)
                elif signal_type == "traffic":
                    signals["traffic"] = float(metrics.get("congestion_index", 0) or 0)
                elif signal_type == "platform":
                    signals["platform_outage"] = float(metrics.get("order_density_drop", 0) or 0)
                elif signal_type == "social":
                    signals["social"] = float(metrics.get("severity", 0) or 0)
                if latest_timestamp is None or (row.captured_at and row.captured_at > latest_timestamp):
                    latest_timestamp = row.captured_at

        # Social signal: prefer DB snapshot; fall back to 0 (no longer derived from platform)
        signals.setdefault("social", 0.0)

        fired = trigger_engine.evaluate_thresholds(signals)
        snapshots.append(
            SignalSnapshotSchema(
                zone=zone,
                timestamp=latest_timestamp.isoformat() if latest_timestamp else "",
                rain_mm_hr=signals.get("rain", 0),
                temperature_c=signals.get("heat", 0),
                aqi_value=int(signals.get("aqi", 0)),
                congestion_index=signals.get("traffic", 0),
                order_density_drop=signals.get("platform_outage", 0),
                normalized_inactivity=signals.get("social", 0),
                triggers_active=fired,
            )
        )
    return {
        "city": city,
        "zones_checked": len(snapshots),
        "snapshots": snapshots,
        "thresholds": {name: config["threshold"] for name, config in trigger_engine.THRESHOLDS.items()},
    }


@router.post("/scenario/{scenario_name}")
async def set_scenario(scenario_name: str):
    valid_scenarios = ["normal", "heavy_rain", "extreme_heat", "hazardous_aqi", "monsoon", "platform_outage", "compound_disaster"]
    if scenario_name not in valid_scenarios:
        return {"error": f"Unknown scenario: {scenario_name}", "valid_scenarios": valid_scenarios}
    scenario_configs = {
        "normal": ("normal", "normal", "normal", "normal"),
        "heavy_rain": ("heavy_rain", "normal", "severe", "platform_outage"),
        "extreme_heat": ("extreme_heat", "moderate", "normal", "normal"),
        "hazardous_aqi": ("normal", "hazardous", "normal", "low_demand"),
        "monsoon": ("monsoon", "normal", "gridlock", "platform_outage"),
        "platform_outage": ("normal", "normal", "normal", "platform_outage"),
        "compound_disaster": ("heavy_rain", "hazardous", "gridlock", "platform_outage"),
    }
    w, a, t, p = scenario_configs[scenario_name]
    weather_simulator.set_scenario(w)
    aqi_simulator.set_scenario(a)
    traffic_simulator.set_scenario(t)
    platform_simulator.set_scenario(p)
    return {
        "scenario": scenario_name,
        "status": "active",
        "simulators": {"weather": w, "aqi": a, "traffic": t, "platform": p},
        "message": f"Scenario '{scenario_name}' is now active. Run /api/triggers/check to process.",
    }


@router.post("/demo-scenario/{scenario_id}")
async def run_demo_story(
    scenario_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin_session),
):
    if scenario_id not in DEMO_SCENARIOS:
        return {
            "error": f"Unknown demo scenario: {scenario_id}",
            "valid_scenarios": list(DEMO_SCENARIOS.keys()),
        }
    return await run_demo_scenario(db, scenario_id)


@router.post("/lab-run")
async def run_lab_scenario(
    request: TriggerLabRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin_session),
):
    city = request.city.lower()
    zones = request.zones or [zone.slug for zone in await location_service.get_active_zones(db, city_slug=city)]
    runs = request.execution.runs if request.execution.mode == "batch" else 1
    run_results = []
    seeded_workers = []

    with _lab_overrides(request.signals.model_dump()):
        for iteration in range(runs):
            worker_payload = None
            if request.worker.seed_demo_worker and zones:
                worker = await _seed_lab_worker(
                    db,
                    city=city,
                    zone=zones[0],
                    profile=request.worker.profile,
                    plan_name=request.worker.plan_name,
                    platform=request.worker.platform,
                    self_reported_income=request.worker.self_reported_income,
                    iteration=iteration,
                )
                worker_payload = {
                    "id": str(worker.id),
                    "name": worker.name,
                    "phone": worker.phone,
                    "profile": request.worker.profile,
                    "plan_name": request.worker.plan_name,
                }
                seeded_workers.append(worker_payload)

            cycle_result = await claim_processor.run_trigger_cycle(
                db=db,
                zones=zones,
                city=city,
                demo_run_id=f"lab-{city}-{iteration}",
            )
            run_results.append(
                {
                    "run_index": iteration + 1,
                    "worker": worker_payload,
                    **cycle_result,
                }
            )

    aggregate = {
        "runs": runs,
        "events_created": sum(item["events_created"] for item in run_results),
        "events_extended": sum(item["events_extended"] for item in run_results),
        "claims_generated": sum(item["claims_generated"] for item in run_results),
        "claims_approved": sum(item["claims_approved"] for item in run_results),
        "claims_delayed": sum(item["claims_delayed"] for item in run_results),
        "claims_rejected": sum(item["claims_rejected"] for item in run_results),
        "claims_duplicate": sum(item["claims_duplicate"] for item in run_results),
        "total_payout": round(sum(item["total_payout"] for item in run_results), 2),
    }
    return {
        "preset_name": request.preset_name,
        "city": city,
        "zones": zones,
        "signals": request.signals.model_dump(),
        "worker_config": request.worker.model_dump(),
        "execution": request.execution.model_dump(),
        "aggregate": aggregate,
        "runs": run_results,
        "seeded_workers": seeded_workers,
        "warning": "Scenario Lab runs create simulation-only records in the working environment.",
    }


class SocialTriggerRequest(BaseModel):
    """Admin-initiated social disruption signal."""
    city: str = Field(default="delhi", description="City slug")
    zone: str = Field(..., description="Zone slug where social disruption is occurring")
    disruption_type: str = Field(
        ..., description="Type of social disruption",
        json_schema_extra={"enum": ["curfew", "strike", "closure", "protest", "bandh"]},
    )
    severity: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="Severity of disruption (0-1). Values >= SOCIAL_INACTIVITY_THRESHOLD trigger claims.",
    )
    description: str = Field(default="", description="Optional context for the disruption")


@router.post("/social-trigger")
async def inject_social_disruption(
    request: SocialTriggerRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin_session),
):
    """Inject an independent social disruption signal for a zone.

    This creates a real SignalSnapshot with signal_type='social' that the
    trigger engine reads alongside weather/aqi/traffic/platform. Unlike the
    old fake derivation, this signal is completely independent of platform
    outage — a curfew can fire even if Zomato servers are healthy.
    """
    now = utc_now_naive()

    snapshot = SignalSnapshotModel(
        city=request.city,
        zone=request.zone,
        signal_type="social",
        provider="admin_trigger",
        source_mode="manual",
        captured_at=now,
        normalized_metrics={
            "severity": request.severity,
            "disruption_type": request.disruption_type,
        },
        raw_payload={
            "disruption_type": request.disruption_type,
            "severity": request.severity,
            "description": request.description,
            "triggered_by": "admin",
            "timestamp": now.isoformat(),
        },
        quality_score=1.0,
        quality_breakdown={"source": "admin_manual", "confidence": 1.0},
        confidence_envelope={"lower": request.severity, "upper": request.severity},
        latency_ms=0,
        is_fallback=False,
    )
    db.add(snapshot)
    await db.commit()

    return {
        "status": "injected",
        "signal_type": "social",
        "zone": request.zone,
        "city": request.city,
        "disruption_type": request.disruption_type,
        "severity": request.severity,
        "description": request.description,
        "snapshot_id": str(snapshot.id),
        "message": f"Social disruption '{request.disruption_type}' injected for {request.zone}. Run /api/triggers/check to process claims.",
    }


@router.post("/reset")
async def reset_simulators():
    weather_simulator.set_scenario("normal")
    aqi_simulator.set_scenario("normal")
    traffic_simulator.set_scenario("normal")
    platform_simulator.set_scenario("normal")
    return {"status": "reset", "message": "All simulators reset to normal conditions."}


@router.post("/simulate-spoofing")
async def simulate_spoofing(
    worker_id: str,
    spoof_type: str = "teleportation",
    intensity: str = "high",
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin_session),
):
    """Inject GPS spoofing attack data for adversarial testing.

    Creates anomalous WorkerActivity records tagged with is_simulated=True.
    Trust score updates happen naturally through the fraud pipeline on the
    next claim — no direct mutations.
    """
    from uuid import UUID
    from simulations.location_spoof_mock import spoof_simulator
    from backend.db.models import Worker
    from sqlalchemy import select

    worker_uuid = UUID(worker_id)
    result = await db.execute(select(Worker).where(Worker.id == worker_uuid))
    worker = result.scalar_one_or_none()
    if not worker:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found.")

    base_zone = worker.zone or "south_delhi"

    if spoof_type == "stationary":
        report = await spoof_simulator.inject_stationary_spoof(
            db, worker_uuid, base_zone, intensity=intensity
        )
    else:
        report = await spoof_simulator.inject_teleportation_attack(
            db, worker_uuid, base_zone, intensity=intensity
        )

    await db.commit()

    return {
        "status": "injected",
        "worker_id": worker_id,
        "worker_name": worker.name,
        "zone": base_zone,
        **report,
        "note": "Spoofed data is tagged is_simulated=True. Trust score will degrade on next claim through the fraud pipeline.",
    }
