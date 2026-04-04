"""
Triggers API for Sprint 2 demos and testing.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.claim_processor import claim_processor
from backend.core.location_service import location_service
from backend.core.trigger_engine import trigger_engine
from backend.database import get_db
from backend.schemas.event import SignalSnapshot, TriggerCheckRequest
from simulations.aqi_mock import aqi_simulator
from simulations.platform_mock import platform_simulator
from simulations.traffic_mock import traffic_simulator
from simulations.weather_mock import weather_simulator

router = APIRouter(prefix="/api/triggers", tags=["Triggers"])


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
    zone_list = zones.split(",") if zones else [zone.slug for zone in await location_service.get_active_zones(db, city_slug=city)]
    snapshots = []
    for zone in zone_list:
        zone = zone.strip()
        signals = await trigger_engine.fetch_all_signals(zone, city, db=db)
        fired = trigger_engine.evaluate_thresholds(signals)
        snapshots.append(
            SignalSnapshot(
                zone=zone,
                timestamp=signals.get("timestamp") or signals.get("raw_data", {}).get("weather", {}).get("timestamp", ""),
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


@router.post("/reset")
async def reset_simulators():
    weather_simulator.set_scenario("normal")
    aqi_simulator.set_scenario("normal")
    traffic_simulator.set_scenario("normal")
    platform_simulator.set_scenario("normal")
    return {"status": "reset", "message": "All simulators reset to normal conditions."}
