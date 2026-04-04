"""Forward-looking disruption forecast service."""

from __future__ import annotations

from datetime import timedelta
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.forecast_preprocessor import forecast_preprocessor
from backend.core.location_service import location_service
from backend.core.risk_model_service import risk_model_service
from backend.core.signal_service import signal_service
from backend.db.models import Event, Payout
from backend.ml.explainability import summarize_forecast
from backend.ml.features.risk_features import risk_feature_builder
from backend.utils.time import utc_now_naive


@dataclass
class ForecastWindow:
    horizon_hours: int
    risk_score: float
    likely_triggers: list[str]
    components: dict[str, float]
    explanation: list[dict[str, Any]]
    summary: str


class ForecastEngine:
    async def forecast_zone(self, db: AsyncSession, city: str, zone: str, horizon_hours: int = 24) -> dict[str, Any]:
        zone_record = await location_service.resolve_zone(db, city, zone)
        month = 7 if horizon_hours >= 168 else 6
        signal_snapshot = await signal_service.fetch_zone_snapshot(db, zone, city, mode="live")
        cleaned_signals, preprocessing = await forecast_preprocessor.preprocess(db, zone_record.slug, signal_snapshot)
        incidents_7d, incidents_30d = await self._incident_pressure(db, zone_record.slug)
        payout_pressure = await self._payout_pressure(db, city)

        context = {
            "city": city,
            "month": month,
            "city_base_risk": settings.CITY_RISK_PROFILES.get(city, {}).get("base_risk", 0.5),
            "zone_profile_risk": float(zone_record.risk_profile.base_risk) if zone_record.risk_profile else settings.CITY_RISK_PROFILES.get(city, {}).get("base_risk", 0.5),
            "incidents_7d": incidents_7d,
            "incidents_30d": incidents_30d,
            "rain_intensity": min(1.0, float(cleaned_signals.get("rain", 0) or 0) / max(1.0, settings.RAIN_THRESHOLD_MM * 1.5)),
            "heat_index": min(1.0, float(cleaned_signals.get("heat", 0) or 0) / max(1.0, settings.HEAT_THRESHOLD_C + 6)),
            "aqi_normalized": min(1.0, float(cleaned_signals.get("aqi", 0) or 0) / 500.0),
            "traffic_congestion": min(1.0, float(cleaned_signals.get("traffic", 0) or 0)),
            "platform_instability": min(1.0, float(cleaned_signals.get("platform_outage", 0) or 0)),
            "worker_density": min(1.0, 0.25 + incidents_7d * 0.04),
            "payout_pressure_30d": payout_pressure,
        }

        ml_result = risk_model_service.score(context)
        features = ml_result["features"]
        if ml_result["fallback_used"]:
            base_risk = (
                0.22 * features["city_base_risk"]
                + 0.12 * features["zone_profile_risk"]
                + 0.14 * features["incidents_7d"]
                + 0.10 * features["incidents_30d"]
                + 0.12 * features["rain_intensity"]
                + 0.07 * features["heat_index"]
                + 0.05 * features["aqi_normalized"]
                + 0.08 * features["traffic_congestion"]
                + 0.05 * features["platform_instability"]
                + 0.05 * features["worker_density"]
            )
            risk_score = round(max(0.02, min(0.98, base_risk)), 3)
        else:
            risk_score = ml_result["risk_score"]

        components = {
            "weather_impact": round((features["rain_intensity"] + features["heat_index"]) / 2, 3),
            "aqi_impact": round(features["aqi_normalized"], 3),
            "traffic_impact": round(features["traffic_congestion"], 3),
            "platform_impact": round(features["platform_instability"], 3),
            "incident_momentum": round((features["incidents_7d"] + features["incidents_30d"]) / 2, 3),
            "seasonal_profile": round((features["month_sin"] + features["month_cos"]) / 2, 3),
        }
        top_factors = risk_feature_builder.explain(
            {
                "rain_intensity": features["rain_intensity"],
                "traffic_congestion": features["traffic_congestion"],
                "platform_instability": features["platform_instability"],
                "incidents_7d": features["incidents_7d"],
                "incidents_30d": features["incidents_30d"],
                "aqi_normalized": features["aqi_normalized"],
            }
        )
        likely_triggers = self._likely_triggers(features)
        return {
            "city": city,
            "zone": zone,
            "horizon_hours": horizon_hours,
            "projected_risk": risk_score,
            "confidence": ml_result.get("confidence", 0.0),
            "model_version": ml_result.get("model_version", "rule-based"),
            "fallback_used": ml_result["fallback_used"],
            "signal_preprocessing": preprocessing,
            "likely_triggers": likely_triggers,
            "components": components,
            "explanation": top_factors,
            "summary": summarize_forecast(city, horizon_hours, top_factors),
        }

    async def forecast_city(self, db: AsyncSession, city: str, horizon_hours: int = 24) -> dict[str, Any]:
        zones = await location_service.get_active_zones(db, city_slug=city)
        forecasts = [await self.forecast_zone(db, city, zone.slug, horizon_hours=horizon_hours) for zone in zones]
        forecasts.sort(key=lambda item: item["projected_risk"], reverse=True)
        return {"city": city, "horizon_hours": horizon_hours, "zones": forecasts}

    async def zone_risk(self, db: AsyncSession, city: str) -> list[dict[str, Any]]:
        current = await self.forecast_city(db, city, horizon_hours=24)
        week = await self.forecast_city(db, city, horizon_hours=168)
        week_lookup = {item["zone"]: item for item in week["zones"]}
        ranked = []
        for item in current["zones"]:
            future = week_lookup[item["zone"]]
            trend = "stable"
            if future["projected_risk"] > item["projected_risk"] + 0.05:
                trend = "increasing"
            elif future["projected_risk"] < item["projected_risk"] - 0.05:
                trend = "easing"
            ranked.append(
                {
                    "zone": item["zone"],
                    "current_risk": item["projected_risk"],
                    "forecast_24h": item["projected_risk"],
                    "forecast_7d": future["projected_risk"],
                    "trend": trend,
                    "likely_triggers": item["likely_triggers"],
                }
            )
        ranked.sort(key=lambda row: row["forecast_24h"], reverse=True)
        return ranked

    @staticmethod
    def _likely_triggers(features: dict[str, float]) -> list[str]:
        mapping = {
            "rain_intensity": "rain",
            "heat_index": "heat",
            "aqi_normalized": "aqi",
            "traffic_congestion": "traffic",
            "platform_instability": "platform_outage",
        }
        return [trigger for feature, trigger in mapping.items() if features.get(feature, 0.0) >= 0.5]

    async def _incident_pressure(self, db: AsyncSession, zone: str) -> tuple[int, int]:
        now = utc_now_naive()
        incidents_7d = (
            await db.execute(
                select(func.count(Event.id)).where(
                    Event.zone == zone,
                    Event.status == "active",
                    Event.started_at >= now - timedelta(days=7),
                )
            )
        ).scalar_one()
        incidents_30d = (
            await db.execute(
                select(func.count(Event.id)).where(
                    Event.zone == zone,
                    Event.started_at >= now - timedelta(days=30),
                )
            )
        ).scalar_one()
        return int(incidents_7d or 0), int(incidents_30d or 0)

    async def _payout_pressure(self, db: AsyncSession, city: str) -> float:
        payout_count = (
            await db.execute(
                select(func.count(Payout.id))
            )
        ).scalar_one_or_none()
        base = settings.CITY_RISK_PROFILES.get(city, {}).get("base_risk", 0.5)
        return min(1.0, (float(payout_count or 0) / 25.0) + base * 0.1)


forecast_engine = ForecastEngine()
