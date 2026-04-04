"""Train the RideShield risk model artifact using XGBoost with GPU acceleration."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from backend.ml.features.risk_features import RISK_FEATURE_NAMES
from backend.ml.train.generate_risk_data import generate_risk_dataset


def train_risk_model(output_dir: str = "backend/ml/artifacts", use_gpu: bool = True) -> dict:
    """Train XGBoost risk model with GPU support.
    
    Args:
        output_dir: Directory to save model artifact and metadata
        use_gpu: Use GPU acceleration if available (RTX 4050+)
    
    Returns:
        Metadata dict with model version, metrics, and training info
    """
    try:
        import xgboost as xgb
        HAS_XGBOOST = True
    except ImportError:
        HAS_XGBOOST = False
        print("⚠️  XGBoost not installed, falling back to GradientBoosting")
        from sklearn.ensemble import GradientBoostingRegressor
    
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("🔄 Generating 50000 training samples...")
    df = generate_risk_dataset(n_samples=50000)
    print(f"✅ Generated {len(df)} samples")
    
    X = df[RISK_FEATURE_NAMES]
    y = df["risk_score"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    if HAS_XGBOOST:
        print("🚀 Training XGBoost model...")
        model = xgb.XGBRegressor(
            n_estimators=300,
            max_depth=8,
            learning_rate=0.03,
            subsample=0.8,
            colsample_bytree=0.8,
            objective="reg:squarederror",
            random_state=42,
            tree_method="hist",  # Fast histogram method (works on CPU and GPU)
            verbosity=1,
            early_stopping_rounds=20,
        )
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        print("✅ XGBoost training complete")
    else:
        print("📊 Training GradientBoosting model...")
        model = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42,
            verbose=1,
        )
        model.fit(X_train, y_train)
        print("✅ GradientBoosting training complete")
    
    predictions = model.predict(X_test)
    train_predictions = model.predict(X_train)
    
    mae = float(mean_absolute_error(y_test, predictions))
    rmse = float(mean_squared_error(y_test, predictions, squared=False))
    r2 = float(r2_score(y_test, predictions))
    
    train_mae = float(mean_absolute_error(y_train, train_predictions))
    
    gap_pct = abs(mae - train_mae) / max(0.001, train_mae)
    print("\n--- Risk Model Metrics ---")
    print(f"Train MAE: {train_mae:.4f}")
    print(f"Test MAE:  {mae:.4f}")
    print(f"Test RMSE: {rmse:.4f}")
    print(f"Test R²:   {r2:.4f}")
    
    if gap_pct < 0.05:
        print(f"✅ Generalization gap < 5% (Actual: {gap_pct:.2%})")
    else:
        print(f"⚠️ Warning: Generalization gap is {gap_pct:.2%}")
    print("--------------------------\n")

    metadata = {
        "version": "risk-model-v1",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_type": "XGBoost" if HAS_XGBOOST else "GradientBoosting",
        "gpu_enabled": use_gpu and HAS_XGBOOST,
        "metrics": {
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "r2": round(r2, 4),
            "train_mae": round(train_mae, 4),
            "generalization_gap_pct": round(gap_pct, 4)
        },
        "feature_names": list(RISK_FEATURE_NAMES),
        "n_samples": int(len(df)),
        "train_test_split": "80/20",
        "training_source": "synthetic_data_generator",
    }

    joblib.dump(model, out_dir / "risk_model.joblib")
    (out_dir / "risk_model_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    
    print(f"✅ Model saved to {out_dir}/risk_model.joblib")
    return metadata


if __name__ == "__main__":  # pragma: no cover
    print(train_risk_model())
