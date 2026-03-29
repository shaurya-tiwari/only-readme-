"""
Tests for admin analytics endpoints.
"""

import pytest


@pytest.mark.asyncio
async def test_admin_overview_requires_admin_token(client):
    response = await client.get("/api/analytics/admin-overview")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_overview_returns_scheduler_and_forecast(client):
    login_response = await client.post(
        "/api/auth/admin/login",
        json={"username": "admin", "password": "rideshield-admin"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["token"]

    overview_response = await client.get(
        "/api/analytics/admin-overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert overview_response.status_code == 200
    data = overview_response.json()

    assert "scheduler" in data
    assert "next_week_forecast" in data
    assert isinstance(data["next_week_forecast"], list)
