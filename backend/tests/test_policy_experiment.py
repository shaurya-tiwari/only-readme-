from collections import Counter
from collections import defaultdict
import random

from scripts.micro_world import generate_micro_world_inputs
from scripts.run_policy_experiment import _candidate_score
from scripts.run_policy_experiment import _source_alignment_summary
from scripts.run_policy_experiment import _promotion_contract


def test_candidate_score_rewards_underfilled_buckets():
    current_counts = defaultdict(Counter)
    targets = {
        "payout_bands": {"lt_75": 10.0},
        "trust_bands": {"ge_0.75": 10.0},
        "cluster_types": {"not_clustered": 10.0},
        "uncertainty_cases": {"none": 10.0},
    }
    candidate = {
        "payout_amount": 60.0,
        "trust_score": 0.81,
        "cluster_type": "not_clustered",
        "uncertainty_case": "none",
    }

    score = _candidate_score(candidate, current_counts, targets)

    assert score > 0


def test_candidate_score_penalizes_oversampled_buckets():
    current_counts = defaultdict(Counter)
    current_counts["payout_bands"]["lt_75"] = 11
    current_counts["trust_bands"]["ge_0.75"] = 11
    current_counts["cluster_types"]["not_clustered"] = 11
    current_counts["uncertainty_cases"]["none"] = 11
    targets = {
        "payout_bands": {"lt_75": 10.0},
        "trust_bands": {"ge_0.75": 10.0},
        "cluster_types": {"not_clustered": 10.0},
        "uncertainty_cases": {"none": 10.0},
    }
    candidate = {
        "payout_amount": 60.0,
        "trust_score": 0.81,
        "cluster_type": "not_clustered",
        "uncertainty_case": "none",
    }

    score = _candidate_score(candidate, current_counts, targets)

    assert score < 0


def test_promotion_contract_blocks_when_distribution_is_not_realistic():
    metrics = {
        "by_traffic_source": {
            "baseline": {
                "count": 150,
                "friction_score": 24.0,
                "automation_efficiency": 58.0,
                "false_auto_approval_risk": 2.5,
            },
            "scenario": {
                "count": 80,
                "friction_score": 20.0,
                "automation_efficiency": 60.0,
                "false_auto_approval_risk": 2.9,
            },
            "replay_amplified": {
                "count": 70,
                "friction_score": 19.5,
                "automation_efficiency": 61.0,
                "false_auto_approval_risk": 2.7,
            },
        }
    }
    comparison = {
        "baseline_present": True,
        "non_baseline_present": True,
        "deltas": {
            "friction_score": -4.0,
            "automation_efficiency": 2.0,
            "false_auto_approval_risk": 0.3,
        },
    }
    gates = {
        "baseline_rows_gate": {"passed": True},
        "false_auto_delta_gate": {"passed": True},
    }
    distribution_governance = {"within_tolerance": False}
    source_alignment = {"within_tolerance": True}

    contract = _promotion_contract(
        distribution_governance=distribution_governance,
        comparison=comparison,
        gates=gates,
        metrics=metrics,
        source_alignment=source_alignment,
    )

    assert contract["checks"]["baseline_improves"] is True
    assert contract["checks"]["multi_source_consistency"] is True
    assert contract["checks"]["distribution_valid"] is False
    assert contract["checks"]["source_alignment_valid"] is True
    assert contract["allow_policy_change"] is False


def test_source_alignment_summary_detects_divergence():
    rows = [
        {
            "traffic_source": "baseline",
            "decision": "approved",
            "rule_id": "threshold_score_approve",
            "surface": "threshold_surface",
            "cluster_type": "not_clustered",
            "uncertainty_case": "none",
            "final_score": 0.72,
            "decision_confidence": 0.84,
            "trust_score": 0.68,
        },
        {
            "traffic_source": "baseline",
            "decision": "approved",
            "rule_id": "threshold_score_approve",
            "surface": "threshold_surface",
            "cluster_type": "not_clustered",
            "uncertainty_case": "none",
            "final_score": 0.73,
            "decision_confidence": 0.83,
            "trust_score": 0.7,
        },
        {
            "traffic_source": "scenario",
            "decision": "approved",
            "rule_id": "fraud_override",
            "surface": "fraud_surface",
            "cluster_type": "fraud_ring",
            "uncertainty_case": "core_contradiction",
            "final_score": 0.71,
            "decision_confidence": 0.42,
            "trust_score": 0.18,
        },
        {
            "traffic_source": "replay_amplified",
            "decision": "approved",
            "rule_id": "fraud_override",
            "surface": "fraud_surface",
            "cluster_type": "fraud_ring",
            "uncertainty_case": "core_contradiction",
            "final_score": 0.69,
            "decision_confidence": 0.46,
            "trust_score": 0.22,
        },
    ]

    summary = _source_alignment_summary(rows)

    assert summary["baseline_present"] is True
    assert summary["synthetic_present"] is True
    assert summary["max_divergence"] > 0.2
    assert summary["within_tolerance"] is False


def test_micro_world_generation_is_behavioral_not_outcome_labeled():
    rng = random.Random(7)
    world = generate_micro_world_inputs(
        anchor_inputs={
            "trust_score": 0.58,
            "payout_amount": 92.0,
            "disruption_score": 0.61,
            "event_confidence": 0.66,
        },
        rng=rng,
        scenario_name="cluster_heavy",
        desired_difficulty="borderline",
    )

    assert "cluster_type" not in world["inputs"]
    assert "uncertainty_case" not in world["inputs"]
    assert "archetype" in world["world_meta"]
    assert world["world_meta"]["behavioral_difficulty"] == "borderline"
    assert isinstance(world["inputs"]["fraud_result"]["flags"], list)


def test_micro_world_supports_behavioral_difficulty_categories():
    rng = random.Random(11)
    world = generate_micro_world_inputs(
        anchor_inputs={
            "trust_score": 0.72,
            "payout_amount": 88.0,
            "disruption_score": 0.59,
            "event_confidence": 0.68,
        },
        rng=rng,
        scenario_name="gray_band_overload",
        desired_difficulty="noisy_legit",
    )

    assert world["world_meta"]["behavioral_difficulty"] == "noisy_legit"
    assert "conflict_pattern" in world["world_meta"]
