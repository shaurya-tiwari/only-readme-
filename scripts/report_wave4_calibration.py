"""Generate a Wave 4 calibration report with simple charts."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from backend.api.analytics import (
    _build_decision_memory_summary,
    _build_false_review_pattern_summary,
    _build_policy_replay_summary,
)
from backend.database import async_session_factory
from backend.db.models import DecisionLog


def _ascii_bar(label: str, count: int, total: int, width: int = 28) -> str:
    share = count / max(1, total)
    filled = max(1 if count else 0, round(share * width))
    return f"{label:<12} {'#' * filled:<28} {count:>3} ({share * 100:>5.1f}%)"


def _render_chart(title: str, values: dict[str, int], total: int) -> str:
    lines = [title, ""]
    for label, count in sorted(values.items(), key=lambda item: (-item[1], item[0])):
        lines.append(_ascii_bar(label, count, total))
    return "\n".join(lines)


async def build_payload() -> dict:
    async with async_session_factory() as db:
        decision_logs = (
            await db.execute(select(DecisionLog).order_by(DecisionLog.created_at.desc()))
        ).scalars().all()
    return {
        "decision_memory_summary": _build_decision_memory_summary(decision_logs),
        "false_review_pattern_summary": _build_false_review_pattern_summary(decision_logs),
        "policy_replay_summary": _build_policy_replay_summary(decision_logs),
    }


def _render_markdown(payload: dict) -> str:
    decision_memory = payload["decision_memory_summary"]
    false_reviews = payload["false_review_pattern_summary"]
    replay = payload["policy_replay_summary"]
    total_false_reviews = false_reviews["false_review_count"]
    total_replayed = replay["rows_replayed"]

    lines = [
        "# Phase 3 Wave 4 Calibration Report",
        "",
        "This report uses the enlarged local working-repo decision-memory dataset after Wave 4 calibration setup.",
        "",
        "## Current Snapshot",
        "",
        f"- logged claim-created rows: `{decision_memory['claim_created_rows']}`",
        f"- resolved labels: `{decision_memory['resolved_labels']}`",
        f"- false reviews: `{false_reviews['false_review_count']}`",
        f"- replay rows: `{replay['rows_replayed']}`",
        f"- replay match rate: `{replay['match_rate']}%`",
        "",
        "## False Review Score Bands",
        "",
        "```text",
        _render_chart(
            "False reviews by score band",
            false_reviews["score_band_distribution"],
            total_false_reviews,
        ),
        "```",
        "",
        "## False Review Payout Bands",
        "",
        "```text",
        _render_chart(
            "False reviews by payout band",
            false_reviews["payout_band_distribution"],
            total_false_reviews,
        ),
        "```",
        "",
        "## Replay Transition Summary",
        "",
        "```text",
        _render_chart(
            "Stored decision -> current policy replay",
            replay["transitions"],
            total_replayed,
        ),
        "```",
        "",
        "## Dominant False Review Patterns",
        "",
    ]

    for pattern in false_reviews["dominant_patterns"]:
        flags = ", ".join(pattern["flags"]) if pattern["flags"] else "no_flags"
        lines.extend(
            [
                f"- flags: `{flags}`",
                f"  count: `{pattern['count']}` share: `{pattern['share']}%`",
            ]
        )

    lines.extend(
        [
            "",
            "## Replay Lift",
            "",
            f"- delayed -> approved: `{replay['delayed_to_approved_count']}`",
            f"- approved -> delayed: `{replay['approved_to_delayed_count']}`",
            f"- rejected -> approved: `{replay['rejected_to_approved_count']}`",
            "",
            "## Takeaway",
            "",
            "The biggest waste is still the `0.60-0.65` band. The current policy already replays some old delayed claims as approved, but the enlarged dataset also shows stronger low-payout patterns such as `cluster + device`, so future loosening must stay narrow and evidence-based.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Wave 4 calibration charts and report.")
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("logs") / "decision_memory" / "wave4_calibration_report.json",
    )
    parser.add_argument(
        "--md-output",
        type=Path,
        default=Path("docs") / "Phase3_Wave4_Calibration_Report.md",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    payload = await build_payload()
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    args.md_output.write_text(_render_markdown(payload), encoding="utf-8")
    print(f"Wrote JSON report to {args.json_output}")
    print(f"Wrote markdown report to {args.md_output}")


if __name__ == "__main__":
    asyncio.run(main())
