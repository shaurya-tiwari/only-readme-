"""Thin orchestration layer between providers and engine consumers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.shadow_diff_service import shadow_diff_service
from backend.core.shadow_diff_writer import shadow_diff_writer
from backend.core.signal_aggregator import signal_aggregator
from backend.core.snapshot_writer import snapshot_writer
from backend.providers.base import NormalizedSignalSnapshot
from backend.providers.registry import provider_registry


class SignalService:
    """Coordinates provider fetches, normalization, persistence, and aggregation."""

    SIGNAL_TYPES = ("weather", "aqi", "traffic", "platform")

    async def fetch_zone_snapshot(
        self,
        db: AsyncSession | None,
        zone: str,
        city: str,
        mode: str = "live",
    ) -> dict[str, Any]:
        source_mode = settings.SIGNAL_SOURCE_MODE if mode == "live" else mode
        primary_snapshots: list[NormalizedSignalSnapshot] = []
        shadow_diffs: list[dict[str, Any]] = []

        for signal_type in self.SIGNAL_TYPES:
            provider = provider_registry.get_provider(signal_type)
            fetch_result = await provider.fetch(db, zone, city, source_mode)
            primary_snapshot = provider_registry.normalize(fetch_result)
            primary_snapshots.append(primary_snapshot)

            if source_mode == "shadow" and settings.ENABLE_SHADOW_DIFF_LOGGING:
                comparison_snapshot = await self._build_shadow_snapshot(db, signal_type, zone, city, primary_snapshot)
                shadow_diffs.append(shadow_diff_service.compare(primary_snapshot, comparison_snapshot))

        await snapshot_writer.persist(db, primary_snapshots)
        await shadow_diff_writer.persist(db, shadow_diffs)
        return signal_aggregator.build_zone_snapshot(
            city,
            zone,
            primary_snapshots,
            source_mode=source_mode,
            shadow_diffs=shadow_diffs,
        )

    async def _build_shadow_snapshot(
        self,
        db: AsyncSession | None,
        signal_type: str,
        zone: str,
        city: str,
        primary_snapshot: NormalizedSignalSnapshot,
    ) -> NormalizedSignalSnapshot:
        shadow_provider = provider_registry.get_shadow_provider(signal_type)
        if shadow_provider is None or shadow_provider.source_name == primary_snapshot.provider:
            return deepcopy(primary_snapshot)

        shadow_result = await shadow_provider.fetch(db, zone, city, "shadow")
        return provider_registry.normalize(shadow_result)

    def source_overview(self) -> dict[str, str]:
        return provider_registry.source_overview()


signal_service = SignalService()
