import pytest

from backend.providers.aqi import RealAQIProvider
from backend.providers.weather import RealWeatherProvider


@pytest.mark.asyncio
async def test_real_weather_provider_returns_openweather_payload(monkeypatch):
    provider = RealWeatherProvider()

    async def fake_fetch(zone: str, city: str):
        return (
            {
                "rain": {"1h": 12.5},
                "main": {"temp": 31.2},
                "weather": [{"main": "Rain"}],
            },
            187,
            "req-weather-1",
        )

    monkeypatch.setattr(provider, "_fetch_openweather_payload", fake_fetch)

    result = await provider.fetch(None, "south_delhi", "delhi", "real")

    assert result.provider == "openweather"
    assert result.is_fallback is False
    assert result.latency_ms == 187
    assert result.request_id == "req-weather-1"
    assert result.raw_payload["rainfall_mm_hr"] == 12.5
    assert result.raw_payload["temperature_c"] == 31.2


@pytest.mark.asyncio
async def test_real_weather_provider_falls_back_to_mock_when_fetch_fails(monkeypatch):
    provider = RealWeatherProvider()

    async def fake_fetch(zone: str, city: str):
        raise RuntimeError("weather api unavailable")

    monkeypatch.setattr(provider, "_fetch_openweather_payload", fake_fetch)

    result = await provider.fetch(None, "south_delhi", "delhi", "real")

    assert result.provider == "openweather_fallback"
    assert result.is_fallback is True
    assert result.raw_payload["fallback_source"] == "weather_simulator"
    assert "fallback_reason" in result.raw_payload


@pytest.mark.asyncio
async def test_real_aqi_provider_returns_openweather_air_payload(monkeypatch):
    provider = RealAQIProvider()

    async def fake_fetch(zone: str, city: str):
        return (
            {
                "list": [
                    {
                        "main": {"aqi": 4},
                        "components": {"pm2_5": 81.2, "pm10": 126.4},
                    }
                ]
            },
            203,
            "req-aqi-1",
        )

    monkeypatch.setattr(provider, "_fetch_openweather_payload", fake_fetch)

    result = await provider.fetch(None, "south_delhi", "delhi", "real")

    assert result.provider == "openweather_air"
    assert result.is_fallback is False
    assert result.latency_ms == 203
    assert result.request_id == "req-aqi-1"
    assert result.raw_payload["aqi_value"] == 200
    assert result.raw_payload["aqi_bucket"] == 4
    assert result.raw_payload["pm25"] == 81.2


@pytest.mark.asyncio
async def test_real_aqi_provider_falls_back_to_mock_when_fetch_fails(monkeypatch):
    provider = RealAQIProvider()

    async def fake_fetch(zone: str, city: str):
        raise RuntimeError("aqi api unavailable")

    monkeypatch.setattr(provider, "_fetch_openweather_payload", fake_fetch)

    result = await provider.fetch(None, "south_delhi", "delhi", "real")

    assert result.provider == "openweather_air_fallback"
    assert result.is_fallback is True
    assert result.raw_payload["fallback_source"] == "aqi_simulator"
    assert "fallback_reason" in result.raw_payload
