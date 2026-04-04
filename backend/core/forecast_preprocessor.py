"""Preprocesses persisted signal snapshots before forecast scoring."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.models import SignalSnapshot
from backend.utils.time import utc_now_naive


class ForecastPreprocessor:
    """Smooths, clips, and gap-fills signal inputs for forecast consumers."""

    METRIC_SPECS = {
        "weather": {
            "rainfall_mm_hr": {"output": "rain", "min": 0.0, "max": 250.0, "default": 0.0, "cast": float},
            "temperature_c": {"output": "heat", "min": -10.0, "max": 60.0, "default": 0.0, "cast": float},
        },
        "aqi": {
            "aqi_value": {"output": "aqi", "min": 0.0, "max": 500.0, "default": 0.0, "cast": int},
        },
        "traffic": {
            "congestion_index": {"output": "traffic", "min": 0.0, "max": 1.0, "default": 0.0, "cast": float},
        },
        "platform": {
            "order_density_drop": {"output": "platform_outage", "min": 0.0, "max": 1.0, "default": 0.0, "cast": float},
        },
    }

    async def preprocess(
        self,
        db: AsyncSession | None,
        zone: str,
        signal_snapshot: dict[str, Any],
    ) -> tuple[dict[str, float | int], dict[str, Any]]:
        current_by_type = {
            snapshot.signal_type: snapshot
            for snapshot in signal_snapshot.get("snapshots", [])
        }
        history = await self._load_recent_history(db, zone, current_by_type)

        cleaned: dict[str, float | int] = {}
        filled_metrics: list[str] = []
        clipped_metrics: list[str] = []
        history_points: dict[str, int] = {}
        smoothing_weight = settings.FORECAST_SIGNAL_SMOOTHING_WEIGHT

        for signal_type, metrics in self.METRIC_SPECS.items():
            current_snapshot = current_by_type.get(signal_type)
            current_metrics = current_snapshot.normalized_metrics if current_snapshot else {}
            history_metrics = history.get(signal_type, {})

            for metric_name, spec in metrics.items():
                output_name = spec["output"]
                history_values = history_metrics.get(metric_name, [])
                history_points[output_name] = len(history_values)
                current_present = metric_name in current_metrics
                current_value = current_metrics.get(metric_name) if current_present else None

                if current_value is None:
                    filled_metrics.append(output_name)
                    normalized_value = self._average(history_values) if history_values else spec["default"]
                else:
                    clipped_value = min(spec["max"], max(spec["min"], float(current_value)))
                    if clipped_value != float(current_value):
                        clipped_metrics.append(output_name)
                    normalized_value = clipped_value
                    if history_values:
                        normalized_value = round(
                            (smoothing_weight * clipped_value)
                            + ((1 - smoothing_weight) * self._average(history_values)),
                            3,
                        )

                cast_type = spec["cast"]
                if cast_type is int:
                    cleaned[output_name] = int(round(float(normalized_value)))
                else:
                    cleaned[output_name] = round(float(normalized_value), 3)

        return cleaned, {
            "filled_metrics": filled_metrics,
            "clipped_metrics": clipped_metrics,
            "history_points": history_points,
            "lookback_hours": settings.FORECAST_SNAPSHOT_LOOKBACK_HOURS,
            "history_limit": settings.FORECAST_SNAPSHOT_HISTORY_LIMIT,
            "smoothing_weight": smoothing_weight,
        }

    async def _load_recent_history(
        self,
        db: AsyncSession | None,
        zone: str,
        current_by_type: dict[str, Any],
    ) -> dict[str, dict[str, list[float]]]:
        if not db:
            return {}

        cutoff = utc_now_naive() - timedelta(hours=settings.FORECAST_SNAPSHOT_LOOKBACK_HOURS)
        rows = (
            await db.execute(
                select(SignalSnapshot)
                .where(
                    SignalSnapshot.zone == zone,
                    SignalSnapshot.captured_at >= cutoff,
                )
                .order_by(desc(SignalSnapshot.captured_at))
            )
        ).scalars().all()

        grouped: dict[str, dict[str, list[float]]] = {}
        counts: dict[tuple[str, str], int] = {}
        history_limit = settings.FORECAST_SNAPSHOT_HISTORY_LIMIT

        for row in rows:
            current_snapshot = current_by_type.get(row.signal_type)
            if current_snapshot and row.captured_at >= current_snapshot.captured_at:
                continue

            specs = self.METRIC_SPECS.get(row.signal_type, {})
            for metric_name in specs:
                metric_value = row.normalized_metrics.get(metric_name)
                if not isinstance(metric_value, (int, float)):
                    continue

                count_key = (row.signal_type, metric_name)
                if counts.get(count_key, 0) >= history_limit:
                    continue

                grouped.setdefault(row.signal_type, {}).setdefault(metric_name, []).append(float(metric_value))
                counts[count_key] = counts.get(count_key, 0) + 1

        return grouped

    @staticmethod
    def _average(values: list[float]) -> float:
        if not values:
            return 0.0
        return round(sum(values) / len(values), 3)


forecast_preprocessor = ForecastPreprocessor()
