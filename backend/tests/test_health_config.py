"""Health config endpoint tests."""

import pytest


@pytest.mark.asyncio
async def test_health_config_exposes_signal_sources(client):
    response = await client.get("/health/config")
    assert response.status_code == 200
    payload = response.json()
    assert payload["signal_sources"]["mode"] == "mock"
    assert payload["signal_sources"]["weather"] == "mock"
    assert payload["provider_snapshot_persistence_enabled"] is True
    assert payload["signal_runtime"]["snapshots"]["retention_days"] == 14
    assert payload["shadow_diff_summary"]["total_diffs"] == 0
