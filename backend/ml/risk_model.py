"""Runtime loader for the RideShield risk model artifact."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd


logger = logging.getLogger(__name__)

@dataclass
class RiskPrediction:
    risk_score: float
    model_version: str
    confidence: float


class RiskModel:
    def __init__(self) -> None:
        self.model = None
        self.metadata: dict[str, Any] = {}
        self.available = False
        self.last_error: str | None = None

    def load(self, artifact_dir: str) -> bool:
        model_path = Path(artifact_dir) / "risk_model.joblib"
        metadata_path = Path(artifact_dir) / "risk_model_metadata.json"
        if not model_path.exists() or not metadata_path.exists():
            self.available = False
            self.last_error = "risk model artifact missing"
            return False

        try:
            self.model = joblib.load(model_path)
            self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            version = self.metadata.get("version", "unknown")
            logger.info(f"Successfully loaded Risk Model: {version}")
            self.available = True
            self.last_error = None
            return True
        except Exception as exc:  # pragma: no cover - defensive load path
            self.available = False
            self.last_error = str(exc)
            return False

    def predict(self, vector: list[float]) -> RiskPrediction:
        if not self.available or self.model is None:
            raise RuntimeError("risk model unavailable")
        feature_names = self.metadata.get("feature_names")
        payload = pd.DataFrame([vector], columns=feature_names) if feature_names else [vector]
        raw = self.model.predict(payload)[0]
        score = max(0.02, min(0.98, float(raw)))
        confidence = float(self.metadata.get("metrics", {}).get("r2", 0.6))
        return RiskPrediction(
            risk_score=round(score, 3),
            model_version=str(self.metadata.get("version", "risk-model")),
            confidence=max(0.0, min(1.0, confidence)),
        )
