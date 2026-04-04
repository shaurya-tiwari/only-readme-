"""Persistence helpers and summaries for shadow signal diffs."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.models import ShadowSignalDiff
from backend.utils.time import utc_now_naive


class ShadowDiffWriter:
    """Stores structured shadow diffs and exposes lightweight summaries."""

    def __init__(self) -> None:
        self._writes_since_cleanup = 0

    async def persist(self, db: AsyncSession | None, diffs: list[dict[str, Any]]) -> None:
        if not db or not settings.ENABLE_SHADOW_DIFF_PERSISTENCE or not diffs:
            return

        for diff in diffs:
            db.add(
                ShadowSignalDiff(
                    city=diff["city"],
                    zone=diff["zone"],
                    signal_type=diff["signal_type"],
                    primary_provider=diff["primary_provider"],
                    shadow_provider=diff["shadow_provider"],
                    compared_at=diff["compared_at"],
                    max_delta=Decimal(str(diff["delta"])),
                    metric_deltas=diff["metric_deltas"],
                    threshold_crossed=diff["threshold_crossed"],
                    alert_triggered=diff["requires_attention"],
                    threshold_state=diff["threshold_state"],
                )
            )

        self._writes_since_cleanup += len(diffs)
        if self._writes_since_cleanup >= settings.SIGNAL_RETENTION_CLEANUP_INTERVAL:
            await self.cleanup_expired(db)
        await db.flush()

    async def cleanup_expired(self, db: AsyncSession | None) -> None:
        if not db:
            return

        cutoff = utc_now_naive() - timedelta(days=settings.SHADOW_DIFF_RETENTION_DAYS)
        await db.execute(delete(ShadowSignalDiff).where(ShadowSignalDiff.compared_at < cutoff))
        self._writes_since_cleanup = 0

    async def daily_summary(self, db: AsyncSession | None, lookback_hours: int = 24) -> dict[str, Any]:
        if not db or not settings.ENABLE_SHADOW_DIFF_PERSISTENCE:
            return {"lookback_hours": lookback_hours, "total_diffs": 0, "alert_count": 0, "signals": []}

        cutoff = utc_now_naive() - timedelta(hours=lookback_hours)
        rows = (
            await db.execute(
                select(
                    ShadowSignalDiff.signal_type,
                    func.count(ShadowSignalDiff.id),
                    func.sum(case((ShadowSignalDiff.alert_triggered.is_(True), 1), else_=0)),
                    func.max(ShadowSignalDiff.max_delta),
                )
                .where(ShadowSignalDiff.compared_at >= cutoff)
                .group_by(ShadowSignalDiff.signal_type)
                .order_by(ShadowSignalDiff.signal_type.asc())
            )
        ).all()

        signals = []
        total_diffs = 0
        alert_count = 0
        for signal_type, count, alerts, max_delta in rows:
            signal_count = int(count or 0)
            signal_alerts = int(alerts or 0)
            signals.append(
                {
                    "signal_type": signal_type,
                    "comparisons": signal_count,
                    "alerts": signal_alerts,
                    "max_delta": float(max_delta or 0),
                }
            )
            total_diffs += signal_count
            alert_count += signal_alerts

        return {
            "lookback_hours": lookback_hours,
            "total_diffs": total_diffs,
            "alert_count": alert_count,
            "signals": signals,
        }


shadow_diff_writer = ShadowDiffWriter()
