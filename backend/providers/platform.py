"""Platform signal provider implementations."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.providers.base import ProviderFetchResult
from backend.utils.time import utc_now_naive
from simulations.platform_mock import platform_simulator


class MockPlatformProvider:
    signal_type = "platform"
    source_name = "platform_simulator"

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
            raw_payload=platform_simulator.get_platform_status(zone),
        )


class DatabasePlatformProvider:
    signal_type = "platform"
    source_name = "platform_db"

    async def fetch(
        self,
        db: AsyncSession | None,
        zone: str,
        city: str,
        source_mode: str,
    ) -> ProviderFetchResult:
        raise NotImplementedError("PLATFORM_SOURCE=db is planned but not implemented in this slice yet.")


class PartnerPlatformProvider:
    signal_type = "platform"
    source_name = "platform_partner"

    async def fetch(
        self,
        db: AsyncSession | None,
        zone: str,
        city: str,
        source_mode: str,
    ) -> ProviderFetchResult:
        raise NotImplementedError("PLATFORM_SOURCE=partner is planned but not implemented yet.")

