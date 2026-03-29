"""
Basic Sprint 2 integration tests for trigger-driven claim generation.
"""

import pytest
from scripts.run_scenario import enrich_worker_for_demo


@pytest.mark.asyncio
async def test_trigger_cycle_creates_event_and_claim(client, valid_worker_data, admin_headers):
    register_response = await client.post("/api/workers/register", json=valid_worker_data)
    assert register_response.status_code == 201
    worker_id = register_response.json()["worker_id"]

    create_policy_response = await client.post("/api/policies/create", json={"worker_id": worker_id, "plan_name": "smart_protect"})
    assert create_policy_response.status_code == 201

    activate_response = await client.post("/api/policies/activate-pending", headers=admin_headers)
    assert activate_response.status_code == 200
    assert activate_response.json()["activated_count"] >= 1

    trigger_response = await client.post("/api/triggers/check", json={"city": "delhi", "zones": ["south_delhi"], "scenario": "heavy_rain"})
    assert trigger_response.status_code == 200
    payload = trigger_response.json()
    assert payload["events_created"] >= 1
    assert payload["claims_generated"] >= 1

    claims_response = await client.get(f"/api/claims/worker/{worker_id}")
    assert claims_response.status_code == 200
    assert claims_response.json()["total"] >= 1


@pytest.mark.asyncio
async def test_event_claim_and_payout_detail_endpoints(client, valid_worker_data, admin_headers):
    register_response = await client.post("/api/workers/register", json=valid_worker_data)
    worker_id = register_response.json()["worker_id"]

    create_policy_response = await client.post("/api/policies/create", json={"worker_id": worker_id, "plan_name": "smart_protect"})
    assert create_policy_response.status_code == 201

    force_activate = await client.post(
        f"/api/policies/admin/force-activate?worker_id={worker_id}",
        headers=admin_headers,
    )
    assert force_activate.status_code == 200

    trigger_response = await client.post("/api/triggers/check", json={"city": "delhi", "zones": ["south_delhi"], "scenario": "heavy_rain"})
    assert trigger_response.status_code == 200
    trigger_data = trigger_response.json()
    assert trigger_data["events_created"] >= 1

    events_history_response = await client.get("/api/events/history?city=delhi&days=7")
    assert events_history_response.status_code == 200
    history_data = events_history_response.json()
    assert history_data["total"] >= 1

    event_id = history_data["events"][0]["id"]
    event_detail_response = await client.get(f"/api/events/detail/{event_id}")
    assert event_detail_response.status_code == 200
    event_detail = event_detail_response.json()
    assert event_detail["total_claims"] >= 1
    assert "approved_claims" in event_detail

    zone_response = await client.get("/api/events/zone/south_delhi?active_only=true")
    assert zone_response.status_code == 200
    assert zone_response.json()["total"] >= 1

    claims_response = await client.get(f"/api/claims/worker/{worker_id}")
    claim_payload = claims_response.json()
    assert claim_payload["total"] >= 1

    claim_id = claim_payload["claims"][0]["id"]
    claim_detail_response = await client.get(f"/api/claims/detail/{claim_id}")
    assert claim_detail_response.status_code == 200
    claim_detail = claim_detail_response.json()
    assert claim_detail["id"] == claim_id
    assert "event" in claim_detail

    if claim_detail["payout"]:
        payout_id = claim_detail["payout"]["id"]
        payout_detail_response = await client.get(f"/api/payouts/detail/{payout_id}")
        assert payout_detail_response.status_code == 200
        payout_detail = payout_detail_response.json()
        assert payout_detail["id"] == payout_id
        assert payout_detail["claim_details"]["trigger_type"] == claim_detail["trigger_type"]


@pytest.mark.asyncio
async def test_review_queue_and_manual_resolution_flow(client, valid_worker_data, admin_headers):
    edge_worker_data = dict(valid_worker_data)
    edge_worker_data["name"] = "Edge Review Worker"
    edge_worker_data["phone"] = "+919999999998"
    edge_worker_data["zone"] = "east_delhi"
    edge_worker_data["self_reported_income"] = 800

    register_response = await client.post("/api/workers/register", json=edge_worker_data)
    worker_id = register_response.json()["worker_id"]

    create_policy_response = await client.post("/api/policies/create", json={"worker_id": worker_id, "plan_name": "assured_plan"})
    assert create_policy_response.status_code == 201

    await enrich_worker_for_demo(worker_id, "east_delhi", "edge")

    force_activate = await client.post(
        f"/api/policies/admin/force-activate?worker_id={worker_id}",
        headers=admin_headers,
    )
    assert force_activate.status_code == 200

    trigger_response = await client.post("/api/triggers/check", json={"city": "delhi", "zones": ["east_delhi"], "scenario": "platform_outage"})
    assert trigger_response.status_code == 200

    review_queue_response = await client.get("/api/claims/review-queue", headers=admin_headers)
    assert review_queue_response.status_code == 200
    queue_data = review_queue_response.json()
    assert queue_data["total_pending"] >= 1

    claim_id = next(claim["id"] for claim in queue_data["claims"] if claim["worker_id"] == worker_id)
    resolve_response = await client.post(
        f"/api/claims/resolve/{claim_id}",
        json={"decision": "approve", "reason": "Manual verification passed.", "reviewed_by": "test_admin"},
        headers=admin_headers,
    )
    assert resolve_response.status_code == 200
    resolve_data = resolve_response.json()
    assert resolve_data["decision"] == "approve"
    assert "within_sla" in resolve_data
    assert resolve_data["claim"]["status"] == "approved"

    updated_claim = await client.get(f"/api/claims/detail/{claim_id}")
    assert updated_claim.status_code == 200
    assert updated_claim.json()["status"] == "approved"
