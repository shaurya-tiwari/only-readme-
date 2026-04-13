"""Traffic provider implementations."""

from __future__ import annotations

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.location_service import ZONE_CENTROIDS
from backend.providers.base import ProviderFetchResult
from backend.utils.time import utc_now_naive
from simulations.traffic_mock import traffic_simulator


class MockTrafficProvider:
    signal_type = "traffic"
    source_name = "traffic_simulator"

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
            raw_payload=traffic_simulator.get_traffic(zone),
        )


class RealTrafficProvider:
    signal_type = "traffic"
    source_name = "tomtom"
    fallback_source_name = "tomtom_fallback"

    def _coordinates_for_zone(self, zone: str) -> tuple[float, float] | None:
        coords = ZONE_CENTROIDS.get(zone)
        if coords is None:
            return None
        return float(coords[0]), float(coords[1])

    async def _fetch_tomtom_flow_payload(self, zone: str, city: str) -> tuple[dict, int, str | None]:
        coords = self._coordinates_for_zone(zone)
        if coords is None:
            raise ValueError(f"No centroid configured for zone '{zone}'")
        if not settings.TOMTOM_API_KEY:
            raise ValueError("TOMTOM_API_KEY is not configured")

        lat, lon = coords
        request_started = utc_now_naive()
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json",
                params={
                    "key": settings.TOMTOM_API_KEY,
                    "point": f"{lat},{lon}",
                    "unit": "kmph",
                },
            )
            response.raise_for_status()
            payload = response.json()
        latency_ms = int(max(0.0, (utc_now_naive() - request_started).total_seconds()) * 1000)
        return payload, latency_ms, response.headers.get("Tracking-ID")

    def _normalize_tomtom_payload(self, payload: dict) -> dict:
        flow = payload.get("flowSegmentData") if isinstance(payload.get("flowSegmentData"), dict) else {}
        current_speed = float(flow.get("currentSpeed", 0) or 0)
        free_flow_speed = float(flow.get("freeFlowSpeed", 0) or 0)
        current_travel_time = float(flow.get("currentTravelTime", 0) or 0)
        free_flow_travel_time = float(flow.get("freeFlowTravelTime", 0) or 0)
        road_closure = bool(flow.get("roadClosure", False))
        confidence = float(flow.get("confidence", 0) or 0)

        speed_ratio = 1.0 if road_closure else (
            max(0.0, min(1.0, current_speed / free_flow_speed)) if free_flow_speed > 0 else 1.0
        )
        travel_time_ratio = (
            max(1.0, current_travel_time / free_flow_travel_time) if free_flow_travel_time > 0 else 1.0
        )
        time_pressure = min(1.0, max(0.0, (travel_time_ratio - 1.0) / 1.5))
        congestion_from_speed = 1.0 - speed_ratio
        congestion_index = 1.0 if road_closure else round(min(1.0, max(congestion_from_speed, time_pressure)), 3)

        if congestion_index >= 0.9:
            congestion_level = "gridlock"
        elif congestion_index >= 0.75:
            congestion_level = "severe"
        elif congestion_index >= 0.5:
            congestion_level = "heavy"
        elif congestion_index >= 0.3:
            congestion_level = "moderate"
        else:
            congestion_level = "free_flow"

        return {
            "zone": payload.get("zone"),
            "timestamp": utc_now_naive().isoformat(),
            "congestion_index": congestion_index,
            "congestion_level": congestion_level,
            "average_speed_kmh": round(current_speed, 1),
            "delay_minutes": round(max(0.0, current_travel_time - free_flow_travel_time) / 60.0, 1),
            "incidents": 1 if road_closure else 0,
            "api_source": self.source_name,
            "scenario": "real_traffic",
            "current_speed_kmh": round(current_speed, 1),
            "free_flow_speed_kmh": round(free_flow_speed, 1),
            "travel_time_ratio": round(travel_time_ratio, 3),
            "confidence": round(confidence, 3),
            "road_closure": road_closure,
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
            payload, latency_ms, request_id = await self._fetch_tomtom_flow_payload(zone, city)
            normalized_raw = self._normalize_tomtom_payload(payload)
            normalized_raw["zone"] = zone
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
            fallback_payload = traffic_simulator.get_traffic(zone)
            fallback_payload = {
                **fallback_payload,
                "fallback_reason": str(exc),
                "fallback_source": MockTrafficProvider.source_name,
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

