import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from backend.core.risk_model_service import RiskModelService
from backend.ml.train.generate_risk_data import generate_risk_dataset

def main():
    print("Generating 10,000 samples for evaluation...")
    df = generate_risk_dataset(n_samples=10000)
    
    print("Loading Model V1...")
    service_v1 = RiskModelService(artifact_dir="backend/ml/artifacts_v1")
    
    print("Loading Model V2...")
    service_v2 = RiskModelService(artifact_dir="backend/ml/artifacts_v2")
    
    results_v1 = []
    results_v2 = []
    
    print("Predicting on samples...")
    samples = df.to_dict('records')
    for sample in samples:
        score_v1 = service_v1.score(sample)
        score_v2 = service_v2.score(sample)
        results_v1.append(score_v1['risk_score'])
        results_v2.append(score_v2['risk_score'])
        
    df['score_v1'] = results_v1
    df['score_v2'] = results_v2
    df['diff'] = df['score_v2'] - df['score_v1']
    
    print(f"Mean V1: {np.mean(results_v1):.4f}")
    print(f"Mean V2: {np.mean(results_v2):.4f}")
    print(f"Mean Absolute Error (Shift): {np.mean(np.abs(df['diff'])):.4f}")
    
    plt.figure(figsize=(12, 5))
    
    plt.subplot(1, 2, 1)
    sns.kdeplot(df['score_v1'], label="Model V1", fill=True, color='blue', alpha=0.3)
    sns.kdeplot(df['score_v2'], label="Model V2", fill=True, color='red', alpha=0.3)
    plt.title("Risk Score Distribution Comparison")
    plt.xlabel("Risk Score")
    plt.ylabel("Density")
    plt.legend()
    
    plt.subplot(1, 2, 2)
    plt.scatter(df['score_v1'], df['score_v2'], alpha=0.1, color='purple', s=2)
    plt.plot([0, 1], [0, 1], 'k--', lw=1)
    plt.title("V1 vs V2 Prediction Correlation")
    plt.xlabel("Model V1 Prediction")
    plt.ylabel("Model V2 Prediction")
    
    plt.tight_layout()
    chart_path = r"C:\Users\satvi\.gemini\antigravity\brain\89aea30a-c491-456c-9c39-9db1d849aa26\model_comparison.png"
    plt.savefig(chart_path, dpi=300)
    print(f"Chart saved to {chart_path}")

if __name__ == "__main__":
    main()
