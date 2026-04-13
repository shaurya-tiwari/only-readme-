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
    assert "timings_ms" in payload
    assert set(payload["timings_ms"].keys()) == {"runtime", "signals", "diagnostics"}


@pytest.mark.asyncio
async def test_health_split_endpoints_expose_runtime_signal_and_diagnostics_payloads(client):
    runtime_response = await client.get("/config/runtime")
    signals_response = await client.get("/health/signals")
    diagnostics_response = await client.get("/health/diagnostics")

    assert runtime_response.status_code == 200
    assert signals_response.status_code == 200
    assert diagnostics_response.status_code == 200

    runtime_payload = runtime_response.json()
    signals_payload = signals_response.json()
    diagnostics_payload = diagnostics_response.json()

    assert "available_cities" in runtime_payload
    assert "city_zone_map" in runtime_payload
    assert "signal_sources" in signals_payload
    assert "signal_source_status" in signals_payload
    assert "scheduler" in diagnostics_payload
    assert "shadow_diff_summary" in diagnostics_payload
    assert "response_ms" in runtime_payload
    assert "response_ms" in signals_payload
    assert "response_ms" in diagnostics_payload


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
