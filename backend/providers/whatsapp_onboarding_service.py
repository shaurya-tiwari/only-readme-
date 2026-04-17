import logging
from decimal import Decimal
from datetime import timedelta
from typing import Dict, Any, Optional
from sqlalchemy import select
from backend.database import async_session_factory
from backend.db.models import Worker, Policy, TrustScore, AuditLog, Zone
from backend.core.risk_scorer import risk_scorer
from backend.core.premium_calculator import premium_calculator
from backend.core.password_auth import hash_password
from backend.core.location_service import location_service
from backend.utils.time import utc_now_naive
from backend.config import settings

logger = logging.getLogger("rideshield.whatsapp")

class WhatsAppOnboardingService:
    """Handles the creation of worker and policy records from WhatsApp data."""
    
    async def get_plans_for_city(self, city_slug: str) -> Dict[str, Any]:
        """Calculate plans for a new worker based on their city's base risk."""
        async with async_session_factory() as session:
            try:
                # Get the first active zone in the city to get a base risk
                zones = await location_service.get_active_zones(session, city_slug=city_slug)
                if not zones:
                    return {"error": "City not supported"}
                
                zone = zones[0]
                base_risk = float(zone.risk_profile.base_risk) if zone.risk_profile else 0.5
                
                # Mock risk score calculation for onboarding
                risk_result = risk_scorer.calculate_risk_score(
                    city=city_slug,
                    zone=zone.slug,
                    city_base_override=base_risk,
                )
                
                plans, recommended = premium_calculator.calculate_all_plans(
                    risk_result["risk_score"],
                    risk_meta=risk_result["breakdown"],
                )
                
                return {
                    "plans": plans,
                    "recommended": recommended,
                    "risk_score": risk_result["risk_score"],
                    "zone_id": zone.id,
                    "city_id": zone.city_id,
                    "zone_slug": zone.slug
                }
            except Exception as e:
                logger.error(f"Error calculating plans for WhatsApp onboarding: {e}")
                return {"error": str(e)}

    async def finalize_onboarding(self, phone: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create Worker and Policy records after mock payment success."""
        async with async_session_factory() as session:
            try:
                # 1. Create Worker
                worker = Worker(
                    name=data["name"],
                    phone=phone,
                    password_hash=hash_password(data["password"]),
                    city_id=data["city_id"],
                    zone_id=data["zone_id"],
                    city=data["city_slug"],
                    zone=data["zone_slug"],
                    platform=data["platform"],
                    self_reported_income=Decimal("500"), # Default
                    working_hours=Decimal("8"),        # Default
                    consent_given=True,
                    consent_timestamp=utc_now_naive(),
                    risk_score=Decimal(str(data["risk_score"])),
                    status="active",
                )
                session.add(worker)
                await session.flush()

                # 2. Create TrustScore
                session.add(
                    TrustScore(
                        worker_id=worker.id,
                        score=Decimal("0.100"),
                        total_claims=0,
                        approved_claims=0,
                        fraud_flags=0,
                        account_age_days=0,
                        device_stability=Decimal("0.500"),
                    )
                )

                # 3. Create Policy
                plan_name = data["plan"]
                plan_def = settings.PLAN_DEFINITIONS[plan_name]
                now = utc_now_naive()
                
                policy = Policy(
                    worker_id=worker.id,
                    plan_name=plan_name,
                    plan_display_name=plan_def["display_name"],
                    base_price=Decimal(str(plan_def["base_price"])),
                    plan_factor=Decimal(str(plan_def["plan_factor"])),
                    risk_score_at_purchase=Decimal(str(data["risk_score"])),
                    weekly_premium=Decimal(str(data["price"])),
                    coverage_cap=Decimal(str(plan_def["coverage_cap"])),
                    triggers_covered=plan_def["triggers_covered"],
                    status="active",
                    purchased_at=now,
                    activates_at=now,
                    expires_at=now + timedelta(days=7),
                )
                session.add(policy)

                # 4. Audit Log
                session.add(
                    AuditLog(
                        entity_type="worker",
                        entity_id=worker.id,
                        action="whatsapp_onboarded",
                        details={
                            "phone": phone,
                            "plan": plan_name,
                            "price": data["price"],
                            "city": data["city_slug"],
                        },
                        performed_by="system_whatsapp",
                    )
                )

                await session.commit()
                return {"success": True, "worker_id": str(worker.id)}
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to finalize WhatsApp onboarding for {phone}: {e}")
                return {"success": False, "error": str(e)}

whatsapp_onboarding = WhatsAppOnboardingService()
