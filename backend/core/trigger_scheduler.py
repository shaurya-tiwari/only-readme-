"""
Background scheduler for periodic trigger checks.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from backend.config import settings
from backend.core.claim_processor import claim_processor
from backend.core.location_service import location_service
from backend.database import async_session_factory

logger = logging.getLogger("rideshield.scheduler")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TriggerScheduler:
    def __init__(self):
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._stop = asyncio.Event()
        self.state = {
            "enabled": settings.ENABLE_TRIGGER_SCHEDULER,
            "running": False,
            "interval_seconds": settings.TRIGGER_CHECK_INTERVAL_SECONDS,
            "run_count": 0,
            "last_started_at": None,
            "last_finished_at": None,
            "next_scheduled_at": None,
            "last_result": None,
            "last_error": None,
        }

    async def start(self):
        if not settings.ENABLE_TRIGGER_SCHEDULER or self._task:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._loop(), name="rideshield-trigger-scheduler")
        logger.info("Trigger scheduler started with interval=%ss", settings.TRIGGER_CHECK_INTERVAL_SECONDS)

    async def stop(self):
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self.state["running"] = False
        self.state["next_scheduled_at"] = None
        logger.info("Trigger scheduler stopped")

    async def run_once(self):
        async with self._lock:
            self.state["running"] = True
            self.state["last_started_at"] = utc_now_iso()
            self.state["last_error"] = None
            try:
                async with async_session_factory() as db:
                    results = {}
                    active_cities = await location_service.get_active_cities(db)
                    if active_cities:
                        city_zone_pairs = [
                            (city.slug, [zone.slug for zone in await location_service.get_active_zones(db, city_slug=city.slug)])
                            for city in active_cities
                        ]
                    else:
                        logger.warning("No active cities found in DB geography. Falling back to config-backed city profiles.")
                        city_zone_pairs = [
                            (city, profile.get("zones", []))
                            for city, profile in settings.CITY_RISK_PROFILES.items()
                        ]

                    for city, zones in city_zone_pairs:
                        if not zones:
                            continue
                        logger.info("Scheduler monitoring %s zones for %s: %s", len(zones), city, ", ".join(zones))
                        result = await claim_processor.run_trigger_cycle(db=db, city=city, zones=zones[:], scenario=None)
                        await db.commit()
                        results[city] = {
                            "events_created": result["events_created"],
                            "events_extended": result["events_extended"],
                            "claims_generated": result["claims_generated"],
                            "claims_approved": result["claims_approved"],
                            "claims_delayed": result["claims_delayed"],
                            "claims_rejected": result["claims_rejected"],
                            "total_payout": result["total_payout"],
                        }
                    self.state["run_count"] += 1
                    self.state["last_result"] = results
                    return results
            except Exception as exc:
                self.state["last_error"] = str(exc)
                logger.exception("Trigger scheduler run failed")
                raise
            finally:
                self.state["last_finished_at"] = utc_now_iso()
                self.state["running"] = False
                self.state["next_scheduled_at"] = None

    async def _loop(self):
        try:
            while not self._stop.is_set():
                try:
                    await self.run_once()
                except Exception:
                    pass
                self.state["next_scheduled_at"] = (
                    datetime.now(timezone.utc) + timedelta(seconds=settings.TRIGGER_CHECK_INTERVAL_SECONDS)
                ).isoformat()
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=settings.TRIGGER_CHECK_INTERVAL_SECONDS)
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            raise


trigger_scheduler = TriggerScheduler()
