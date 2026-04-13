"""Runtime orchestration for risk-model scoring with rule fallback."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.config import settings
from backend.ml.features.risk_features import risk_feature_builder
from backend.ml.risk_model import RiskModel


class RiskModelService:
    def __init__(self, artifact_dir: str | None = None) -> None:
        self.artifact_dir = Path(
            artifact_dir
            or settings.RISK_ML_ARTIFACT_DIR
            or settings.ML_ARTIFACT_DIR
        )
        self.model = RiskModel()
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
        bundle = risk_feature_builder.build(context)
        if not self.model_available:
            return {
                "available": False,
                "fallback_used": True,
                "model_version": "rule-based",
                "confidence": 0.0,
                "features": bundle.features,
                "explanation": risk_feature_builder.explain(bundle.features),
                "last_error": self.last_error,
            }

        prediction = self.model.predict(bundle.vector)
        return {
            "available": True,
            "fallback_used": False,
            "model_version": prediction.model_version,
            "confidence": prediction.confidence,
            "risk_score": prediction.risk_score,
            "features": bundle.features,
            "explanation": risk_feature_builder.explain(bundle.features),
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


risk_model_service = RiskModelService()
