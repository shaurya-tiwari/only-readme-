"""Analyze false-review patterns from decision-memory rows."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import inspect, select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import settings
from backend.database import async_session_factory, engine, init_db
from backend.db.models import DecisionLog


def _score_band(score: Any) -> str:
    value = float(score or 0)
    if value < 0.45:
        return "lt_0.45"
    if value < 0.55:
        return "0.45_0.55"
    if value < 0.60:
        return "0.55_0.60"
    if value < 0.65:
        return "0.60_0.65"
    return "ge_0.65"


def _payout_band(amount: Any) -> str:
    value = float(amount or 0)
    if value < 75:
        return "lt_75"
    if value < 125:
        return "75_125"
    if value < 200:
        return "125_200"
    return "ge_200"


async def _ensure_schema() -> None:
    async with engine.begin() as conn:
        decision_logs_exists = await conn.run_sync(lambda sync_conn: inspect(sync_conn).has_table("decision_logs"))
    if not decision_logs_exists and settings.ENV != "prod":
        await init_db()


def _false_review_rows(rows: list[DecisionLog]) -> tuple[dict[str, DecisionLog], dict[str, DecisionLog], list[tuple[DecisionLog, DecisionLog]]]:
    claim_created: dict[str, DecisionLog] = {}
    resolved: dict[str, DecisionLog] = {}
    for row in rows:
        claim_id = str(row.claim_id)
        if row.lifecycle_stage == "claim_created":
            claim_created[claim_id] = row
        if row.final_label:
            resolved[claim_id] = row

    false_reviews: list[tuple[DecisionLog, DecisionLog]] = []
    for claim_id, resolution in resolved.items():
        created = claim_created.get(claim_id)
        if not created:
            continue
        if created.system_decision == "delayed" and resolution.final_label == "legit":
            false_reviews.append((created, resolution))
    return claim_created, resolved, false_reviews


async def build_report(*, limit: int | None = None) -> dict[str, Any]:
    await _ensure_schema()
    async with async_session_factory() as db:
        rows = (await db.execute(select(DecisionLog).order_by(DecisionLog.created_at.asc()))).scalars().all()

    claim_created, resolved, false_reviews = _false_review_rows(rows)

    by_score = Counter()
    by_payout = Counter()
    by_flags = Counter()
    by_combo = Counter()
    examples = defaultdict(list)
    trust_values: list[float] = []
    fraud_values: list[float] = []

    for created, _ in false_reviews:
        feature_snapshot = created.feature_snapshot if isinstance(created.feature_snapshot, dict) else {}
        decision_inputs = feature_snapshot.get("decision_inputs") if isinstance(feature_snapshot.get("decision_inputs"), dict) else {}
        fraud_result = decision_inputs.get("fraud_result") if isinstance(decision_inputs.get("fraud_result"), dict) else {}
        flags = tuple(sorted(fraud_result.get("flags") or [])) or ("no_flags",)
        score_band = _score_band(created.final_score)
        payout_band = _payout_band(created.payout_amount)

        by_score[score_band] += 1
        by_payout[payout_band] += 1
        by_flags[flags] += 1
        by_combo[(score_band, payout_band, flags)] += 1

        trust_values.append(float(created.trust_score or 0))
        fraud_values.append(float(created.fraud_score or 0))

        examples[(score_band, payout_band, flags)].append(
            {
                "claim_id": str(created.claim_id),
                "score": float(created.final_score or 0),
                "payout": float(created.payout_amount or 0),
                "fraud_score": float(created.fraud_score or 0),
                "trust_score": float(created.trust_score or 0),
                "reason": (((created.output_snapshot or {}).get("decision") or {}).get("primary_reason")),
            }
        )

    total_false_reviews = len(false_reviews)
    return {
        "total_decision_logs": len(rows),
        "claim_created_rows": len(claim_created),
        "resolved_rows": len(resolved),
        "false_reviews": total_false_reviews,
        "by_score_band": dict(by_score),
        "by_payout_band": dict(by_payout),
        "by_flag_combination": [
            {"flags": list(flags), "count": count, "share": round((count / max(1, total_false_reviews)) * 100, 1)}
            for flags, count in by_flags.most_common()
        ],
        "top_pattern_combinations": [
            {
                "score_band": score_band,
                "payout_band": payout_band,
                "flags": list(flags),
                "count": count,
                "share": round((count / max(1, total_false_reviews)) * 100, 1),
                "examples": examples[(score_band, payout_band, flags)][:3],
            }
            for (score_band, payout_band, flags), count in by_combo.most_common(limit or 10)
        ],
        "ranges": {
            "avg_trust_score": round(sum(trust_values) / max(1, len(trust_values)), 3),
            "min_trust_score": round(min(trust_values), 3) if trust_values else None,
            "max_trust_score": round(max(trust_values), 3) if trust_values else None,
            "avg_fraud_score": round(sum(fraud_values) / max(1, len(fraud_values)), 3),
            "min_fraud_score": round(min(fraud_values), 3) if fraud_values else None,
            "max_fraud_score": round(max(fraud_values), 3) if fraud_values else None,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report false-review patterns from decision memory.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of top combinations to print.")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output path.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    report = await build_report(limit=args.limit)
    payload = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(f"Wrote report to {args.output}")
    else:
        print(payload)


if __name__ == "__main__":
    asyncio.run(main())
