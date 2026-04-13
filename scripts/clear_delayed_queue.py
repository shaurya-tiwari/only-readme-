"""Local-only queue cleanup for Phase 3 dataset generation."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from decimal import Decimal
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
        "is_suspicious": float(claim.fraud_score or 0) > 0.5,
        "is_high_risk": float(claim.fraud_score or 0) > 0.7,
    }


def _model_version(claim: Claim) -> str:
    breakdown = claim.decision_breakdown if isinstance(claim.decision_breakdown, dict) else {}
    fraud_model = breakdown.get("fraud_model") if isinstance(breakdown.get("fraud_model"), dict) else {}
    return str(fraud_model.get("model_version") or "unknown")


def _classify(claim: Claim) -> tuple[str | None, str]:
    fraud_result = _fraud_result(claim)
    flags = set(fraud_result["flags"])
    payout = float(claim.final_payout or claim.calculated_payout or 0)
    fraud_score = float(claim.fraud_score or 0)
    final_score = float(claim.final_score or 0)
    trust_score = float(claim.trust_score or 0)
    model_version = _model_version(claim)
    reevaluated = decision_engine.decide(
        disruption_score=float(claim.disruption_score or 0),
        event_confidence=float(claim.event_confidence or 0),
        fraud_result=fraud_result,
        trust_score=trust_score,
        payout_amount=payout,
    )

    if reevaluated["decision"] == "approved":
        return "approve", "current_policy_safe"

    if model_version == "fraud-model-v1" and not (flags & decision_engine.STRONG_REVIEW_FLAGS) and payout <= 125 and final_score >= 0.60:
        return "approve", "legacy_weak_signal_backlog"

    if flags == {"device"} and payout <= 40 and fraud_score <= 0.10 and trust_score >= 0.60:
        return "approve", "device_only_micro_payout"

    if flags == {"pre_activity"} and payout <= 40 and fraud_score <= 0.08 and trust_score >= 0.80 and final_score >= 0.60:
        return "approve", "pre_activity_micro_payout"

    if not flags and payout <= 35 and fraud_score <= 0.10 and trust_score >= 0.60 and final_score >= 0.45:
        return "approve", "clean_micro_payout"

    if "cluster" in flags and payout <= 100 and fraud_score <= 0.30 and final_score <= 0.56:
        return "reject", "cluster_caution_resolution"

    if "income_inflation" in flags and fraud_score >= 0.35:
        return "reject", "income_inflation_resolution"

    if flags & decision_engine.STRONG_REVIEW_FLAGS and final_score < 0.58:
        return "reject", "strong_flag_review_resolution"

    return None, "leave_for_manual_review"


async def clear_delayed_queue(*, apply_changes: bool) -> dict[str, Any]:
    async with async_session_factory() as db:
        claims = (
            await db.execute(
                select(Claim)
                .options(selectinload(Claim.worker), selectinload(Claim.policy), selectinload(Claim.event), selectinload(Claim.payout))
                .where(Claim.status == "delayed")
                .order_by(Claim.created_at.asc())
            )
        ).scalars().all()

        decisions = []
        reason_counts = Counter()
        for claim in claims:
            decision, reason = _classify(claim)
            reason_counts[reason] += 1
            decisions.append((claim, decision, reason))

        print(f"Current delayed queue: {len(claims)}")
        print("Classification:")
        for reason, count in sorted(reason_counts.items(), key=lambda item: (-item[1], item[0])):
            print(f"- {reason}: {count}")

        preview = []
        for claim, decision, reason in decisions:
            if decision:
                preview.append(
                    {
                        "claim_id": str(claim.id)[:8],
                        "worker": claim.worker.name if claim.worker else str(claim.worker_id),
                        "decision": decision,
                        "reason": reason,
                        "model": _model_version(claim),
                        "payout": float(claim.final_payout or claim.calculated_payout or 0),
                        "score": float(claim.final_score or 0),
                        "fraud": float(claim.fraud_score or 0),
                        "flags": _fraud_result(claim)["flags"],
                    }
                )
        print(f"Resolvable now: {len(preview)}")
        for row in preview:
            print(
                f"- {row['decision']:7} {row['claim_id']} {row['worker']} "
                f"model={row['model']} payout={row['payout']:.2f} "
                f"score={row['score']:.3f} fraud={row['fraud']:.3f} "
                f"reason={row['reason']} flags={','.join(row['flags']) or 'none'}"
            )

        if not apply_changes:
            return {"queue_size": len(claims), "resolvable": len(preview), "reason_counts": dict(reason_counts)}

        approved = 0
        rejected = 0
        now = utc_now_naive()
        for claim, decision, reason in decisions:
            if not decision:
                continue
            previous_status = claim.status
            claim.reviewed_by = "phase3_queue_cleanup"
            claim.reviewed_at = now
            claim.updated_at = now
            payout_result = None

            if decision == "approve":
                claim.status = "approved"
                claim.review_deadline = None
                claim.rejection_reason = None
                payout_amount = float(claim.final_payout or claim.calculated_payout or 0)
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
                approved += 1
            else:
                claim.status = "rejected"
                claim.review_deadline = None
                claim.rejection_reason = f"Synthetic Phase 3 queue cleanup: {reason}."
                claim.final_payout = Decimal("0")
                rejected += 1

            db.add(
                AuditLog(
                    entity_type="claim",
                    entity_id=claim.id,
                    action=f"phase3_queue_cleanup_{decision}",
                    details={
                        "decision": decision,
                        "reason_code": reason,
                        "reviewed_by": "phase3_queue_cleanup",
                        "previous_status": previous_status,
                    },
                )
            )
            await record_claim_resolution(
                db=db,
                claim=claim,
                event=claim.event,
                decision_source="admin",
                reviewed_by="phase3_queue_cleanup",
                review_reason=f"Synthetic Phase 3 queue cleanup: {reason}.",
                label_source="admin_review",
                payout_result=payout_result,
                resolution_payload={
                    "previous_status": previous_status,
                    "resolved_by": "phase3_queue_cleanup",
                    "decision": decision,
                    "reason_code": reason,
                },
            )

        await db.commit()
        remaining = (
            await db.execute(select(Claim).where(Claim.status == "delayed"))
        ).scalars().all()
        print(f"Applied approvals: {approved}")
        print(f"Applied rejections: {rejected}")
        print(f"Remaining delayed queue: {len(remaining)}")
        return {
            "queue_size": len(claims),
            "approved": approved,
            "rejected": rejected,
            "remaining_delayed": len(remaining),
            "reason_counts": dict(reason_counts),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve the local delayed queue into labeled outcomes.")
    parser.add_argument("--apply", action="store_true", help="Apply the cleanup instead of running in dry-run mode.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(clear_delayed_queue(apply_changes=args.apply))
