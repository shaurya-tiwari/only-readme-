"""
Health check endpoint.
First endpoint created - verifies backend and database are running.
"""

import logging
from datetime import datetime, timezone

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


@router.get("/health/config")
async def config_check(db: AsyncSession = Depends(get_db)):
    """Show current configuration (non-sensitive)."""
    cities = await location_service.get_active_cities(db)
    city_map = await location_service.get_city_zone_map(db)
    shadow_diff_summary = await shadow_diff_writer.daily_summary(db)
    signal_source_status = await signal_service.source_runtime_status(db)
    return {
        "simulation_mode": settings.SIMULATION_MODE,
        "signal_sources": signal_service.source_overview(),
        "signal_source_status": signal_source_status,
        "signal_runtime": settings.signal_runtime_config,
        "provider_snapshot_persistence_enabled": settings.ENABLE_PROVIDER_SNAPSHOT_PERSISTENCE,
        "shadow_diff_summary": shadow_diff_summary,
        "scheduler": trigger_scheduler.state,
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
