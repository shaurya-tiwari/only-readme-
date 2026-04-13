"""Scenario outcome tests for seeded worker profiles."""

import pytest

from backend.core.demo_scenarios import enrich_worker_for_demo


async def create_worker_policy(client, admin_cookies, name: str, phone: str, zone: str, income: int, plan_name: str, profile: str):
    password = "scenario123"
    register_response = await client.post(
        "/api/workers/register",
        json={
            "name": name,
            "phone": phone,
            "password": password,
            "city": "delhi",
            "zone": zone,
            "platform": "zomato",
            "self_reported_income": income,
            "working_hours": 8,
            "consent_given": True,
        },
    )
    assert register_response.status_code == 201, register_response.text
    worker_id = register_response.json()["worker_id"]
    create_policy_response = await client.post("/api/policies/create", json={"worker_id": worker_id, "plan_name": plan_name})
    assert create_policy_response.status_code == 201
    await enrich_worker_for_demo(worker_id, zone, profile)
    force_activate = await client.post(
        f"/api/policies/admin/force-activate?worker_id={worker_id}",
        cookies=admin_cookies,
    )
    assert force_activate.status_code == 200
    login_response = await client.post(
        "/api/auth/worker/login",
        json={"phone": phone, "password": password},
    )
    assert login_response.status_code == 200, login_response.text
    worker_cookies = dict(client.cookies)
    return worker_id, worker_cookies


@pytest.mark.asyncio
async def test_legitimate_rain_scenario_auto_approves(client, admin_cookies):
    worker_id, worker_cookies = await create_worker_policy(
        client,
        admin_cookies,
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

    claims_response = await client.get(f"/api/claims/worker/{worker_id}", cookies=worker_cookies)
    claims = claims_response.json()["claims"]
    assert claims
    assert all(claim["status"] == "approved" for claim in claims)

    payouts_response = await client.get(f"/api/payouts/worker/{worker_id}", cookies=worker_cookies)
    assert payouts_response.json()["total_payouts"] >= 1


@pytest.mark.asyncio
async def test_fraud_rain_scenario_is_not_auto_approved(client, admin_cookies):
    worker_id, worker_cookies = await create_worker_policy(
        client,
        admin_cookies,
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

    claims_response = await client.get(f"/api/claims/worker/{worker_id}", cookies=worker_cookies)
    claims = claims_response.json()["claims"]
    assert claims
    assert all(claim["status"] != "approved" for claim in claims)
    assert any(claim["status"] in {"rejected", "delayed"} for claim in claims)


@pytest.mark.asyncio
async def test_edge_platform_outage_scenario_routes_to_review_or_reject(client, admin_cookies):
    worker_id, worker_cookies = await create_worker_policy(
        client,
        admin_cookies,
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

    claims_response = await client.get(f"/api/claims/worker/{worker_id}", cookies=worker_cookies)
    claims = claims_response.json()["claims"]
    assert claims
    assert claims[0]["status"] in {"delayed", "rejected"}


@pytest.mark.asyncio
async def test_demo_scenario_endpoint_runs_deterministic_legit_flow(client, admin_cookies):
    response = await client.post("/api/triggers/demo-scenario/clean_legit", cookies=admin_cookies)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["demo_scenario"] == "clean_legit"
    assert payload["city"] == "delhi"
    assert payload["zone"] == "south_delhi"
    assert payload["worker"]["name"] == "Rahul Kumar"
    assert payload["claims_generated"] >= 1
    assert payload["latest_claim_status"] == "approved"


@pytest.mark.asyncio
async def test_lab_run_endpoint_executes_shared_engine_with_seeded_worker(client, admin_cookies):
    response = await client.post(
        "/api/triggers/lab-run",
        json={
            "city": "delhi",
            "zones": ["south_delhi"],
            "signals": {
                "rain_mm_hr": 42,
                "temperature_c": 26,
                "aqi_value": 140,
                "congestion_index": 0.35,
                "order_density_drop": 0.15,
            },
            "worker": {
                "seed_demo_worker": True,
                "profile": "legit",
                "plan_name": "smart_protect",
                "platform": "zomato",
                "self_reported_income": 900,
                "working_hours": 8,
            },
            "execution": {
                "mode": "single",
                "runs": 1,
            },
            "preset_name": "rain-lab",
        },
        cookies=admin_cookies,
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["city"] == "delhi"
    assert payload["zones"] == ["south_delhi"]
    assert payload["aggregate"]["runs"] == 1
    assert len(payload["runs"]) == 1
    assert payload["runs"][0]["worker"]["profile"] == "legit"
    assert "warning" in payload
