from typing import Any, Dict, Optional
from sqlalchemy import select
from backend.database import async_session_factory
from backend.db.models import Worker, Policy, Claim

class WhatsAppDataService:
    """Safe, read-only data service for WhatsApp status checks."""
    
    async def get_worker_status(self, phone: str) -> Dict[str, Any]:
        """Fetch worker onboarding and policy status by phone."""
        async with async_session_factory() as session:
            # Normalize phone (remove +)
            clean_phone = phone.replace("+", "")
            
            stmt = select(Worker).where(Worker.phone.like(f"%{clean_phone}"))
            result = await session.execute(stmt)
            worker = result.scalar_one_or_none()
            
            if not worker:
                return {"found": False}
                
            # Get latest policy
            policy_stmt = select(Policy).where(Policy.worker_id == worker.id).order_by(Policy.created_at.desc())
            policy_result = await session.execute(policy_stmt)
            policy = policy_result.scalar_one_or_none()
            
            # Simple status check
            status = "inactive"
            if worker.status == "active":
                if policy and policy.is_active:
                    status = "active"
                else:
                    status = "pending"
                    
            return {
                "found": True,
                "name": worker.name,
                "status": status,
                "risk_score": float(worker.risk_score or 0.5),
                "plan": policy.plan_display_name if policy else None,
                "coverage_cap": float(policy.coverage_cap) if policy else 0,
            }

whatsapp_data = WhatsAppDataService()
