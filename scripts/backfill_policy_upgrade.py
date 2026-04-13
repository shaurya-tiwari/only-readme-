"""Safely re-resolve delayed claims using the current policy with strong guardrails."""

from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import settings
from backend.core.decision_engine import decision_engine
from backend.core.decision_memory import record_claim_resolution
from backend.core.payout_executor import payout_executor
from backend.database import async_session_factory
from backend.db.models import AuditLog, Claim, TrustScore
from backend.utils.time import utc_now_naive


def _fraud_result(claim: Claim) -> dict[str, Any]:
    breakdown = claim.decision_breakdown if isinstance(claim.decision_breakdown, dict) else {}
    inputs = breakdown.get("inputs") if isinstance(breakdown.get("inputs"), dict) else {}
    fraud_model = breakdown.get("fraud_model") if isinstance(breakdown.get("fraud_model"), dict) else {}
    return {
        "adjusted_fraud_score": float(claim.fraud_score or 0),
        "raw_fraud_score": float(inputs.get("raw_fraud_score", claim.fraud_score or 0)),
        "flags": list(inputs.get("fraud_flags") or []),
        "signals": fraud_model.get("signals") or {},
        "ml_confidence": fraud_model.get("confidence"),
        "fallback_used": fraud_model.get("fallback_used", False),
        "model_version": fraud_model.get("model_version"),
        "fraud_probability": fraud_model.get("fraud_probability"),
        "top_factors": fraud_model.get("top_factors") or [],
    }


def _candidate_review(claim: Claim) -> tuple[bool, str, dict[str, Any] | None]:
    payout = float(claim.final_payout or claim.calculated_payout or 0)
    trust_score = float(claim.trust_score or 0)
    fraud_result = _fraud_result(claim)
    flags = set(fraud_result["flags"])
    if flags & decision_engine.STRONG_REVIEW_FLAGS:
        return False, "strong_flags_present", None
    if flags - decision_engine.LOW_RISK_REVIEW_FLAGS:
        return False, "non_weak_flags_present", None
    if payout > settings.DECISION_FALSE_REVIEW_PAYOUT_CAP:
        return False, "payout_above_safe_lane", None
    if trust_score < settings.DECISION_HIGH_TRUST_THRESHOLD:
        return False, "trust_below_guardrail", None

    replayed = decision_engine.decide(
        disruption_score=float(claim.disruption_score or 0),
        event_confidence=float(claim.event_confidence or 0),
        fraud_result=fraud_result,
        trust_score=trust_score,
        payout_amount=payout,
    )
    if replayed["decision"] != "approved":
        return False, "current_policy_not_approved", replayed
    if replayed["decision_confidence_band"] != "high":
        return False, "confidence_not_high", replayed
    if replayed["uncertainty"]["case"] is not None:
        return False, "uncertainty_case_present", replayed
    return True, "policy_upgrade_safe_lane", replayed


async def run_backfill(*, apply_changes: bool, limit: int | None) -> dict[str, Any]:
    async with async_session_factory() as db:
        claims = (
            await db.execute(
                select(Claim)
                .options(selectinload(Claim.worker), selectinload(Claim.policy), selectinload(Claim.event), selectinload(Claim.payout))
                .where(Claim.status == "delayed")
                .order_by(Claim.created_at.asc())
            )
        ).scalars().all()
        if limit:
            claims = claims[:limit]

        candidates: list[tuple[Claim, str, dict[str, Any]]] = []
        skipped: dict[str, int] = {}
        for claim in claims:
            okay, reason, replayed = _candidate_review(claim)
            if okay and replayed is not None:
                candidates.append((claim, reason, replayed))
            else:
                skipped[reason] = skipped.get(reason, 0) + 1

        print(f"Delayed claims scanned: {len(claims)}")
        print(f"Safe policy-upgrade candidates: {len(candidates)}")
        if skipped:
            print("Skipped:")
            for reason, count in sorted(skipped.items(), key=lambda item: (-item[1], item[0])):
                print(f"- {reason}: {count}")

        for claim, reason, replayed in candidates:
            payout = float(claim.final_payout or claim.calculated_payout or 0)
            print(
                f"- approve {str(claim.id)[:8]} worker={claim.worker.name if claim.worker else claim.worker_id} "
                f"payout={payout:.2f} confidence={float(replayed['decision_confidence']):.3f} "
                f"rule={replayed['rule_id']} reason={reason}"
            )

        if not apply_changes:
            return {"scanned": len(claims), "candidates": len(candidates), "skipped": skipped}

        approved = 0
        now = utc_now_naive()
        for claim, reason, replayed in candidates:
            previous_status = claim.status
            claim.status = "approved"
            claim.reviewed_by = "policy_upgrade_backfill"
            claim.reviewed_at = now
            claim.updated_at = now
            claim.review_deadline = None
            claim.rejection_reason = None
            payout_amount = float(claim.final_payout or claim.calculated_payout or 0)
            payout_result = None
            if not claim.payout:
                payout_result = await payout_executor.execute(
                    db,
                    claim,
                    claim.worker,
                    claim.policy.plan_name if claim.policy else "smart_protect",
                    payout_amount,
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
                    action="policy_upgrade_backfill_approve",
                    details={
                        "reason_code": reason,
                        "previous_status": previous_status,
                        "policy_layer": replayed["policy_layer"],
                        "rule_id": replayed["rule_id"],
                        "decision_confidence": replayed["decision_confidence"],
                    },
                )
            )
            await record_claim_resolution(
                db=db,
                claim=claim,
                event=claim.event,
                decision_source="system_backfill",
                reviewed_by="policy_upgrade_backfill",
                review_reason="Policy-upgrade backfill approved this legacy delayed claim using the current guarded safe lane.",
                label_source="policy_backfill",
                payout_result=payout_result,
                resolution_payload={
                    "backfill_resolution": True,
                    "reason_code": reason,
                    "previous_status": previous_status,
                    "policy_layer": replayed["policy_layer"],
                    "rule_id": replayed["rule_id"],
                },
            )
            approved += 1

        await db.commit()
        print(f"Applied approvals: {approved}")
        return {"scanned": len(claims), "approved": approved, "skipped": skipped}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely backfill delayed claims using the current policy.")
    parser.add_argument("--apply", action="store_true", help="Apply the backfill instead of running in dry-run mode.")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit on delayed claims scanned.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_backfill(apply_changes=args.apply, limit=args.limit))
