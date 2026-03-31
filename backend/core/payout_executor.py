"""
Payout executor for simulated wallet and UPI transfers.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import AuditLog, Claim, Payout, Worker


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PayoutExecutor:
    async def execute(self, db: AsyncSession, claim: Claim, worker: Worker, plan_name: str, amount: float) -> Dict:
        if plan_name == "pro_max":
            channel = "upi"
            result = {"transaction_id": f"upi_{uuid.uuid4().hex[:12]}", "provider": "upi_simulator"}
        else:
            channel = "wallet"
            result = {"transaction_id": f"wallet_{uuid.uuid4().hex[:12]}", "provider": "razorpay_sandbox"}

        now = utc_now_naive()
        payout = Payout(
            claim_id=claim.id,
            worker_id=worker.id,
            amount=Decimal(str(amount)),
            channel=channel,
            transaction_id=result["transaction_id"],
            status="completed",
            initiated_at=now,
            completed_at=now,
        )
        db.add(payout)
        await db.flush()
        claim.final_payout = Decimal(str(amount))
        db.add(
            AuditLog(
                entity_type="payout",
                entity_id=payout.id,
                action="executed",
                details={
                    "claim_id": str(claim.id),
                    "worker_id": str(worker.id),
                    "worker_name": worker.name,
                    "amount": amount,
                    "channel": channel,
                    "transaction_id": result["transaction_id"],
                    "plan_name": plan_name,
                },
            )
        )
        return {
            "payout_id": str(payout.id),
            "amount": amount,
            "channel": channel,
            "transaction_id": result["transaction_id"],
            "status": "completed",
            "initiated_at": payout.initiated_at.isoformat(),
            "completed_at": payout.completed_at.isoformat(),
            "notification": {
                "type": "payout_credited",
                "title": f"INR {amount} income protection credited",
                "message": f"Income protection payout of INR {amount} has been credited to your {channel}.",
                "worker_name": worker.name,
                "amount": amount,
                "channel": channel,
            },
        }


payout_executor = PayoutExecutor()
