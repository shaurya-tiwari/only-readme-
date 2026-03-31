"""
Scenario outcome tests for the Sprint 2 demo personas.
"""

import pytest

from scripts.run_scenario import enrich_worker_for_demo


async def create_worker_policy(client, admin_headers, name: str, phone: str, zone: str, income: int, plan_name: str, profile: str) -> str:
    register_response = await client.post(
        "/api/workers/register",
        json={
            "name": name,
            "phone": phone,
            "city": "delhi",
            "zone": zone,
            "platform": "zomato",
            "self_reported_income": income,
            "working_hours": 8,
            "consent_given": True,
        },
    )
    worker_id = register_response.json()["worker_id"]
    create_policy_response = await client.post("/api/policies/create", json={"worker_id": worker_id, "plan_name": plan_name})
    assert create_policy_response.status_code == 201
    await enrich_worker_for_demo(worker_id, zone, profile)
    force_activate = await client.post(
        f"/api/policies/admin/force-activate?worker_id={worker_id}",
        headers=admin_headers,
    )
    assert force_activate.status_code == 200
    return worker_id


@pytest.mark.asyncio
async def test_legitimate_rain_scenario_auto_approves(client, admin_headers):
    worker_id = await create_worker_policy(
        client,
        admin_headers,
        "Rahul Kumar",
        "+919111111111",
        "south_delhi",
        900,
        "smart_protect",
        "legit",
    )

    trigger_response = await client.post(
        "/api/triggers/check",
        json={"city": "delhi", "zones": ["south_delhi"], "scenario": "heavy_rain"},
    )
    assert trigger_response.status_code == 200

    claims_response = await client.get(f"/api/claims/worker/{worker_id}")
    claims = claims_response.json()["claims"]
    assert claims
    assert all(claim["status"] == "approved" for claim in claims)

    payouts_response = await client.get(f"/api/payouts/worker/{worker_id}")
    assert payouts_response.json()["total_payouts"] >= 1


@pytest.mark.asyncio
async def test_fraud_rain_scenario_is_not_auto_approved(client, admin_headers):
    worker_id = await create_worker_policy(
        client,
        admin_headers,
        "Vikram Singh",
        "+919111111112",
        "south_delhi",
        2500,
        "smart_protect",
        "fraud",
    )

    trigger_response = await client.post(
        "/api/triggers/check",
        json={"city": "delhi", "zones": ["south_delhi"], "scenario": "heavy_rain"},
    )
    assert trigger_response.status_code == 200

    claims_response = await client.get(f"/api/claims/worker/{worker_id}")
    claims = claims_response.json()["claims"]
    assert claims
    assert all(claim["status"] != "approved" for claim in claims)
    assert any(claim["status"] in {"rejected", "delayed"} for claim in claims)


@pytest.mark.asyncio
async def test_edge_platform_outage_scenario_routes_to_review_or_reject(client, admin_headers):
    worker_id = await create_worker_policy(
        client,
        admin_headers,
        "Arun Patel",
        "+919111111113",
        "east_delhi",
        800,
        "assured_plan",
        "edge",
    )

    trigger_response = await client.post(
        "/api/triggers/check",
        json={"city": "delhi", "zones": ["east_delhi"], "scenario": "platform_outage"},
    )
    assert trigger_response.status_code == 200

    claims_response = await client.get(f"/api/claims/worker/{worker_id}")
    claims = claims_response.json()["claims"]
    assert claims
    assert claims[0]["status"] in {"delayed", "rejected"}
