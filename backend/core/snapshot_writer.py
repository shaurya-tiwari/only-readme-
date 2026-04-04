"""Persistence helpers for normalized signal snapshots."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.models import SignalSnapshot
from backend.providers.base import NormalizedSignalSnapshot
from backend.utils.time import utc_now_naive


class SnapshotWriter:
    """Persists normalized signal snapshots when the feature flag is enabled."""

    def __init__(self) -> None:
        self._writes_since_cleanup = 0

    async def persist(
        self,
        db: AsyncSession | None,
        snapshots: list[NormalizedSignalSnapshot],
    ) -> None:
        if not db or not settings.ENABLE_PROVIDER_SNAPSHOT_PERSISTENCE:
            return

        for snapshot in snapshots:
            db.add(
                SignalSnapshot(
                    city=snapshot.city,
                    zone=snapshot.zone,
                    signal_type=snapshot.signal_type,
                    provider=snapshot.provider,
                    source_mode=snapshot.source_mode,
                    captured_at=snapshot.captured_at,
                    normalized_metrics=snapshot.normalized_metrics,
                    raw_payload=snapshot.raw_payload,
                    quality_score=Decimal(str(snapshot.quality_score)),
                    quality_breakdown=snapshot.quality_breakdown,
                    confidence_envelope=snapshot.confidence_envelope,
                    latency_ms=int(snapshot.latency_ms or 0),
                    is_fallback=snapshot.is_fallback,
                    request_id=snapshot.request_id,
                )
            )
        self._writes_since_cleanup += len(snapshots)
        if self._writes_since_cleanup >= settings.SIGNAL_RETENTION_CLEANUP_INTERVAL:
            await self.cleanup_expired(db)
        await db.flush()

    async def cleanup_expired(self, db: AsyncSession | None) -> None:
        if not db:
            return

        cutoff = utc_now_naive() - timedelta(days=settings.SIGNAL_SNAPSHOT_RETENTION_DAYS)
        await db.execute(delete(SignalSnapshot).where(SignalSnapshot.captured_at < cutoff))
        self._writes_since_cleanup = 0


snapshot_writer = SnapshotWriter()
