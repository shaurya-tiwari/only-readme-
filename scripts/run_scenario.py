"""
End-to-end Sprint 2 scenario runner.
"""

import asyncio
import sys
import time
from datetime import datetime

import httpx

from backend.core.demo_scenarios import enrich_worker_for_demo


BASE_URL = "http://localhost:8000"


def unique_phone(offset: int = 0) -> str:
    return f"+91{(int(time.time()) % 10000000000) + offset:010d}"


def print_trigger_summary(trigger_data: dict) -> None:
    print(
        "   Trigger summary: "
        f"events={trigger_data['events_created']} "
        f"claims={trigger_data['claims_generated']} "
        f"approved={trigger_data['claims_approved']} "
        f"delayed={trigger_data['claims_delayed']} "
        f"rejected={trigger_data['claims_rejected']} "
        f"payout={trigger_data['total_payout']}"
    )


async def create_worker_and_policy(
    client: httpx.AsyncClient,
    name: str,
    zone: str,
    plan_name: str,
    income: int,
    profile: str,
    offset: int = 0,
) -> str:
    register_response = await client.post(
        "/api/workers/register",
        json={
            "name": name,
            "phone": unique_phone(offset),
            "city": "delhi",
            "zone": zone,
            "platform": "zomato",
            "self_reported_income": income,
            "working_hours": 8,
            "consent_given": True,
        },
    )
    register_response.raise_for_status()
    worker_id = register_response.json()["worker_id"]

    policy_response = await client.post(
        "/api/policies/create",
        json={"worker_id": worker_id, "plan_name": plan_name},
    )
    policy_response.raise_for_status()
    await enrich_worker_for_demo(worker_id, zone, profile)
    await client.post(
        f"/api/policies/admin/force-activate?worker_id={worker_id}",
        headers=await admin_headers(client),
    )
    return worker_id


async def admin_headers(client: httpx.AsyncClient) -> dict:
    login_response = await client.post(
        "/api/auth/admin/login",
        json={"username": "admin", "password": "rideshield-admin"},
    )
    login_response.raise_for_status()
    token = login_response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


async def scenario_legitimate_rain(client: httpx.AsyncClient) -> dict:
    print("\n" + "=" * 70)
    print("SCENARIO 1: Legitimate Rain Disruption")
    print("=" * 70)
    worker_id = await create_worker_and_policy(client, "Rahul Kumar", "south_delhi", "smart_protect", 900, "legit", 0)
    print(f"   Worker created: {worker_id}")

    trigger = await client.post(
        "/api/triggers/check",
        json={"city": "delhi", "zones": ["south_delhi"], "scenario": "heavy_rain"},
    )
    trigger.raise_for_status()
    trigger_data = trigger.json()
    print_trigger_summary(trigger_data)

    claims = await client.get(f"/api/claims/worker/{worker_id}")
    claims.raise_for_status()
    payouts = await client.get(f"/api/payouts/worker/{worker_id}")
    payouts.raise_for_status()
    print(f"   Worker claims: {claims.json()['total']}")
    print(f"   Worker payouts: {payouts.json()['total_payouts']}")
    return {
        "scenario": "legitimate_rain",
        "worker_id": worker_id,
        "trigger": trigger_data,
        "claims": claims.json(),
        "payouts": payouts.json(),
    }


async def scenario_fraud_attempt(client: httpx.AsyncClient) -> dict:
    print("\n" + "=" * 70)
    print("SCENARIO 2: Fraud Attempt")
    print("=" * 70)
    worker_id = await create_worker_and_policy(client, "Vikram Singh", "south_delhi", "smart_protect", 2500, "fraud", 1)
    print(f"   Worker created: {worker_id}")

    trigger = await client.post(
        "/api/triggers/check",
        json={"city": "delhi", "zones": ["south_delhi"], "scenario": "heavy_rain"},
    )
    trigger.raise_for_status()
    trigger_data = trigger.json()
    print_trigger_summary(trigger_data)

    claims = await client.get(f"/api/claims/worker/{worker_id}")
    claims.raise_for_status()
    claim_payload = claims.json()
    print(f"   Worker claims: {claim_payload['total']}")
    if claim_payload["claims"]:
        first_claim = claim_payload["claims"][0]
        print(
            "   First claim: "
            f"status={first_claim['status']} "
            f"fraud_score={first_claim.get('fraud_score')} "
            f"final_score={first_claim.get('final_score')}"
        )
    return {
        "scenario": "fraud_attempt",
        "worker_id": worker_id,
        "trigger": trigger_data,
        "claims": claim_payload,
    }


async def scenario_edge_case(client: httpx.AsyncClient) -> dict:
    print("\n" + "=" * 70)
    print("SCENARIO 3: Edge Case and Admin Review")
    print("=" * 70)
    worker_id = await create_worker_and_policy(client, "Arun Patel", "east_delhi", "assured_plan", 800, "edge", 2)
    print(f"   Worker created: {worker_id}")

    trigger = await client.post(
        "/api/triggers/check",
        json={"city": "delhi", "zones": ["east_delhi"], "scenario": "platform_outage"},
    )
    trigger.raise_for_status()
    trigger_data = trigger.json()
    print_trigger_summary(trigger_data)

    claims = await client.get(f"/api/claims/worker/{worker_id}")
    claims.raise_for_status()
    admin_auth_headers = await admin_headers(client)
    review_queue = await client.get("/api/claims/review-queue", headers=admin_auth_headers)
    review_queue.raise_for_status()
    queue_data = review_queue.json()
    print(f"   Review queue size: {queue_data['total_pending']}")

    resolution = None
    target_claim = next((claim for claim in queue_data["claims"] if claim["worker_id"] == worker_id), None)
    if target_claim:
        claim_id = target_claim["id"]
        resolve = await client.post(
            f"/api/claims/resolve/{claim_id}",
            json={
                "decision": "approve",
                "reason": "Manual review confirms the disruption was legitimate.",
                "reviewed_by": "scenario_runner",
            },
            headers=admin_auth_headers,
        )
        resolve.raise_for_status()
        resolution = resolve.json()
        print(
            "   Admin resolution: "
            f"decision={resolution['decision']} within_sla={resolution['within_sla']}"
        )
    else:
        print("   Admin resolution: no delayed claim for this worker")

    return {
        "scenario": "edge_case",
        "worker_id": worker_id,
        "trigger": trigger_data,
        "claims": claims.json(),
        "review_queue": queue_data,
        "resolution": resolution,
    }


async def run_all() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        health = await client.get("/health")
        health.raise_for_status()

        print("RideShield Sprint 2 scenario runner")
        print(f"Server: {BASE_URL}")
        print(f"Time: {datetime.utcnow().isoformat()}")
        print(f"Health: {health.json()['status']}")

        results = []
        await client.post("/api/triggers/reset")
        results.append(await scenario_legitimate_rain(client))
        await client.post("/api/triggers/reset")
        results.append(await scenario_fraud_attempt(client))
        await client.post("/api/triggers/reset")
        results.append(await scenario_edge_case(client))
        await client.post("/api/triggers/reset")

        claim_stats = (await client.get("/api/claims/stats?days=7")).json()
        payout_stats = (await client.get("/api/payouts/stats?days=7")).json()
        events = (await client.get("/api/events/active?city=delhi")).json()

    print("\n" + "=" * 70)
    print("FINAL STATISTICS")
    print("=" * 70)
    print(f"   Total claims: {claim_stats['total_claims']}")
    print(f"   Approved: {claim_stats['approved']}")
    print(f"   Delayed: {claim_stats['delayed']}")
    print(f"   Rejected: {claim_stats['rejected']}")
    print(f"   Approval rate: {claim_stats['approval_rate']}%")
    print(f"   Fraud rate: {claim_stats['fraud_rate']}%")
    print(f"   Total payout: INR {claim_stats['total_payout']}")
    print(f"   Payouts executed: {payout_stats['total_payouts']}")
    print(f"   Avg payout: INR {payout_stats['avg_payout']}")
    print(f"   Active events: {events['total']}")

    for result in results:
        print(f"\nCompleted scenario: {result['scenario']}")


if __name__ == "__main__":
    scenario_num = None
    if len(sys.argv) > 2 and sys.argv[1] == "--scenario":
        scenario_num = int(sys.argv[2])

    async def dispatch():
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
            if scenario_num == 1:
                await scenario_legitimate_rain(client)
            elif scenario_num == 2:
                await scenario_fraud_attempt(client)
            elif scenario_num == 3:
                await scenario_edge_case(client)
            else:
                await run_all()

    asyncio.run(dispatch())
