"""
Tests for Workers API.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app


@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == "RideShield"


@pytest.mark.asyncio
async def test_register_worker():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/workers/register", json={
            "name": "Test Rider",
            "phone": "+911234567890",
            "password": "testrider123",
            "city": "delhi",
            "zone": "south_delhi",
            "platform": "zomato",
            "self_reported_income": 900,
            "working_hours": 9,
            "consent_given": True
        })

        assert response.status_code == 201
        data = response.json()

        assert "worker_id" in data
        assert data["name"] == "Test Rider"
        assert data["city"] == "delhi"
        assert 0 < data["risk_score"] <= 1.0
        assert len(data["available_plans"]) == 4
        assert data["recommended_plan"] in [
            "basic_protect", "smart_protect", "assured_plan", "pro_max"
        ]
        assert data["activation_delay_hours"] == 24


@pytest.mark.asyncio
async def test_register_without_consent_fails():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/workers/register", json={
            "name": "No Consent Worker",
            "phone": "+911234567891",
            "password": "noconsent123",
            "city": "delhi",
            "platform": "zomato",
            "self_reported_income": 800,
            "working_hours": 8,
            "consent_given": False
        })

        assert response.status_code == 422  # validation error


@pytest.mark.asyncio
async def test_register_invalid_city_fails():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/workers/register", json={
            "name": "Invalid City Worker",
            "phone": "+911234567892",
            "password": "invalidcity123",
            "city": "jaipur",
            "platform": "zomato",
            "self_reported_income": 800,
            "working_hours": 8,
            "consent_given": True
        })

        assert response.status_code == 400
        assert "not supported" in response.json()["detail"]


@pytest.mark.asyncio
async def test_duplicate_phone_fails():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        worker_data = {
            "name": "Duplicate Test",
            "phone": "+911234567893",
            "password": "duplicate123",
            "city": "delhi",
            "platform": "zomato",
            "self_reported_income": 800,
            "working_hours": 8,
            "consent_given": True
        }

        # First registration should succeed
        response1 = await client.post("/api/workers/register", json=worker_data)
        assert response1.status_code == 201

        # Second registration with same phone should fail
        response2 = await client.post("/api/workers/register", json=worker_data)
        assert response2.status_code == 409


@pytest.mark.asyncio
async def test_risk_score_varies_by_city():
    """Delhi should have higher risk than Bengaluru."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        delhi_response = await client.post("/api/workers/register", json={
            "name": "Delhi Worker",
            "phone": "+911111111111",
            "password": "delhiworker123",
            "city": "delhi",
            "platform": "zomato",
            "self_reported_income": 900,
            "working_hours": 9,
            "consent_given": True
        })

        bengaluru_response = await client.post("/api/workers/register", json={
            "name": "Bengaluru Worker",
            "phone": "+912222222222",
            "password": "bengaluru123",
            "city": "bengaluru",
            "platform": "swiggy",
            "self_reported_income": 850,
            "working_hours": 8,
            "consent_given": True
        })

        delhi_risk = delhi_response.json()["risk_score"]
        bengaluru_risk = bengaluru_response.json()["risk_score"]

        assert delhi_risk > bengaluru_risk


@pytest.mark.asyncio
async def test_worker_profile_requires_matching_session():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first_worker = {
            "name": "Secure Worker",
            "phone": "+919888777666",
            "password": "secureworker123",
            "city": "delhi",
            "zone": "south_delhi",
            "platform": "zomato",
            "self_reported_income": 900,
            "working_hours": 9,
            "consent_given": True,
        }
        second_worker = {
            **first_worker,
            "name": "Other Worker",
            "phone": "+919888777667",
        }

        first_register = await client.post("/api/workers/register", json=first_worker)
        second_register = await client.post("/api/workers/register", json=second_worker)
        first_worker_id = first_register.json()["worker_id"]
        second_worker_id = second_register.json()["worker_id"]

        no_auth = await client.get(f"/api/workers/me/{first_worker_id}")
        assert no_auth.status_code == 401

        login_response = await client.post(
            "/api/auth/worker/login",
            json={"phone": first_worker["phone"], "password": first_worker["password"]},
        )
        worker_headers = {"Authorization": f"Bearer {login_response.json()['token']}"}

        own_profile = await client.get(f"/api/workers/me/{first_worker_id}", headers=worker_headers)
        assert own_profile.status_code == 200

        forbidden = await client.get(f"/api/workers/me/{second_worker_id}", headers=worker_headers)
        assert forbidden.status_code == 403
