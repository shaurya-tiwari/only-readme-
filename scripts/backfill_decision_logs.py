"""Backfill Wave 1 decision-memory rows for existing claims."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from pathlib import Path
import sys

from sqlalchemy import inspect, select
from sqlalchemy.orm import selectinload

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import settings
from backend.core.decision_memory import record_claim_decision, record_claim_resolution
from backend.database import async_session_factory, engine, init_db
from backend.db.models import Claim


def _build_fraud_result(claim: Claim) -> dict:
    breakdown = claim.decision_breakdown if isinstance(claim.decision_breakdown, dict) else {}
    inputs = breakdown.get("inputs") if isinstance(breakdown.get("inputs"), dict) else {}
    fraud_model = breakdown.get("fraud_model") if isinstance(breakdown.get("fraud_model"), dict) else {}
    return {
        "adjusted_fraud_score": float(claim.fraud_score or 0),
        "raw_fraud_score": inputs.get("raw_fraud_score", float(claim.fraud_score or 0)),
        "flags": list(inputs.get("fraud_flags") or []),
        "ml_confidence": fraud_model.get("confidence"),
        "fallback_used": fraud_model.get("fallback_used", False),
        "model_version": fraud_model.get("model_version", "rule-based"),
        "fraud_probability": fraud_model.get("fraud_probability"),
        "top_factors": fraud_model.get("top_factors", []),
    }


async def _ensure_schema() -> None:
    async with engine.begin() as conn:
        decision_logs_exists = await conn.run_sync(lambda sync_conn: inspect(sync_conn).has_table("decision_logs"))
    if not decision_logs_exists and settings.ENV != "prod":
        await init_db()


async def backfill_decision_logs(*, apply_changes: bool, limit: int | None) -> None:
    await _ensure_schema()

    async with async_session_factory() as db:
        claims = (
            await db.execute(
                select(Claim)
                .options(
                    selectinload(Claim.worker),
                    selectinload(Claim.policy),
                    selectinload(Claim.event),
                    selectinload(Claim.decision_logs),
                )
                .order_by(Claim.created_at.asc())
            )
        ).scalars().all()

        if limit:
            claims = claims[:limit]

        creation_candidates = []
        resolution_candidates = []
        review_sources = Counter()

        for claim in claims:
            stages = {log.lifecycle_stage for log in claim.decision_logs}
            has_creation = "claim_created" in stages
            has_resolution = bool(stages & {"manual_resolution", "backfill_resolution"})

            if not has_creation:
                creation_candidates.append(claim)

            if claim.reviewed_by and not has_resolution:
                review_sources[claim.reviewed_by] += 1
                resolution_candidates.append(claim)

        print(f"Scanned claims: {len(claims)}")
        print(f"Missing claim_created logs: {len(creation_candidates)}")
        print(f"Missing resolution logs: {len(resolution_candidates)}")
        if review_sources:
            print("Existing review sources:", dict(review_sources))

        if not apply_changes:
            return

        created_rows = 0
        resolved_rows = 0

        for claim in creation_candidates:
            await record_claim_decision(
                db=db,
                claim=claim,
                worker=claim.worker,
                policy=claim.policy,
                event=claim.event,
                fraud_result=_build_fraud_result(claim),
                payout_calc=None,
                feedback_result=None,
            )
            created_rows += 1

        for claim in resolution_candidates:
            if claim.reviewed_by == "system_backfill":
                decision_source = "system_backfill"
                label_source = "policy_backfill"
                review_reason = "Backfilled legacy policy reconciliation."
            else:
                decision_source = "admin"
                label_source = "legacy_admin_review"
                review_reason = claim.rejection_reason or "Backfilled legacy admin review."

            await record_claim_resolution(
                db=db,
                claim=claim,
                event=claim.event,
                decision_source=decision_source,
                reviewed_by=claim.reviewed_by,
                review_reason=review_reason,
                label_source=label_source,
                payout_result=None,
                resolution_payload={
                    "backfill_applied": True,
                    "legacy_status": claim.status,
                    "legacy_reviewed_at": claim.reviewed_at.isoformat() if claim.reviewed_at else None,
                },
            )
            resolved_rows += 1

        await db.commit()
        print(f"Created claim_created logs: {created_rows}")
        print(f"Created resolution logs: {resolved_rows}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill decision-memory rows for existing claims.")
    parser.add_argument("--apply", action="store_true", help="Persist backfilled decision-memory rows.")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit on number of claims scanned.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(backfill_decision_logs(apply_changes=args.apply, limit=args.limit))
