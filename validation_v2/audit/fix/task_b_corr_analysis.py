import os
import joblib
import pandas as pd
import numpy as np

REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
PARQUET_PATH = os.path.join(REPO_ROOT, "Data", "RawData", "real_features.parquet")
MODELS_DIR = os.path.join(REPO_ROOT, "ml_pipeline", "models")
FEATURE_COLS_PATH = os.path.join(MODELS_DIR, "feature_cols.joblib")

def run_task_b():
    print("==========================================================================")
    print(" TASK B: CORRELATION FEATURES ANALYSIS (corr_nan_by_factory.csv)")
    print("==========================================================================")

    df_pq = pd.read_parquet(PARQUET_PATH)
    print(f"Loaded real_features.parquet: Shape {df_pq.shape}")
    print("Columns:", list(df_pq.columns))

    corr_cols = [c for c in df_pq.columns if c.startswith("corr_")]
    print(f"Found {len(corr_cols)} correlation columns: {corr_cols}")

    # Inspect parameter presence per factory in parquet
    fac_params = {}
    for fac, grp in df_pq.groupby("factory_id"):
        fac_params[fac] = set(grp["parameter_id"].unique())

    corr_nan_rows = []

    for fac, grp in df_pq.groupby("factory_id"):
        fac_p_set = fac_params[fac]
        n_fac_rows = len(grp)

        for col in corr_cols:
            # Parse the two parameters from column name corr_P1_P2
            parts = col.replace("corr_", "").split("_")
            p1 = parts[0]
            p2 = parts[1]

            n_nan = int(grp[col].isna().sum())
            pct_nan = round(100.0 * n_nan / n_fac_rows, 2)

            p1_present = p1 in fac_p_set
            p2_present = p2 in fac_p_set

            if not (p1_present and p2_present):
                reason = "Missing Parameter (One/Both parameters not monitored)"
                missing_p = []
                if not p1_present: missing_p.append(p1)
                if not p2_present: missing_p.append(p2)
                detail = f"Missing: {', '.join(missing_p)}"
            else:
                reason = "Window Gaps / Constant Variance / NaN Values"
                detail = f"Both present. {pct_nan}% NaN in 24H rolling corr"

            corr_nan_rows.append({
                "factory_id": fac,
                "corr_column": col,
                "param_1": p1,
                "param_2": p2,
                "param_1_present": p1_present,
                "param_2_present": p2_present,
                "total_factory_rows": n_fac_rows,
                "nan_count": n_nan,
                "pct_nan": pct_nan,
                "reason": reason,
                "detail": detail
            })

    df_corr_out = pd.DataFrame(corr_nan_rows)
    out_csv = os.path.join(r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance\validation_v2\audit\fix", "corr_nan_by_factory.csv")
    df_corr_out.to_csv(out_csv, index=False)
    print(f"Saved corr_nan_by_factory.csv to {out_csv} ({len(df_corr_out)} rows)")

    # Overall summary per corr column
    print("\nOverall NaN % per corr column across entire dataset:")
    corr_summary = []
    for c in corr_cols:
        pct = round(100.0 * df_pq[c].isna().sum() / len(df_pq), 2)
        corr_summary.append((c, pct))
        print(f"  {c:<25}: {pct:>6.2f}% NaN")

    # Audit Isolation Forest Training Row Imputation
    print("\n--- Auditing Isolation Forest Training Row Imputation (train_models.py logic) ---")
    feature_cols = joblib.load(FEATURE_COLS_PATH)
    print(f"Loaded Isolation Forest feature_cols ({len(feature_cols)} cols):")
    print(feature_cols)

    # Replicate train_models.py 100k random sampling
    np.random.seed(42)
    sample_size = min(100000, len(df_pq))
    sample_indices = np.random.choice(len(df_pq), size=sample_size, replace=False)
    df_sample = df_pq.iloc[sample_indices][feature_cols]

    na_counts_per_row = df_sample.isna().sum(axis=1)
    rows_with_at_least_1_imputed = int((na_counts_per_row > 0).sum())
    pct_rows_imputed = round(100.0 * rows_with_at_least_1_imputed / sample_size, 2)
    avg_imputed_cols_per_row = round(float(na_counts_per_row.mean()), 2)

    print(f"Sample Size                          : {sample_size:,}")
    print(f"Rows with >= 1 imputed feature       : {rows_with_at_least_1_imputed:,} ({pct_rows_imputed}%)")
    print(f"Avg imputed features per row (out of {len(feature_cols)}) : {avg_imputed_cols_per_row}")

    return df_corr_out, pct_rows_imputed, avg_imputed_cols_per_row

if __name__ == "__main__":
    run_task_b()
