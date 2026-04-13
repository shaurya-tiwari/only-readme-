"""Replay historical decision-memory rows and write versioned reannotations."""

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
from backend.core.decision_memory import default_export_path, replay_decision_log
from backend.database import async_session_factory, close_db, engine, init_db
from backend.db.models import DecisionLog


async def ensure_decision_memory_schema() -> None:
    async with engine.begin() as conn:
        decision_logs_exists = await conn.run_sync(lambda sync_conn: inspect(sync_conn).has_table("decision_logs"))
    if not decision_logs_exists and settings.ENV != "prod":
        await init_db()


def _policy_version_delta(row: DecisionLog, replayed: dict[str, Any]) -> dict[str, Any]:
    original_output = row.output_snapshot if isinstance(row.output_snapshot, dict) else {}
    original_decision = original_output.get("decision") if isinstance(original_output.get("decision"), dict) else {}
    return {
        "decision_changed": replayed["decision"] != row.system_decision,
        "policy_version_changed": row.decision_policy_version != replayed["decision_policy_version"],
        "layer_changed": str(original_decision.get("policy_layer") or "unknown") != replayed["policy_layer"],
        "rule_changed": str(original_decision.get("rule_id") or "unknown") != replayed["rule_id"],
    }


def _serialize_reannotation(row: DecisionLog, replayed: dict[str, Any]) -> dict[str, Any]:
    original_output = row.output_snapshot if isinstance(row.output_snapshot, dict) else {}
    original_decision = original_output.get("decision") if isinstance(original_output.get("decision"), dict) else {}
    context_snapshot = row.context_snapshot if isinstance(row.context_snapshot, dict) else {}
    return {
        "claim_id": str(row.claim_id),
        "decision_log_id": str(row.id),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "traffic_source": str(context_snapshot.get("traffic_source") or "baseline"),
        "pressure_profile": context_snapshot.get("pressure_profile"),
        "original": {
            "system_decision": row.system_decision,
            "resulting_status": row.resulting_status,
            "policy_version": row.decision_policy_version,
            "policy_layer": str(original_decision.get("policy_layer") or "unknown"),
            "rule_id": str(original_decision.get("rule_id") or "unknown"),
            "final_score": float(row.final_score or 0),
            "decision_confidence": float(row.decision_confidence or 0),
        },
        "replayed": {
            "decision": replayed["decision"],
            "policy_version": replayed["decision_policy_version"],
            "policy_layer": replayed["policy_layer"],
            "rule_id": replayed["rule_id"],
            "final_score": float(replayed["final_score"]),
            "decision_confidence": float(replayed["decision_confidence"]),
            "decision_confidence_band": replayed["decision_confidence_band"],
            "primary_reason": replayed["primary_reason"],
            "uncertainty_case": replayed["uncertainty"]["case"],
        },
        "policy_version_delta": _policy_version_delta(row, replayed),
    }


async def reannotate_history(*, limit: int, output_path: Path, traffic_source: str | None) -> int:
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
    written = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            current_source = (
                (row.context_snapshot or {}).get("traffic_source")
                if isinstance(row.context_snapshot, dict)
                else "baseline"
            )
            if traffic_source and current_source != traffic_source:
                continue
            replayed = replay_decision_log(row)
            handle.write(json.dumps(_serialize_reannotation(row, replayed), ensure_ascii=True) + "\n")
            written += 1
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay historical decision rows and write versioned reannotations.")
    parser.add_argument("--limit", type=int, default=500, help="Maximum number of claim-created rows to reannotate.")
    parser.add_argument(
        "--traffic-source",
        type=str,
        default=None,
        choices=["baseline", "simulation_pressure", "scenario", "replay_amplified"],
        help="Optional source filter before reannotation.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_export_path() / "reannotated_history.jsonl",
        help="Where to write the reannotation rows.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    written = asyncio.run(
        reannotate_history(limit=args.limit, output_path=args.output, traffic_source=args.traffic_source)
    )
    print(f"Wrote {written} reannotated decision row(s) to {args.output}")
