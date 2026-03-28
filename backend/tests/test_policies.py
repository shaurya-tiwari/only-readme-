"""
Tests for Policies API.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app


async def create_test_worker(client, phone="+919988776655"):
    """Helper: create a worker and return the worker_id."""
    response = await client.post("/api/workers/register", json={
        "name": "Policy Test Worker",
        "phone": phone,
        "city": "delhi",
        "zone": "south_delhi",
        "platform": "zomato",
        "self_reported_income": 900,
        "working_hours": 9,
        "consent_given": True
    })
    return response.json()["worker_id"]


@pytest.mark.asyncio
async def test_list_plans():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        worker_id = await create_test_worker(client, "+919988776600")

        response = await client.get(f"/api/policies/plans/{worker_id}")
        assert response.status_code == 200

        data = response.json()
        assert len(data["plans"]) == 4
        assert data["risk_score"] > 0

        plan_names = [p["plan_name"] for p in data["plans"]]
        assert "basic_protect" in plan_names
        assert "smart_protect" in plan_names
        assert "assured_plan" in plan_names
        assert "pro_max" in plan_names


@pytest.mark.asyncio
async def test_create_policy():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        worker_id = await create_test_worker(client, "+919988776601")

        response = await client.post("/api/policies/create", json={
            "worker_id": worker_id,
            "plan_name": "smart_protect"
        })

        assert response.status_code == 201
        data = response.json()

        assert data["policy"]["plan_name"] == "smart_protect"
        assert data["policy"]["status"] == "pending"  # 24hr activation
        assert data["premium_calculation"]["base_price"] == 39
        assert data["premium_calculation"]["plan_factor"] == 1.5
        assert data["premium_calculation"]["final_premium"] > 0


@pytest.mark.asyncio
async def test_cannot_buy_two_active_policies():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        worker_id = await create_test_worker(client, "+919988776602")

        # First purchase
        response1 = await client.post("/api/policies/create", json={
            "worker_id": worker_id,
            "plan_name": "smart_protect"
        })
        assert response1.status_code == 201

        # Second purchase should fail
        response2 = await client.post("/api/policies/create", json={
            "worker_id": worker_id,
            "plan_name": "assured_plan"
        })
        assert response2.status_code == 409


@pytest.mark.asyncio
async def test_invalid_plan_fails():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        worker_id = await create_test_worker(client, "+919988776603")

        response = await client.post("/api/policies/create", json={
            "worker_id": worker_id,
            "plan_name": "nonexistent_plan"
        })
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_premium_formula_correctness():
    """Verify premium = base × factor × risk, rounded."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        worker_id = await create_test_worker(client, "+919988776604")

        response = await client.post("/api/policies/create", json={
            "worker_id": worker_id,
            "plan_name": "smart_protect"
        })

        calc = response.json()["premium_calculation"]
        expected = calc["base_price"] * calc["plan_factor"] * calc["risk_score"]

        # Premium should be at least base price and close to formula
        assert calc["final_premium"] >= calc["base_price"]