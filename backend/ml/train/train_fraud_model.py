"""Train the RideShield fraud model artifact using synthetic scenario data."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from backend.ml.features.fraud_features import FRAUD_FEATURE_NAMES, fraud_feature_builder


def generate_fraud_dataset(n_samples: int = 50000) -> pd.DataFrame:
    import numpy as np

    np.random.seed(42)
    rows: list[dict[str, float | int]] = []

    for _ in range(n_samples):
        duplicate_signal = np.random.beta(1.1, 8.0)
        movement_signal = np.random.beta(2.2, 3.6)
        device_signal = np.random.beta(1.8, 4.8)
        cluster_signal = np.random.beta(2.0, 3.4)
        timing_signal = np.random.beta(1.7, 4.5)
        income_inflation_signal = np.random.beta(1.9, 4.0)
        pre_activity_signal = np.random.beta(2.1, 3.7)
        trust_score = np.random.beta(4.5, 2.8)
        account_age_days = int(np.random.gamma(shape=4.0, scale=28.0))
        recent_claims = int(np.random.poisson(1.8))
        cluster_claims = int(np.random.poisson(2.1))
        activity_count = int(np.random.randint(0, 10))
        policy_age_hours = int(np.random.gamma(shape=3.0, scale=18.0))
        income_ratio = float(np.random.uniform(0.8, 2.6))
        event_severity = float(np.random.uniform(0.35, 0.95))
        event_confidence = float(np.random.uniform(0.45, 0.98))

        latent_score = (
            0.14 * duplicate_signal
            + 0.13 * movement_signal
            + 0.10 * device_signal
            + 0.12 * cluster_signal
            + 0.12 * timing_signal
            + 0.11 * income_inflation_signal
            + 0.10 * pre_activity_signal
            + 0.08 * min(income_ratio / 2.5, 1.0)
            + 0.07 * min(cluster_claims / 7.0, 1.0)
            + 0.05 * (1.0 - min(account_age_days / 180.0, 1.0))
            - 0.10 * trust_score
            - 0.05 * min(activity_count / 8.0, 1.0)
            - 0.03 * event_confidence
        )
        latent_score += float(np.random.normal(0.0, 0.09))
        fraud_probability = 1.0 / (1.0 + np.exp(-((latent_score - 0.33) * 5.2)))
        is_fraud = int(np.random.random() < fraud_probability)

        # Inject controlled noise / edge cases (~6% of data)
        rand_edge = np.random.random()
        if rand_edge < 0.03:
            # 3% chance: Legit user but behaves like fraud (high movement/timing issues, low trust)
            is_fraud = 0
            duplicate_signal = float(np.random.uniform(0.6, 0.95))
            movement_signal = float(np.random.uniform(0.7, 1.0))
            trust_score = float(np.random.uniform(0.0, 0.25))
            timing_signal = float(np.random.uniform(0.6, 1.0))
        elif rand_edge < 0.06:
            # 3% chance: Fraud user with completely clean profile (sophisticated actor)
            is_fraud = 1
            duplicate_signal = float(np.random.uniform(0.0, 0.15))
            movement_signal = float(np.random.uniform(0.0, 0.2))
            trust_score = float(np.random.uniform(0.8, 1.0))
            pre_activity_signal = float(np.random.uniform(0.0, 0.1))

        # Add light class-conditioned drift after label sampling so classes overlap but remain learnable.
        if is_fraud:
            duplicate_signal = min(1.0, duplicate_signal + np.random.uniform(0.0, 0.22))
            movement_signal = min(1.0, movement_signal + np.random.uniform(0.02, 0.18))
            timing_signal = min(1.0, timing_signal + np.random.uniform(0.02, 0.18))
            pre_activity_signal = min(1.0, pre_activity_signal + np.random.uniform(0.01, 0.16))
            trust_score = max(0.0, trust_score - np.random.uniform(0.0, 0.18))
        else:
            trust_score = min(1.0, trust_score + np.random.uniform(0.0, 0.08))
            event_confidence = min(1.0, event_confidence + np.random.uniform(0.0, 0.05))

        context = {
            "duplicate_signal": duplicate_signal,
            "movement_signal": movement_signal,
            "device_signal": device_signal,
            "cluster_signal": cluster_signal,
            "timing_signal": timing_signal,
            "income_inflation_signal": income_inflation_signal,
            "pre_activity_signal": pre_activity_signal,
            "trust_score": trust_score,
            "account_age_days": account_age_days,
            "income_ratio": income_ratio,
            "activity_count": activity_count,
            "recent_claims_count": recent_claims,
            "cluster_claims_count": cluster_claims,
            "policy_age_hours": policy_age_hours,
            "event_severity_norm": event_severity,
            "event_confidence_norm": event_confidence,
        }
        bundle = fraud_feature_builder.build(context)
        rows.append({**bundle.features, "is_fraud": int(is_fraud)})

    return pd.DataFrame(rows)


def train_fraud_model(output_dir: str = "backend/ml/artifacts") -> dict:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = generate_fraud_dataset()
    X = df[FRAUD_FEATURE_NAMES]
    y = df["is_fraud"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=9,
        min_samples_leaf=15,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    train_probs = model.predict_proba(X_train)[:, 1]
    train_preds = (train_probs >= 0.5).astype(int)
    test_probs = model.predict_proba(X_test)[:, 1]
    test_preds = (test_probs >= 0.5).astype(int)

    train_auc = float(roc_auc_score(y_train, train_probs))
    test_auc = float(roc_auc_score(y_test, test_probs))
    train_acc = float((train_preds == y_train).mean())
    test_acc = float((test_preds == y_test).mean())
    precision = float(precision_score(y_test, test_preds, zero_division=0))
    recall = float(recall_score(y_test, test_preds, zero_division=0))
    avg_prec = float(average_precision_score(y_test, test_probs))

    print(f"\n--- Fraud Model Metrics ({len(df)} samples) ---")
    print(f"Train Accuracy: {train_acc:.4f}")
    print(f"Test Accuracy:  {test_acc:.4f}")
    print(f"Train ROC AUC:  {train_auc:.4f}")
    print(f"Test ROC AUC:   {test_auc:.4f}")
    print(f"Precision:      {precision:.4f}")
    print(f"Recall:         {recall:.4f}")

    gap = train_acc - test_acc
    if abs(gap) < 0.05:
        print(f"✅ Generalization gap < 5% (Actual gap: {abs(gap):.2%})")
    else:
        print(f"⚠️ Warning: Generalization gap is {abs(gap):.2%}")
    print("------------------------------------------\n")

    importance = {
        name: round(float(value), 4)
        for name, value in sorted(
            zip(FRAUD_FEATURE_NAMES, model.feature_importances_, strict=False),
            key=lambda item: item[1],
            reverse=True,
        )
    }

    metadata = {
        "version": "fraud-model-v2",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_type": "RandomForestClassifier",
        "metrics": {
            "roc_auc": round(test_auc, 4),
            "average_precision": round(avg_prec, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "train_acc": round(train_acc, 4),
            "test_acc": round(test_acc, 4),
            "generalization_gap": round(abs(gap), 4),
        },
        "feature_names": list(FRAUD_FEATURE_NAMES),
        "feature_importance": importance,
        "n_samples": int(len(df)),
        "positive_rate": round(float(df["is_fraud"].mean()), 4),
        "train_test_split": "80/20",
        "training_source": "synthetic_scenario_generator",
    }

    joblib.dump(model, out_dir / "fraud_model.joblib")
    (out_dir / "fraud_model_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


if __name__ == "__main__":  # pragma: no cover
    print(train_fraud_model())
