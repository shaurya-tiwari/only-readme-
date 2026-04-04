"""Weather provider implementations."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

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

    async def fetch(
        self,
        db: AsyncSession | None,
        zone: str,
        city: str,
        source_mode: str,
    ) -> ProviderFetchResult:
        raise NotImplementedError("WEATHER_SOURCE=real is planned but not implemented yet.")

