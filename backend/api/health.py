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
async def config_check():
    """Show current configuration (non-sensitive)."""
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
        "available_cities": list(settings.CITY_RISK_PROFILES.keys()),
        "available_plans": list(settings.PLAN_DEFINITIONS.keys()),
    }
