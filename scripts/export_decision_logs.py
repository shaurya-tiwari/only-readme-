"""Export decision-memory rows for evaluation or retraining prep."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

from sqlalchemy import inspect

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.decision_memory import default_export_path, export_decision_logs
from backend.config import settings
from backend.database import async_session_factory, close_db, engine, init_db


async def ensure_decision_memory_schema() -> None:
    async with engine.begin() as conn:
        decision_logs_exists = await conn.run_sync(lambda sync_conn: inspect(sync_conn).has_table("decision_logs"))
    if not decision_logs_exists and settings.ENV != "prod":
        await init_db()


async def run_export(*, output_path: Path, resolved_only: bool, limit: int | None) -> None:
    await ensure_decision_memory_schema()
    try:
        async with async_session_factory() as db:
            rows = await export_decision_logs(db, resolved_only=resolved_only, limit=limit)
    finally:
        await close_db()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")

    print(f"Exported {len(rows)} decision log row(s) to {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export RideShield decision-memory rows.")
    parser.add_argument("--resolved-only", action="store_true", help="Export only rows with a final label.")
    parser.add_argument("--limit", type=int, default=None, help="Optional max rows to export.")
    parser.add_argument(
        "--output",
        type=Path,
        default=default_export_path() / "decision_logs.jsonl",
        help="Output JSONL path.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_export(output_path=args.output, resolved_only=args.resolved_only, limit=args.limit))
