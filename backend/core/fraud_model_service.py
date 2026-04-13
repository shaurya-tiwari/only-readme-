"""Runtime orchestration for fraud-model scoring with rule fallback."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.config import settings
from backend.ml.features.fraud_features import fraud_feature_builder
from backend.ml.fraud_model import FraudModel


class FraudModelService:
    def __init__(self, artifact_dir: str | None = None) -> None:
        self.artifact_dir = Path(
            artifact_dir
            or settings.FRAUD_ML_ARTIFACT_DIR
            or settings.ML_ARTIFACT_DIR
        )
        self.model = FraudModel()
        self.model_available = False
        self.last_error: str | None = None
        self.reload()

    def reload(self) -> None:
        if not settings.ML_ENABLED:
            self.model_available = False
            self.last_error = "ml disabled"
            return
        self.model_available = self.model.load(str(self.artifact_dir))
        self.last_error = self.model.last_error

    def score(self, context: dict[str, Any]) -> dict[str, Any]:
        bundle = fraud_feature_builder.build(context)
        if not self.model_available:
            return {
                "available": False,
                "fallback_used": True,
                "model_version": "rule-based",
                "confidence": 0.0,
                "fraud_probability": None,
                "ml_fraud_score": None,
                "features": bundle.features,
                "top_factors": fraud_feature_builder.explain(bundle.features),
                "last_error": self.last_error,
            }

        prediction = self.model.predict(bundle.vector)
        return {
            "available": True,
            "fallback_used": False,
            "model_version": prediction.model_version,
            "confidence": prediction.confidence,
            "fraud_probability": prediction.fraud_probability,
            "ml_fraud_score": prediction.fraud_score,
            "features": bundle.features,
            "top_factors": fraud_feature_builder.explain(bundle.features, prediction.feature_importance),
            "last_error": None,
            "scored_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_model_info(self) -> dict[str, Any]:
        status = "active" if self.model_available else "rule_based_fallback"
        metadata = self.model.metadata if self.model_available else {}
        return {
            "status": status,
            "version": metadata.get("version", "rule-based"),
            "trained_at": metadata.get("trained_at"),
            "metrics": metadata.get("metrics", {}),
            "model_type": metadata.get("model_type"),
            "n_samples": metadata.get("n_samples"),
            "artifact_dir": str(self.artifact_dir),
            "last_error": self.last_error,
            "fallback_used": not self.model_available,
        }


fraud_model_service = FraudModelService()
