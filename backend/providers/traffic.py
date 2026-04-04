"""Traffic provider implementations."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

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

    async def fetch(
        self,
        db: AsyncSession | None,
        zone: str,
        city: str,
        source_mode: str,
    ) -> ProviderFetchResult:
        raise NotImplementedError("TRAFFIC_SOURCE=real is planned but not implemented yet.")

