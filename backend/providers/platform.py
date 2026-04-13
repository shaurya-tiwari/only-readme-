"""Platform signal provider implementations."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.platform_telemetry import platform_telemetry_engine
from backend.db.models import SignalSnapshot, Worker
from backend.providers.base import ProviderFetchResult
from backend.utils.time import utc_now_naive
from simulations.platform_mock import platform_simulator


class MockPlatformProvider:
    signal_type = "platform"
    source_name = "platform_simulator"

    async def fetch(
        self,
        db: AsyncSession | None,
        zone: str,
        city: str,
        source_mode: str,
    ) -> ProviderFetchResult:
        return ProviderFetchResult(
            signal_type=self.signal_type,
            provider=self.source_name,
            source_mode=source_mode,
            city=city,
            zone=zone,
            captured_at=utc_now_naive(),
            raw_payload=platform_simulator.get_platform_status(zone),
        )


class DatabasePlatformProvider:
    signal_type = "platform"
    source_name = "platform_db"
    fallback_source_name = "platform_db_fallback"

    async def fetch(
        self,
        db: AsyncSession | None,
        zone: str,
        city: str,
        source_mode: str,
    ) -> ProviderFetchResult:
        captured_at = utc_now_naive()
        try:
            raw_payload = await self._build_platform_status(db, zone, city, captured_at)
            return ProviderFetchResult(
                signal_type=self.signal_type,
                provider=self.source_name,
                source_mode=source_mode,
                city=city,
                zone=zone,
                captured_at=captured_at,
                raw_payload=raw_payload,
            )
        except Exception as exc:
            fallback_payload = platform_simulator.get_platform_status(zone)
            fallback_payload["fallback_reason"] = str(exc)
            fallback_payload["fallback_source"] = "platform_simulator"
            return ProviderFetchResult(
                signal_type=self.signal_type,
                provider=self.fallback_source_name,
                source_mode=source_mode,
                city=city,
                zone=zone,
                captured_at=captured_at,
                raw_payload=fallback_payload,
                is_fallback=True,
            )

    async def _build_platform_status(
        self,
        db: AsyncSession | None,
        zone: str,
        city: str,
        captured_at,
    ) -> dict:
        signal_context = await self._latest_signal_context(db, zone)
        active_workers = await self._active_worker_count(db, zone)
        scenario = getattr(platform_simulator, "scenario", None) or "normal"
        return platform_telemetry_engine.build_status(
            zone=zone,
            city=city,
            scenario=scenario,
            signal_context=signal_context,
            active_worker_count=active_workers,
            captured_at=captured_at,
            provider_name=self.source_name,
            model_variant="behavioral",
        )

    async def _latest_signal_context(self, db: AsyncSession | None, zone: str) -> dict:
        if not db:
            return {}

        context: dict[str, dict] = {}
        for signal_type in ("weather", "aqi", "traffic"):
            snapshot = (
                await db.execute(
                    select(SignalSnapshot)
                    .where(SignalSnapshot.zone == zone, SignalSnapshot.signal_type == signal_type)
                    .order_by(SignalSnapshot.captured_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if snapshot:
                context[signal_type] = snapshot.normalized_metrics or {}
        return context

    async def _active_worker_count(self, db: AsyncSession | None, zone: str) -> int | None:
        if not db:
            return None

        result = await db.execute(
            select(func.count(Worker.id)).where(Worker.zone == zone, Worker.status == "active")
        )
        count = int(result.scalar() or 0)
        return count or None


class PartnerPlatformProvider:
    signal_type = "platform"
    source_name = "platform_partner"

    async def fetch(
        self,
        db: AsyncSession | None,
        zone: str,
        city: str,
        source_mode: str,
    ) -> ProviderFetchResult:
        raise NotImplementedError("PLATFORM_SOURCE=partner is planned but not implemented yet.")

