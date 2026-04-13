"""Local-only history growth tool for Phase 3 calibration work."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import random
import sys
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.claim_processor import claim_processor
from backend.core.decision_engine import decision_engine
from backend.core.decision_memory import record_claim_resolution
from backend.core.location_service import location_service
from backend.core.payout_executor import payout_executor
from backend.database import async_session_factory
from backend.db.models import AuditLog, Claim, Event, TrustScore
from backend.utils.time import utc_now_naive

DEFAULT_SCENARIOS = [
    "heavy_rain",
    "platform_outage",
    "compound_disaster",
    "hazardous_aqi",
    "monsoon",
    "extreme_heat",
]

PRESSURE_PROFILES = {
    "balanced_pressure": {
        "description": "Mixed legitimate and suspicious pressure with moderate payout and trust spread.",
        "scenario_weights": {
            "heavy_rain": 2,
            "platform_outage": 2,
            "compound_disaster": 2,
            "hazardous_aqi": 1,
            "monsoon": 1,
            "extreme_heat": 1,
        },
        "resolve_limit_multiplier": 1.0,
    },
    "gray_band_heavy": {
        "description": "Pushes the engine into low-mid payout ambiguous territory to stress gray-band routing.",
        "scenario_weights": {
            "platform_outage": 3,
            "compound_disaster": 3,
            "heavy_rain": 2,
            "hazardous_aqi": 1,
        },
        "resolve_limit_multiplier": 1.25,
    },
    "fraud_pressure": {
        "description": "Higher density of cluster-like and suspicious multi-signal conditions.",
        "scenario_weights": {
            "compound_disaster": 4,
            "platform_outage": 3,
            "hazardous_aqi": 2,
            "heavy_rain": 1,
        },
        "resolve_limit_multiplier": 0.75,
    },
    "clean_baseline": {
        "description": "Mostly legitimate, calmer pressure profile for sanity checks against over-caution.",
        "scenario_weights": {
            "heavy_rain": 3,
            "monsoon": 2,
            "extreme_heat": 2,
            "platform_outage": 1,
        },
        "resolve_limit_multiplier": 1.0,
    },
}


def _weighted_scenarios(scenarios: list[str], pressure_profile: str | None) -> tuple[list[str], float]:
    if not pressure_profile or pressure_profile not in PRESSURE_PROFILES:
        return scenarios or DEFAULT_SCENARIOS, 1.0
    profile = PRESSURE_PROFILES[pressure_profile]
    weights = profile.get("scenario_weights", {})
    weighted: list[str] = []
    for scenario in scenarios or DEFAULT_SCENARIOS:
        weight = int(weights.get(scenario, 0))
        if weight > 0:
            weighted.extend([scenario] * weight)
    if not weighted:
        weighted = scenarios or DEFAULT_SCENARIOS
    return weighted, float(profile.get("resolve_limit_multiplier", 1.0))


def _build_fraud_result(claim: Claim) -> dict[str, Any]:
    breakdown = claim.decision_breakdown or {}
    inputs = breakdown.get("inputs") or {}
    fraud_model = breakdown.get("fraud_model") or {}
    return {
        "adjusted_fraud_score": float(claim.fraud_score or 0),
        "raw_fraud_score": inputs.get("raw_fraud_score", float(claim.fraud_score or 0)),
        "flags": list(inputs.get("fraud_flags") or []),
        "signals": fraud_model.get("signals") or {},
        "ml_confidence": fraud_model.get("confidence"),
        "fallback_used": fraud_model.get("fallback_used", False),
        "is_suspicious": float(claim.fraud_score or 0) > 0.5,
        "is_high_risk": float(claim.fraud_score or 0) > 0.7,
    }


def _resolution_candidates(claim: Claim) -> tuple[str | None, str]:
    fraud_result = _build_fraud_result(claim)
    reevaluated = decision_engine.decide(
        disruption_score=float(claim.disruption_score or 0),
        event_confidence=float(claim.event_confidence or 0),
        fraud_result=fraud_result,
        trust_score=float(claim.trust_score or 0),
        payout_amount=float(claim.final_payout or claim.calculated_payout or 0),
    )
    flags = set(fraud_result["flags"])
    payout = float(claim.final_payout or claim.calculated_payout or 0)
    final_score = float(claim.final_score or 0)
    fraud_score = float(claim.fraud_score or 0)
    trust_score = float(claim.trust_score or 0)

    if reevaluated["decision"] == "approved":
        return "approve", "current_policy_safe"

    strong_flags = flags & decision_engine.STRONG_REVIEW_FLAGS
    if (
        reevaluated["decision"] == "rejected"
        and strong_flags
        and fraud_score >= 0.52
        and trust_score <= 0.25
    ):
        return "reject", "strong_flag_high_fraud"

    if (
        final_score < 0.42
        and fraud_score >= 0.48
        and payout >= 100
        and (strong_flags or trust_score <= 0.18)
    ):
        return "reject", "low_score_high_risk"

    return None, "hold_for_manual_review"


async def _resolve_delayed_claims(
    *,
    created_after,
    per_round_limit: int,
    reviewed_by: str,
) -> dict[str, Any]:
    async with async_session_factory() as db:
        claims = (
            await db.execute(
                select(Claim)
                .options(selectinload(Claim.worker), selectinload(Claim.policy), selectinload(Claim.event), selectinload(Claim.payout))
                .where(Claim.status == "delayed", Claim.created_at >= created_after)
                .order_by(Claim.created_at.asc())
            )
        ).scalars().all()

        approved = 0
        rejected = 0
        skipped = 0
        reasons = Counter()

        for claim in claims:
            if approved + rejected >= per_round_limit:
                break
            resolution, reason_code = _resolution_candidates(claim)
            reasons[reason_code] += 1
            if resolution is None:
                skipped += 1
                continue

            now = utc_now_naive()
            previous_status = claim.status
            payout_result = None
            claim.reviewed_by = reviewed_by
            claim.reviewed_at = now
            claim.updated_at = now

            if resolution == "approve":
                claim.status = "approved"
                payout_amount = claim.final_payout or claim.calculated_payout or 0
                payout_result = await payout_executor.execute(
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
                approved += 1
            else:
                claim.status = "rejected"
                claim.rejection_reason = "Local synthetic review marked this claim unsafe for auto payout."
                claim.final_payout = Decimal("0")
                rejected += 1

            db.add(
                AuditLog(
                    entity_type="claim",
                    entity_id=claim.id,
                    action=f"synthetic_resolved_{resolution}",
                    details={
                        "reviewed_by": reviewed_by,
                        "decision": resolution,
                        "reason_code": reason_code,
                        "previous_status": previous_status,
                    },
                )
            )
            await record_claim_resolution(
                db=db,
                claim=claim,
                event=claim.event,
                decision_source="admin",
                reviewed_by=reviewed_by,
                review_reason=f"Synthetic Phase 3 history growth resolution: {reason_code}.",
                label_source="admin_review",
                payout_result=payout_result,
                resolution_payload={
                    "previous_status": previous_status,
                    "resolved_by": reviewed_by,
                    "decision": resolution,
                    "reason_code": reason_code,
                },
            )

        await db.commit()
        return {
            "approved": approved,
            "rejected": rejected,
            "skipped": skipped,
            "reason_counts": dict(reasons),
        }


async def _close_active_events(*, cities: list[str]) -> int:
    async with async_session_factory() as db:
        events = (
            await db.execute(
                select(Event).where(Event.status == "active", Event.city.in_(cities))
            )
        ).scalars().all()
        now = utc_now_naive()
        for event in events:
            event.status = "ended"
            event.ended_at = now
            event.updated_at = now
        await db.commit()
        return len(events)


async def _active_zone_map(cities: list[str]) -> dict[str, list[str]]:
    async with async_session_factory() as db:
        zone_map: dict[str, list[str]] = {}
        for city in cities:
            zones = await location_service.get_active_zones(db, city_slug=city)
            zone_map[city] = [zone.slug for zone in zones]
        return zone_map


async def grow_history(
    *,
    rounds: int,
    cities: list[str],
    scenarios: list[str],
    resolve_limit: int,
    close_events_each_round: bool,
    traffic_source: str,
    pressure_profile: str | None,
) -> dict[str, Any]:
    zone_map = await _active_zone_map(cities)
    weighted_scenarios, resolve_limit_multiplier = _weighted_scenarios(scenarios, pressure_profile)
    rng = random.Random(42)
    started_at = utc_now_naive()
    summary = {
        "started_at": started_at.isoformat(),
        "rounds": rounds,
        "cities": cities,
        "traffic_source": traffic_source,
        "pressure_profile": pressure_profile,
        "round_summaries": [],
        "totals": defaultdict(float),
    }

    for round_index in range(rounds):
        round_payload: dict[str, Any] = {
            "round": round_index + 1,
            "city_runs": [],
            "resolutions": None,
            "closed_events": 0,
        }
        for city_index, city in enumerate(cities):
            scenario = rng.choice(weighted_scenarios)
            zones = zone_map.get(city) or []
            async with async_session_factory() as db:
                cycle = await claim_processor.run_trigger_cycle(
                    db=db,
                    city=city,
                    zones=zones,
                    scenario=scenario,
                    demo_run_id=f"phase3-growth-r{round_index + 1}-{city}",
                    traffic_source=traffic_source,
                    pressure_profile=pressure_profile,
                )
                await db.commit()
            round_payload["city_runs"].append(
                {
                    "city": city,
                    "scenario": scenario,
                    "traffic_source": traffic_source,
                    "pressure_profile": pressure_profile,
                    "events_created": cycle["events_created"],
                    "events_extended": cycle["events_extended"],
                    "claims_generated": cycle["claims_generated"],
                    "claims_approved": cycle["claims_approved"],
                    "claims_delayed": cycle["claims_delayed"],
                    "claims_rejected": cycle["claims_rejected"],
                    "claims_duplicate": cycle["claims_duplicate"],
                    "total_payout": round(cycle["total_payout"], 2),
                }
            )
            summary["totals"]["events_created"] += cycle["events_created"]
            summary["totals"]["events_extended"] += cycle["events_extended"]
            summary["totals"]["claims_generated"] += cycle["claims_generated"]
            summary["totals"]["claims_approved"] += cycle["claims_approved"]
            summary["totals"]["claims_delayed"] += cycle["claims_delayed"]
            summary["totals"]["claims_rejected"] += cycle["claims_rejected"]
            summary["totals"]["claims_duplicate"] += cycle["claims_duplicate"]
            summary["totals"]["total_payout"] += cycle["total_payout"]

        if resolve_limit > 0:
            effective_resolve_limit = max(0, round(resolve_limit * resolve_limit_multiplier))
            resolution_summary = await _resolve_delayed_claims(
                created_after=started_at,
                per_round_limit=effective_resolve_limit,
                reviewed_by="phase3_growth_runner",
            )
            round_payload["resolutions"] = resolution_summary
            summary["totals"]["resolved_approved"] += resolution_summary["approved"]
            summary["totals"]["resolved_rejected"] += resolution_summary["rejected"]

        if close_events_each_round:
            closed_events = await _close_active_events(cities=cities)
            round_payload["closed_events"] = closed_events
            summary["totals"]["closed_events"] += closed_events

        summary["round_summaries"].append(round_payload)

    summary["totals"] = {
        key: round(value, 2) if isinstance(value, float) else value
        for key, value in summary["totals"].items()
    }
    summary["completed_at"] = utc_now_naive().isoformat()
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate local-only Phase 3 decision history.")
    parser.add_argument("--rounds", type=int, default=4, help="How many multi-city rounds to run.")
    parser.add_argument(
        "--cities",
        type=str,
        default="all",
        help="Comma-separated city slugs or 'all'.",
    )
    parser.add_argument(
        "--scenarios",
        type=str,
        default=",".join(DEFAULT_SCENARIOS),
        help="Comma-separated scenario rotation.",
    )
    parser.add_argument(
        "--resolve-limit",
        type=int,
        default=12,
        help="How many delayed claims to synthetically resolve per round.",
    )
    parser.add_argument(
        "--keep-events-open",
        action="store_true",
        help="Do not end active events after each round.",
    )
    parser.add_argument(
        "--traffic-source",
        type=str,
        default="simulation_pressure",
        choices=["baseline", "simulation_pressure", "scenario", "replay_amplified"],
        help="Traffic-source label to persist with generated history.",
    )
    parser.add_argument(
        "--pressure-profile",
        type=str,
        default="balanced_pressure",
        choices=sorted(PRESSURE_PROFILES.keys()),
        help="Controlled pressure profile for scenario weighting and resolution pressure.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    async with async_session_factory() as db:
        all_cities = sorted(city.slug for city in await location_service.get_active_cities(db))
    cities = all_cities if args.cities == "all" else [city.strip().lower() for city in args.cities.split(",") if city.strip()]
    scenarios = [scenario.strip() for scenario in args.scenarios.split(",") if scenario.strip()]
    summary = await grow_history(
        rounds=args.rounds,
        cities=cities,
        scenarios=scenarios or DEFAULT_SCENARIOS,
        resolve_limit=max(0, args.resolve_limit),
        close_events_each_round=not args.keep_events_open,
        traffic_source=args.traffic_source,
        pressure_profile=args.pressure_profile,
    )
    print(f"Growth window started: {summary['started_at']}")
    print(f"Growth window completed: {summary['completed_at']}")
    if summary.get("pressure_profile"):
        profile = PRESSURE_PROFILES.get(summary["pressure_profile"], {})
        print(f"Pressure profile: {summary['pressure_profile']} - {profile.get('description', '').strip()}")
    print("Totals:")
    for key, value in summary["totals"].items():
        print(f"- {key}: {value}")
    for round_summary in summary["round_summaries"]:
        print(f"Round {round_summary['round']}:")
        for city_run in round_summary["city_runs"]:
            print(
                "  "
                f"{city_run['city']} {city_run['scenario']} "
                f"claims={city_run['claims_generated']} "
                f"approved={city_run['claims_approved']} "
                f"delayed={city_run['claims_delayed']} "
                f"rejected={city_run['claims_rejected']} "
                f"duplicate={city_run['claims_duplicate']}"
            )
        if round_summary["resolutions"]:
            print(f"  resolutions={round_summary['resolutions']}")
        print(f"  closed_events={round_summary['closed_events']}")


if __name__ == "__main__":
    asyncio.run(main())
