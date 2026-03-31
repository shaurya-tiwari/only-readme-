"""
RideShield - Main FastAPI Application
Entry point for the backend server.
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.api.analytics import router as analytics_router
from backend.api.auth import router as auth_router
from backend.api.claims import router as claims_router
from backend.api.events import router as events_router
from backend.api.health import router as health_router
from backend.api.locations import router as locations_router
from backend.api.policies import router as policies_router
from backend.api.payouts import router as payouts_router
from backend.api.triggers import router as triggers_router
from backend.api.workers import router as workers_router
from backend.config import settings
from backend.core.location_service import location_service
from backend.core.runtime_logging import configure_logging
from backend.core.trigger_scheduler import trigger_scheduler
from backend.database import async_session_factory, close_db, init_db

configure_logging()
logger = logging.getLogger("rideshield")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    display_host = "localhost" if settings.HOST == "0.0.0.0" else settings.HOST

    logger.info("%s v%s starting...", settings.APP_NAME, settings.APP_VERSION)
    logger.info("Simulation mode: %s", settings.SIMULATION_MODE)
    logger.info("Available cities: %s", ", ".join(settings.CITY_RISK_PROFILES.keys()))
    logger.info("Available plans: %s", ", ".join(settings.PLAN_DEFINITIONS.keys()))
    logger.info(
        "Trigger thresholds: "
        f"rain={settings.RAIN_THRESHOLD_MM}, "
        f"heat={settings.HEAT_THRESHOLD_C}, "
        f"aqi={settings.AQI_THRESHOLD}, "
        f"traffic={settings.TRAFFIC_THRESHOLD}, "
        f"platform={settings.PLATFORM_OUTAGE_THRESHOLD}"
    )

    if settings.DEBUG:
        await init_db()
        logger.info("Database tables initialized")
    async with async_session_factory() as session:
        await location_service.ensure_bootstrap(session, strict_backfill=True)
        await session.commit()
    logger.info("Geography bootstrap complete")

    if settings.ENABLE_TRIGGER_SCHEDULER:
        await trigger_scheduler.start()
        logger.info("Trigger scheduler enabled")
    else:
        logger.info("Trigger scheduler disabled")

    logger.info("Server ready at http://%s:%s", display_host, settings.PORT)

    yield

    await trigger_scheduler.stop()
    await close_db()
    logger.info("RideShield shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Parametric AI Insurance for Gig Delivery Workers. "
        "Zero-touch claims, multi-signal fraud detection, "
        "and instant income protection."
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        "%s %s -> %s in %sms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


app.include_router(health_router)
app.include_router(locations_router)
app.include_router(analytics_router)
app.include_router(auth_router)
app.include_router(workers_router)
app.include_router(policies_router)
app.include_router(triggers_router)
app.include_router(events_router)
app.include_router(claims_router)
app.include_router(payouts_router)


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Parametric AI Insurance for Gig Delivery Workers",
        "docs": "/docs",
        "health": "/health",
        "demo_flow": {
            "step_1": "POST /api/workers/register",
            "step_2": "POST /api/policies/create",
            "step_3": "POST /api/triggers/scenario/heavy_rain",
            "step_4": "POST /api/triggers/check",
            "step_5": "GET /api/claims/worker/{id}",
            "step_6": "GET /api/payouts/worker/{id}",
        },
        "endpoints": {
            "workers": "/api/workers",
            "locations": "/api/locations",
            "policies": "/api/policies",
            "triggers": "/api/triggers",
            "events": "/api/events",
            "claims": "/api/claims",
            "payouts": "/api/payouts",
        },
    }
