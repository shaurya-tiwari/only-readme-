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


def test_mid_score_is_delayed():
    result = decision_engine.decide(
        disruption_score=0.5,
        event_confidence=0.6,
        fraud_result={"adjusted_fraud_score": 0.35, "raw_fraud_score": 0.45, "flags": ["movement"], "is_suspicious": True, "is_high_risk": False},
        trust_score=0.2,
    )
    assert result["decision"] == "delayed"


def test_low_score_is_rejected():
    result = decision_engine.decide(
        disruption_score=0.2,
        event_confidence=0.4,
        fraud_result={"adjusted_fraud_score": 0.8, "raw_fraud_score": 0.9, "flags": ["cluster"], "is_suspicious": True, "is_high_risk": True},
        trust_score=0.1,
    )
    assert result["decision"] == "rejected"
