"""Behavioral platform telemetry generator used by mock and DB-backed providers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import random
from typing import Any

from backend.config import settings


@dataclass(frozen=True)
class ZoneTelemetryProfile:
    zone_class: str
    baseline_orders: int
    resilience: float
    workforce_density: float
    baseline_delay_min: float


class PlatformTelemetryEngine:
    """Generates time-aware, disruption-aware platform telemetry."""

    DAYPART_MULTIPLIERS = {
        "late_night": 0.55,
        "breakfast": 0.75,
        "lunch": 1.15,
        "afternoon": 0.70,
        "dinner": 1.35,
        "evening": 0.85,
    }

    ZONE_PROFILES: dict[str, ZoneTelemetryProfile] = {
        "south_delhi": ZoneTelemetryProfile("high_density", 140, 0.82, 0.46, 23.0),
        "central_delhi": ZoneTelemetryProfile("high_density", 135, 0.80, 0.44, 24.0),
        "east_delhi": ZoneTelemetryProfile("mixed_density", 112, 0.68, 0.42, 25.0),
        "north_delhi": ZoneTelemetryProfile("mixed_density", 105, 0.65, 0.40, 26.0),
        "west_delhi": ZoneTelemetryProfile("residential_spread", 96, 0.61, 0.38, 27.0),
        "south_mumbai": ZoneTelemetryProfile("high_density", 150, 0.83, 0.48, 24.0),
        "western_suburbs": ZoneTelemetryProfile("mixed_density", 118, 0.72, 0.43, 25.0),
        "navi_mumbai": ZoneTelemetryProfile("residential_spread", 92, 0.66, 0.36, 27.0),
        "koramangala": ZoneTelemetryProfile("high_density", 132, 0.79, 0.45, 23.0),
        "whitefield": ZoneTelemetryProfile("mixed_density", 104, 0.69, 0.39, 26.0),
    }

    CITY_DEFAULTS: dict[str, ZoneTelemetryProfile] = {
        "delhi": ZoneTelemetryProfile("mixed_density", 108, 0.70, 0.41, 25.0),
        "mumbai": ZoneTelemetryProfile("mixed_density", 116, 0.74, 0.42, 25.0),
        "bengaluru": ZoneTelemetryProfile("mixed_density", 102, 0.72, 0.40, 24.0),
        "chennai": ZoneTelemetryProfile("mixed_density", 96, 0.68, 0.38, 25.0),
        "hyderabad": ZoneTelemetryProfile("mixed_density", 98, 0.71, 0.39, 24.0),
        "pune": ZoneTelemetryProfile("mixed_density", 90, 0.69, 0.37, 24.0),
        "kolkata": ZoneTelemetryProfile("mixed_density", 94, 0.67, 0.37, 25.0),
    }

    SCENARIO_EFFECTS = {
        "normal": {"orders": 1.0, "delay": 1.0, "worker_capacity": 1.0, "status": "operational"},
        "low_demand": {"orders": 0.72, "delay": 1.06, "worker_capacity": 0.93, "status": "operational"},
        "platform_outage": {"orders": 0.22, "delay": 1.60, "worker_capacity": 0.58, "status": "degraded"},
        "peak_demand": {"orders": 1.28, "delay": 1.22, "worker_capacity": 1.08, "status": "stressed"},
    }

    def build_status(
        self,
        *,
        zone: str,
        city: str,
        scenario: str = "normal",
        signal_context: dict[str, dict[str, Any]] | None = None,
        active_worker_count: int | None = None,
        captured_at: datetime,
        provider_name: str,
        model_variant: str = "baseline",
    ) -> dict[str, Any]:
        signal_context = signal_context or {}
        weather = signal_context.get("weather") or {}
        aqi = signal_context.get("aqi") or {}
        traffic = signal_context.get("traffic") or {}

        profile = self.ZONE_PROFILES.get(zone) or self.CITY_DEFAULTS.get(city) or self.CITY_DEFAULTS["delhi"]
        daypart = self._daypart(captured_at.hour)
        normal_avg_orders = max(18, int(round(profile.baseline_orders * self.DAYPART_MULTIPLIERS[daypart])))
        scenario_key = scenario if scenario in self.SCENARIO_EFFECTS else "normal"
        scenario_effect = self.SCENARIO_EFFECTS[scenario_key]

        rainfall = float(weather.get("rainfall_mm_hr", 0) or 0)
        congestion = float(traffic.get("congestion_index", 0) or 0)
        aqi_value = float(aqi.get("aqi_value", 0) or 0)

        weather_severity = min(1.0, rainfall / max(1.0, settings.RAIN_THRESHOLD_MM))
        traffic_severity = min(1.0, congestion / max(0.01, settings.TRAFFIC_THRESHOLD))
        aqi_severity = min(1.0, aqi_value / max(1.0, float(settings.AQI_THRESHOLD)))

        rng = self._seeded_rng(zone, city, scenario_key, captured_at, model_variant)
        resilience = profile.resilience if model_variant == "behavioral" else 0.55
        order_noise = rng.uniform(0.94, 1.06) if model_variant == "behavioral" else rng.uniform(0.97, 1.03)
        delay_noise = rng.uniform(0.96, 1.10) if model_variant == "behavioral" else rng.uniform(0.98, 1.04)

        weather_drag = weather_severity * (0.34 if model_variant == "behavioral" else 0.18)
        traffic_drag = traffic_severity * (0.16 if model_variant == "behavioral" else 0.08)
        aqi_drag = aqi_severity * (0.10 if model_variant == "behavioral" else 0.05)
        protected_drag = (weather_drag + traffic_drag + aqi_drag) * (1.0 - (resilience * 0.55))

        order_factor = scenario_effect["orders"] * max(0.08, 1.0 - protected_drag) * order_noise
        orders_per_hour = max(0, int(round(normal_avg_orders * order_factor)))

        worker_capacity_factor = scenario_effect["worker_capacity"] * max(
            0.35,
            1.0 - ((weather_severity * 0.12) + (aqi_severity * 0.08)),
        )
        estimated_active_workers = max(
            1,
            int(round((normal_avg_orders * profile.workforce_density) * worker_capacity_factor)),
        )
        if active_worker_count is not None and active_worker_count > 0:
            if model_variant == "behavioral":
                active_workers = max(1, min(active_worker_count, estimated_active_workers))
            else:
                active_workers = max(1, active_worker_count)
        else:
            active_workers = estimated_active_workers

        fulfillment_delay = profile.baseline_delay_min * scenario_effect["delay"]
        fulfillment_delay *= 1 + (traffic_severity * 0.50) + (weather_severity * 0.22) + (aqi_severity * 0.08)
        fulfillment_delay *= delay_noise
        fulfillment_delay = round(max(10.0, fulfillment_delay), 1)

        order_density_drop = round(max(0.0, min(1.0, 1 - (orders_per_hour / max(1, normal_avg_orders)))), 3)
        worker_utilization = round(min(1.0, orders_per_hour / max(1, active_workers * 3)), 3)
        confidence = round(
            min(
                0.96,
                0.68
                + (0.08 if signal_context else 0.0)
                + (0.06 if active_worker_count is not None else 0.0)
                + (0.05 if model_variant == "behavioral" else 0.0),
            ),
            3,
        )

        status = scenario_effect["status"]
        if order_density_drop >= settings.PLATFORM_OUTAGE_THRESHOLD:
            status = "degraded"
        elif order_density_drop >= settings.PLATFORM_OUTAGE_THRESHOLD * 0.6:
            status = "stressed"

        return {
            "zone": zone,
            "city": city,
            "timestamp": captured_at.isoformat(),
            "orders_per_hour": orders_per_hour,
            "normal_avg_orders": normal_avg_orders,
            "order_density_drop": order_density_drop,
            "active_workers": active_workers,
            "fulfillment_delay": fulfillment_delay,
            "worker_utilization": worker_utilization,
            "platform_status": status,
            "confidence": confidence,
            "api_source": provider_name,
            "scenario": scenario_key,
            "daypart": daypart,
            "zone_class": profile.zone_class,
            "model_variant": model_variant,
            "signal_inputs": {
                "rainfall_mm_hr": rainfall,
                "congestion_index": congestion,
                "aqi_value": aqi_value,
            },
        }

    def _daypart(self, hour: int) -> str:
        if 0 <= hour < 6:
            return "late_night"
        if 6 <= hour < 11:
            return "breakfast"
        if 11 <= hour < 15:
            return "lunch"
        if 15 <= hour < 18:
            return "afternoon"
        if 18 <= hour < 23:
            return "dinner"
        return "evening"

    def _seeded_rng(
        self,
        zone: str,
        city: str,
        scenario: str,
        captured_at: datetime,
        model_variant: str,
    ) -> random.Random:
        bucket = captured_at.replace(minute=(captured_at.minute // 5) * 5, second=0, microsecond=0)
        seed_input = f"{city}:{zone}:{scenario}:{model_variant}:{bucket.isoformat()}"
        seed = int(hashlib.sha256(seed_input.encode("utf-8")).hexdigest()[:16], 16)
        return random.Random(seed)


platform_telemetry_engine = PlatformTelemetryEngine()
