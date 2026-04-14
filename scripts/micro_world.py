"""Minimal worker-archetype micro-world for causal experiment generation."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any


@dataclass(frozen=True)
class WorkerArchetype:
    name: str
    base_trust_range: tuple[float, float]
    activity_rate: tuple[float, float]
    variance: tuple[float, float]
    coordination_tendency: tuple[float, float]
    payout_profile: str
    legit_bias: float


ARCHETYPES: dict[str, WorkerArchetype] = {
    "LEGIT_STABLE": WorkerArchetype("LEGIT_STABLE", (0.68, 0.92), (0.25, 0.45), (0.04, 0.12), (0.0, 0.08), "low_mid", 0.95),
    "LEGIT_NOISY": WorkerArchetype("LEGIT_NOISY", (0.42, 0.76), (0.35, 0.62), (0.18, 0.34), (0.02, 0.12), "low_mid", 0.82),
    "FRAUD_OPPORTUNISTIC": WorkerArchetype("FRAUD_OPPORTUNISTIC", (0.18, 0.48), (0.22, 0.5), (0.15, 0.28), (0.18, 0.4), "mid_high", 0.18),
    "FRAUD_RING_MEMBER": WorkerArchetype("FRAUD_RING_MEMBER", (0.1, 0.34), (0.4, 0.7), (0.08, 0.18), (0.72, 0.95), "mid_high", 0.05),
    "MIXED_BEHAVIOR": WorkerArchetype("MIXED_BEHAVIOR", (0.28, 0.66), (0.28, 0.58), (0.12, 0.28), (0.18, 0.46), "mixed", 0.55),
}

ARCHETYPE_WEIGHTS: dict[str, dict[str, float]] = {
    "default": {
        "LEGIT_STABLE": 0.32,
        "LEGIT_NOISY": 0.28,
        "FRAUD_OPPORTUNISTIC": 0.16,
        "FRAUD_RING_MEMBER": 0.08,
        "MIXED_BEHAVIOR": 0.16,
    },
    "gray_band_overload": {
        "LEGIT_STABLE": 0.16,
        "LEGIT_NOISY": 0.38,
        "FRAUD_OPPORTUNISTIC": 0.1,
        "FRAUD_RING_MEMBER": 0.06,
        "MIXED_BEHAVIOR": 0.3,
    },
    "cluster_heavy": {
        "LEGIT_STABLE": 0.1,
        "LEGIT_NOISY": 0.18,
        "FRAUD_OPPORTUNISTIC": 0.18,
        "FRAUD_RING_MEMBER": 0.32,
        "MIXED_BEHAVIOR": 0.22,
    },
    "fraud_pressure": {
        "LEGIT_STABLE": 0.08,
        "LEGIT_NOISY": 0.12,
        "FRAUD_OPPORTUNISTIC": 0.34,
        "FRAUD_RING_MEMBER": 0.28,
        "MIXED_BEHAVIOR": 0.18,
    },
}

BEHAVIORAL_PRESSURE: dict[str, dict[str, float]] = {
    "clean_legit": {"noise": 0.72, "coordination": 0.75, "adversarial": 0.55, "conflict": 0.05},
    "noisy_legit": {"noise": 1.08, "coordination": 0.92, "adversarial": 0.75, "conflict": 0.22},
    "borderline": {"noise": 1.0, "coordination": 1.0, "adversarial": 1.0, "conflict": 0.28},
    "adversarial": {"noise": 1.12, "coordination": 1.18, "adversarial": 1.35, "conflict": 0.32},
}


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _pick_archetype(rng: random.Random, scenario_name: str | None) -> WorkerArchetype:
    weights = ARCHETYPE_WEIGHTS.get(scenario_name or "default", ARCHETYPE_WEIGHTS["default"])
    names = list(weights.keys())
    chosen = rng.choices(names, weights=[weights[name] for name in names], k=1)[0]
    return ARCHETYPES[chosen]


def _draw_in_range(rng: random.Random, bounds: tuple[float, float]) -> float:
    return rng.uniform(bounds[0], bounds[1])


def _evolve_trust(anchor_trust: float, archetype: WorkerArchetype, rng: random.Random, history_bias: float) -> float:
    base = _draw_in_range(rng, archetype.base_trust_range)
    return round(_clamp((0.45 * anchor_trust) + (0.4 * base) + (0.15 * history_bias), 0.05, 0.98), 3)


def _payout_from_profile(anchor_payout: float, profile: str, rng: random.Random, window_density: float) -> float:
    if profile == "low_mid":
        return round(_clamp((0.45 * anchor_payout) + rng.uniform(35.0, 118.0) + (window_density * 10), 25.0, 155.0), 2)
    if profile == "mid_high":
        return round(_clamp((0.4 * anchor_payout) + rng.uniform(85.0, 240.0) + (window_density * 18), 65.0, 320.0), 2)
    return round(_clamp((0.4 * anchor_payout) + rng.uniform(45.0, 200.0) + (window_density * 14), 30.0, 260.0), 2)


def generate_micro_world_inputs(
    *,
    anchor_inputs: dict[str, Any],
    rng: random.Random,
    scenario_name: str | None,
    desired_difficulty: str,
) -> dict[str, Any]:
    archetype = _pick_archetype(rng, scenario_name)
    pressure = BEHAVIORAL_PRESSURE[desired_difficulty]

    anchor_trust = float(anchor_inputs.get("trust_score") or 0.52)
    anchor_payout = float(anchor_inputs.get("payout_amount") or 92.0)
    anchor_disruption = float(anchor_inputs.get("disruption_score") or 0.6)
    anchor_confidence = float(anchor_inputs.get("event_confidence") or 0.66)

    window_density = _draw_in_range(rng, archetype.activity_rate)
    timing_jitter = _draw_in_range(rng, archetype.variance) * pressure["noise"]
    coordination = _draw_in_range(rng, archetype.coordination_tendency) * pressure["coordination"]
    repeated_participation = _clamp(window_density + rng.uniform(-0.08, 0.15), 0.0, 1.0)
    history_bias = 0.78 if archetype.legit_bias >= 0.75 else (0.2 if archetype.legit_bias <= 0.2 else 0.48)
    conflict_roll = rng.random()
    conflict_pattern = "none"

    trust_score = _evolve_trust(anchor_trust, archetype, rng, history_bias)
    payout_amount = _payout_from_profile(anchor_payout, archetype.payout_profile, rng, window_density)

    disruption_score = _clamp(anchor_disruption + rng.uniform(-0.08, 0.08) + (window_density * 0.08), 0.25, 0.92)
    event_confidence = _clamp(anchor_confidence + rng.uniform(-0.1, 0.1) + (repeated_participation * 0.05), 0.28, 0.95)

    flags: list[str] = []
    if coordination >= 0.62 and repeated_participation >= 0.45:
        flags.append("cluster")

    if archetype.name == "LEGIT_NOISY":
        if timing_jitter >= 0.16:
            flags.extend(["movement", "pre_activity"])
        if desired_difficulty != "clean_legit" and rng.random() < 0.35:
            flags.append("location_drift")
    elif archetype.name == "FRAUD_RING_MEMBER":
        flags.extend(["device", "timing"])
        if payout_amount >= 135 or rng.random() < 0.45:
            flags.append("income_inflation")
    elif archetype.name == "FRAUD_OPPORTUNISTIC":
        flags.append("timing")
        if desired_difficulty != "clean_legit":
            flags.append("device")
        if rng.random() < 0.45 * pressure["adversarial"]:
            flags.append("income_inflation")
    elif archetype.name == "MIXED_BEHAVIOR":
        if rng.random() < 0.55:
            flags.append("movement")
        if rng.random() < 0.35:
            flags.append("device")
        if coordination >= 0.32:
            flags.append("cluster")
    else:
        if rng.random() < 0.18:
            flags.append("device")

    # Conflict patterns are generated as upstream tensions, not explicit uncertainty labels.
    if conflict_roll < pressure["conflict"]:
        if archetype.name in {"LEGIT_STABLE", "LEGIT_NOISY"}:
            conflict_pattern = "trust_vs_cluster"
            trust_score = _clamp(max(trust_score, 0.72), 0.05, 0.98)
            flags = list(dict.fromkeys(flags + ["cluster", "device"]))
            coordination = _clamp(max(coordination, 0.66), 0.0, 1.0)
            event_confidence = _clamp(max(event_confidence, 0.74), 0.28, 0.95)
            payout_amount = max(payout_amount, 118.0)
        elif archetype.name == "MIXED_BEHAVIOR":
            conflict_pattern = "score_vs_behavior"
            disruption_score = _clamp(max(disruption_score, 0.7), 0.25, 0.92)
            event_confidence = _clamp(min(event_confidence, 0.53), 0.28, 0.95)
            flags = list(dict.fromkeys(flags + ["movement"]))
        else:
            conflict_pattern = "deceptive_semi_fraud"
            trust_score = _clamp(max(trust_score, 0.38), 0.05, 0.98)
            flags = list(dict.fromkeys(flags + ["device"]))
            if "income_inflation" not in flags and rng.random() < 0.5:
                flags.append("income_inflation")
            disruption_score = _clamp(max(disruption_score, 0.66), 0.25, 0.92)
            event_confidence = _clamp(max(event_confidence, 0.68), 0.28, 0.95)

    # Make uncertainty emerge from signal relationships rather than explicit case injection.
    if desired_difficulty in {"noisy_legit", "borderline"}:
        disruption_score = _clamp(disruption_score, 0.56, 0.78)
        if archetype.name in {"LEGIT_NOISY", "MIXED_BEHAVIOR"}:
            event_confidence = _clamp(event_confidence - 0.1, 0.4, 0.72)
        if desired_difficulty == "noisy_legit":
            trust_score = _clamp(max(trust_score, 0.46), 0.05, 0.98)
            flags = list(dict.fromkeys(flags + ["movement", "pre_activity"]))
    elif desired_difficulty == "adversarial":
        if archetype.name in {"FRAUD_RING_MEMBER", "FRAUD_OPPORTUNISTIC"}:
            disruption_score = _clamp(max(disruption_score, 0.72), 0.25, 0.92)
            event_confidence = _clamp(max(event_confidence, 0.72), 0.28, 0.95)
            trust_score = _clamp(min(trust_score, 0.34), 0.05, 0.98)
        elif archetype.name in {"LEGIT_NOISY", "MIXED_BEHAVIOR"}:
            disruption_score = _clamp(max(disruption_score, 0.66), 0.25, 0.92)
            event_confidence = _clamp(min(event_confidence, 0.56), 0.28, 0.95)

    # Too-perfect state requires one moderate cue with extremely strong trust.
    if archetype.name == "LEGIT_STABLE" and desired_difficulty in {"noisy_legit", "borderline"} and rng.random() < 0.16:
        trust_score = _clamp(max(trust_score, 0.92), 0.05, 0.98)
        flags = ["device"]
        disruption_score = _clamp(max(disruption_score, 0.74), 0.25, 0.92)
        event_confidence = _clamp(max(event_confidence, 0.82), 0.28, 0.95)
        conflict_pattern = "too_perfect_signal"

    flags = list(dict.fromkeys(flags))
    weak_flags = {"movement", "pre_activity", "location_drift"}
    moderate_flags = {"device"}
    strong_flags = {"timing", "income_inflation", "duplicate"}

    adjusted_fraud = 0.04
    raw_fraud = 0.06
    for flag in flags:
        if flag in strong_flags:
            adjusted_fraud += 0.14
            raw_fraud += 0.16
        elif flag in moderate_flags:
            adjusted_fraud += 0.08
            raw_fraud += 0.1
        else:
            adjusted_fraud += 0.04
            raw_fraud += 0.05

    adjusted_fraud += (1.0 - trust_score) * 0.12
    raw_fraud += coordination * 0.08
    if conflict_pattern == "trust_vs_cluster":
        adjusted_fraud += 0.05
        raw_fraud += 0.08
    elif conflict_pattern == "score_vs_behavior":
        adjusted_fraud += 0.04
        raw_fraud += 0.05
    elif conflict_pattern == "deceptive_semi_fraud":
        adjusted_fraud += 0.08
        raw_fraud += 0.09
    adjusted_fraud = round(_clamp(adjusted_fraud, 0.02, 0.78), 3)
    raw_fraud = round(_clamp(max(adjusted_fraud, raw_fraud), 0.03, 0.84), 3)

    fraud_probability = round(_clamp((adjusted_fraud * 0.65) + ((1.0 - trust_score) * 0.25), 0.01, 0.95), 3)
    label = "legit" if rng.random() <= archetype.legit_bias else "fraud"
    if archetype.name == "FRAUD_RING_MEMBER":
        label = "fraud"
    elif archetype.name == "LEGIT_STABLE":
        label = "legit"

    return {
        "inputs": {
            "disruption_score": round(disruption_score, 3),
            "event_confidence": round(event_confidence, 3),
            "trust_score": round(trust_score, 3),
            "payout_amount": payout_amount,
            "fraud_result": {
                "adjusted_fraud_score": adjusted_fraud,
                "raw_fraud_score": raw_fraud,
                "flags": flags,
                "ml_confidence": round(_clamp(0.58 + coordination - timing_jitter, 0.31, 0.91), 3),
                "fallback_used": False,
                "fraud_probability": fraud_probability,
                "top_factors": [{"label": flag.replace("_", " ")} for flag in flags[:3]],
            },
            "feedback_result": {},
        },
        "label": label,
        "world_meta": {
            "archetype": archetype.name,
            "behavioral_difficulty": desired_difficulty,
            "conflict_pattern": conflict_pattern,
            "window_density": round(window_density, 3),
            "timing_jitter": round(timing_jitter, 3),
            "coordination": round(coordination, 3),
            "repeated_participation": round(repeated_participation, 3),
        },
    }
