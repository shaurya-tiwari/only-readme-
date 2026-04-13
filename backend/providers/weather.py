"""Weather provider implementations."""

from __future__ import annotations

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.location_service import ZONE_CENTROIDS
from backend.providers.base import ProviderFetchResult
from backend.utils.time import utc_now_naive
from simulations.weather_mock import weather_simulator


class MockWeatherProvider:
    signal_type = "weather"
    source_name = "weather_simulator"

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
            raw_payload=weather_simulator.get_weather(zone),
        )


class RealWeatherProvider:
    signal_type = "weather"
    source_name = "openweather"
    fallback_source_name = "openweather_fallback"

    def _coordinates_for_zone(self, zone: str) -> tuple[float, float] | None:
        coords = ZONE_CENTROIDS.get(zone)
        if coords is None:
            return None
        return float(coords[0]), float(coords[1])

    async def _fetch_openweather_payload(self, zone: str, city: str) -> tuple[dict, int, str | None]:
        coords = self._coordinates_for_zone(zone)
        if coords is None:
            raise ValueError(f"No centroid configured for zone '{zone}'")
        if not settings.OPENWEATHER_API_KEY:
            raise ValueError("OPENWEATHER_API_KEY is not configured")

        lat, lon = coords
        request_started = utc_now_naive()
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": "metric",
                },
            )
            response.raise_for_status()
            payload = response.json()
        latency_ms = int(max(0.0, (utc_now_naive() - request_started).total_seconds()) * 1000)
        return payload, latency_ms, response.headers.get("x-request-id")

    def _normalize_openweather_payload(self, payload: dict) -> dict:
        rain = payload.get("rain") if isinstance(payload.get("rain"), dict) else {}
        main = payload.get("main") if isinstance(payload.get("main"), dict) else {}
        weather_list = payload.get("weather") if isinstance(payload.get("weather"), list) else []
        weather_entry = weather_list[0] if weather_list and isinstance(weather_list[0], dict) else {}
        return {
            "rainfall_mm_hr": float(rain.get("1h", 0) or 0),
            "temperature_c": float(main.get("temp", 0) or 0),
            "scenario": weather_entry.get("main", "real_weather"),
            "timestamp": utc_now_naive().isoformat(),
            "provider_payload": payload,
        }

    async def fetch(
        self,
        db: AsyncSession | None,
        zone: str,
        city: str,
        source_mode: str,
    ) -> ProviderFetchResult:
        captured_at = utc_now_naive()
        try:
            payload, latency_ms, request_id = await self._fetch_openweather_payload(zone, city)
            normalized_raw = self._normalize_openweather_payload(payload)
            return ProviderFetchResult(
                signal_type=self.signal_type,
                provider=self.source_name,
                source_mode=source_mode,
                city=city,
                zone=zone,
                captured_at=captured_at,
                raw_payload=normalized_raw,
                latency_ms=latency_ms,
                is_fallback=False,
                request_id=request_id,
            )
        except Exception as exc:
            fallback_payload = weather_simulator.get_weather(zone)
            fallback_payload = {
                **fallback_payload,
                "fallback_reason": str(exc),
                "fallback_source": MockWeatherProvider.source_name,
            }
            return ProviderFetchResult(
                signal_type=self.signal_type,
                provider=self.fallback_source_name,
                source_mode=source_mode,
                city=city,
                zone=zone,
                captured_at=captured_at,
                raw_payload=fallback_payload,
                latency_ms=0,
                is_fallback=True,
                request_id=None,
            )

