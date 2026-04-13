"""
Payout executor for simulated wallet and UPI transfers.
"""

import uuid
from decimal import Decimal
from typing import Dict

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import AuditLog, Claim, Payout, Worker
from backend.utils.time import utc_now_naive


class PayoutExecutor:
    def _channel_for_plan(self, plan_name: str) -> tuple[str, str]:
        if plan_name == "pro_max":
            return "upi", "upi_simulator"
        return "wallet", "razorpay_sandbox"

    def _notification_for_status(self, *, status: str, amount: float, channel: str, worker_name: str) -> dict:
        if status == "completed":
            return {
                "type": "payout_credited",
                "title": f"INR {amount} income protection credited",
                "message": f"Income protection payout of INR {amount} has been credited to your {channel}.",
                "worker_name": worker_name,
                "amount": amount,
                "channel": channel,
            }
        return {
            "type": "payout_failed",
            "title": "Payout needs another attempt",
            "message": "Your claim is approved, but the transfer could not be completed right now.",
            "worker_name": worker_name,
            "amount": amount,
            "channel": channel,
        }

    async def _mark_failed(
        self,
        db: AsyncSession,
        claim: Claim,
        worker: Worker,
        plan_name: str,
        amount: float,
        error: str,
        payout: Payout | None = None,
    ) -> Dict:
        channel, provider = self._channel_for_plan(plan_name)
        now = utc_now_naive()
        payout = payout or Payout(
            claim_id=claim.id,
            worker_id=worker.id,
            amount=Decimal(str(amount)),
            channel=channel,
            status="failed",
            initiated_at=now,
        )
        payout.channel = channel
        payout.status = "failed"
        payout.completed_at = None
        payout.transaction_id = None
        db.add(payout)
        await db.flush()
        db.add(
            AuditLog(
                entity_type="payout",
                entity_id=payout.id,
                action="failed",
                details={
                    "claim_id": str(claim.id),
                    "worker_id": str(worker.id),
                    "worker_name": worker.name,
                    "amount": amount,
                    "channel": channel,
                    "plan_name": plan_name,
                    "provider": provider,
                    "error": error,
                },
            )
        )
        return {
            "payout_id": str(payout.id),
            "amount": amount,
            "channel": channel,
            "transaction_id": None,
            "status": "failed",
            "initiated_at": payout.initiated_at.isoformat() if payout.initiated_at else None,
            "completed_at": None,
            "notification": self._notification_for_status(
                status="failed",
                amount=amount,
                channel=channel,
                worker_name=worker.name,
            ),
            "error": error,
        }

    async def record_failed(self, db: AsyncSession, claim: Claim, worker: Worker, plan_name: str, amount: float, error: str) -> Dict:
        return await self._mark_failed(db, claim, worker, plan_name, amount, error)

    def _simulate_transfer(self, plan_name: str) -> Dict:
        channel, provider = self._channel_for_plan(plan_name)
        transaction_prefix = "upi" if channel == "upi" else "wallet"
        return {
            "channel": channel,
            "provider": provider,
            "transaction_id": f"{transaction_prefix}_{uuid.uuid4().hex[:12]}",
        }

    async def execute(self, db: AsyncSession, claim: Claim, worker: Worker, plan_name: str, amount: float) -> Dict:
        now = utc_now_naive()
        channel, _ = self._channel_for_plan(plan_name)
        payout = Payout(
            claim_id=claim.id,
            worker_id=worker.id,
            amount=Decimal(str(amount)),
            channel=channel,
            transaction_id=None,
            status="processing",
            initiated_at=now,
            completed_at=None,
        )
        db.add(payout)
        await db.flush()
        try:
            result = self._simulate_transfer(plan_name)
            payout.channel = result["channel"]
            payout.transaction_id = result["transaction_id"]
            payout.status = "completed"
            payout.completed_at = utc_now_naive()
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
                        "channel": payout.channel,
                        "transaction_id": result["transaction_id"],
                        "plan_name": plan_name,
                        "provider": result["provider"],
                    },
                )
            )
            return {
                "payout_id": str(payout.id),
                "amount": amount,
                "channel": payout.channel,
                "transaction_id": result["transaction_id"],
                "status": "completed",
                "initiated_at": payout.initiated_at.isoformat(),
                "completed_at": payout.completed_at.isoformat() if payout.completed_at else None,
                "notification": self._notification_for_status(
                    status="completed",
                    amount=amount,
                    channel=payout.channel,
                    worker_name=worker.name,
                ),
            }
        except Exception as exc:
            return await self._mark_failed(
                db,
                claim,
                worker,
                plan_name,
                amount,
                str(exc),
                payout=payout,
            )


payout_executor = PayoutExecutor()
