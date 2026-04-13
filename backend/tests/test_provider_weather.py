import pytest

from backend.providers.aqi import RealAQIProvider
from backend.providers.platform import DatabasePlatformProvider
from backend.providers.traffic import RealTrafficProvider
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


@pytest.mark.asyncio
async def test_real_traffic_provider_returns_tomtom_payload(monkeypatch):
    provider = RealTrafficProvider()

    async def fake_fetch(zone: str, city: str):
        return (
            {
                "flowSegmentData": {
                    "currentSpeed": 18,
                    "freeFlowSpeed": 48,
                    "currentTravelTime": 420,
                    "freeFlowTravelTime": 180,
                    "confidence": 0.92,
                    "roadClosure": False,
                }
            },
            154,
            "req-traffic-1",
        )

    monkeypatch.setattr(provider, "_fetch_tomtom_flow_payload", fake_fetch)

    result = await provider.fetch(None, "south_delhi", "delhi", "real")

    assert result.provider == "tomtom"
    assert result.is_fallback is False
    assert result.latency_ms == 154
    assert result.request_id == "req-traffic-1"
    assert result.raw_payload["congestion_index"] > 0.6
    assert result.raw_payload["api_source"] == "tomtom"
    assert result.raw_payload["average_speed_kmh"] == 18.0


@pytest.mark.asyncio
async def test_real_traffic_provider_falls_back_to_mock_when_fetch_fails(monkeypatch):
    provider = RealTrafficProvider()

    async def fake_fetch(zone: str, city: str):
        raise RuntimeError("traffic api unavailable")

    monkeypatch.setattr(provider, "_fetch_tomtom_flow_payload", fake_fetch)

    result = await provider.fetch(None, "south_delhi", "delhi", "real")

    assert result.provider == "tomtom_fallback"
    assert result.is_fallback is True
    assert result.raw_payload["fallback_source"] == "traffic_simulator"
    assert "fallback_reason" in result.raw_payload


@pytest.mark.asyncio
async def test_database_platform_provider_returns_behavioral_telemetry(monkeypatch):
    provider = DatabasePlatformProvider()

    async def fake_build(db, zone: str, city: str, captured_at):
        return {
            "zone": zone,
            "city": city,
            "timestamp": captured_at.isoformat(),
            "orders_per_hour": 78,
            "normal_avg_orders": 122,
            "order_density_drop": 0.361,
            "active_workers": 29,
            "fulfillment_delay": 31.4,
            "platform_status": "stressed",
            "confidence": 0.84,
            "api_source": "platform_db",
            "scenario": "normal",
            "daypart": "lunch",
            "zone_class": "high_density",
            "model_variant": "behavioral",
        }

    monkeypatch.setattr(provider, "_build_platform_status", fake_build)

    result = await provider.fetch(None, "south_delhi", "delhi", "db")

    assert result.provider == "platform_db"
    assert result.is_fallback is False
    assert result.raw_payload["orders_per_hour"] == 78
    assert result.raw_payload["order_density_drop"] == 0.361
    assert result.raw_payload["active_workers"] == 29
    assert result.raw_payload["fulfillment_delay"] == 31.4


@pytest.mark.asyncio
async def test_database_platform_provider_falls_back_to_mock_when_build_fails(monkeypatch):
    provider = DatabasePlatformProvider()

    async def fake_build(db, zone: str, city: str, captured_at):
        raise RuntimeError("platform telemetry unavailable")

    monkeypatch.setattr(provider, "_build_platform_status", fake_build)

    result = await provider.fetch(None, "south_delhi", "delhi", "db")

    assert result.provider == "platform_db_fallback"
    assert result.is_fallback is True
    assert result.raw_payload["fallback_source"] == "platform_simulator"
    assert "fallback_reason" in result.raw_payload
