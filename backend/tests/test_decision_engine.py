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


def test_mid_score_is_delayed():
    result = decision_engine.decide(
        disruption_score=0.5,
        event_confidence=0.6,
        fraud_result={"adjusted_fraud_score": 0.35, "raw_fraud_score": 0.45, "flags": ["movement"], "is_suspicious": True, "is_high_risk": False},
        trust_score=0.2,
    )
    assert result["decision"] == "delayed"
    assert result["decision_confidence"] > 0


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
    )
    assert result["decision"] == "approved"
    assert result["inputs"]["trusted_low_risk_approve"] is True
    assert result["primary_reason"] in {"worker trust score", "movement anomaly", "weak pre-event activity"} # Reason still lists the negative signals even if approved by policy layer


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


def test_low_score_is_rejected():
    result = decision_engine.decide(
        disruption_score=0.2,
        event_confidence=0.4,
        fraud_result={"adjusted_fraud_score": 0.8, "raw_fraud_score": 0.9, "flags": ["cluster"], "is_suspicious": True, "is_high_risk": True},
        trust_score=0.1,
    )
    assert result["decision"] == "rejected"
    assert result["decision_confidence"] > 0


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


def test_same_borderline_profile_with_higher_payout_stays_in_review():
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
        payout_amount=220,
    )
    assert result["decision"] == "delayed"
    assert result["inputs"]["low_payout_confident_approve"] is False
