"""AQI provider implementations."""

from __future__ import annotations

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.location_service import ZONE_CENTROIDS
from backend.providers.base import ProviderFetchResult
from backend.utils.time import utc_now_naive
from simulations.aqi_mock import aqi_simulator


class MockAQIProvider:
    signal_type = "aqi"
    source_name = "aqi_simulator"

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
            raw_payload=aqi_simulator.get_aqi(zone, city),
        )


class RealAQIProvider:
    signal_type = "aqi"
    source_name = "openweather_air"
    fallback_source_name = "openweather_air_fallback"

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
                "https://api.openweathermap.org/data/2.5/air_pollution",
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": settings.OPENWEATHER_API_KEY,
                },
            )
            response.raise_for_status()
            payload = response.json()
        latency_ms = int(max(0.0, (utc_now_naive() - request_started).total_seconds()) * 1000)
        return payload, latency_ms, response.headers.get("x-request-id")

    def _aqi_bucket_to_value(self, bucket: int) -> int:
        return {
            1: 50,
            2: 100,
            3: 150,
            4: 200,
            5: 300,
        }.get(int(bucket or 0), 0)

    def _normalize_openweather_payload(self, payload: dict) -> dict:
        entries = payload.get("list") if isinstance(payload.get("list"), list) else []
        entry = entries[0] if entries and isinstance(entries[0], dict) else {}
        main = entry.get("main") if isinstance(entry.get("main"), dict) else {}
        components = entry.get("components") if isinstance(entry.get("components"), dict) else {}
        aqi_bucket = int(main.get("aqi", 0) or 0)
        return {
            "aqi_value": self._aqi_bucket_to_value(aqi_bucket),
            "aqi_bucket": aqi_bucket,
            "category": {
                1: "good",
                2: "fair",
                3: "moderate",
                4: "poor",
                5: "very_poor",
            }.get(aqi_bucket, "unknown"),
            "dominant_pollutant": "pm25",
            "pm25": float(components.get("pm2_5", 0) or 0),
            "pm10": float(components.get("pm10", 0) or 0),
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
            fallback_payload = aqi_simulator.get_aqi(zone, city)
            fallback_payload = {
                **fallback_payload,
                "fallback_reason": str(exc),
                "fallback_source": MockAQIProvider.source_name,
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

