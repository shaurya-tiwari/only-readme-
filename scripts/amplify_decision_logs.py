"""Generate bounded replay-amplified variants from stored decision-memory rows."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import inspect, select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import settings
from backend.core.decision_engine import decision_engine
from backend.core.decision_memory import default_export_path
from backend.database import async_session_factory, close_db, engine, init_db
from backend.db.models import DecisionLog


def _bounded_variants(row: DecisionLog) -> list[dict[str, Any]]:
    snapshot = row.feature_snapshot if isinstance(row.feature_snapshot, dict) else {}
    decision_inputs = snapshot.get("decision_inputs") if isinstance(snapshot.get("decision_inputs"), dict) else {}
    fraud_result = decision_inputs.get("fraud_result") if isinstance(decision_inputs.get("fraud_result"), dict) else {}

    base_payout = float(decision_inputs.get("payout_amount") or 0)
    base_trust = float(decision_inputs.get("trust_score") or 0)
    base_conf = float(decision_inputs.get("event_confidence") or 0)
    base_disruption = float(decision_inputs.get("disruption_score") or 0)

    variants = []
    for payout_delta, trust_delta, conf_delta, label in [
        (15.0, -0.04, -0.03, "slightly_riskier"),
        (-12.0, 0.03, 0.02, "slightly_safer"),
        (8.0, -0.02, 0.01, "nearby_variant"),
    ]:
        amplified_inputs = {
            "disruption_score": round(max(0.0, min(1.0, base_disruption)), 3),
            "event_confidence": round(max(0.0, min(1.0, base_conf + conf_delta)), 3),
            "trust_score": round(max(0.0, min(1.0, base_trust + trust_delta)), 3),
            "payout_amount": round(max(0.0, base_payout + payout_delta), 2),
            "fraud_result": {
                **fraud_result,
            },
            "feedback_result": decision_inputs.get("feedback_result") or {},
        }
        replayed = decision_engine.decide(
            disruption_score=amplified_inputs["disruption_score"],
            event_confidence=amplified_inputs["event_confidence"],
            fraud_result={
                "adjusted_fraud_score": float(fraud_result.get("adjusted_fraud_score") or 0),
                "raw_fraud_score": float(fraud_result.get("raw_fraud_score") or 0),
                "flags": list(fraud_result.get("flags") or []),
                "ml_confidence": fraud_result.get("ml_confidence"),
                "fallback_used": fraud_result.get("fallback_used", False),
                "model_version": fraud_result.get("model_version"),
                "fraud_probability": fraud_result.get("fraud_probability"),
                "top_factors": fraud_result.get("top_factors") or [],
            },
            trust_score=amplified_inputs["trust_score"],
            feedback_result=amplified_inputs["feedback_result"],
            payout_amount=amplified_inputs["payout_amount"],
        )
        variants.append(
            {
                "original_claim_id": str(row.claim_id),
                "original_decision": row.system_decision,
                "original_traffic_source": (
                    (row.context_snapshot or {}).get("traffic_source") if isinstance(row.context_snapshot, dict) else "baseline"
                ),
                "traffic_source": "replay_amplified",
                "variant_label": label,
                "amplified_inputs": amplified_inputs,
                "replayed_decision": replayed["decision"],
                "replayed_score": replayed["final_score"],
                "replayed_policy_layer": replayed.get("policy_layer"),
                "replayed_rule_id": replayed.get("rule_id"),
            }
        )
    return variants


async def ensure_decision_memory_schema() -> None:
    async with engine.begin() as conn:
        decision_logs_exists = await conn.run_sync(lambda sync_conn: inspect(sync_conn).has_table("decision_logs"))
    if not decision_logs_exists and settings.ENV != "prod":
        await init_db()


async def amplify_logs(*, limit: int, output_path: Path, traffic_source: str | None) -> int:
    await ensure_decision_memory_schema()
    try:
        async with async_session_factory() as db:
            query = (
                select(DecisionLog)
                .where(DecisionLog.lifecycle_stage == "claim_created")
                .order_by(DecisionLog.created_at.desc())
                .limit(limit)
            )
            rows = (await db.execute(query)).scalars().all()
    finally:
        await close_db()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            source = (row.context_snapshot or {}).get("traffic_source") if isinstance(row.context_snapshot, dict) else "baseline"
            if traffic_source and source != traffic_source:
                continue
            for variant in _bounded_variants(row):
                handle.write(json.dumps(variant, ensure_ascii=True) + "\n")
                count += 1
    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate replay-amplified decision-log variants.")
    parser.add_argument("--limit", type=int, default=25, help="Max claim-created rows to amplify.")
    parser.add_argument(
        "--traffic-source",
        type=str,
        default=None,
        choices=["baseline", "simulation_pressure", "scenario", "replay_amplified"],
        help="Optional source filter before amplification.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_export_path() / "replay_amplified.jsonl",
        help="Where to write the amplified variants.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    written = asyncio.run(
        amplify_logs(limit=args.limit, output_path=args.output, traffic_source=args.traffic_source)
    )
    print(f"Wrote {written} replay-amplified row(s) to {args.output}")
