"""Smoke tests for fraud model training and runtime loading."""

from backend.core.fraud_model_service import FraudModelService
from backend.ml.train.train_fraud_model import train_fraud_model


def test_train_and_load_fraud_model(tmp_path):
    metadata = train_fraud_model(output_dir=str(tmp_path))
    assert metadata["version"] == "fraud-model-v2"
    assert metadata["metrics"]["roc_auc"] > 0.5
    assert metadata["metrics"]["roc_auc"] < 1.0

    service = FraudModelService(artifact_dir=str(tmp_path))
    result = service.score(
        {
            "duplicate_signal": 0.0,
            "movement_signal": 0.2,
            "device_signal": 0.1,
            "cluster_signal": 0.1,
            "timing_signal": 0.05,
            "income_inflation_signal": 0.1,
            "pre_activity_signal": 0.1,
            "trust_score": 0.8,
            "account_age_days": 90,
            "income_ratio": 1.1,
            "activity_count": 6,
            "recent_claims_count": 1,
            "cluster_claims_count": 1,
            "policy_age_hours": 72,
            "event_severity_norm": 0.6,
            "event_confidence_norm": 0.9,
        }
    )

    assert result["available"] is True
    assert result["fallback_used"] is False
    assert 0.0 <= result["fraud_probability"] <= 1.0
    assert result["model_version"] == "fraud-model-v2"
    assert result["top_factors"]
