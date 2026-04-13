"""
Standalone scheduler worker process.

Runs the trigger scheduler in its own process, completely separate from
the FastAPI API server. This eliminates event loop contention between
heavy external API calls (weather, traffic, AQI) and user-facing requests.

Usage:
    python -m backend.scheduler_worker
"""

import asyncio
import logging
import sys

from backend.config import settings
from backend.core.location_service import location_service
from backend.core.runtime_logging import configure_logging
from backend.core.trigger_scheduler import trigger_scheduler
from backend.database import async_session_factory, close_db, init_db

configure_logging()
logger = logging.getLogger("rideshield.scheduler")


async def main():
    logger.info(
        "Scheduler worker starting (pid=%s, interval=%ss, concurrency=%s)",
        __import__("os").getpid(),
        settings.TRIGGER_CHECK_INTERVAL_SECONDS,
        settings.SCHEDULER_FETCH_CONCURRENCY,
    )

    if settings.DEBUG:
        await init_db()
        logger.info("Database tables initialized")

    async with async_session_factory() as session:
        await location_service.ensure_bootstrap(session, strict_backfill=True)
        await session.commit()
    logger.info("Geography bootstrap complete")

    if not settings.ENABLE_TRIGGER_SCHEDULER:
        logger.info("Trigger scheduler is disabled (ENABLE_TRIGGER_SCHEDULER=False). Exiting.")
        await close_db()
        return

    try:
        await trigger_scheduler.start()
        logger.info("Scheduler loop running. Press Ctrl+C to stop.")
        # Keep the process alive until interrupted
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Scheduler worker interrupted")
    finally:
        await trigger_scheduler.stop()
        await close_db()
        logger.info("Scheduler worker stopped cleanly")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
