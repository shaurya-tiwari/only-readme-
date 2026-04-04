"""Provider registry and source selection."""

from __future__ import annotations

from typing import Callable

from backend.config import settings
from backend.providers.aqi import MockAQIProvider, RealAQIProvider
from backend.providers.base import NormalizedSignalSnapshot, ProviderFetchResult, SignalProvider
from backend.providers.normalizers.aqi import normalize_aqi
from backend.providers.normalizers.platform import normalize_platform
from backend.providers.normalizers.traffic import normalize_traffic
from backend.providers.normalizers.weather import normalize_weather
from backend.providers.platform import DatabasePlatformProvider, MockPlatformProvider, PartnerPlatformProvider
from backend.providers.traffic import MockTrafficProvider, RealTrafficProvider
from backend.providers.weather import MockWeatherProvider, RealWeatherProvider


class ProviderRegistry:
    """Resolves signal providers and normalizers from runtime config."""

    def __init__(self) -> None:
        self._providers: dict[str, dict[str, SignalProvider]] = {
            "weather": {
                "mock": MockWeatherProvider(),
                "real": RealWeatherProvider(),
            },
            "aqi": {
                "mock": MockAQIProvider(),
                "real": RealAQIProvider(),
            },
            "traffic": {
                "mock": MockTrafficProvider(),
                "real": RealTrafficProvider(),
            },
            "platform": {
                "mock": MockPlatformProvider(),
                "db": DatabasePlatformProvider(),
                "partner": PartnerPlatformProvider(),
            },
        }
        self._normalizers: dict[str, Callable[[ProviderFetchResult], NormalizedSignalSnapshot]] = {
            "weather": normalize_weather,
            "aqi": normalize_aqi,
            "traffic": normalize_traffic,
            "platform": normalize_platform,
        }

    def configured_source(self, signal_type: str) -> str:
        if settings.SIGNAL_SOURCE_MODE == "mock":
            return "mock"
        if signal_type == "weather":
            return settings.WEATHER_SOURCE
        if signal_type == "aqi":
            return settings.AQI_SOURCE
        if signal_type == "traffic":
            return settings.TRAFFIC_SOURCE
        if signal_type == "platform":
            return settings.PLATFORM_SOURCE
        raise KeyError(f"Unknown signal type: {signal_type}")

    def get_provider(self, signal_type: str) -> SignalProvider:
        source = self.configured_source(signal_type)
        return self._providers[signal_type][source]

    def get_shadow_provider(self, signal_type: str) -> SignalProvider | None:
        if settings.SIGNAL_SOURCE_MODE != "shadow":
            return None
        configured_source = self.configured_source(signal_type)
        if configured_source == "mock":
            return self._providers[signal_type]["mock"]
        return self._providers[signal_type].get("mock")

    def normalize(self, fetch_result: ProviderFetchResult) -> NormalizedSignalSnapshot:
        return self._normalizers[fetch_result.signal_type](fetch_result)

    def source_overview(self) -> dict[str, str]:
        return {
            "mode": settings.SIGNAL_SOURCE_MODE,
            "weather": self.configured_source("weather"),
            "aqi": self.configured_source("aqi"),
            "traffic": self.configured_source("traffic"),
            "platform": self.configured_source("platform"),
        }


provider_registry = ProviderRegistry()
