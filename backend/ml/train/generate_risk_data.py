"""Generate synthetic training data for the RideShield risk model."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.config import settings
from backend.ml.features.risk_features import risk_feature_builder


def generate_risk_dataset(n_samples: int = 5000) -> pd.DataFrame:
    """Generate 5000+ diverse risk training samples covering all cities, zones, and seasonal patterns."""
    import numpy as np
    np.random.seed(42)
    
    rows: list[dict] = []
    months = list(range(1, 13))  # All 12 months for better seasonal coverage
    
    total_zones = sum(len(profile["zones"]) for profile in settings.CITY_RISK_PROFILES.values())
    total_combos = total_zones * len(months)
    samples_per_combo = max(1, n_samples // total_combos)
    
    for city, profile in settings.CITY_RISK_PROFILES.items():
        for zone_idx, zone in enumerate(profile["zones"]):
            for month in months:
                for sample_idx in range(samples_per_combo):
                    # Add noise and variation to make data more realistic
                    noise_factor = np.random.uniform(0.8, 1.2)
                    seasonal_boost = 1.0 if month in {6, 7, 8, 9} else 0.7
                    
                    context = {
                        "city": city,
                        "month": month,
                        "city_base_risk": profile["base_risk"],
                        "zone_profile_risk": min(0.95, profile["base_risk"] + (zone_idx * 0.02)),
                        "incidents_7d": int(np.random.poisson(3 * noise_factor)),
                        "incidents_30d": int(np.random.poisson(10 * noise_factor)),
                        "rain_intensity": min(1.0, np.random.exponential(0.15) * seasonal_boost),
                        "heat_index": min(1.0, np.random.beta(2, 5) * (1.0 if month in {4, 5, 6} else 0.4)),
                        "aqi_normalized": min(1.0, np.random.exponential(0.20) * (1.3 if city == "delhi" else 0.8)),
                        "traffic_congestion": min(1.0, np.random.beta(2, 3)),
                        "platform_instability": min(1.0, np.random.exponential(0.10)),
                        "worker_density": min(1.0, np.random.beta(3, 4)),
                        "payout_pressure_30d": min(1.0, np.random.exponential(0.12)),
                    }
                    
                    bundle = risk_feature_builder.build(context)
                    
                    # Enhanced weighted scoring
                    score = (
                        0.20 * bundle.features["city_base_risk"]
                        + 0.10 * bundle.features["zone_profile_risk"]
                        + 0.12 * min(1.0, bundle.features["incidents_7d"] / 10.0)
                        + 0.08 * min(1.0, bundle.features["incidents_30d"] / 25.0)
                        + 0.14 * bundle.features["rain_intensity"]
                        + 0.09 * bundle.features["heat_index"]
                        + 0.07 * bundle.features["aqi_normalized"]
                        + 0.10 * bundle.features["traffic_congestion"]
                        + 0.05 * bundle.features["platform_instability"]
                        + 0.05 * bundle.features["worker_density"]
                    )
                    
                    rows.append({**bundle.features, "risk_score": round(max(0.02, min(0.98, score + np.random.normal(0, 0.03))), 3)})
    
    return pd.DataFrame(rows)


def save_default_dataset(output_path: str | None = None) -> Path:
    path = Path(output_path or "backend/ml/artifacts/risk_training_data.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    generate_risk_dataset().to_csv(path, index=False)
    return path


if __name__ == "__main__":  # pragma: no cover
    print(save_default_dataset())

