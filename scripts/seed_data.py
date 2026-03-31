"""
Seed script populates database with stable demo data for testing.
Run: python -m scripts.seed_data
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.premium_calculator import premium_calculator
from backend.core.risk_scorer import risk_scorer
from backend.core.location_service import location_service
from backend.database import async_session_factory, init_db
from backend.db.models import AuditLog, Policy, TrustScore, Worker, WorkerActivity


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


WORKERS = [
    {
        "key": "rahul",
        "label": "Rahul Kumar",
        "phone": "+919876543210",
        "city": "delhi",
        "zone": "south_delhi",
        "platform": "zomato",
        "income": Decimal("900"),
        "hours": Decimal("9"),
        "consent_days": 30,
        "trust": {
            "score": Decimal("0.750"),
            "total_claims": 12,
            "approved_claims": 10,
            "fraud_flags": 0,
            "account_age_days": 30,
            "device_stability": Decimal("0.900"),
        },
        "plan": {
            "plan_name": "smart_protect",
            "status": "active",
            "purchased_offset": timedelta(hours=25),
            "activates_offset": timedelta(hours=1),
            "expires_offset": timedelta(days=6, hours=23),
            "triggers": ["rain", "heat", "aqi", "traffic", "platform_outage"],
            "base_price": Decimal("39"),
            "plan_factor": Decimal("1.5"),
            "coverage_cap": Decimal("600"),
        },
        "activity": [
            {
                "zone": "south_delhi",
                "latitude": Decimal("28.52") + Decimal(str(i * 0.002)),
                "longitude": Decimal("77.22") + Decimal(str(i * 0.003)),
                "speed_kmh": Decimal(str(15 + i * 3)),
                "has_delivery_stop": True,
                "recorded_offset": timedelta(hours=4) - timedelta(minutes=i * 25),
            }
            for i in range(8)
        ],
        "notes": "active legit",
    },
    {
        "key": "vikram",
        "label": "Vikram Singh",
        "phone": "+919876543211",
        "city": "delhi",
        "zone": "south_delhi",
        "platform": "zomato",
        "income": Decimal("2000"),
        "hours": Decimal("8"),
        "consent_days": 2,
        "trust": {
            "score": Decimal("0.100"),
            "total_claims": 0,
            "approved_claims": 0,
            "fraud_flags": 0,
            "account_age_days": 2,
            "device_stability": Decimal("0.300"),
        },
        "plan": {
            "plan_name": "smart_protect",
            "status": "pending",
            "purchased_offset": timedelta(hours=1),
            "activates_offset": -timedelta(hours=23),
            "expires_offset": timedelta(days=7, hours=23),
            "triggers": ["rain", "heat", "aqi", "traffic", "platform_outage"],
            "base_price": Decimal("39"),
            "plan_factor": Decimal("1.5"),
            "coverage_cap": Decimal("600"),
        },
        "activity": [],
        "notes": "pending fraud",
    },
    {
        "key": "arun",
        "label": "Arun Patel",
        "phone": "+919876543212",
        "city": "delhi",
        "zone": "east_delhi",
        "platform": "zomato",
        "income": Decimal("800"),
        "hours": Decimal("8"),
        "consent_days": 5,
        "trust": {
            "score": Decimal("0.150"),
            "total_claims": 0,
            "approved_claims": 0,
            "fraud_flags": 0,
            "account_age_days": 5,
            "device_stability": Decimal("0.500"),
        },
        "plan": {
            "plan_name": "assured_plan",
            "status": "pending",
            "purchased_offset": timedelta(hours=2),
            "activates_offset": -timedelta(hours=22),
            "expires_offset": timedelta(days=7, hours=22),
            "triggers": ["rain", "heat", "aqi", "traffic", "platform_outage", "social"],
            "base_price": Decimal("49"),
            "plan_factor": Decimal("2.0"),
            "coverage_cap": Decimal("800"),
        },
        "activity": [
            {
                "zone": "east_delhi",
                "latitude": Decimal("28.63"),
                "longitude": Decimal("77.30"),
                "speed_kmh": Decimal("12"),
                "has_delivery_stop": True,
                "recorded_offset": timedelta(hours=3),
            }
        ],
        "notes": "pending edge",
    },
    {
        "key": "priya",
        "label": "Priya Sharma",
        "phone": "+919876543213",
        "city": "bengaluru",
        "zone": "koramangala",
        "platform": "swiggy",
        "income": Decimal("850"),
        "hours": Decimal("8"),
        "consent_days": 60,
        "trust": {
            "score": Decimal("0.850"),
            "total_claims": 25,
            "approved_claims": 22,
            "fraud_flags": 0,
            "account_age_days": 60,
            "device_stability": Decimal("0.950"),
        },
        "plan": {
            "plan_name": "smart_protect",
            "status": "active",
            "purchased_offset": timedelta(hours=48),
            "activates_offset": timedelta(hours=24),
            "expires_offset": timedelta(days=5),
            "triggers": ["rain", "heat", "aqi", "traffic", "platform_outage"],
            "base_price": Decimal("39"),
            "plan_factor": Decimal("1.5"),
            "coverage_cap": Decimal("600"),
        },
        "activity": [],
        "notes": "active multi",
    },
    {
        "key": "aman",
        "label": "Aman Verma",
        "phone": "+919876543214",
        "city": "mumbai",
        "zone": "south_mumbai",
        "platform": "swiggy",
        "income": Decimal("780"),
        "hours": Decimal("8"),
        "consent_days": 20,
        "trust": {
            "score": Decimal("0.620"),
            "total_claims": 8,
            "approved_claims": 6,
            "fraud_flags": 1,
            "account_age_days": 20,
            "device_stability": Decimal("0.800"),
        },
        "plan": {
            "plan_name": "smart_protect",
            "status": "active",
            "purchased_offset": timedelta(hours=14),
            "activates_offset": timedelta(hours=2),
            "expires_offset": timedelta(days=6, hours=6),
            "triggers": ["rain", "heat", "traffic"],
            "base_price": Decimal("39"),
            "plan_factor": Decimal("1.4"),
            "coverage_cap": Decimal("550"),
        },
        "activity": [
            {
                "zone": "south_mumbai",
                "latitude": Decimal("18.93") + Decimal(str(i * 0.002)),
                "longitude": Decimal("72.83") + Decimal(str(i * 0.002)),
                "speed_kmh": Decimal(str(17 + i * 2)),
                "has_delivery_stop": True,
                "recorded_offset": timedelta(hours=5) - timedelta(minutes=i * 20),
            }
            for i in range(6)
        ],
        "notes": "mumbai active",
    },
    {
        "key": "farhan",
        "label": "Farhan Ali",
        "phone": "+919876543215",
        "city": "mumbai",
        "zone": "navi_mumbai",
        "platform": "zomato",
        "income": Decimal("1100"),
        "hours": Decimal("10"),
        "consent_days": 90,
        "trust": {
            "score": Decimal("0.910"),
            "total_claims": 40,
            "approved_claims": 38,
            "fraud_flags": 0,
            "account_age_days": 90,
            "device_stability": Decimal("0.980"),
        },
        "plan": {
            "plan_name": "assured_plan",
            "status": "active",
            "purchased_offset": timedelta(hours=72),
            "activates_offset": timedelta(hours=24),
            "expires_offset": timedelta(days=5, hours=12),
            "triggers": ["rain", "heat", "aqi", "traffic"],
            "base_price": Decimal("49"),
            "plan_factor": Decimal("2.3"),
            "coverage_cap": Decimal("900"),
        },
        "activity": [
            {
                "zone": "navi_mumbai",
                "latitude": Decimal("19.03") + Decimal(str(i * 0.001)),
                "longitude": Decimal("73.02") + Decimal(str(i * 0.001)),
                "speed_kmh": Decimal(str(22 + i * 2)),
                "has_delivery_stop": True,
                "recorded_offset": timedelta(hours=6) - timedelta(minutes=i * 18),
            }
            for i in range(5)
        ],
        "notes": "mumbai high trust",
    },
    {
        "key": "sneha",
        "label": "Sneha Iyer",
        "phone": "+919876543216",
        "city": "chennai",
        "zone": "adyar",
        "platform": "swiggy",
        "income": Decimal("950"),
        "hours": Decimal("9"),
        "consent_days": 45,
        "trust": {
            "score": Decimal("0.880"),
            "total_claims": 30,
            "approved_claims": 28,
            "fraud_flags": 0,
            "account_age_days": 45,
            "device_stability": Decimal("0.970"),
        },
        "plan": {
            "plan_name": "assured_plan",
            "status": "active",
            "purchased_offset": timedelta(hours=36),
            "activates_offset": timedelta(hours=6),
            "expires_offset": timedelta(days=5, hours=20),
            "triggers": ["rain", "aqi", "social"],
            "base_price": Decimal("49"),
            "plan_factor": Decimal("2.1"),
            "coverage_cap": Decimal("850"),
        },
        "activity": [
            {
                "zone": "adyar",
                "latitude": Decimal("13.01") + Decimal(str(i * 0.001)),
                "longitude": Decimal("80.25") + Decimal(str(i * 0.001)),
                "speed_kmh": Decimal(str(18 + i * 2)),
                "has_delivery_stop": True,
                "recorded_offset": timedelta(hours=4) - timedelta(minutes=i * 22),
            }
            for i in range(6)
        ],
        "notes": "chennai active",
    },
    {
        "key": "neha",
        "label": "Neha Gupta",
        "phone": "+919876543217",
        "city": "chennai",
        "zone": "anna_nagar",
        "platform": "swiggy",
        "income": Decimal("980"),
        "hours": Decimal("9"),
        "consent_days": 70,
        "trust": {
            "score": Decimal("0.890"),
            "total_claims": 22,
            "approved_claims": 20,
            "fraud_flags": 0,
            "account_age_days": 70,
            "device_stability": Decimal("0.960"),
        },
        "plan": {
            "plan_name": "assured_plan",
            "status": "active",
            "purchased_offset": timedelta(hours=30),
            "activates_offset": timedelta(hours=5),
            "expires_offset": timedelta(days=5, hours=10),
            "triggers": ["rain", "aqi", "social"],
            "base_price": Decimal("49"),
            "plan_factor": Decimal("2.0"),
            "coverage_cap": Decimal("800"),
        },
        "activity": [
            {
                "zone": "anna_nagar",
                "latitude": Decimal("13.08") + Decimal(str(i * 0.001)),
                "longitude": Decimal("80.21") + Decimal(str(i * 0.001)),
                "speed_kmh": Decimal(str(16 + i * 2)),
                "has_delivery_stop": True,
                "recorded_offset": timedelta(hours=3) - timedelta(minutes=i * 17),
            }
            for i in range(4)
        ],
        "notes": "chennai high trust",
    },
    {
        "key": "rohit",
        "label": "Rohit Yadav",
        "phone": "+919876543218",
        "city": "bengaluru",
        "zone": "whitefield",
        "platform": "zomato",
        "income": Decimal("720"),
        "hours": Decimal("7"),
        "consent_days": 12,
        "trust": {
            "score": Decimal("0.410"),
            "total_claims": 3,
            "approved_claims": 2,
            "fraud_flags": 0,
            "account_age_days": 12,
            "device_stability": Decimal("0.620"),
        },
        "plan": {
            "plan_name": "smart_protect",
            "status": "pending",
            "purchased_offset": timedelta(hours=4),
            "activates_offset": -timedelta(hours=20),
            "expires_offset": timedelta(days=7, hours=12),
            "triggers": ["heat", "traffic", "platform_outage"],
            "base_price": Decimal("39"),
            "plan_factor": Decimal("1.6"),
            "coverage_cap": Decimal("500"),
        },
        "activity": [
            {
                "zone": "whitefield",
                "latitude": Decimal("12.97") + Decimal(str(i * 0.001)),
                "longitude": Decimal("77.75") + Decimal(str(i * 0.001)),
                "speed_kmh": Decimal(str(14 + i * 2)),
                "has_delivery_stop": i % 2 == 0,
                "recorded_offset": timedelta(hours=2) - timedelta(minutes=i * 15),
            }
            for i in range(5)
        ],
        "notes": "bengaluru pending",
    },
]


def policy_display_name(plan_name: str) -> str:
    return {
        "smart_protect": "Smart Protect",
        "assured_plan": "Assured Plan",
    }.get(plan_name, plan_name.replace("_", " ").title())


async def upsert_worker(db, spec: dict, now: datetime):
    worker = (await db.execute(select(Worker).where(Worker.phone == spec["phone"]))).scalar_one_or_none()
    zone_record = await location_service.resolve_zone(db, spec["city"], spec["zone"])
    risk = risk_scorer.calculate_risk_score(
        spec["city"],
        zone_record.slug,
        city_base_override=float(zone_record.risk_profile.base_risk) if zone_record.risk_profile else None,
    )

    payload = {
        "name": spec["label"],
        "phone": spec["phone"],
        "city_id": zone_record.city_id,
        "zone_id": zone_record.id,
        "city": spec["city"],
        "zone": zone_record.slug,
        "platform": spec["platform"],
        "self_reported_income": spec["income"],
        "working_hours": spec["hours"],
        "consent_given": True,
        "consent_timestamp": now - timedelta(days=spec["consent_days"]),
        "risk_score": Decimal(str(risk["risk_score"])),
        "status": "active",
        "updated_at": now,
    }

    created = worker is None
    if created:
        worker = Worker(**payload, created_at=now)
        db.add(worker)
        await db.flush()
    else:
        for key, value in payload.items():
            setattr(worker, key, value)

    return worker, zone_record, risk, created


async def upsert_trust_score(db, worker: Worker, trust_spec: dict, now: datetime):
    trust = (await db.execute(select(TrustScore).where(TrustScore.worker_id == worker.id))).scalar_one_or_none()
    payload = {**trust_spec, "worker_id": worker.id, "last_updated": now}

    if trust is None:
        trust = TrustScore(**payload)
        db.add(trust)
    else:
        for key, value in payload.items():
            setattr(trust, key, value)

    return trust


async def upsert_policy(db, worker: Worker, spec: dict, risk_score: float, now: datetime):
    policy = (
        await db.execute(
            select(Policy).where(
                Policy.worker_id == worker.id,
                Policy.plan_name == spec["plan"]["plan_name"],
            )
        )
    ).scalar_one_or_none()

    premium = premium_calculator.calculate(spec["plan"]["plan_name"], float(risk_score))
    plan = spec["plan"]
    payload = {
        "worker_id": worker.id,
        "plan_name": plan["plan_name"],
        "plan_display_name": policy_display_name(plan["plan_name"]),
        "base_price": plan["base_price"],
        "plan_factor": plan["plan_factor"],
        "risk_score_at_purchase": Decimal(str(risk_score)),
        "weekly_premium": Decimal(str(premium["final_premium"])),
        "coverage_cap": plan["coverage_cap"],
        "triggers_covered": plan["triggers"],
        "status": plan["status"],
        "purchased_at": now - plan["purchased_offset"],
        "activates_at": now - plan["activates_offset"],
        "expires_at": now + plan["expires_offset"],
        "created_at": now if policy is None else policy.created_at,
    }

    if policy is None:
        policy = Policy(**payload)
        db.add(policy)
    else:
        for key, value in payload.items():
            setattr(policy, key, value)

    return policy, premium


async def replace_activity_logs(db, worker: Worker, activity_spec: list[dict], now: datetime):
    existing = (await db.execute(select(WorkerActivity).where(WorkerActivity.worker_id == worker.id))).scalars().all()
    for row in existing:
        await db.delete(row)

    for item in activity_spec:
        db.add(
            WorkerActivity(
                worker_id=worker.id,
                zone_id=worker.zone_id,
                zone=item["zone"],
                latitude=item["latitude"],
                longitude=item["longitude"],
                speed_kmh=item["speed_kmh"],
                has_delivery_stop=item["has_delivery_stop"],
                recorded_at=now - item["recorded_offset"],
            )
        )


async def seed():
    """Create or refresh demo workers, policies, and activity data."""

    await init_db()

    async with async_session_factory() as db:
        print("Seeding database...")
        await location_service.ensure_bootstrap(db, strict_backfill=True)
        now = utc_now_naive()
        results = []

        for spec in WORKERS:
            worker, zone_record, risk, created = await upsert_worker(db, spec, now)
            await upsert_trust_score(db, worker, spec["trust"], now)
            policy, premium = await upsert_policy(db, worker, spec, risk["risk_score"], now)
            await replace_activity_logs(db, worker, spec["activity"], now)

            results.append(
                {
                    "label": spec["label"],
                    "worker_id": worker.id,
                    "city": zone_record.city_ref.slug,
                    "zone": zone_record.slug,
                    "risk_score": risk["risk_score"],
                    "premium": premium["final_premium"],
                    "notes": spec["notes"],
                    "policy_status": policy.status,
                    "created": created,
                    "activity_count": len(spec["activity"]),
                }
            )

        db.add(
            AuditLog(
                entity_type="system",
                entity_id=results[0]["worker_id"],
                action="database_seeded",
                details={
                    "workers_upserted": len(results),
                    "policies_upserted": len(results),
                    "active_policies": sum(1 for row in results if row["policy_status"] == "active"),
                    "pending_policies": sum(1 for row in results if row["policy_status"] == "pending"),
                    "personas": [row["notes"] for row in results],
                },
            )
        )

        await db.commit()

        for row in results:
            action = "created" if row["created"] else "updated"
            print(f"  [ok] {row['label']} {action} (ID: {row['worker_id']}) [{row['notes']}]")
            print(f"     Risk: {row['risk_score']}, Premium: INR {row['premium']}/week")

        print("\nDatabase seeded successfully!")
        print(f"   Workers upserted: {len(results)}")
        print(f"   Policies upserted: {len(results)}")
        print(f"   Active policies: {sum(1 for row in results if row['policy_status'] == 'active')}")
        print(f"   Pending policies: {sum(1 for row in results if row['policy_status'] == 'pending')}")
        print(f"   Activity logs refreshed: {sum(row['activity_count'] for row in results)}")
        print("\nWorker IDs for testing:")
        for row in results:
            print(f"   {row['label']} ({row['notes']}): {row['worker_id']}")


if __name__ == "__main__":
    asyncio.run(seed())
