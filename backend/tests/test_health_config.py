"""Health config endpoint tests."""

import pytest


@pytest.mark.asyncio
async def test_health_config_exposes_signal_sources(client):
    response = await client.get("/health/config")
    assert response.status_code == 200
    payload = response.json()
    assert payload["signal_sources"]["mode"] == "mock"
    assert payload["signal_sources"]["weather"] == "mock"
    assert payload["signal_source_status"]["weather"]["configured_source"] == "mock"
    assert payload["signal_source_status"]["weather"]["captured_at"] is None
    assert payload["provider_snapshot_persistence_enabled"] is True
    assert payload["signal_runtime"]["snapshots"]["retention_days"] == 14
    assert payload["shadow_diff_summary"]["total_diffs"] == 0


@pytest.mark.asyncio
async def test_health_config_exposes_signal_runtime_freshness_contract(client, monkeypatch):
    async def fake_source_runtime_status(db):
        return {
            "weather": {
                "configured_source": "real",
                "latest_provider": "openweather",
                "source_mode": "real",
                "captured_at": "2026-04-07T12:00:00",
                "data_age_seconds": 42,
                "latency_ms": 145,
                "is_fallback": False,
                "quality_score": 0.93,
            }
        }

    monkeypatch.setattr("backend.api.health.signal_service.source_runtime_status", fake_source_runtime_status)

    response = await client.get("/health/config")
    assert response.status_code == 200
    payload = response.json()
    weather_status = payload["signal_source_status"]["weather"]

    assert weather_status["latest_provider"] == "openweather"
    assert weather_status["captured_at"] is not None
    assert weather_status["data_age_seconds"] == 42
    assert weather_status["latency_ms"] == 145
    assert weather_status["is_fallback"] is False
