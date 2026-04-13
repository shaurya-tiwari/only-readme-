"""Run governed large-scale policy experiments from decision-memory anchors."""

from __future__ import annotations

import argparse
import asyncio
import json
import random
from collections import Counter
from collections import defaultdict
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import inspect, select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import settings
from backend.core.decision_engine import decision_engine
from backend.core.decision_memory import default_export_path, replay_decision_log
from backend.database import async_session_factory, close_db, engine, init_db
from backend.db.models import DecisionLog
from scripts.micro_world import generate_micro_world_inputs


SCENARIO_PROFILES: dict[str, dict[str, Any]] = {
    "gray_band_overload": {
        "payout_delta": (5.0, 28.0),
        "trust_delta": (-0.08, 0.02),
        "confidence_delta": (-0.06, 0.01),
        "force_flags": ["movement", "pre_activity"],
    },
    "cluster_heavy": {
        "payout_delta": (0.0, 18.0),
        "trust_delta": (-0.12, -0.02),
        "confidence_delta": (-0.04, 0.03),
        "force_flags": ["cluster", "device"],
    },
    "fraud_pressure": {
        "payout_delta": (15.0, 45.0),
        "trust_delta": (-0.15, -0.05),
        "confidence_delta": (-0.08, -0.01),
        "force_flags": ["timing", "income_inflation"],
    },
}

DIFFICULTY_PROFILES: dict[str, dict[str, float]] = {
    "balanced": {"clean_legit": 0.3, "noisy_legit": 0.3, "borderline": 0.25, "adversarial": 0.15},
    "safer": {"clean_legit": 0.42, "noisy_legit": 0.28, "borderline": 0.2, "adversarial": 0.1},
    "harder": {"clean_legit": 0.18, "noisy_legit": 0.27, "borderline": 0.35, "adversarial": 0.2},
}

EXPERIMENT_DISTRIBUTIONS: dict[str, dict[str, dict[str, float]]] = {
    "balanced_realism": {
        "payout_bands": {"lt_75": 0.35, "75_125": 0.35, "125_200": 0.2, "ge_200": 0.1},
        "trust_bands": {"lt_0.30": 0.15, "0.30_0.45": 0.25, "0.45_0.75": 0.4, "ge_0.75": 0.2},
        "cluster_types": {"not_clustered": 0.6, "coincidence_cluster": 0.1, "mixed_cluster": 0.2, "fraud_ring": 0.1},
        "uncertainty_cases": {"none": 0.7, "noise_overload": 0.15, "silent_conflict": 0.08, "core_contradiction": 0.04, "too_perfect_state": 0.03},
    },
    "gray_band_focus": {
        "payout_bands": {"lt_75": 0.45, "75_125": 0.35, "125_200": 0.15, "ge_200": 0.05},
        "trust_bands": {"lt_0.30": 0.1, "0.30_0.45": 0.35, "0.45_0.75": 0.4, "ge_0.75": 0.15},
        "cluster_types": {"not_clustered": 0.7, "coincidence_cluster": 0.08, "mixed_cluster": 0.17, "fraud_ring": 0.05},
        "uncertainty_cases": {"none": 0.55, "noise_overload": 0.25, "silent_conflict": 0.1, "core_contradiction": 0.05, "too_perfect_state": 0.05},
    },
    "fraud_focus": {
        "payout_bands": {"lt_75": 0.2, "75_125": 0.3, "125_200": 0.3, "ge_200": 0.2},
        "trust_bands": {"lt_0.30": 0.35, "0.30_0.45": 0.3, "0.45_0.75": 0.25, "ge_0.75": 0.1},
        "cluster_types": {"not_clustered": 0.35, "coincidence_cluster": 0.05, "mixed_cluster": 0.3, "fraud_ring": 0.3},
        "uncertainty_cases": {"none": 0.45, "noise_overload": 0.1, "silent_conflict": 0.15, "core_contradiction": 0.15, "too_perfect_state": 0.15},
    },
}

MIN_BASELINE_ROWS = 100
MAX_SYNTHETIC_SHARE = 70.0
MAX_FALSE_AUTO_DELTA = 2.0
TARGET_MAX_GAP = 0.1
IDEAL_MAX_GAP = 0.05
MAX_SOURCE_DIVERGENCE = 0.2


async def ensure_decision_memory_schema() -> None:
    async with engine.begin() as conn:
        decision_logs_exists = await conn.run_sync(lambda sync_conn: inspect(sync_conn).has_table("decision_logs"))
    if not decision_logs_exists and settings.ENV != "prod":
        await init_db()


def _resolved_label_map(rows: list[DecisionLog]) -> dict[str, str]:
    return {
        str(row.claim_id): str(row.final_label)
        for row in rows
        if row.final_label and str(row.claim_id)
    }


def _source_of(row: DecisionLog) -> str:
    context_snapshot = row.context_snapshot if isinstance(row.context_snapshot, dict) else {}
    return str(context_snapshot.get("traffic_source") or "baseline")


def _inputs_from(row: DecisionLog) -> dict[str, Any]:
    feature_snapshot = row.feature_snapshot if isinstance(row.feature_snapshot, dict) else {}
    return feature_snapshot.get("decision_inputs") if isinstance(feature_snapshot.get("decision_inputs"), dict) else {}


def _bounded_replay_variant(row: DecisionLog, rng: random.Random) -> dict[str, Any]:
    decision_inputs = _inputs_from(row)
    fraud_result = decision_inputs.get("fraud_result") if isinstance(decision_inputs.get("fraud_result"), dict) else {}
    return {
        "disruption_score": round(max(0.0, min(1.0, float(decision_inputs.get("disruption_score") or 0))), 3),
        "event_confidence": round(
            max(0.0, min(1.0, float(decision_inputs.get("event_confidence") or 0) + rng.uniform(-0.04, 0.03))), 3
        ),
        "trust_score": round(
            max(0.0, min(1.0, float(decision_inputs.get("trust_score") or 0) + rng.uniform(-0.05, 0.04))), 3
        ),
        "payout_amount": round(max(0.0, float(decision_inputs.get("payout_amount") or 0) + rng.uniform(-15.0, 18.0)), 2),
        "fraud_result": {
            "adjusted_fraud_score": float(fraud_result.get("adjusted_fraud_score") or 0),
            "raw_fraud_score": float(fraud_result.get("raw_fraud_score") or 0),
            "flags": list(fraud_result.get("flags") or []),
            "ml_confidence": fraud_result.get("ml_confidence"),
            "fallback_used": fraud_result.get("fallback_used", False),
            "model_version": fraud_result.get("model_version"),
            "fraud_probability": fraud_result.get("fraud_probability"),
            "top_factors": fraud_result.get("top_factors") or [],
        },
        "feedback_result": decision_inputs.get("feedback_result") or {},
    }


def _scenario_variant(row: DecisionLog, rng: random.Random, scenario_name: str) -> dict[str, Any]:
    base = _bounded_replay_variant(row, rng)
    profile = SCENARIO_PROFILES[scenario_name]
    fraud_result = dict(base["fraud_result"])
    forced_flags = list(dict.fromkeys(list(fraud_result.get("flags") or []) + list(profile["force_flags"])))
    fraud_result["flags"] = forced_flags
    return {
        **base,
        "event_confidence": round(
            max(0.0, min(1.0, base["event_confidence"] + rng.uniform(*profile["confidence_delta"]))), 3
        ),
        "trust_score": round(max(0.0, min(1.0, base["trust_score"] + rng.uniform(*profile["trust_delta"]))), 3),
        "payout_amount": round(max(0.0, base["payout_amount"] + rng.uniform(*profile["payout_delta"])), 2),
        "fraud_result": fraud_result,
    }


def _simulate_row(
    *,
    row: DecisionLog,
    label: str | None,
    generation_tier: str,
    traffic_source: str,
    inputs: dict[str, Any],
    scenario_name: str | None = None,
) -> dict[str, Any]:
    replayed = replay_decision_log(row) if generation_tier == "anchor" else None
    decision = replayed or decision_engine.decide(
        disruption_score=float(inputs["disruption_score"]),
        event_confidence=float(inputs["event_confidence"]),
        fraud_result=inputs["fraud_result"],
        trust_score=float(inputs["trust_score"]),
        feedback_result=inputs.get("feedback_result") or {},
        payout_amount=float(inputs["payout_amount"]),
    )
    return {
        "origin_claim_id": str(row.claim_id),
        "origin_traffic_source": _source_of(row),
        "traffic_source": traffic_source,
        "generation_tier": generation_tier,
        "scenario_name": scenario_name,
        "decision": decision["decision"],
        "rule_id": decision["rule_id"],
        "policy_layer": decision["policy_layer"],
        "surface": decision["breakdown"]["rule_metadata"]["surface"],
        "risk_expectation": decision["breakdown"]["rule_metadata"]["risk_expectation"],
        "payout_amount": float(inputs["payout_amount"]),
        "trust_score": float(inputs["trust_score"]),
        "cluster_type": decision["breakdown"]["cluster_type"],
        "uncertainty_case": decision["uncertainty"]["case"],
        "final_score": float(decision["final_score"]),
        "decision_confidence": float(decision["decision_confidence"]),
        "decision_confidence_band": decision["decision_confidence_band"],
        "label": label,
    }


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    delayed = [row for row in rows if row["decision"] == "delayed"]
    approved = [row for row in rows if row["decision"] == "approved"]
    friction = sum(1 for row in delayed if row.get("label") == "legit")
    false_auto = sum(1 for row in approved if row.get("label") == "fraud")

    rule_counts = Counter(row["rule_id"] for row in rows)
    surface_counts = Counter(row["surface"] for row in rows)
    source_counts = Counter(row["traffic_source"] for row in rows)

    def top_counts(counter: Counter, key_name: str) -> list[dict[str, Any]]:
        return [
            {key_name: key, "count": count, "share": round((count / max(1, total)) * 100, 1)}
            for key, count in counter.most_common(5)
        ]

    by_source: dict[str, dict[str, Any]] = {}
    for source, count in source_counts.items():
        source_rows = [row for row in rows if row["traffic_source"] == source]
        source_delayed = [row for row in source_rows if row["decision"] == "delayed"]
        source_approved = [row for row in source_rows if row["decision"] == "approved"]
        source_friction = sum(1 for row in source_delayed if row.get("label") == "legit")
        source_false_auto = sum(1 for row in source_approved if row.get("label") == "fraud")
        by_source[source] = {
            "count": count,
            "share": round((count / max(1, total)) * 100, 1),
            "friction_score": round((source_friction / max(1, len(source_delayed))) * 100, 1),
            "automation_efficiency": round((len(source_approved) / max(1, count)) * 100, 1),
            "false_auto_approval_risk": round((source_false_auto / max(1, len(source_approved))) * 100, 1),
        }

    return {
        "rows": total,
        "friction_score": round((friction / max(1, len(delayed))) * 100, 1),
        "automation_efficiency": round((len(approved) / max(1, total)) * 100, 1),
        "false_auto_approval_risk": round((false_auto / max(1, len(approved))) * 100, 1),
        "rule_concentration": top_counts(rule_counts, "rule_id"),
        "surface_imbalance": top_counts(surface_counts, "surface"),
        "by_traffic_source": by_source,
    }


def _payout_band(value: float) -> str:
    if value < 75:
        return "lt_75"
    if value < 125:
        return "75_125"
    if value < 200:
        return "125_200"
    return "ge_200"


def _trust_band(value: float) -> str:
    if value < 0.30:
        return "lt_0.30"
    if value < 0.45:
        return "0.30_0.45"
    if value < 0.75:
        return "0.45_0.75"
    return "ge_0.75"


def _distribution_summary(rows: list[dict[str, Any]], profile_name: str) -> dict[str, Any]:
    targets = EXPERIMENT_DISTRIBUTIONS[profile_name]
    total = len(rows)

    def normalized(counter: Counter) -> dict[str, float]:
        keys = set(counter.keys())
        return {key: round(counter.get(key, 0) / max(1, total), 3) for key in sorted(keys)}

    payout_actual = Counter(_payout_band(float(row["payout_amount"])) for row in rows)
    trust_actual = Counter(_trust_band(float(row["trust_score"])) for row in rows)
    cluster_actual = Counter(str(row["cluster_type"] or "not_clustered") for row in rows)
    uncertainty_actual = Counter(str(row["uncertainty_case"] or "none") for row in rows)

    actuals = {
        "payout_bands": normalized(payout_actual),
        "trust_bands": normalized(trust_actual),
        "cluster_types": normalized(cluster_actual),
        "uncertainty_cases": normalized(uncertainty_actual),
    }

    gaps: dict[str, dict[str, float]] = {}
    max_gap = 0.0
    for family, target_map in targets.items():
        family_actual = actuals.get(family, {})
        family_keys = sorted(set(target_map.keys()) | set(family_actual.keys()))
        gaps[family] = {}
        for key in family_keys:
            gap = round(abs(family_actual.get(key, 0.0) - target_map.get(key, 0.0)), 3)
            gaps[family][key] = gap
            max_gap = max(max_gap, gap)

    return {
        "profile": profile_name,
        "targets": targets,
        "actuals": actuals,
        "gaps": gaps,
        "max_gap": round(max_gap, 3),
        "within_tolerance": max_gap <= TARGET_MAX_GAP,
        "ideal_tolerance": IDEAL_MAX_GAP,
        "target_tolerance": TARGET_MAX_GAP,
    }


def _baseline_comparison(metrics: dict[str, Any]) -> dict[str, Any]:
    by_source = metrics.get("by_traffic_source", {})
    baseline = by_source.get("baseline", {})
    non_baseline_rows = [
        value for key, value in by_source.items()
        if key != "baseline"
    ]
    total_non_baseline = sum(int(row.get("count", 0)) for row in non_baseline_rows)
    if not baseline or total_non_baseline == 0:
        return {
            "baseline_present": bool(baseline),
            "non_baseline_present": total_non_baseline > 0,
            "deltas": {},
        }

    def weighted(metric_name: str) -> float:
        weighted_sum = sum(float(row.get(metric_name, 0.0)) * int(row.get("count", 0)) for row in non_baseline_rows)
        return round(weighted_sum / max(1, total_non_baseline), 1)

    non_baseline = {
        "friction_score": weighted("friction_score"),
        "automation_efficiency": weighted("automation_efficiency"),
        "false_auto_approval_risk": weighted("false_auto_approval_risk"),
    }
    deltas = {
        metric: round(non_baseline[metric] - float(baseline.get(metric, 0.0)), 1)
        for metric in non_baseline
    }
    return {
        "baseline_present": True,
        "non_baseline_present": True,
        "baseline": baseline,
        "non_baseline": non_baseline,
        "deltas": deltas,
    }


def _governance_gates(metrics: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    by_source = metrics.get("by_traffic_source", {})
    baseline = by_source.get("baseline", {})
    baseline_rows = int(baseline.get("count", 0))
    simulated_share = round(
        sum(float(row.get("share", 0.0)) for key, row in by_source.items() if key != "baseline"),
        1,
    )
    false_auto_delta = float(comparison.get("deltas", {}).get("false_auto_approval_risk", 0.0))
    return {
        "baseline_rows_gate": {
            "required": MIN_BASELINE_ROWS,
            "actual": baseline_rows,
            "passed": baseline_rows >= MIN_BASELINE_ROWS,
        },
        "synthetic_share_gate": {
            "max_allowed": MAX_SYNTHETIC_SHARE,
            "actual": simulated_share,
            "passed": simulated_share <= MAX_SYNTHETIC_SHARE,
        },
        "false_auto_delta_gate": {
            "max_allowed": MAX_FALSE_AUTO_DELTA,
            "actual": false_auto_delta,
            "passed": false_auto_delta <= MAX_FALSE_AUTO_DELTA,
        },
        "eligible_for_policy_change": (
            baseline_rows >= MIN_BASELINE_ROWS
            and simulated_share <= MAX_SYNTHETIC_SHARE
            and false_auto_delta <= MAX_FALSE_AUTO_DELTA
        ),
    }


def _row_bucket_map(row: dict[str, Any]) -> dict[str, str]:
    return {
        "payout_bands": _payout_band(float(row["payout_amount"])),
        "trust_bands": _trust_band(float(row["trust_score"])),
        "cluster_types": str(row["cluster_type"] or "not_clustered"),
        "uncertainty_cases": str(row["uncertainty_case"] or "none"),
    }


def _target_counts(rows: int, distribution_profile: str) -> dict[str, dict[str, float]]:
    targets = EXPERIMENT_DISTRIBUTIONS[distribution_profile]
    return {
        family: {bucket: rows * share for bucket, share in values.items()}
        for family, values in targets.items()
    }


def _candidate_score(
    candidate: dict[str, Any],
    current_counts: dict[str, Counter],
    targets: dict[str, dict[str, float]],
) -> float:
    buckets = _row_bucket_map(candidate)
    score = 0.0
    for family, bucket in buckets.items():
        current = float(current_counts[family][bucket])
        target = float(targets.get(family, {}).get(bucket, 0.0))
        before_gap = abs(target - current)
        after_gap = abs(target - (current + 1.0))
        improvement = before_gap - after_gap
        score += improvement
        if target <= 0.0 and current > 0.0:
            score -= 1.0
    return round(score, 4)


def _record_candidate(candidate: dict[str, Any], current_counts: dict[str, Counter]) -> None:
    for family, bucket in _row_bucket_map(candidate).items():
        current_counts[family][bucket] += 1


def _pick_weighted_bucket(weights: dict[str, float], rng: random.Random) -> str:
    labels = list(weights.keys())
    return rng.choices(labels, weights=[weights[label] for label in labels], k=1)[0]


def _difficulty_targets(rows: int, profile_name: str) -> dict[str, float]:
    weights = DIFFICULTY_PROFILES[profile_name]
    return {bucket: rows * share for bucket, share in weights.items()}


def _difficulty_band(candidate: dict[str, Any]) -> str:
    final_score = float(candidate["final_score"])
    confidence = float(candidate["decision_confidence"])
    trust_score = float(candidate["trust_score"])
    cluster_type = str(candidate["cluster_type"] or "not_clustered")
    uncertainty_case = str(candidate["uncertainty_case"] or "none")

    if (
        cluster_type == "fraud_ring"
        or uncertainty_case in {"core_contradiction", "silent_conflict"}
        or confidence < 0.55
        or trust_score < 0.28
    ):
        return "adversarial"
    if uncertainty_case == "noise_overload":
        return "noisy_legit"
    if 0.58 <= final_score <= 0.7 or uncertainty_case == "too_perfect_state" or cluster_type == "mixed_cluster":
        return "borderline"
    if trust_score >= 0.65 and confidence >= 0.72 and cluster_type == "not_clustered":
        return "clean_legit"
    return "noisy_legit"


def _difficulty_score(
    candidate: dict[str, Any],
    current_counts: Counter,
    targets: dict[str, float],
) -> float:
    bucket = _difficulty_band(candidate)
    current = float(current_counts[bucket])
    target = float(targets.get(bucket, 0.0))
    before_gap = abs(target - current)
    after_gap = abs(target - (current + 1.0))
    return round(before_gap - after_gap, 4)


def _source_consistency(metrics: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    by_source = metrics.get("by_traffic_source", {})
    baseline = by_source.get("baseline")
    if not baseline:
        return {
            "baseline_present": False,
            "consistent": False,
            "details": {},
        }

    details = {}
    consistent = True
    for source, row in by_source.items():
        if source == "baseline":
            continue
        friction_delta = round(float(row.get("friction_score", 0.0)) - float(baseline.get("friction_score", 0.0)), 1)
        false_auto_delta = round(
            float(row.get("false_auto_approval_risk", 0.0)) - float(baseline.get("false_auto_approval_risk", 0.0)),
            1,
        )
        source_ok = false_auto_delta <= MAX_FALSE_AUTO_DELTA
        details[source] = {
            "friction_delta_vs_baseline": friction_delta,
            "false_auto_delta_vs_baseline": false_auto_delta,
            "passed": source_ok,
        }
        consistent = consistent and source_ok
    return {
        "baseline_present": True,
        "consistent": consistent,
        "details": details,
    }


def _promotion_contract(
    *,
    distribution_governance: dict[str, Any],
    comparison: dict[str, Any],
    gates: dict[str, Any],
    metrics: dict[str, Any],
    source_alignment: dict[str, Any],
) -> dict[str, Any]:
    deltas = comparison.get("deltas", {})
    baseline_improves = (
        comparison.get("baseline_present")
        and comparison.get("non_baseline_present")
        and float(deltas.get("friction_score", 0.0)) <= 0.0
        and float(deltas.get("false_auto_approval_risk", 0.0)) <= MAX_FALSE_AUTO_DELTA
    )
    source_consistency = _source_consistency(metrics, comparison)
    checks = {
        "distribution_valid": bool(distribution_governance.get("within_tolerance")),
        "baseline_improves": bool(baseline_improves),
        "fraud_risk_within_limit": bool(gates.get("false_auto_delta_gate", {}).get("passed")),
        "sufficient_sample_size": bool(gates.get("baseline_rows_gate", {}).get("passed")),
        "multi_source_consistency": bool(source_consistency.get("consistent")),
        "source_alignment_valid": bool(source_alignment.get("within_tolerance")),
    }
    return {
        "checks": checks,
        "allow_policy_change": all(checks.values()),
        "source_consistency": source_consistency,
    }


def _build_candidate(
    *,
    rng: random.Random,
    anchors: list[DecisionLog],
    resolved_labels: dict[str, str],
    generation_tier: str,
    scenario_names: list[str],
    desired_buckets: dict[str, str] | None = None,
    desired_difficulty: str | None = None,
) -> dict[str, Any]:
    row = rng.choice(anchors)
    anchor_label = resolved_labels.get(str(row.claim_id))
    if generation_tier == "anchor":
        return _simulate_row(
            row=row,
            label=anchor_label,
            generation_tier="anchor",
            traffic_source="baseline",
            inputs=_inputs_from(row),
        )
    desired_buckets = desired_buckets or {}
    best_candidate: dict[str, Any] | None = None
    best_match_count = -1
    best_distribution_score = float("-inf")

    for _ in range(8):
        scenario_name = None
        if generation_tier == "replay_amplified":
            inputs = _bounded_replay_variant(row, rng)
            label = anchor_label
        else:
            scenario_name = rng.choice(scenario_names)
            world = generate_micro_world_inputs(
                anchor_inputs=_inputs_from(row),
                rng=rng,
                scenario_name=scenario_name,
                desired_difficulty=desired_difficulty or "borderline",
            )
            inputs = world["inputs"]
            label = world["label"]
        inputs = _shape_inputs_for_targets(inputs, desired_buckets, rng)
        candidate = _simulate_row(
            row=row,
            label=label,
            generation_tier=generation_tier,
            traffic_source="replay_amplified" if generation_tier == "replay_amplified" else "scenario",
            inputs=inputs,
            scenario_name=scenario_name,
        )
        bucket_map = _row_bucket_map(candidate)
        match_count = sum(1 for family, bucket in desired_buckets.items() if bucket_map.get(family) == bucket)
        difficulty_match = 1 if (desired_difficulty is None or _difficulty_band(candidate) == desired_difficulty) else 0
        distribution_score = float(match_count) + (0.5 * difficulty_match)
        if match_count > best_match_count or (match_count == best_match_count and distribution_score > best_distribution_score):
            best_candidate = candidate
            best_match_count = match_count
            best_distribution_score = distribution_score
        if match_count == len(desired_buckets) and difficulty_match:
            return candidate

    return best_candidate if best_candidate is not None else _simulate_row(
        row=row,
        label=anchor_label if generation_tier == "replay_amplified" else None,
        generation_tier=generation_tier,
        traffic_source="replay_amplified" if generation_tier == "replay_amplified" else "scenario",
        inputs=_shape_inputs_for_targets(
            _bounded_replay_variant(row, rng)
            if generation_tier == "replay_amplified"
            else generate_micro_world_inputs(
                anchor_inputs=_inputs_from(row),
                rng=rng,
                scenario_name=rng.choice(scenario_names),
                desired_difficulty=desired_difficulty or "borderline",
            )["inputs"],
            desired_buckets,
            rng,
        ),
    )


def _highest_deficit_buckets(
    current_counts: dict[str, Counter],
    targets: dict[str, dict[str, float]],
) -> dict[str, str]:
    desired: dict[str, str] = {}
    for family, target_map in targets.items():
        best_bucket = None
        best_deficit = 0.0
        for bucket, target in target_map.items():
            deficit = float(target) - float(current_counts[family][bucket])
            if deficit > best_deficit:
                best_deficit = deficit
                best_bucket = bucket
        if best_bucket is not None:
            desired[family] = best_bucket
    return desired


def _payout_value_for_bucket(bucket: str, rng: random.Random) -> float:
    if bucket == "lt_75":
        return round(rng.uniform(28.0, 72.0), 2)
    if bucket == "75_125":
        return round(rng.uniform(78.0, 122.0), 2)
    if bucket == "125_200":
        return round(rng.uniform(128.0, 196.0), 2)
    return round(rng.uniform(205.0, 280.0), 2)


def _trust_value_for_bucket(bucket: str, rng: random.Random) -> float:
    if bucket == "lt_0.30":
        return round(rng.uniform(0.08, 0.28), 3)
    if bucket == "0.30_0.45":
        return round(rng.uniform(0.31, 0.44), 3)
    if bucket == "0.45_0.75":
        return round(rng.uniform(0.46, 0.74), 3)
    return round(rng.uniform(0.76, 0.95), 3)


def _shape_inputs_for_targets(
    inputs: dict[str, Any],
    desired_buckets: dict[str, str],
    rng: random.Random,
) -> dict[str, Any]:
    shaped = {
        **inputs,
        "fraud_result": dict(inputs.get("fraud_result") or {}),
        "feedback_result": dict(inputs.get("feedback_result") or {}),
    }
    fraud_result = shaped["fraud_result"]
    fraud_result["flags"] = list(fraud_result.get("flags") or [])

    payout_bucket = desired_buckets.get("payout_bands")
    if payout_bucket:
        shaped["payout_amount"] = _payout_value_for_bucket(payout_bucket, rng)

    trust_bucket = desired_buckets.get("trust_bands")
    if trust_bucket:
        shaped["trust_score"] = _trust_value_for_bucket(trust_bucket, rng)

    return shaped


def _guided_generate_rows(
    *,
    rows: int,
    anchors: list[DecisionLog],
    resolved_labels: dict[str, str],
    scenario_names: list[str],
    distribution_profile: str,
    difficulty_profile: str,
    anchor_share: float,
    amplified_share: float,
    rng: random.Random,
) -> list[dict[str, Any]]:
    amplified_rows = int(rows * amplified_share)
    anchor_rows = int(rows * anchor_share)
    scenario_rows = max(0, rows - anchor_rows - amplified_rows)
    tier_counts = {
        "anchor": anchor_rows,
        "replay_amplified": amplified_rows,
        "scenario": scenario_rows,
    }
    targets = _target_counts(rows, distribution_profile)
    difficulty_targets = _difficulty_targets(rows, difficulty_profile)
    current_counts: dict[str, Counter] = defaultdict(Counter)
    difficulty_counts: Counter = Counter()
    simulated: list[dict[str, Any]] = []
    candidate_pool_size = 18

    for generation_tier, target_count in tier_counts.items():
        for _ in range(target_count):
            desired_difficulty = _pick_weighted_bucket(
                {
                    bucket: max(0.0, target - float(difficulty_counts[bucket]))
                    for bucket, target in difficulty_targets.items()
                },
                rng,
            )
            candidates = [
                _build_candidate(
                    rng=rng,
                    anchors=anchors,
                    resolved_labels=resolved_labels,
                    generation_tier=generation_tier,
                    scenario_names=scenario_names,
                    desired_buckets=_highest_deficit_buckets(current_counts, targets),
                    desired_difficulty=desired_difficulty,
                )
                for _ in range(candidate_pool_size)
            ]
            best_candidate = max(
                candidates,
                key=lambda candidate: (
                    _candidate_score(candidate, current_counts, targets)
                    + (0.35 * _difficulty_score(candidate, difficulty_counts, difficulty_targets))
                ),
            )
            simulated.append(best_candidate)
            _record_candidate(best_candidate, current_counts)
            difficulty_counts[_difficulty_band(best_candidate)] += 1

    return simulated


def _distribution_distance(
    baseline_counts: Counter,
    comparison_counts: Counter,
) -> float:
    baseline_total = sum(baseline_counts.values())
    comparison_total = sum(comparison_counts.values())
    keys = set(baseline_counts.keys()) | set(comparison_counts.keys())
    distance = 0.0
    for key in keys:
        baseline_share = baseline_counts.get(key, 0) / max(1, baseline_total)
        comparison_share = comparison_counts.get(key, 0) / max(1, comparison_total)
        distance += abs(baseline_share - comparison_share)
    return round(distance / 2.0, 3)


def _source_alignment_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    baseline_rows = [row for row in rows if row["traffic_source"] == "baseline"]
    synthetic_rows = [row for row in rows if row["traffic_source"] != "baseline"]
    if not baseline_rows or not synthetic_rows:
        return {
            "baseline_present": bool(baseline_rows),
            "synthetic_present": bool(synthetic_rows),
            "within_tolerance": False,
            "max_divergence": None,
            "distances": {},
        }

    distances = {
        "decision_outcomes": _distribution_distance(
            Counter(row["decision"] for row in baseline_rows),
            Counter(row["decision"] for row in synthetic_rows),
        ),
        "rule_ids": _distribution_distance(
            Counter(row["rule_id"] for row in baseline_rows),
            Counter(row["rule_id"] for row in synthetic_rows),
        ),
        "surfaces": _distribution_distance(
            Counter(row["surface"] for row in baseline_rows),
            Counter(row["surface"] for row in synthetic_rows),
        ),
        "difficulty": _distribution_distance(
            Counter(_difficulty_band(row) for row in baseline_rows),
            Counter(_difficulty_band(row) for row in synthetic_rows),
        ),
    }
    max_divergence = max(distances.values())
    return {
        "baseline_present": True,
        "synthetic_present": True,
        "distances": distances,
        "max_divergence": round(max_divergence, 3),
        "target_tolerance": MAX_SOURCE_DIVERGENCE,
        "within_tolerance": max_divergence <= MAX_SOURCE_DIVERGENCE,
    }


async def run_experiment(
    *,
    rows: int,
    seed_sources: list[str],
    scenario_profile: str,
    distribution_profile: str,
    difficulty_profile: str,
    anchor_share: float,
    amplified_share: float,
    output_path: Path,
) -> dict[str, Any]:
    await ensure_decision_memory_schema()
    try:
        async with async_session_factory() as db:
            decision_rows = (
                await db.execute(
                    select(DecisionLog)
                    .where(DecisionLog.lifecycle_stage.in_(["claim_created", "manual_resolution", "backfill_resolution"]))
                    .order_by(DecisionLog.created_at.desc())
                )
            ).scalars().all()
    finally:
        await close_db()

    resolved_labels = _resolved_label_map(decision_rows)
    anchors = [
        row
        for row in decision_rows
        if row.lifecycle_stage == "claim_created" and _source_of(row) in seed_sources
    ]
    if not anchors:
        raise RuntimeError("No anchor decision rows matched the requested seed sources.")

    rng = random.Random(42)
    scenario_names = list(SCENARIO_PROFILES.keys()) if scenario_profile == "mixed" else [scenario_profile]
    simulated = _guided_generate_rows(
        rows=rows,
        anchors=anchors,
        resolved_labels=resolved_labels,
        scenario_names=scenario_names,
        distribution_profile=distribution_profile,
        difficulty_profile=difficulty_profile,
        anchor_share=anchor_share,
        amplified_share=amplified_share,
        rng=rng,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "experiment": {
            "rows_requested": rows,
            "seed_sources": seed_sources,
            "scenario_profile": scenario_profile,
            "distribution_profile": distribution_profile,
            "difficulty_profile": difficulty_profile,
            "anchor_share": anchor_share,
            "amplified_share": amplified_share,
            "scenario_share": round(1.0 - anchor_share - amplified_share, 3),
        },
        "metrics": _metrics(simulated),
    }
    report["distribution_governance"] = _distribution_summary(simulated, distribution_profile)
    report["source_alignment"] = _source_alignment_summary(simulated)
    report["baseline_comparison"] = _baseline_comparison(report["metrics"])
    report["governance_gates"] = _governance_gates(report["metrics"], report["baseline_comparison"])
    report["promotion_contract"] = _promotion_contract(
        distribution_governance=report["distribution_governance"],
        comparison=report["baseline_comparison"],
        gates=report["governance_gates"],
        metrics=report["metrics"],
        source_alignment=report["source_alignment"],
    )
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=True, indent=2)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a governed large-scale policy experiment from decision-memory anchors.")
    parser.add_argument("--rows", type=int, default=100000, help="How many simulated rows to generate.")
    parser.add_argument(
        "--seed-sources",
        type=str,
        default="baseline",
        help="Comma-separated traffic sources to use as anchor memory.",
    )
    parser.add_argument(
        "--scenario-profile",
        type=str,
        default="mixed",
        choices=["mixed", *sorted(SCENARIO_PROFILES.keys())],
        help="Scenario profile for the scenario-generation tier.",
    )
    parser.add_argument(
        "--distribution-profile",
        type=str,
        default="balanced_realism",
        choices=sorted(EXPERIMENT_DISTRIBUTIONS.keys()),
        help="Target distribution profile used to judge experiment realism.",
    )
    parser.add_argument(
        "--difficulty-profile",
        type=str,
        default="balanced",
        choices=sorted(DIFFICULTY_PROFILES.keys()),
        help="Difficulty mix used to keep synthetic traffic from becoming unrealistically easy.",
    )
    parser.add_argument("--anchor-share", type=float, default=0.5, help="Share of anchor rows.")
    parser.add_argument("--amplified-share", type=float, default=0.35, help="Share of bounded replay-amplified rows.")
    parser.add_argument(
        "--output",
        type=Path,
        default=default_export_path() / "policy_experiment_report.json",
        help="Where to write the experiment report.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    report = asyncio.run(
        run_experiment(
            rows=max(1, args.rows),
            seed_sources=[item.strip() for item in args.seed_sources.split(",") if item.strip()],
            scenario_profile=args.scenario_profile,
            distribution_profile=args.distribution_profile,
            difficulty_profile=args.difficulty_profile,
            anchor_share=max(0.0, min(1.0, args.anchor_share)),
            amplified_share=max(0.0, min(1.0, args.amplified_share)),
            output_path=args.output,
        )
    )
    print(f"Wrote experiment report to {args.output}")
    print(json.dumps(report["metrics"], ensure_ascii=True, indent=2))
