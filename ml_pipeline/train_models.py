import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

FEATURE_COLS = [
    'value', 'rolling_mean', 'rolling_std', 'rolling_cov', 'flatline_flag',
    'corr_ETP-Flow_ETP-pH', 'corr_ETP-BOD_ETP-COD', 'corr_ETP-BOD_ETP-Flow',
    'corr_ETP-BOD_ETP-TSS', 'corr_ETP-BOD_ETP-pH', 'corr_ETP-COD_ETP-Flow',
    'corr_ETP-COD_ETP-TSS', 'corr_ETP-COD_ETP-pH', 'corr_ETP-Flow_ETP-TSS',
    'corr_ETP-TSS_ETP-pH', 'autocorrelation', 'missing_rate', 'limit_hugging'
]

# QC FIX (2026-08, Phase 2): this script used to also train a supervised
# XGBoost classifier on Data/SynData/synthetic_features.parquet (100%
# synthetic features AND labels). It was retired -- over-flagged 45.7% of
# real readings due to a synthetic/real distribution mismatch (e.g.
# rolling_cov: synthetic-normal median 0.065 vs real median 0.002, a ~32x
# gap) -- and a weak-supervision retrain attempt at the same per-reading
# granularity also failed validation. It's been replaced by a factory-level
# model trained on real telemetry with proxy labels from the fingerprint
# engine; see ml_pipeline/train_xgboost_weak_supervision.py, which is now a
# separate, standalone training script (produces factory_scaler.joblib,
# factory_tamper_model.joblib, factory_tamper_feature_cols.joblib). Run that
# script after this one if those artifacts need refreshing.
#
# This script now only trains Isolation Forest, which never needed
# synthetic data -- it's unsupervised and only ever needed realistic
# examples of "normal," which real telemetry already provides.


def train():
    output_dir = os.path.join(os.path.dirname(__file__), "models")
    os.makedirs(output_dir, exist_ok=True)

    print("--- 1. Training Isolation Forest on Real Features ---")
    real_path = "Data/RawData/real_features.parquet"
    if not os.path.exists(real_path):
        real_path = os.path.join("..", real_path)
    df_real = pd.read_parquet(real_path)

    X_real = df_real[FEATURE_COLS].copy()
    X_real = X_real.fillna(X_real.median())

    iso_scaler = StandardScaler()
    X_real_scaled = iso_scaler.fit_transform(X_real)

    sample_idx = np.random.choice(len(X_real_scaled), size=min(100000, len(X_real_scaled)), replace=False)
    iso_forest = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42,
        n_jobs=-1
    )
    iso_forest.fit(X_real_scaled[sample_idx])

    print("\n--- 2. Saving Artifacts ---")
    joblib.dump(iso_scaler, os.path.join(output_dir, "iso_scaler.joblib"))
    joblib.dump(iso_forest, os.path.join(output_dir, "iso_forest.joblib"))
    joblib.dump(FEATURE_COLS, os.path.join(output_dir, "feature_cols.joblib"))

    print(f"Successfully saved Isolation Forest artifacts to {output_dir}")
    print("NOTE: run train_xgboost_weak_supervision.py separately for the "
          "factory-level tamper model (factory_scaler.joblib, "
          "factory_tamper_model.joblib, factory_tamper_feature_cols.joblib).")

if __name__ == "__main__":
    train()
