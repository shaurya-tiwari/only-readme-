"""Background scheduler for periodic trigger checks."""

import asyncio
import math
import logging
from datetime import datetime, timedelta, timezone

from backend.config import settings
from backend.core.claim_processor import claim_processor
from backend.core.location_service import location_service
from backend.core.trigger_engine import trigger_engine
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
            "configured_interval_seconds": settings.TRIGGER_CHECK_INTERVAL_SECONDS,
            "run_count": 0,
            "last_started_at": None,
            "last_finished_at": None,
            "next_scheduled_at": None,
            "last_result": None,
            "last_error": None,
        }

    def _budgeted_interval_seconds(self, zone_count: int) -> int:
        configured = settings.TRIGGER_CHECK_INTERVAL_SECONDS
        traffic_real = settings.TRAFFIC_SOURCE == "real" and bool(settings.TOMTOM_API_KEY)
        if not traffic_real or zone_count <= 0:
            return configured

        budget = max(1, settings.TRAFFIC_DAILY_REQUEST_BUDGET)
        min_interval = math.ceil((86400 * zone_count) / budget)
        return max(configured, min_interval)

    def _flatten_zone_count(self, city_zone_pairs: list[tuple[str, list[str]]]) -> int:
        return sum(len(zones) for _, zones in city_zone_pairs)

    async def start(self):
        if not settings.ENABLE_TRIGGER_SCHEDULER or self._task:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._loop(), name="rideshield-trigger-scheduler")
        logger.info(
            "Trigger scheduler started with configured_interval=%ss",
            settings.TRIGGER_CHECK_INTERVAL_SECONDS,
        )

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
            logger.info(
                "scheduler_run_start interval_seconds=%s run_count=%s",
                settings.TRIGGER_CHECK_INTERVAL_SECONDS,
                self.state["run_count"] + 1,
            )
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

                    zone_count = self._flatten_zone_count(city_zone_pairs)
                    effective_interval = self._budgeted_interval_seconds(zone_count)
                    self.state["configured_interval_seconds"] = settings.TRIGGER_CHECK_INTERVAL_SECONDS
                    self.state["interval_seconds"] = effective_interval
                    logger.info(
                        "scheduler_interval_resolved configured=%ss effective=%ss zones=%s traffic_source=%s daily_budget=%s",
                        settings.TRIGGER_CHECK_INTERVAL_SECONDS,
                        effective_interval,
                        zone_count,
                        settings.TRAFFIC_SOURCE,
                        settings.TRAFFIC_DAILY_REQUEST_BUDGET,
                    )

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
                    stale_events_closed = await trigger_engine.end_stale_events(db)
                    await db.commit()
                    self.state["run_count"] += 1
                    self.state["last_result"] = results
                    total_events_created = sum(item["events_created"] for item in results.values())
                    total_events_extended = sum(item["events_extended"] for item in results.values())
                    total_claims_generated = sum(item["claims_generated"] for item in results.values())
                    total_claims_approved = sum(item["claims_approved"] for item in results.values())
                    total_claims_delayed = sum(item["claims_delayed"] for item in results.values())
                    total_claims_rejected = sum(item["claims_rejected"] for item in results.values())
                    total_payout = round(sum(item["total_payout"] for item in results.values()), 2)
                    logger.info(
                        "scheduler_run_done cities=%s events_created=%s events_extended=%s claims_generated=%s claims_approved=%s claims_delayed=%s claims_rejected=%s stale_events_closed=%s total_payout=%s",
                        len(results),
                        total_events_created,
                        total_events_extended,
                        total_claims_generated,
                        total_claims_approved,
                        total_claims_delayed,
                        total_claims_rejected,
                        stale_events_closed,
                        total_payout,
                    )
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
                interval_seconds = settings.TRIGGER_CHECK_INTERVAL_SECONDS
                try:
                    await self.run_once()
                except Exception:
                    logger.exception("Trigger scheduler loop iteration failed")
                interval_seconds = self.state.get("interval_seconds") or settings.TRIGGER_CHECK_INTERVAL_SECONDS
                self.state["next_scheduled_at"] = (
                    datetime.now(timezone.utc) + timedelta(seconds=interval_seconds)
                ).isoformat()
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=interval_seconds)
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            raise


trigger_scheduler = TriggerScheduler()
