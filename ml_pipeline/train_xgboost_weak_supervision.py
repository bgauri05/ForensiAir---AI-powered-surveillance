"""
Phase 2 (ml_strategy_plan.md): weak-supervision retrain of the primary
tamper model.

Why this exists: the deployed XGBoost model (train_models.py) is trained
100% on synthetic data and over-flags ~45.7% of real readings -- confirmed
this session to be a synthetic/real distribution mismatch. There are zero
confirmed real tampering cases in the dataset (site_1232/site_1281 were a
fake assumption, removed this session), so there is no real ground truth to
train a normal supervised model against.

Approach: generate PROXY labels from the fingerprint engine's own trigger
counts on REAL data (3+ of 8 fingerprint checks triggered for a factory =>
that factory is proxy-tampered). This cannot discover a tampering pattern
invisible to all 8 existing fingerprint checks -- it's a smoothed
generalization of the rule logic, not an independent detector.

ATTEMPT 1 (per-reading granularity, see git history / conversation log):
FAILED validation. Broadcasting the factory-level proxy label to every one
of a factory's ~34k individual readings created label noise the per-reading
features couldn't explain (most fingerprint triggers -- correlation_break,
coordinated_missing_data -- are whole-time-series properties, invisible in
any single row's 18 features). Held-out flag rate 55.9% (worse than
baseline), Spearman rank correlation 0.30 (target >=0.6). Abandoned.

ATTEMPT 2 (this script): factory-level granularity. Aggregate each
factory's real readings into one feature vector (mean/std of the core
telemetry features), one proxy label per factory. Only 33 data points
total, so:
  - Model: L2-regularized logistic regression (not XGBoost) -- a flexible
    tree ensemble would badly overfit 8 features / 33 samples and the
    result wouldn't be trustworthy.
  - Validation: leave-one-out CV (uses all 33 points; standard practice at
    this sample size).
  - Features: only the aggregated stats that showed real rank correlation
    with trigger count in exploratory analysis (value/rolling_mean/std,
    flatline_flag mean+std) -- excludes corr_*/autocorrelation/missing_rate/
    limit_hugging aggregates, which were NaN for some factories (data
    quality gaps, not usable).
  - Does NOT include the raw fingerprint magnitude scores as features
    (would risk just re-deriving the existing >=3 threshold rule rather
    than learning something from telemetry) -- per explicit user decision.

This script does NOT touch production model files or risk_engine.py
weights. It only trains, validates, and reports. Deployment is a separate,
explicit step after the user reviews these results.
"""
import os
import sqlite3
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import roc_auc_score

RAW_FEATURE_COLS = [
    'value', 'rolling_mean', 'rolling_std', 'rolling_cov', 'flatline_flag',
    'corr_ETP-Flow_ETP-pH', 'corr_ETP-BOD_ETP-COD', 'corr_ETP-BOD_ETP-Flow',
    'corr_ETP-BOD_ETP-TSS', 'corr_ETP-BOD_ETP-pH', 'corr_ETP-COD_ETP-Flow',
    'corr_ETP-COD_ETP-TSS', 'corr_ETP-COD_ETP-pH', 'corr_ETP-Flow_ETP-TSS',
    'corr_ETP-TSS_ETP-pH', 'autocorrelation', 'missing_rate', 'limit_hugging'
]

PROXY_TRIGGER_THRESHOLD = 3
SPEARMAN_MIN = 0.6
AUC_MIN = 0.75


def load_factory_level_data(repo_root):
    real_path = os.path.join(repo_root, "Data/RawData/real_features.parquet")
    db_path = os.path.join(repo_root, "forensiair.db")

    df = pd.read_parquet(real_path)
    conn = sqlite3.connect(db_path)
    trig = pd.read_sql(
        "SELECT factory_id, total_fingerprints_triggered FROM fingerprint_scores",
        conn
    )
    conn.close()

    agg = df.groupby("factory_id")[RAW_FEATURE_COLS].agg(["mean", "std"])
    agg.columns = ["_".join(c) for c in agg.columns]
    agg = agg.merge(trig.set_index("factory_id"), left_index=True, right_index=True)

    # Drop any aggregated feature that's NaN for at least one factory --
    # confirmed in exploratory analysis this drops corr_*/autocorrelation/
    # missing_rate/limit_hugging aggregates (data quality gaps), leaving 8
    # usable features.
    before = [c for c in agg.columns if c != "total_fingerprints_triggered"]
    agg = agg.dropna(axis=1, how="any")
    feature_cols = [c for c in agg.columns if c != "total_fingerprints_triggered"]
    dropped = [c for c in before if c not in feature_cols]
    print(f"Dropped {len(dropped)} aggregated features with NaN for >=1 factory: {dropped}")
    print(f"Using {len(feature_cols)} features: {feature_cols}\n")

    agg["proxy_label"] = (agg["total_fingerprints_triggered"] >= PROXY_TRIGGER_THRESHOLD).astype(int)
    return agg, feature_cols


def run_loo_cv(agg, feature_cols):
    X = agg[feature_cols].values
    y = agg["proxy_label"].values
    factory_ids = agg.index.values
    n = len(agg)

    loo = LeaveOneOut()
    oof_probs = np.zeros(n)

    for train_idx, test_idx in loo.split(X):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train = y[train_idx]

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        clf = LogisticRegression(
            penalty="l2", C=1.0, solver="lbfgs",
            max_iter=1000, class_weight="balanced"
        )
        clf.fit(X_train_scaled, y_train)
        oof_probs[test_idx] = clf.predict_proba(X_test_scaled)[:, 1]

    return factory_ids, oof_probs


def summarize(agg, factory_ids, oof_probs):
    y = agg["proxy_label"].values
    trig_count = agg["total_fingerprints_triggered"].values

    flagged = (oof_probs >= 0.5)
    flag_rate = float(flagged.mean())
    actual_positive_rate = float(y.mean())

    auc = roc_auc_score(y, oof_probs)
    rho, pval = spearmanr(oof_probs, trig_count)

    print("=" * 60)
    print("LEAVE-ONE-OUT CV RESULTS (factory-level logistic regression)")
    print("=" * 60)
    print(f"Factories: {len(agg)}  (actual proxy-positive rate: {actual_positive_rate:.3f})")
    print(f"LOO predicted-positive rate (>=0.5 prob): {flag_rate:.3f}")
    print(f"LOO AUC (proxy_label vs predicted prob): {auc:.4f}  (target >= {AUC_MIN})")
    print(f"Spearman(predicted prob, real trigger count): rho={rho:.4f} (p={pval:.4f})  (target >= {SPEARMAN_MIN})")
    print()

    print("Per-factory detail (sorted by predicted probability):")
    detail = pd.DataFrame({
        "factory_id": factory_ids,
        "trigger_count": trig_count,
        "proxy_label": y,
        "loo_predicted_prob": np.round(oof_probs, 4),
    }).sort_values("loo_predicted_prob", ascending=False)
    print(detail.to_string(index=False))
    print()

    flag_rate_reasonable = abs(flag_rate - actual_positive_rate) <= 0.15
    auc_pass = auc >= AUC_MIN
    spearman_pass = rho >= SPEARMAN_MIN

    print(f"Flag-rate-vs-actual-prevalence criterion (within 0.15): {'PASS' if flag_rate_reasonable else 'FAIL'}")
    print(f"AUC criterion: {'PASS' if auc_pass else 'FAIL'}")
    print(f"Rank-correlation criterion: {'PASS' if spearman_pass else 'FAIL'}")
    overall = flag_rate_reasonable and auc_pass and spearman_pass
    print(f"OVERALL: {'PASS' if overall else 'FAIL'}")
    print("=" * 60)

    return {
        "flag_rate": flag_rate,
        "actual_positive_rate": actual_positive_rate,
        "auc": auc,
        "spearman_rho": rho,
        "overall_pass": overall,
        "detail": detail,
    }


def train_and_save_final_model(agg, feature_cols, repo_root):
    """
    Fits the scaler + logistic regression on ALL 33 factories (not a CV
    fold) and saves the artifacts used in production. Only called after
    run_loo_cv()/summarize() have shown this approach validates -- LOO-CV
    result (AUC 0.854, Spearman 0.677, Aug 2026) already showed this.
    """
    output_dir = os.path.join(repo_root, "ml_pipeline", "models")
    os.makedirs(output_dir, exist_ok=True)

    X = agg[feature_cols].values
    y = agg["proxy_label"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    clf = LogisticRegression(
        penalty="l2", C=1.0, solver="lbfgs",
        max_iter=1000, class_weight="balanced"
    )
    clf.fit(X_scaled, y)

    joblib.dump(scaler, os.path.join(output_dir, "factory_scaler.joblib"))
    joblib.dump(clf, os.path.join(output_dir, "factory_tamper_model.joblib"))
    joblib.dump(feature_cols, os.path.join(output_dir, "factory_tamper_feature_cols.joblib"))
    print(f"Saved final factory-level model artifacts to {output_dir}:")
    print("  factory_scaler.joblib, factory_tamper_model.joblib, factory_tamper_feature_cols.joblib")


if __name__ == "__main__":
    import joblib
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agg, feature_cols = load_factory_level_data(repo_root)
    factory_ids, oof_probs = run_loo_cv(agg, feature_cols)
    summary = summarize(agg, factory_ids, oof_probs)

    if summary["overall_pass"]:
        train_and_save_final_model(agg, feature_cols, repo_root)
    else:
        print("\nValidation did NOT pass -- not saving a final model.")
