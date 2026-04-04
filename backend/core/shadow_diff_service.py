"""Structured shadow-mode comparisons for provider output."""

from __future__ import annotations

from typing import Any

from backend.config import settings
from backend.providers.base import NormalizedSignalSnapshot


class ShadowDiffService:
    """Compares primary and shadow snapshots in a structured way."""

    THRESHOLDS = {
        "weather": {
            "rainfall_mm_hr": settings.RAIN_THRESHOLD_MM,
            "temperature_c": settings.HEAT_THRESHOLD_C,
        },
        "aqi": {
            "aqi_value": settings.AQI_THRESHOLD,
        },
        "traffic": {
            "congestion_index": settings.TRAFFIC_THRESHOLD,
        },
        "platform": {
            "order_density_drop": settings.PLATFORM_OUTAGE_THRESHOLD,
        },
    }

    def compare(
        self,
        primary: NormalizedSignalSnapshot,
        shadow: NormalizedSignalSnapshot,
    ) -> dict[str, Any]:
        metric_deltas: dict[str, dict[str, float | int]] = {}
        for metric_name, primary_value in primary.normalized_metrics.items():
            shadow_value = shadow.normalized_metrics.get(metric_name)
            if not isinstance(primary_value, (int, float)) or not isinstance(shadow_value, (int, float)):
                continue
            metric_deltas[metric_name] = {
                "primary": primary_value,
                "shadow": shadow_value,
                "delta": round(float(shadow_value) - float(primary_value), 3),
            }

        thresholds = self.THRESHOLDS.get(primary.signal_type, {})
        primary_crossed = any(
            float(primary.normalized_metrics.get(metric_name, 0) or 0) >= threshold
            for metric_name, threshold in thresholds.items()
        )
        shadow_crossed = any(
            float(shadow.normalized_metrics.get(metric_name, 0) or 0) >= threshold
            for metric_name, threshold in thresholds.items()
        )

        max_delta = max((abs(values["delta"]) for values in metric_deltas.values()), default=0.0)
        requires_attention = (primary_crossed != shadow_crossed) or max_delta >= settings.SHADOW_DIFF_ALERT_DELTA
        return {
            "signal_type": primary.signal_type,
            "city": primary.city,
            "zone": primary.zone,
            "primary_provider": primary.provider,
            "shadow_provider": shadow.provider,
            "compared_at": primary.captured_at,
            "delta": round(max_delta, 3),
            "metric_deltas": metric_deltas,
            "threshold_crossed": primary_crossed != shadow_crossed,
            "requires_attention": requires_attention,
            "threshold_state": {
                "primary": primary_crossed,
                "shadow": shadow_crossed,
            },
        }


shadow_diff_service = ShadowDiffService()
