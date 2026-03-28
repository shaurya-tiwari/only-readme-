"""
Seed script populates database with demo data for testing.
Run: python -m scripts.seed_data
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.premium_calculator import premium_calculator
from backend.core.risk_scorer import risk_scorer
from backend.database import async_session_factory, init_db
from backend.db.models import AuditLog, Policy, TrustScore, Worker, WorkerActivity


async def seed():
    """Create demo workers, policies, and activity data."""

    await init_db()

    async with async_session_factory() as db:
        print("Seeding database...")
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # ============================================
        # WORKER 1: Rahul (Main persona - legitimate)
        # ============================================
        rahul_risk = risk_scorer.calculate_risk_score("delhi", "south_delhi")

        rahul = Worker(
            name="Rahul Kumar",
            phone="+919876543210",
            city="delhi",
            zone="south_delhi",
            platform="zomato",
            self_reported_income=Decimal("900"),
            working_hours=Decimal("9"),
            consent_given=True,
            consent_timestamp=now - timedelta(days=30),
            risk_score=Decimal(str(rahul_risk["risk_score"])),
            status="active",
        )
        db.add(rahul)
        await db.flush()

        rahul_trust = TrustScore(
            worker_id=rahul.id,
            score=Decimal("0.750"),
            total_claims=12,
            approved_claims=10,
            fraud_flags=0,
            account_age_days=30,
            device_stability=Decimal("0.900"),
        )
        db.add(rahul_trust)

        rahul_premium = premium_calculator.calculate(
            "smart_protect", float(rahul_risk["risk_score"])
        )

        rahul_policy = Policy(
            worker_id=rahul.id,
            plan_name="smart_protect",
            plan_display_name="Smart Protect",
            base_price=Decimal("39"),
            plan_factor=Decimal("1.5"),
            risk_score_at_purchase=Decimal(str(rahul_risk["risk_score"])),
            weekly_premium=Decimal(str(rahul_premium["final_premium"])),
            coverage_cap=Decimal("600"),
            triggers_covered=["rain", "heat", "aqi", "traffic", "platform_outage"],
            status="active",
            purchased_at=now - timedelta(hours=25),
            activates_at=now - timedelta(hours=1),
            expires_at=now + timedelta(days=6, hours=23),
        )
        db.add(rahul_policy)

        for i in range(8):
            activity = WorkerActivity(
                worker_id=rahul.id,
                zone="south_delhi",
                latitude=Decimal("28.52") + Decimal(str(i * 0.002)),
                longitude=Decimal("77.22") + Decimal(str(i * 0.003)),
                speed_kmh=Decimal(str(15 + i * 3)),
                has_delivery_stop=True,
                recorded_at=now - timedelta(hours=4) + timedelta(minutes=i * 25),
            )
            db.add(activity)

        print(f"  [ok] Rahul Kumar created (ID: {rahul.id})")
        print(
            f"     Risk: {rahul_risk['risk_score']}, "
            f"Premium: INR {rahul_premium['final_premium']}/week"
        )

        # ============================================
        # WORKER 2: Vikram (Fraud persona)
        # ============================================
        vikram_risk = risk_scorer.calculate_risk_score("delhi", "south_delhi")

        vikram = Worker(
            name="Vikram Singh",
            phone="+919876543211",
            city="delhi",
            zone="south_delhi",
            platform="zomato",
            self_reported_income=Decimal("2000"),
            working_hours=Decimal("8"),
            consent_given=True,
            consent_timestamp=now - timedelta(days=2),
            risk_score=Decimal(str(vikram_risk["risk_score"])),
            status="active",
        )
        db.add(vikram)
        await db.flush()

        vikram_trust = TrustScore(
            worker_id=vikram.id,
            score=Decimal("0.100"),
            total_claims=0,
            approved_claims=0,
            fraud_flags=0,
            account_age_days=2,
            device_stability=Decimal("0.300"),
        )
        db.add(vikram_trust)

        vikram_premium = premium_calculator.calculate(
            "smart_protect", float(vikram_risk["risk_score"])
        )

        vikram_policy = Policy(
            worker_id=vikram.id,
            plan_name="smart_protect",
            plan_display_name="Smart Protect",
            base_price=Decimal("39"),
            plan_factor=Decimal("1.5"),
            risk_score_at_purchase=Decimal(str(vikram_risk["risk_score"])),
            weekly_premium=Decimal(str(vikram_premium["final_premium"])),
            coverage_cap=Decimal("600"),
            triggers_covered=["rain", "heat", "aqi", "traffic", "platform_outage"],
            status="active",
            purchased_at=now - timedelta(hours=26),
            activates_at=now - timedelta(hours=2),
            expires_at=now + timedelta(days=6, hours=22),
        )
        db.add(vikram_policy)

        print(f"  [ok] Vikram Singh created (ID: {vikram.id}) [fraud persona]")

        # ============================================
        # WORKER 3: Arun (Edge case - new user)
        # ============================================
        arun_risk = risk_scorer.calculate_risk_score("delhi", "east_delhi")

        arun = Worker(
            name="Arun Patel",
            phone="+919876543212",
            city="delhi",
            zone="east_delhi",
            platform="zomato",
            self_reported_income=Decimal("800"),
            working_hours=Decimal("8"),
            consent_given=True,
            consent_timestamp=now - timedelta(days=5),
            risk_score=Decimal(str(arun_risk["risk_score"])),
            status="active",
        )
        db.add(arun)
        await db.flush()

        arun_trust = TrustScore(
            worker_id=arun.id,
            score=Decimal("0.150"),
            total_claims=0,
            approved_claims=0,
            fraud_flags=0,
            account_age_days=5,
            device_stability=Decimal("0.500"),
        )
        db.add(arun_trust)

        arun_premium = premium_calculator.calculate(
            "assured_plan", float(arun_risk["risk_score"])
        )

        arun_policy = Policy(
            worker_id=arun.id,
            plan_name="assured_plan",
            plan_display_name="Assured Plan",
            base_price=Decimal("49"),
            plan_factor=Decimal("2.0"),
            risk_score_at_purchase=Decimal(str(arun_risk["risk_score"])),
            weekly_premium=Decimal(str(arun_premium["final_premium"])),
            coverage_cap=Decimal("800"),
            triggers_covered=[
                "rain",
                "heat",
                "aqi",
                "traffic",
                "platform_outage",
                "social",
            ],
            status="active",
            purchased_at=now - timedelta(hours=30),
            activates_at=now - timedelta(hours=6),
            expires_at=now + timedelta(days=6, hours=18),
        )
        db.add(arun_policy)

        minimal_activity = WorkerActivity(
            worker_id=arun.id,
            zone="east_delhi",
            latitude=Decimal("28.63"),
            longitude=Decimal("77.30"),
            speed_kmh=Decimal("12"),
            has_delivery_stop=True,
            recorded_at=now - timedelta(hours=3),
        )
        db.add(minimal_activity)

        print(f"  [ok] Arun Patel created (ID: {arun.id}) [edge case persona]")

        # ============================================
        # WORKER 4: Priya (Multi-city demo - Bengaluru)
        # ============================================
        priya_risk = risk_scorer.calculate_risk_score("bengaluru", "koramangala")

        priya = Worker(
            name="Priya Sharma",
            phone="+919876543213",
            city="bengaluru",
            zone="koramangala",
            platform="swiggy",
            self_reported_income=Decimal("850"),
            working_hours=Decimal("8"),
            consent_given=True,
            consent_timestamp=now - timedelta(days=60),
            risk_score=Decimal(str(priya_risk["risk_score"])),
            status="active",
        )
        db.add(priya)
        await db.flush()

        priya_trust = TrustScore(
            worker_id=priya.id,
            score=Decimal("0.850"),
            total_claims=25,
            approved_claims=22,
            fraud_flags=0,
            account_age_days=60,
            device_stability=Decimal("0.950"),
        )
        db.add(priya_trust)

        priya_premium = premium_calculator.calculate(
            "smart_protect", float(priya_risk["risk_score"])
        )

        priya_policy = Policy(
            worker_id=priya.id,
            plan_name="smart_protect",
            plan_display_name="Smart Protect",
            base_price=Decimal("39"),
            plan_factor=Decimal("1.5"),
            risk_score_at_purchase=Decimal(str(priya_risk["risk_score"])),
            weekly_premium=Decimal(str(priya_premium["final_premium"])),
            coverage_cap=Decimal("600"),
            triggers_covered=["rain", "heat", "aqi", "traffic", "platform_outage"],
            status="active",
            purchased_at=now - timedelta(hours=48),
            activates_at=now - timedelta(hours=24),
            expires_at=now + timedelta(days=5),
        )
        db.add(priya_policy)

        print(f"  [ok] Priya Sharma created (ID: {priya.id}) [Bengaluru, high trust]")
        print(
            f"     Risk: {priya_risk['risk_score']}, "
            f"Premium: INR {priya_premium['final_premium']}/week"
        )

        audit = AuditLog(
            entity_type="system",
            entity_id=rahul.id,
            action="database_seeded",
            details={
                "workers_created": 4,
                "policies_created": 4,
                "personas": [
                    "rahul_legitimate",
                    "vikram_fraud",
                    "arun_edge_case",
                    "priya_multi_city",
                ],
            },
        )
        db.add(audit)

        await db.commit()
        print("\nDatabase seeded successfully!")
        print("   Workers: 4")
        print("   Policies: 4")
        print("   Activity logs: 9")
        print("\nWorker IDs for testing:")
        print(f"   Rahul (legit):  {rahul.id}")
        print(f"   Vikram (fraud): {vikram.id}")
        print(f"   Arun (edge):    {arun.id}")
        print(f"   Priya (multi):  {priya.id}")


if __name__ == "__main__":
    asyncio.run(seed())
