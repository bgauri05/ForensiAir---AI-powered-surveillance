"""
Precomputes real SHAP explanations for both components of the composite
risk score that have a trained model behind them:

  - factory_tamper_model.joblib (LogisticRegression, 10% weight): explained
    with shap.LinearExplainer -- clean, exact, instant (see Phase 2 findings).
  - iso_forest.joblib (IsolationForest, 22.5% weight): shap.TreeExplainer
    does NOT work for IsolationForest (its raw_value leaf-sum decomposition
    doesn't reconstruct score_samples() -- verified this diverges by ~12
    points, not a rounding difference). shap.KernelExplainer run directly
    against iso.score_samples DOES reconstruct it exactly. But the real
    per-factory IsolationForest score used in risk_engine.py is the MEAN of
    score_samples() across every real reading for that factory (see
    database/seed_db.py::score_factory) -- median 31k readings/factory, up
    to 92.7k, so explaining every reading live is intractable (est. 8+ min
    for a median factory at ~0.016s/reading). This script samples a fixed,
    seeded subset per factory and averages their SHAP values as a real,
    reproducible approximation of that mean.

Output: Data/RawData/factory_shap_explanations.json, keyed by factory_id.
Read by backend/main.py's /api/factories/{id}/shap endpoint. Rerun this
script whenever factory_tamper_model.joblib or iso_forest.joblib are
retrained.

This replaces Data/RawData/factory_shap_attributions.csv as the backing
data for that endpoint -- that file's 25-feature schema matches the old
Stage-2 model's feature set, which no longer exists anywhere in the app.
Left on disk untouched, just no longer read.
"""
import os
import json
import datetime
import warnings

import joblib
import numpy as np
import pandas as pd
import shap

warnings.filterwarnings("ignore")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(REPO_ROOT, "ml_pipeline", "models")
REAL_FEATURES_PATH = os.path.join(REPO_ROOT, "Data", "RawData", "real_features.parquet")
OUTPUT_PATH = os.path.join(REPO_ROOT, "Data", "RawData", "factory_shap_explanations.json")

RAW_FEATURE_COLS = [
    'value', 'rolling_mean', 'rolling_std', 'rolling_cov', 'flatline_flag',
    'corr_ETP-Flow_ETP-pH', 'corr_ETP-BOD_ETP-COD', 'corr_ETP-BOD_ETP-Flow',
    'corr_ETP-BOD_ETP-TSS', 'corr_ETP-BOD_ETP-pH', 'corr_ETP-COD_ETP-Flow',
    'corr_ETP-COD_ETP-TSS', 'corr_ETP-COD_ETP-pH', 'corr_ETP-Flow_ETP-TSS',
    'corr_ETP-TSS_ETP-pH', 'autocorrelation', 'missing_rate', 'limit_hugging'
]

LR_FEATURE_LABELS = {
    'value_mean': 'Reading value (mean)',
    'value_std': 'Reading value (std dev)',
    'rolling_mean_mean': 'Rolling mean (mean)',
    'rolling_mean_std': 'Rolling mean (std dev)',
    'rolling_std_mean': 'Rolling std dev (mean)',
    'rolling_std_std': 'Rolling std dev (std dev)',
    'flatline_flag_mean': 'Flatline flag rate',
    'flatline_flag_std': 'Flatline flag rate (std dev)',
}

IF_FEATURE_LABELS = {
    'value': 'Reading value',
    'rolling_mean': 'Rolling mean',
    'rolling_std': 'Rolling std dev',
    'rolling_cov': 'Rolling coefficient of variation',
    'flatline_flag': 'Flatline flag',
    'corr_ETP-Flow_ETP-pH': 'Correlation: Flow vs pH',
    'corr_ETP-BOD_ETP-COD': 'Correlation: BOD vs COD',
    'corr_ETP-BOD_ETP-Flow': 'Correlation: BOD vs Flow',
    'corr_ETP-BOD_ETP-TSS': 'Correlation: BOD vs TSS',
    'corr_ETP-BOD_ETP-pH': 'Correlation: BOD vs pH',
    'corr_ETP-COD_ETP-Flow': 'Correlation: COD vs Flow',
    'corr_ETP-COD_ETP-TSS': 'Correlation: COD vs TSS',
    'corr_ETP-COD_ETP-pH': 'Correlation: COD vs pH',
    'corr_ETP-Flow_ETP-TSS': 'Correlation: Flow vs TSS',
    'corr_ETP-TSS_ETP-pH': 'Correlation: TSS vs pH',
    'autocorrelation': 'Autocorrelation',
    'missing_rate': 'Missing-data rate',
    'limit_hugging': 'Limit-hugging flag',
}

IF_SAMPLE_SIZE = 150
IF_BACKGROUND_SIZE = 30
RANDOM_SEED = 42


def build_lr_explanations(df_real):
    lr = joblib.load(os.path.join(MODELS_DIR, "factory_tamper_model.joblib"))
    scaler = joblib.load(os.path.join(MODELS_DIR, "factory_scaler.joblib"))
    cols = joblib.load(os.path.join(MODELS_DIR, "factory_tamper_feature_cols.joblib"))

    agg = df_real.groupby("factory_id")[RAW_FEATURE_COLS].agg(["mean", "std"])
    agg.columns = ["_".join(c) for c in agg.columns]
    agg = agg.dropna(axis=1, how="any")
    agg = agg[cols]

    X_scaled = scaler.transform(agg.values)
    explainer = shap.LinearExplainer(lr, X_scaled)
    shap_values = explainer.shap_values(X_scaled)
    base_value = float(np.asarray(explainer.expected_value).reshape(-1)[0])

    probs = lr.predict_proba(X_scaled)[:, 1]

    out = {}
    for i, fid in enumerate(agg.index):
        features = []
        for j, col in enumerate(cols):
            features.append({
                "feature": col,
                "label": LR_FEATURE_LABELS.get(col, col),
                "raw_value": round(float(agg.iloc[i][col]), 4),
                "shap_value_logit": round(float(shap_values[i][j]), 4),
            })
        features.sort(key=lambda f: abs(f["shap_value_logit"]), reverse=True)
        out[fid] = {
            "base_value_logit": round(base_value, 4),
            "predicted_probability": round(float(probs[i]), 4),
            "features": features,
        }
    return out


def build_isolation_forest_explanations(df_real):
    iso = joblib.load(os.path.join(MODELS_DIR, "iso_forest.joblib"))
    iso_scaler = joblib.load(os.path.join(MODELS_DIR, "iso_scaler.joblib"))
    iso_cols = joblib.load(os.path.join(MODELS_DIR, "feature_cols.joblib"))

    # QC: matches ml_pipeline/inference.py's InferenceEngine.predict_batch
    # and database/seed_db.py's score_factory() -- both fillna(0.0) rather
    # than dropping rows, since only 7/33 factories have every one of the
    # 18 features (mostly corr_* columns) non-null simultaneously. Real
    # production anomaly_score_norm for every factory is already computed
    # this way; matching it here means the "mean_anomaly_score" in this
    # explanation equals the real number shown elsewhere in the app,
    # instead of a different number computed over a 7-factory subset.
    df_filled = df_real.copy()
    df_filled[iso_cols] = df_filled[iso_cols].fillna(0.0)
    X_all_scaled = iso_scaler.transform(df_filled[iso_cols].values)

    rng = np.random.RandomState(RANDOM_SEED)
    background_idx = rng.choice(len(X_all_scaled), size=min(IF_BACKGROUND_SIZE * 50, len(X_all_scaled)), replace=False)
    background = shap.kmeans(X_all_scaled[background_idx], IF_BACKGROUND_SIZE)

    explainer = shap.KernelExplainer(iso.score_samples, background)
    base_value = float(explainer.expected_value)

    out = {}
    factory_ids = sorted(df_filled["factory_id"].unique())
    for fid in factory_ids:
        fac_mask = (df_filled["factory_id"] == fid).values
        fac_idx = np.where(fac_mask)[0]
        n_available = len(fac_idx)
        sample_n = min(IF_SAMPLE_SIZE, n_available)
        sampled_idx = rng.choice(fac_idx, size=sample_n, replace=False)

        X_sample = X_all_scaled[sampled_idx]
        sv = explainer.shap_values(X_sample, nsamples=100, silent=True)
        sv_mean = np.asarray(sv).mean(axis=0)

        raw_means = df_filled.iloc[fac_idx][iso_cols].mean()
        mean_anomaly_score = float(iso.score_samples(X_all_scaled[fac_idx]).mean())

        features = []
        for j, col in enumerate(iso_cols):
            features.append({
                "feature": col,
                "label": IF_FEATURE_LABELS.get(col, col),
                "raw_value": round(float(raw_means[col]), 4),
                "shap_value": round(float(sv_mean[j]), 5),
            })
        features.sort(key=lambda f: abs(f["shap_value"]), reverse=True)

        out[fid] = {
            "base_value": round(base_value, 5),
            "mean_anomaly_score": round(mean_anomaly_score, 5),
            "n_readings_total": int(n_available),
            "n_readings_sampled": int(sample_n),
            "features": features,
        }
        print(f"  {fid}: {n_available} readings, sampled {sample_n}")
    return out


def main():
    print("Loading real telemetry features...")
    df_real = pd.read_parquet(REAL_FEATURES_PATH)

    print("Computing LinearExplainer SHAP for factory_tamper_model (LR)...")
    lr_explanations = build_lr_explanations(df_real)
    print(f"  done: {len(lr_explanations)} factories")

    print("Computing KernelExplainer SHAP for iso_forest (sampled per factory)...")
    iso_explanations = build_isolation_forest_explanations(df_real)
    print(f"  done: {len(iso_explanations)} factories")

    all_factory_ids = sorted(set(lr_explanations) | set(iso_explanations))
    payload = {
        "generated_at": datetime.datetime.now().isoformat(),
        "method": {
            "tamper_model": "shap.LinearExplainer, exact (logit space)",
            "isolation_forest": f"shap.KernelExplainer against iso.score_samples, seeded sample of up to {IF_SAMPLE_SIZE} readings/factory averaged (TreeExplainer verified non-additive for IsolationForest, not used)",
        },
        "factories": {
            fid: {
                "tamper_model_shap": lr_explanations.get(fid),
                "isolation_forest_shap": iso_explanations.get(fid),
            }
            for fid in all_factory_ids
        },
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\nSaved {len(all_factory_ids)} factory explanations to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
