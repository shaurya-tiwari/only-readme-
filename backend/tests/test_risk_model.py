"""Tests for risk model service and fallback behavior."""

from backend.core.risk_model_service import RiskModelService
from backend.ml.train.train_risk_model import train_risk_model


def test_risk_model_service_falls_back_without_artifact():
    service = RiskModelService(artifact_dir="backend/ml/artifacts/does-not-exist")
    result = service.score({"city": "mumbai", "month": 7, "zone_profile_risk": 0.7})
    assert result["fallback_used"] is True
    assert result["model_version"] == "rule-based"
    assert "features" in result


def test_risk_model_service_loads_trained_artifact(tmp_path):
    train_risk_model(output_dir=str(tmp_path))
    service = RiskModelService(artifact_dir=str(tmp_path))
    result = service.score({"city": "mumbai", "month": 7, "zone_profile_risk": 0.8, "incidents_7d": 6})
    assert result["fallback_used"] is False
    assert 0 <= result["risk_score"] <= 1
    assert result["model_version"] == "risk-model-v2"
    assert len(result["explanation"]) > 0

