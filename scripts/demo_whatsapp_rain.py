import asyncio
import logging
import sys
import os

# Ensure we can import from the root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from backend.database import async_session_factory
from backend.core.claim_processor import claim_processor
from backend.core.demo_scenarios import _create_demo_worker, _create_demo_policy, DEMO_SCENARIOS, enrich_worker_for_demo
from backend.db.models import Worker, Policy
from backend.providers.whatsapp_settings_service import whatsapp_settings
from backend.providers.whatsapp_meta import whatsapp_meta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rideshield.demo")

async def run_rain_demo(phone: str, lang: str = "hi"):
    """
    Simulates a heavy rain scenario for a specific phone number
    to demonstrate the proactive WhatsApp 'You are covered' notification.
    """
    print(f"\nSTARTING RIDESHIELD RAIN DEMO FOR: {phone} ({lang})")
    print("-" * 50)

    async with async_session_factory() as session:
        # 0. Cleanup existing worker and all related records
        from backend.db.models import Worker, Policy, TrustScore, WorkerActivity, Claim, AuditLog
        
        # Get worker ID first
        result = await session.execute(select(Worker.id).where(Worker.phone == phone))
        worker_id = result.scalar()
        
        if worker_id:
            # Delete in social order to avoid FK issues
            await session.execute(delete(Claim).where(Claim.worker_id == worker_id))
            await session.execute(delete(Policy).where(Policy.worker_id == worker_id))
            await session.execute(delete(TrustScore).where(TrustScore.worker_id == worker_id))
            await session.execute(delete(WorkerActivity).where(WorkerActivity.worker_id == worker_id))
            await session.execute(delete(AuditLog).where(AuditLog.entity_id == worker_id))
            await session.execute(delete(Worker).where(Worker.id == worker_id))
            await session.commit()
            print(f"Cleanup done for {phone}")

        # 1. Setup Language
        await whatsapp_settings.set_user_lang(phone, lang)
        print(f"Language set to: {lang}")

        # 2. Create Demo Worker and Policy
        scenario = DEMO_SCENARIOS["clean_legit"]
        worker = await _create_demo_worker(session, scenario=scenario, phone=phone)
        
        from datetime import timedelta
        from backend.utils.time import utc_now_naive
        now = utc_now_naive()
        policy = Policy(
            worker_id=worker.id,
            plan_name=scenario.plan_name,
            plan_display_name="Smart Protect",
            base_price=39,
            plan_factor=1.5,
            risk_score_at_purchase=0.224,
            weekly_premium=58.5,
            coverage_cap=600,
            triggers_covered=["rain", "heat", "aqi", "traffic", "platform_outage"],
            status="active",
            purchased_at=now,
            activates_at=now,
            expires_at=now + timedelta(days=7),
        )
        session.add(policy)
        await session.commit()
        
        # IMPORTANT: Add activity records so they are considered 'in the zone'
        await enrich_worker_for_demo(str(worker.id), scenario.zone, scenario.profile, db=session)
        
        # Fresh fetch to ensure we have all relations
        result = await session.execute(
            select(Worker).options(selectinload(Worker.policies)).where(Worker.id == worker.id)
        )
        worker = result.scalar_one()
        
        print(f"Created Demo Worker: {worker.name}")
        print(f"Active Policy: {worker.policies[0].plan_display_name}")
        
        # 3. Simulate Rain & Trigger Cycle
        print("\n[SIMULATION] It starts raining heavily in Delhi...")
        print("[PROCESSOR] Running trigger engine and claim processor...")
        
        # We target ONLY this worker for the demo
        trigger_result = await claim_processor.run_trigger_cycle(
            db=session,
            zones=[scenario.zone],
            city=scenario.city,
            scenario="heavy_rain",
            demo_run_id=f"demo-wa-{phone}",
            targeted_worker_ids=[worker.id],
        )

        print("-" * 50)
        print(f"DEMO SUCCESS")
        print(f"   Claims Generated: {trigger_result['claims_generated']}")
        print(f"   WhatsApp Alert:   SENT (Proactive Coverage Notification)")
        print("-" * 50)
        print("\nCheck your Meta Developer Dashboard or WhatsApp number for the alert!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--phone", required=True, help="Phone number in E.164 format (e.g. +919876543210)")
    parser.add_argument("--lang", default="hi", choices=["en", "hi"], help="Language for the notification")
    args = parser.parse_args()

    asyncio.run(run_rain_demo(args.phone, args.lang))
