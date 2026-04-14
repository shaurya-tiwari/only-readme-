"""
Tests for Sprint 2 decision engine.
"""

from backend.core.decision_engine import decision_engine


def test_high_score_is_approved():
    result = decision_engine.decide(
        disruption_score=0.9,
        event_confidence=0.9,
        fraud_result={"adjusted_fraud_score": 0.1, "raw_fraud_score": 0.1, "flags": [], "is_suspicious": False, "is_high_risk": False},
        trust_score=0.8,
    )
    assert result["decision"] == "approved"
    assert result["decision_confidence"] > 0.7
    assert result["decision_confidence_band"] == "high"
    assert result["reason_labels"][0] == result["primary_reason"]
    assert result["uncertainty"]["case"] is None
    assert result["policy_layer"] == "strong_approve_layer"
    assert result["rule_id"] in {"auto_approve_strong_signal_alignment", "threshold_score_approve"}


def test_mid_score_is_delayed():
    result = decision_engine.decide(
        disruption_score=0.5,
        event_confidence=0.6,
        fraud_result={"adjusted_fraud_score": 0.35, "raw_fraud_score": 0.45, "flags": ["movement"], "is_suspicious": True, "is_high_risk": False},
        trust_score=0.2,
        payout_amount=100,
    )
    assert result["decision"] == "delayed"
    assert result["decision_confidence"] > 0
    assert result["uncertainty"]["route"] in {"standard", "review"}
    assert result["policy_layer"] in {"ambiguity_resolver", "review_fallback"}
    assert result["rule_id"]


def test_trusted_low_fraud_profile_is_approved_even_below_primary_score_threshold():
    result = decision_engine.decide(
        disruption_score=0.374,
        event_confidence=0.773,
        fraud_result={
            "adjusted_fraud_score": 0.138,
            "raw_fraud_score": 0.304,
            "flags": ["movement", "pre_activity"],
            "is_suspicious": False,
            "is_high_risk": False,
        },
        trust_score=0.83,
    )
    assert result["decision"] == "approved"
    assert result["inputs"]["trusted_low_risk_approve"] is True
    assert result["decision_confidence"] >= 0.48


def test_low_trust_profile_with_same_band_stays_manual_review():
    result = decision_engine.decide(
        disruption_score=0.374,
        event_confidence=0.773,
        fraud_result={
            "adjusted_fraud_score": 0.138,
            "raw_fraud_score": 0.304,
            "flags": ["movement", "pre_activity"],
            "is_suspicious": False,
            "is_high_risk": False,
        },
        trust_score=0.15,
        payout_amount=100,
    )
    assert result["decision"] == "delayed"
    assert result["inputs"]["trusted_low_risk_approve"] is False
    assert result["primary_reason"] in {"worker trust score", "movement anomaly", "weak pre-event activity"}


def test_hard_review_flags_do_not_use_trusted_low_risk_fast_path():
    result = decision_engine.decide(
        disruption_score=0.45,
        event_confidence=0.78,
        fraud_result={
            "adjusted_fraud_score": 0.17,
            "raw_fraud_score": 0.28,
            "flags": ["movement", "timing"],
            "is_suspicious": False,
            "is_high_risk": False,
        },
        trust_score=0.82,
    )
    assert result["decision"] == "delayed"
    assert result["inputs"]["trusted_low_risk_approve"] is False


def test_gps_spoofing_class_movement_cannot_auto_approve():
    result = decision_engine.decide(
        disruption_score=0.82,
        event_confidence=0.91,
        fraud_result={
            "adjusted_fraud_score": 0.18,
            "raw_fraud_score": 0.31,
            "flags": ["movement"],
            "signals": {"movement": 1.0},
            "is_suspicious": False,
            "is_high_risk": False,
            "ml_confidence": 0.88,
            "fallback_used": False,
        },
        trust_score=0.78,
        payout_amount=95,
    )
    assert result["decision"] == "delayed"
    assert result["inputs"]["gps_spoof_detected"] is True
    assert result["rule_id"] == "gps_spoof_review_override"


def test_low_score_is_rejected():
    result = decision_engine.decide(
        disruption_score=0.2,
        event_confidence=0.4,
        fraud_result={"adjusted_fraud_score": 0.8, "raw_fraud_score": 0.9, "flags": ["cluster"], "is_suspicious": True, "is_high_risk": True},
        trust_score=0.1,
    )
    assert result["decision"] == "rejected"
    assert result["decision_confidence"] > 0
    assert result["policy_layer"] == "fraud_layer"
    assert result["rule_id"] == "auto_reject_fraud_override"


def test_positive_feedback_bias_can_promote_borderline_claim():
    result = decision_engine.decide(
        disruption_score=0.39,
        event_confidence=0.79,
        fraud_result={
            "adjusted_fraud_score": 0.17,
            "raw_fraud_score": 0.29,
            "flags": ["movement", "pre_activity"],
            "is_suspicious": False,
            "is_high_risk": False,
            "ml_confidence": 0.89,
        },
        trust_score=0.72,
        feedback_result={"score_adjustment": 0.05, "confidence": 0.67, "approved_matches": 2, "rejected_matches": 0},
    )
    assert result["decision"] == "approved"
    assert result["breakdown"]["feedback_adjustment"] > 0


def test_low_payout_moderate_risk_claim_can_approve_when_signals_are_only_weak():
    result = decision_engine.decide(
        disruption_score=0.42,
        event_confidence=0.8,
        fraud_result={
            "adjusted_fraud_score": 0.23,
            "raw_fraud_score": 0.31,
            "flags": ["movement", "pre_activity"],
            "signals": {"movement": 0.58, "pre_activity": 0.56},
            "is_suspicious": False,
            "is_high_risk": False,
            "ml_confidence": 0.86,
            "fallback_used": False,
        },
        trust_score=0.56,
        payout_amount=48,
    )
    assert result["decision"] == "approved"
    assert result["inputs"]["low_payout_confident_approve"] is True or result["inputs"]["weak_signal_confident_approve"] is True
    assert result["decision_confidence"] >= 0.6


def test_same_borderline_profile_above_new_caps_stays_in_review():
    result = decision_engine.decide(
        disruption_score=0.42,
        event_confidence=0.8,
        fraud_result={
            "adjusted_fraud_score": 0.23,
            "raw_fraud_score": 0.31,
            "flags": ["movement", "pre_activity"],
            "signals": {"movement": 0.58, "pre_activity": 0.56},
            "is_suspicious": False,
            "is_high_risk": False,
            "ml_confidence": 0.86,
            "fallback_used": False,
        },
        trust_score=0.56,
        payout_amount=260,
    )
    assert result["decision"] == "delayed"
    assert result["inputs"]["low_payout_confident_approve"] is False


def test_safe_borderline_band_can_auto_approve_stable_moderate_claim():
    result = decision_engine.decide(
        disruption_score=0.47,
        event_confidence=0.68,
        fraud_result={
            "adjusted_fraud_score": 0.27,
            "raw_fraud_score": 0.34,
            "flags": ["movement", "pre_activity"],
            "signals": {"movement": 0.57, "pre_activity": 0.55},
            "is_suspicious": False,
            "is_high_risk": False,
            "ml_confidence": 0.9,
            "fallback_used": False,
        },
        trust_score=0.58,
        payout_amount=190,
    )
    assert result["decision"] == "approved"
    assert result["inputs"]["borderline_confident_approve"] is True
    assert result["breakdown"]["automation_confidence"] >= 0.6


def test_safe_borderline_band_does_not_approve_low_trust_claim():
    result = decision_engine.decide(
        disruption_score=0.47,
        event_confidence=0.68,
        fraud_result={
            "adjusted_fraud_score": 0.27,
            "raw_fraud_score": 0.34,
            "flags": ["movement", "pre_activity"],
            "signals": {"movement": 0.57, "pre_activity": 0.55},
            "is_suspicious": False,
            "is_high_risk": False,
            "ml_confidence": 0.9,
            "fallback_used": False,
        },
        trust_score=0.18,
        payout_amount=190,
    )
    assert result["decision"] == "delayed"
    assert result["inputs"]["borderline_confident_approve"] is False


def test_extended_low_payout_cap_approves_moderate_exposure_weak_signal_claim():
    result = decision_engine.decide(
        disruption_score=0.43,
        event_confidence=0.68,
        fraud_result={
            "adjusted_fraud_score": 0.25,
            "raw_fraud_score": 0.33,
            "flags": ["movement", "pre_activity"],
            "signals": {"movement": 0.56, "pre_activity": 0.54},
            "is_suspicious": False,
            "is_high_risk": False,
            "ml_confidence": 0.88,
            "fallback_used": False,
        },
        trust_score=0.44,
        payout_amount=160,
    )
    assert result["decision"] == "approved"
    assert result["inputs"]["low_payout_confident_approve"] is True


def test_extended_caps_still_hold_high_exposure_weak_signal_claim_for_review():
    result = decision_engine.decide(
        disruption_score=0.43,
        event_confidence=0.68,
        fraud_result={
            "adjusted_fraud_score": 0.25,
            "raw_fraud_score": 0.33,
            "flags": ["movement", "pre_activity"],
            "signals": {"movement": 0.56, "pre_activity": 0.54},
            "is_suspicious": False,
            "is_high_risk": False,
            "ml_confidence": 0.88,
            "fallback_used": False,
        },
        trust_score=0.44,
        payout_amount=260,
    )
    assert result["decision"] == "delayed"
    assert result["inputs"]["low_payout_confident_approve"] is False
    assert result["inputs"]["borderline_confident_approve"] is False


def test_false_review_safe_lane_approves_low_payout_weak_signal_review_band_claim():
    result = decision_engine.decide(
        disruption_score=0.55,
        event_confidence=0.63,
        fraud_result={
            "adjusted_fraud_score": 0.26,
            "raw_fraud_score": 0.34,
            "flags": ["movement", "pre_activity"],
            "signals": {"movement": 0.48, "pre_activity": 0.44},
            "ml_confidence": 0.76,
            "fallback_used": False,
        },
        trust_score=0.46,
        payout_amount=98,
    )
    assert result["decision"] == "approved"
    assert result["inputs"]["false_review_safe_lane_approve"] is True
    assert result["inputs"]["gray_band_surface"] == "low_payout_legit_surface"
    assert "low-payout gray-band lane" in result["explanation"]


def test_gray_band_low_payout_legit_surface_is_explicit_and_approves():
    result = decision_engine.decide(
        disruption_score=0.58,
        event_confidence=0.64,
        fraud_result={
            "adjusted_fraud_score": 0.22,
            "raw_fraud_score": 0.29,
            "flags": ["movement", "pre_activity"],
            "signals": {"movement": 0.44, "pre_activity": 0.41},
            "ml_confidence": 0.8,
            "fallback_used": False,
        },
        trust_score=0.52,
        payout_amount=72,
    )
    assert result["inputs"]["gray_band_surface"] == "low_payout_legit_surface"
    assert result["rule_id"] == "gray_band_low_payout_legit_approve"
    assert result["decision"] == "approved"


def test_gray_band_cluster_sensitive_surface_routes_to_review():
    result = decision_engine.decide(
        disruption_score=0.58,
        event_confidence=0.63,
        fraud_result={
            "adjusted_fraud_score": 0.26,
            "raw_fraud_score": 0.33,
            "flags": ["cluster", "movement"],
            "signals": {"cluster": 0.62, "movement": 0.45},
            "ml_confidence": 0.77,
            "fallback_used": False,
        },
        trust_score=0.54,
        payout_amount=82,
    )
    assert result["inputs"]["gray_band_surface"] == "cluster_sensitive_surface"
    assert result["rule_id"] == "gray_band_cluster_sensitive_review"
    assert result["decision"] == "delayed"


def test_cluster_no_longer_claims_raw_penalty_activity():
    result = decision_engine.decide(
        disruption_score=0.34,
        event_confidence=0.46,
        fraud_result={
            "adjusted_fraud_score": 0.62,
            "raw_fraud_score": 0.71,
            "flags": ["cluster", "timing"],
            "signals": {"cluster": 0.77, "timing": 0.7},
            "ml_confidence": 0.82,
            "fallback_used": False,
        },
        trust_score=0.19,
        payout_amount=135,
    )
    assert result["breakdown"]["cluster_raw_penalty_active"] is False


def test_false_review_safe_lane_does_not_approve_same_band_when_payout_is_above_observed_safe_cap():
    result = decision_engine.decide(
        disruption_score=0.55,
        event_confidence=0.63,
        fraud_result={
            "adjusted_fraud_score": 0.26,
            "raw_fraud_score": 0.34,
            "flags": ["movement", "pre_activity"],
            "signals": {"movement": 0.48, "pre_activity": 0.44},
            "ml_confidence": 0.76,
            "fallback_used": False,
        },
        trust_score=0.46,
        payout_amount=165,
    )
    assert result["inputs"]["false_review_safe_lane_approve"] is False
    assert result["decision"] == "delayed"


def test_core_contradiction_routes_to_review_with_explicit_uncertainty_case():
    result = decision_engine.decide(
        disruption_score=0.82,
        event_confidence=0.79,
        fraud_result={
            "adjusted_fraud_score": 0.41,
            "raw_fraud_score": 0.48,
            "flags": ["movement", "pre_activity"],
            "signals": {"movement": 0.72, "pre_activity": 0.68},
            "ml_confidence": 0.74,
            "fallback_used": False,
        },
        trust_score=0.14,
        payout_amount=118,
    )
    assert result["decision"] == "delayed"
    assert result["uncertainty"]["case"] == "core_contradiction"
    assert result["uncertainty"]["route"] == "review"
    assert "worker trust score" in result["reason_labels"]


def test_too_perfect_state_blocks_threshold_approve_when_device_signal_exists():
    result = decision_engine.decide(
        disruption_score=0.86,
        event_confidence=0.88,
        fraud_result={
            "adjusted_fraud_score": 0.04,
            "raw_fraud_score": 0.09,
            "flags": ["device"],
            "signals": {"device": 0.7},
            "ml_confidence": 0.94,
            "fallback_used": False,
        },
        trust_score=0.95,
        payout_amount=42,
    )
    assert result["decision"] == "delayed"
    assert result["uncertainty"]["case"] == "too_perfect_state"
    assert result["uncertainty"]["route"] == "review"
    assert result["primary_reason"] == "device risk"


def test_noise_overload_stays_review_even_when_weak_flags_stack():
    result = decision_engine.decide(
        disruption_score=0.51,
        event_confidence=0.56,
        fraud_result={
            "adjusted_fraud_score": 0.21,
            "raw_fraud_score": 0.29,
            "flags": ["movement", "pre_activity", "movement"],
            "signals": {"movement": 0.45, "pre_activity": 0.44},
            "ml_confidence": 0.41,
            "fallback_used": False,
        },
        trust_score=0.38,
        payout_amount=74,
    )
    assert result["decision"] == "delayed"
    assert result["uncertainty"]["case"] == "noise_overload"
    assert result["uncertainty"]["route"] == "review"


def test_silent_conflict_routes_borderline_band_to_review():
    result = decision_engine.decide(
        disruption_score=0.79,
        event_confidence=0.49,
        fraud_result={
            "adjusted_fraud_score": 0.18,
            "raw_fraud_score": 0.26,
            "flags": ["movement", "pre_activity"],
            "signals": {"movement": 0.52, "pre_activity": 0.49},
            "ml_confidence": 0.52,
            "fallback_used": False,
        },
        trust_score=0.61,
        payout_amount=102,
    )
    assert result["decision"] == "delayed"
    assert result["uncertainty"]["case"] == "silent_conflict"
    assert result["uncertainty"]["route"] == "review"


def test_device_only_micro_payout_lane_approves_isolated_device_noise():
    result = decision_engine.decide(
        disruption_score=0.33,
        event_confidence=0.52,
        fraud_result={
            "adjusted_fraud_score": 0.08,
            "raw_fraud_score": 0.16,
            "flags": ["device"],
            "signals": {"device": 0.58},
            "ml_confidence": 0.64,
            "fallback_used": False,
        },
        trust_score=0.74,
        payout_amount=28,
    )
    assert result["decision"] == "approved"
    assert result["inputs"]["device_micro_payout_approve"] is True
    assert result["breakdown"]["pattern_taxonomy"] == "device_micro_noise"


def test_cluster_device_combo_does_not_use_device_micro_lane():
    result = decision_engine.decide(
        disruption_score=0.44,
        event_confidence=0.66,
        fraud_result={
            "adjusted_fraud_score": 0.19,
            "raw_fraud_score": 0.27,
            "flags": ["cluster", "device"],
            "signals": {"cluster": 0.61, "device": 0.56},
            "ml_confidence": 0.77,
            "fallback_used": False,
        },
        trust_score=0.66,
        payout_amount=29,
    )
    assert result["decision"] == "delayed"
    assert result["inputs"]["device_micro_payout_approve"] is False
    assert result["breakdown"]["pattern_taxonomy"] == "cluster_combo_pressure"


def test_cluster_device_micro_lane_can_approve_tiny_high_confidence_combo():
    result = decision_engine.decide(
        disruption_score=0.67,
        event_confidence=0.94,
        fraud_result={
            "adjusted_fraud_score": 0.15,
            "raw_fraud_score": 0.24,
            "flags": ["cluster", "device"],
            "signals": {"cluster": 0.61, "device": 0.56},
            "ml_confidence": 0.83,
            "fallback_used": False,
        },
        trust_score=0.32,
        payout_amount=28,
    )
    assert result["decision"] == "approved"
    assert result["inputs"]["cluster_micro_resolved_approve"] is True
    assert result["breakdown"]["pattern_taxonomy"] == "cluster_micro_resolved"


def test_cluster_combo_pressure_still_blocks_larger_or_lower_confidence_combo():
    result = decision_engine.decide(
        disruption_score=0.61,
        event_confidence=0.76,
        fraud_result={
            "adjusted_fraud_score": 0.17,
            "raw_fraud_score": 0.25,
            "flags": ["cluster", "device"],
            "signals": {"cluster": 0.62, "device": 0.58},
            "ml_confidence": 0.81,
            "fallback_used": False,
        },
        trust_score=0.32,
        payout_amount=58,
    )
    assert result["decision"] == "delayed"
    assert result["inputs"]["cluster_micro_resolved_approve"] is False
    assert result["breakdown"]["pattern_taxonomy"] == "cluster_combo_pressure"


def test_policy_contract_exposes_layer_rule_and_guardrails():
    result = decision_engine.decide(
        disruption_score=0.55,
        event_confidence=0.63,
        fraud_result={
            "adjusted_fraud_score": 0.26,
            "raw_fraud_score": 0.34,
            "flags": ["movement", "pre_activity"],
            "signals": {"movement": 0.48, "pre_activity": 0.44},
            "ml_confidence": 0.76,
            "fallback_used": False,
        },
        trust_score=0.46,
        payout_amount=98,
    )
    assert result["policy_layer"] == "micro_payout_safe_lane"
    assert result["rule_id"] == "gray_band_low_payout_legit_approve"
    assert result["breakdown"]["policy_layer"] == result["policy_layer"]
    assert result["breakdown"]["rule_id"] == result["rule_id"]
    assert result["breakdown"]["guardrails"] == {
        "low_payout": 100,
        "high_payout": 200,
        "high_trust": 0.75,
        "low_confidence": 0.45,
        "gray_band_low": 0.60,
        "gray_band_high": 0.65,
    }
    assert result["inputs"]["low_payout_threshold"] == 100
    assert result["inputs"]["high_payout_threshold"] == 200
    assert result["inputs"]["high_trust_threshold"] == 0.75
    assert result["inputs"]["low_confidence_threshold"] == 0.45
    assert result["inputs"]["gray_band_low"] == 0.60
    assert result["inputs"]["gray_band_high"] == 0.65


def test_cluster_context_is_emitted_and_used_for_strong_review_routing():
    result = decision_engine.decide(
        disruption_score=0.44,
        event_confidence=0.66,
        fraud_result={
            "adjusted_fraud_score": 0.19,
            "raw_fraud_score": 0.27,
            "flags": ["cluster", "device"],
            "signals": {"cluster": 0.61, "device": 0.56},
            "ml_confidence": 0.77,
            "fallback_used": False,
        },
        trust_score=0.66,
        payout_amount=29,
    )
    assert result["decision"] == "delayed"
    assert result["breakdown"]["cluster_type"] == "fraud_ring"
    assert result["breakdown"]["cluster_routing"] == "strong_review"
    assert result["breakdown"]["cluster_raw_penalty_active"] is False
    assert result["breakdown"]["strong_flag_count"] == 0


def test_explicit_gray_band_surface_can_route_low_payout_clean_case():
    result = decision_engine.decide(
        disruption_score=0.55,
        event_confidence=0.61,
        fraud_result={
            "adjusted_fraud_score": 0.28,
            "raw_fraud_score": 0.35,
            "flags": [],
            "signals": {},
            "ml_confidence": 0.67,
            "fallback_used": False,
        },
        trust_score=0.52,
        payout_amount=70,
    )
    assert 0.60 <= result["final_score"] < 0.65
    assert result["decision"] == "approved"
    assert result["policy_layer"] == "micro_payout_safe_lane"
    assert result["rule_id"] == "gray_band_low_payout_legit_approve"
    assert result["breakdown"]["rule_metadata"]["surface"] == "low_payout_legit_surface"


def test_uncertainty_rule_metadata_is_present_and_exclusive():
    result = decision_engine.decide(
        disruption_score=0.79,
        event_confidence=0.49,
        fraud_result={
            "adjusted_fraud_score": 0.18,
            "raw_fraud_score": 0.26,
            "flags": ["movement", "pre_activity"],
            "signals": {"movement": 0.52, "pre_activity": 0.49},
            "ml_confidence": 0.52,
            "fallback_used": False,
        },
        trust_score=0.61,
        payout_amount=102,
    )
    assert result["decision"] == "delayed"
    assert result["rule_id"] == "uncertainty_silent_conflict_review"
    assert result["breakdown"]["rule_metadata"] == {
        "purpose": "Escalate low-agreement borderline cases.",
        "surface": "uncertainty_silent_conflict",
        "risk_expectation": "protect_from_bad_automation",
    }
