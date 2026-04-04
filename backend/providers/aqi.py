"""AQI provider implementations."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

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
    source_name = "waqi"

    async def fetch(
        self,
        db: AsyncSession | None,
        zone: str,
        city: str,
        source_mode: str,
    ) -> ProviderFetchResult:
        raise NotImplementedError("AQI_SOURCE=real is planned but not implemented yet.")

