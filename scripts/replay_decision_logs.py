"""Replay stored decision-memory rows through the current decision engine."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import inspect, select

from backend.core.decision_memory import replay_decision_log
from backend.config import settings
from backend.database import async_session_factory, close_db, engine, init_db
from backend.db.models import DecisionLog


async def ensure_decision_memory_schema() -> None:
    async with engine.begin() as conn:
        decision_logs_exists = await conn.run_sync(lambda sync_conn: inspect(sync_conn).has_table("decision_logs"))
    if not decision_logs_exists and settings.ENV != "prod":
        await init_db()


async def run_replay(*, claim_id: UUID | None, limit: int | None) -> None:
    await ensure_decision_memory_schema()
    try:
        async with async_session_factory() as db:
            query = (
                select(DecisionLog)
                .where(DecisionLog.lifecycle_stage == "claim_created")
                .order_by(DecisionLog.created_at.desc())
            )
            if claim_id:
                query = query.where(DecisionLog.claim_id == claim_id)
            if limit:
                query = query.limit(limit)
            rows = (await db.execute(query)).scalars().all()
    finally:
        await close_db()

    print(f"Loaded {len(rows)} decision log row(s) for replay.")
    for row in rows:
        replayed = replay_decision_log(row)
        status = "match" if replayed["decision"] == row.system_decision else "mismatch"
        print(
            f"{row.claim_id} stage={row.lifecycle_stage} stored={row.system_decision} "
            f"replayed={replayed['decision']} score={replayed['final_score']:.3f} status={status}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay stored RideShield decision-memory rows.")
    parser.add_argument("--claim-id", type=UUID, default=None, help="Replay a single claim id.")
    parser.add_argument("--limit", type=int, default=25, help="Optional max rows to replay.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_replay(claim_id=args.claim_id, limit=args.limit))
