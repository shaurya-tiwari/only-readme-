"""Aggregates normalized provider snapshots into the current engine contract."""

from __future__ import annotations

from typing import Any

from backend.config import settings
from backend.providers.base import NormalizedSignalSnapshot


class SignalAggregator:
    """Combines normalized snapshots into the current trigger-engine signal shape."""

    VERSION = "signal-aggregation-v1"

    def build_zone_snapshot(
        self,
        city: str,
        zone: str,
        snapshots: list[NormalizedSignalSnapshot],
        source_mode: str,
        shadow_diffs: list[dict[str, Any]] | None = None,
        social_snapshot_value: float | None = None,
    ) -> dict[str, Any]:
        by_type = {snapshot.signal_type: snapshot for snapshot in snapshots}
        weather = by_type.get("weather")
        aqi = by_type.get("aqi")
        traffic = by_type.get("traffic")
        platform = by_type.get("platform")

        weather_metrics = weather.normalized_metrics if weather else {}
        aqi_metrics = aqi.normalized_metrics if aqi else {}
        traffic_metrics = traffic.normalized_metrics if traffic else {}
        platform_metrics = platform.normalized_metrics if platform else {}

        # Social signal: prefer independently-injected DB value, else weak fallback
        if social_snapshot_value is not None and social_snapshot_value > 0:
            social_signal = social_snapshot_value
        else:
            social_signal = self._fallback_social_signal(
                platform.raw_payload if platform else {},
                platform_metrics,
            )

        timestamp = next(
            (
                snapshot.raw_payload.get("timestamp")
                for snapshot in snapshots
                if snapshot.raw_payload.get("timestamp")
            ),
            None,
        )

        return {
            "city": city,
            "zone": zone,
            "timestamp": timestamp,
            "source_mode": source_mode,
            "aggregation_version": self.VERSION,
            "sources": {snapshot.signal_type: snapshot.provider for snapshot in snapshots},
            "snapshots": snapshots,
            "shadow_diffs": shadow_diffs or [],
            "rain": float(weather_metrics.get("rainfall_mm_hr", 0) or 0),
            "heat": float(weather_metrics.get("temperature_c", 0) or 0),
            "aqi": int(aqi_metrics.get("aqi_value", 0) or 0),
            "traffic": float(traffic_metrics.get("congestion_index", 0) or 0),
            "platform_outage": float(platform_metrics.get("order_density_drop", 0) or 0),
            "social": social_signal,
            "raw_data": {
                "weather": weather.raw_payload if weather else {},
                "aqi": aqi.raw_payload if aqi else {},
                "traffic": traffic.raw_payload if traffic else {},
                "platform": platform.raw_payload if platform else {},
            },
        }

    def _fallback_social_signal(
        self,
        platform_payload: dict[str, Any],
        platform_metrics: dict[str, Any],
    ) -> float:
        """Weak fallback: only fires during extreme platform collapse.

        This is NOT the primary social signal anymore. The real social signal
        comes from admin-injected SignalSnapshots (signal_type='social').
        This fallback exists solely so compound-disaster scenarios that
        explicitly crash the platform still produce some social signal.
        """
        platform_drop = float(platform_metrics.get("order_density_drop", 0) or 0)
        platform_scenario = platform_payload.get("scenario")

        if platform_scenario == "platform_outage" and platform_drop >= 0.85:
            return round(min(1.0, platform_drop * 0.7), 2)

        return 0.0


signal_aggregator = SignalAggregator()
