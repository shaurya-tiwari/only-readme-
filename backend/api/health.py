"""
Health check endpoints.
"""

import logging
from datetime import datetime, timezone
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.fraud_model_service import fraud_model_service
from backend.core.location_service import location_service
from backend.core.risk_model_service import risk_model_service
from backend.core.shadow_diff_writer import shadow_diff_writer
from backend.core.signal_service import signal_service
from backend.core.trigger_scheduler import trigger_scheduler
from backend.database import get_db

START_TIME = datetime.now(timezone.utc)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


async def _runtime_config_payload(db: AsyncSession) -> dict:
    cities = await location_service.get_active_cities(db)
    city_map = await location_service.get_city_zone_map(db)
    return {
        "simulation_mode": settings.SIMULATION_MODE,
        "activation_delay_hours": settings.ACTIVATION_DELAY_HOURS,
        "policy_duration_days": settings.POLICY_DURATION_DAYS,
        "triggers": {
            "rain_threshold_mm": settings.RAIN_THRESHOLD_MM,
            "heat_threshold_c": settings.HEAT_THRESHOLD_C,
            "aqi_threshold": settings.AQI_THRESHOLD,
            "traffic_threshold": settings.TRAFFIC_THRESHOLD,
            "platform_outage_threshold": settings.PLATFORM_OUTAGE_THRESHOLD,
            "social_inactivity_threshold": settings.SOCIAL_INACTIVITY_THRESHOLD,
        },
        "trigger_check_interval_seconds": settings.TRIGGER_CHECK_INTERVAL_SECONDS,
        "available_cities": [city.slug for city in cities] or list(settings.CITY_RISK_PROFILES.keys()),
        "city_zone_map": city_map,
        "available_plans": list(settings.PLAN_DEFINITIONS.keys()),
    }


async def _signal_health_payload(db: AsyncSession) -> dict:
    return {
        "signal_sources": signal_service.source_overview(),
        "signal_source_status": await signal_service.source_runtime_status(db),
        "signal_runtime": settings.signal_runtime_config,
    }


async def _diagnostics_payload(db: AsyncSession) -> dict:
    return {
        "provider_snapshot_persistence_enabled": settings.ENABLE_PROVIDER_SNAPSHOT_PERSISTENCE,
        "shadow_diff_summary": await shadow_diff_writer.daily_summary(db),
        "scheduler": trigger_scheduler.state,
    }


def _with_timing(payload: dict, started_at: float) -> dict:
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    payload["response_ms"] = round((perf_counter() - started_at) * 1000, 1)
    return payload


@router.get("/health")
async def health_check():
    """Basic health check - is the server running?"""
    uptime_seconds = (datetime.now(timezone.utc) - START_TIME).total_seconds()
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "simulation_mode": settings.SIMULATION_MODE,
        "uptime_seconds": int(uptime_seconds),
    }


@router.get("/health/db")
async def db_health_check(db: AsyncSession = Depends(get_db)):
    """Database health check - can we query PostgreSQL?"""
    try:
        result = await db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "result": result.scalar(),
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Database connection failed")


@router.get("/config/runtime")
async def runtime_config(db: AsyncSession = Depends(get_db)):
    """Static-ish runtime configuration for UI controls and operator context."""
    started_at = perf_counter()
    payload = await _runtime_config_payload(db)
    logger.info("runtime_config_ready response_ms=%.1f", (perf_counter() - started_at) * 1000)
    return _with_timing(payload, started_at)


@router.get("/health/signals")
async def signal_health(db: AsyncSession = Depends(get_db)):
    """Signal-provider runtime state and freshness."""
    started_at = perf_counter()
    payload = await _signal_health_payload(db)
    logger.info("signal_health_ready response_ms=%.1f", (perf_counter() - started_at) * 1000)
    return _with_timing(payload, started_at)


@router.get("/health/diagnostics")
async def diagnostics_health(db: AsyncSession = Depends(get_db)):
    """Operational diagnostics for scheduler and shadow-diff internals."""
    started_at = perf_counter()
    payload = await _diagnostics_payload(db)
    logger.info("diagnostics_health_ready response_ms=%.1f", (perf_counter() - started_at) * 1000)
    return _with_timing(payload, started_at)


@router.get("/health/config")
async def config_check(db: AsyncSession = Depends(get_db)):
    """Compatibility aggregate for older clients. Prefer the split endpoints."""
    started_at = perf_counter()
    runtime_started = perf_counter()
    runtime_payload = await _runtime_config_payload(db)
    runtime_ms = round((perf_counter() - runtime_started) * 1000, 1)

    signals_started = perf_counter()
    signals_payload = await _signal_health_payload(db)
    signals_ms = round((perf_counter() - signals_started) * 1000, 1)

    diagnostics_started = perf_counter()
    diagnostics_payload = await _diagnostics_payload(db)
    diagnostics_ms = round((perf_counter() - diagnostics_started) * 1000, 1)

    logger.info(
        "config_health_ready runtime_ms=%.1f signals_ms=%.1f diagnostics_ms=%.1f total_ms=%.1f",
        runtime_ms,
        signals_ms,
        diagnostics_ms,
        (perf_counter() - started_at) * 1000,
    )
    return _with_timing(
        {
            **runtime_payload,
            **signals_payload,
            **diagnostics_payload,
            "timings_ms": {
                "runtime": runtime_ms,
                "signals": signals_ms,
                "diagnostics": diagnostics_ms,
            },
        },
        started_at,
    )


@router.get("/health/models")
async def model_health_check():
    """ML model status — shows whether fraud/risk models loaded or are running rule-based fallback."""
    fraud_info = fraud_model_service.get_model_info()
    risk_info = risk_model_service.get_model_info()

    all_active = fraud_info["status"] == "active" and risk_info["status"] == "active"
    any_fallback = fraud_info["fallback_used"] or risk_info["fallback_used"]

    overall = "fully_operational" if all_active else ("degraded_rule_based_fallback" if any_fallback else "partial")

    return {
        "overall_status": overall,
        "ml_enabled": settings.ML_ENABLED,
        "fraud_model": fraud_info,
        "risk_model": risk_info,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
