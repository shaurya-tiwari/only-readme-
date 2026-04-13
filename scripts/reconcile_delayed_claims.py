"""Dry-run/apply tool for re-evaluating delayed claims under the current policy."""

from __future__ import annotations

import argparse
import asyncio
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import sys

from sqlalchemy import select
from sqlalchemy.orm import selectinload

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.decision_memory import record_claim_resolution
from backend.core.decision_engine import decision_engine
from backend.core.payout_executor import payout_executor
from backend.database import async_session_factory
from backend.db.models import AuditLog, Claim, TrustScore
from backend.utils.time import utc_now_naive


def _build_fraud_result(claim: Claim) -> dict:
    breakdown = claim.decision_breakdown or {}
    inputs = breakdown.get("inputs") or {}
    fraud_model = breakdown.get("fraud_model") or {}
    return {
        "adjusted_fraud_score": float(claim.fraud_score or 0),
        "raw_fraud_score": inputs.get("raw_fraud_score", float(claim.fraud_score or 0)),
        "flags": list(inputs.get("fraud_flags") or []),
        "ml_confidence": fraud_model.get("confidence"),
        "fallback_used": fraud_model.get("fallback_used", False),
        "is_suspicious": float(claim.fraud_score or 0) > 0.5,
        "is_high_risk": float(claim.fraud_score or 0) > 0.7,
    }


async def reconcile_delayed_claims(*, apply_changes: bool, days: int, limit: int | None) -> None:
    cutoff = utc_now_naive() - timedelta(days=days)
    async with async_session_factory() as db:
        query = (
            select(Claim)
            .options(selectinload(Claim.worker), selectinload(Claim.policy), selectinload(Claim.payout), selectinload(Claim.event))
            .where(Claim.status == "delayed", Claim.created_at >= cutoff)
            .order_by(Claim.created_at.desc())
        )
        if limit:
            query = query.limit(limit)
        claims = (await db.execute(query)).scalars().all()

        candidates = []
        for claim in claims:
            fraud_result = _build_fraud_result(claim)
            decision_result = decision_engine.decide(
                disruption_score=float(claim.disruption_score or 0),
                event_confidence=float(claim.event_confidence or 0),
                fraud_result=fraud_result,
                trust_score=float(claim.trust_score or 0),
                payout_amount=float(claim.final_payout or claim.calculated_payout or 0),
            )
            if decision_result["decision"] != "approved":
                continue
            candidates.append((claim, decision_result))

        print(f"Scanned {len(claims)} delayed claims from the last {days} day(s).")
        print(f"Eligible for approval under current policy: {len(candidates)}")

        for claim, decision_result in candidates:
            print(
                f"- {claim.worker.name if claim.worker else claim.worker_id} "
                f"{str(claim.id)[:8]} final={float(claim.final_score or 0):.3f} "
                f"fraud={float(claim.fraud_score or 0):.3f} trust={float(claim.trust_score or 0):.3f} "
                f"confidence={decision_result['decision_confidence']:.3f}"
            )

        if not apply_changes or not candidates:
            return

        now = utc_now_naive()
        applied = 0
        for claim, decision_result in candidates:
            if claim.payout:
                continue
            claim.status = "approved"
            claim.reviewed_by = "system_backfill"
            claim.reviewed_at = now
            claim.updated_at = now
            claim.review_deadline = None
            claim.rejection_reason = None
            claim.final_score = Decimal(str(decision_result["final_score"]))
            claim.decision_breakdown = {
                **(claim.decision_breakdown or {}),
                "backfill_reconciled_at": now.isoformat(),
                "backfill_reason": "approved_under_current_policy",
                "review_deadline": None,
                "decision_confidence": decision_result["decision_confidence"],
                "decision_confidence_band": decision_result["decision_confidence_band"],
                "primary_reason": decision_result["primary_reason"],
                "explanation": decision_result["explanation"],
                "inputs": {
                    **((claim.decision_breakdown or {}).get("inputs") or {}),
                    "backfill_applied": True,
                },
            }
            payout_amount = claim.final_payout
            if payout_amount is None:
                payout_amount = claim.calculated_payout or 0
            await payout_executor.execute(
                db,
                claim,
                claim.worker,
                claim.policy.plan_name if claim.policy else "smart_protect",
                float(payout_amount),
            )
            trust = (
                await db.execute(select(TrustScore).where(TrustScore.worker_id == claim.worker_id))
            ).scalar_one_or_none()
            if trust:
                trust.approved_claims = (trust.approved_claims or 0) + 1
                trust.score = Decimal(str(min(1.0, float(trust.score) + 0.02)))
                trust.last_updated = now
            db.add(
                AuditLog(
                    entity_type="claim",
                    entity_id=claim.id,
                    action="backfill_resolved_approve",
                    details={
                        "reviewed_by": "system_backfill",
                        "decision": "approve",
                        "reason": "Current policy now approves this previously delayed claim.",
                    },
                )
            )
            await record_claim_resolution(
                db=db,
                claim=claim,
                event=claim.event,
                decision_source="system_backfill",
                reviewed_by="system_backfill",
                review_reason="Current policy now approves this previously delayed claim.",
                label_source="policy_backfill",
                resolution_payload={
                    "decision": "approve",
                    "backfill_reason": "approved_under_current_policy",
                },
            )
            applied += 1

        await db.commit()
        print(f"Applied approvals: {applied}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reconcile delayed claims under the current decision policy.")
    parser.add_argument("--apply", action="store_true", help="Apply approvals instead of running in dry-run mode.")
    parser.add_argument("--days", type=int, default=7, help="Only inspect delayed claims newer than this many days.")
    parser.add_argument("--limit", type=int, default=None, help="Optional cap on claims scanned.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(reconcile_delayed_claims(apply_changes=args.apply, days=args.days, limit=args.limit))
