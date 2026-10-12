import os
import sys
import pandas as pd
import numpy as np

# Ensure repo root and feature engineering directory are in sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_FE_DIR = os.path.join(REPO_ROOT, "Feature Engineering", "Raw Data Feature Engineering")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if RAW_FE_DIR not in sys.path:
    sys.path.insert(0, RAW_FE_DIR)

from loader import normalize_csv, convert_to_long_format, get_default_cto_limits, FACTORY_FILES, DATA_DIR
from features import assemble_feature_matrix
from ml_pipeline.inference import ForensierInference
from ml_pipeline.risk_engine import calculate_composite_risk

CONFIG = {
    "windows": {
        "flatline_window": "2H",
        "flatline_std_threshold": 0.01,
        "correlation_window": "24H",
        "autocorr_lag": 96,
        "missing_rate_window": "7D",
        "limit_hugging_pct": 0.05
    },
    "parameters": ["ETP-Flow", "ETP-pH", "ETP-COD", "ETP-BOD", "ETP-TSS"]
}

# Reference dataset baseline stats (from 33 reference factories in training dataset)
TYPICAL_REF_CORR_MEAN = 0.5512
TYPICAL_REF_CORR_STD = 0.1081
REF_CORR_THRESHOLD = TYPICAL_REF_CORR_MEAN - 1.0 * TYPICAL_REF_CORR_STD  # ~0.4431

TYPICAL_REF_MISSING_MEDIAN = 0.0210
TYPICAL_REF_MISSING_STD = 0.0450

TYPICAL_REF_ERROR_MEDIAN = 0.0
TYPICAL_REF_ERROR_STD = 0.0100

def compute_factory_fingerprints(long_telemetry: pd.DataFrame, feature_matrix: pd.DataFrame) -> dict:
    """
    Computes the 8 fingerprint magnitude metrics and trigger decisions for a single factory.
    Reuse exact logic and thresholds from fingerprint_engine.py.
    """
    fac_id = long_telemetry["factory_id"].iloc[0]
    cto_limits = get_default_cto_limits()
    fac_limits = cto_limits[cto_limits["factory_id"] == fac_id]
    
    # 1. IMPOSSIBLE_PH_RANGE
    ph_df = long_telemetry[(long_telemetry["parameter_id"] == "ETP-pH") & long_telemetry["value"].notna()]
    total_ph = len(ph_df)
    if total_ph > 0:
        vals = ph_df["value"].values
        flagged = (vals < 0) | (vals > 14) | (vals < 5.5) | (vals > 9.0)
        ph_score = float(100.0 * np.sum(flagged) / total_ph)
    else:
        ph_score = 0.0
    trig_ph = 1 if ph_score > 0.0 else 0

    # 2. INSPECTION_DIP (None for unseen real factories without physical inspection logs)
    inspection_dip_score = np.nan
    trig_dip = 0

    # 3. FLATLINE
    flatline_series = feature_matrix["flatline_flag"].dropna()
    if len(flatline_series) > 0:
        flatline_score = float(100.0 * np.sum(flatline_series == 1.0) / len(flatline_series))
    else:
        flatline_score = 0.0
    trig_flat = 1 if flatline_score > 5.0 else 0

    # 4. LIMIT_HUGGING
    hugging_series = feature_matrix["limit_hugging"].dropna()
    if len(hugging_series) > 0:
        hugging_score = float(100.0 * np.sum(hugging_series == 1.0) / len(hugging_series))
    else:
        hugging_score = 0.0
    trig_hug = 1 if hugging_score > 5.0 else 0

    # 5. CORRELATION_BREAK
    corr_cols = [c for c in feature_matrix.columns if c.startswith("corr_")]
    if len(corr_cols) > 0:
        row_avg_corr = feature_matrix[corr_cols].mean(axis=1).dropna()
        if len(row_avg_corr) > 0:
            corr_score = float(row_avg_corr.mean())
        else:
            corr_score = np.nan
    else:
        corr_score = np.nan

    trig_corr = 0
    if not np.isnan(corr_score) and corr_score < REF_CORR_THRESHOLD:
        trig_corr = 1

    # 6. COPY_PASTE
    autocorr_series = feature_matrix["autocorrelation"].dropna()
    if len(autocorr_series) > 0:
        copy_score = float(100.0 * np.sum(autocorr_series > 0.95) / len(autocorr_series))
    else:
        copy_score = 0.0
    trig_copy = 1 if copy_score > 1.0 else 0

    # 7. COORDINATED_MISSING_DATA
    total_possible = len(feature_matrix)
    actual_missing = feature_matrix["value"].isna().sum()
    fac_missing_rate = float(actual_missing / total_possible) if total_possible > 0 else 0.0
    missing_z = (fac_missing_rate - TYPICAL_REF_MISSING_MEDIAN) / TYPICAL_REF_MISSING_STD
    trig_missing = 1 if missing_z > 1.5 else 0

    # 8. DATA_INTEGRITY
    fac_error_rate = 0.0  # Raw quality code error rate
    error_z = (fac_error_rate - TYPICAL_REF_ERROR_MEDIAN) / TYPICAL_REF_ERROR_STD if TYPICAL_REF_ERROR_STD > 0 else 0.0
    trig_integrity = 1 if error_z > 1.5 else 0

    trig_dict = {
        'impossible_ph_range': trig_ph,
        'inspection_dip': trig_dip,
        'flatline': trig_flat,
        'limit_hugging': trig_hug,
        'correlation_break': trig_corr,
        'copy_paste': trig_copy,
        'coordinated_missing_data': trig_missing,
        'data_integrity': trig_integrity
    }

    mag_dict = {
        'impossible_ph_range': round(ph_score, 2),
        'inspection_dip': round(inspection_dip_score, 2) if not np.isnan(inspection_dip_score) else np.nan,
        'flatline': round(flatline_score, 2),
        'limit_hugging': round(hugging_score, 2),
        'correlation_break': round(corr_score, 4) if not np.isnan(corr_score) else np.nan,
        'copy_paste': round(copy_score, 2),
        'coordinated_missing_data': round(missing_z, 2),
        'data_integrity': round(error_z, 2)
    }

    total_triggered = sum(trig_dict.values())
    return mag_dict, trig_dict, total_triggered

def run_clean_evaluation():
    print("=== STARTING CLEAN PASS EVALUATION ON 4 UNSEEN FACTORIES ===")
    
    inference_engine = ForensierInference()
    cto_limits = get_default_cto_limits()

    factory_results = []
    feature_matrices = {}

    for f_name, f_file in FACTORY_FILES.items():
        csv_path = os.path.join(DATA_DIR, f_file)
        wide_df = normalize_csv(f_name, csv_path)
        long_df = convert_to_long_format(f_name, wide_df)

        print(f"\nProcessing clean telemetry for [{f_name}]...")
        print(f"  Long telemetry rows: {len(long_df):,}")

        # Assemble features using production pipeline
        feat_df = assemble_feature_matrix(long_df, cto_limits, CONFIG)
        feature_matrices[f_name] = feat_df

        # Compute row-level anomaly flag rate
        # Row flagged if flatline_flag==1 or limit_hugging==1 or (autocorrelation > 0.95)
        row_flags = (feat_df["flatline_flag"] == 1.0) | (feat_df["limit_hugging"] == 1.0) | (feat_df["autocorrelation"] > 0.95)
        flag_rate = float(100.0 * row_flags.sum() / len(feat_df))

        # Fingerprint magnitudes and triggers
        mag_dict, trig_dict, total_trig = compute_factory_fingerprints(long_df, feat_df)

        # Model inferences
        tamper_prob = inference_engine.predict_factory_tamper_probability(feat_df)

        # Isolation Forest scoring
        X_iso = feat_df.reindex(columns=inference_engine.feature_cols).fillna(0.0)
        X_iso_scaled = inference_engine.iso_scaler.transform(X_iso)
        raw_if_scores = inference_engine.iso_forest.score_samples(X_iso_scaled)
        mean_if_score = float(np.mean(raw_if_scores))

        # Calculate composite risk
        risk_res = calculate_composite_risk(tamper_prob, mean_if_score, trig_dict)

        result_entry = {
            "factory_id": f_name,
            "total_rows": len(wide_df),
            "flag_rate_pct": round(flag_rate, 2),
            "tamper_probability": round(tamper_prob, 4),
            "raw_if_score": round(mean_if_score, 4),
            "norm_anomaly_score": risk_res["anomaly_score"],
            "composite_risk_score": risk_res["risk_score"],
            "risk_category": risk_res["risk_category"],
            "total_fingerprints_triggered": total_trig,
            "trig_impossible_ph_range": trig_dict["impossible_ph_range"],
            "trig_inspection_dip": trig_dict["inspection_dip"],
            "trig_flatline": trig_dict["flatline"],
            "trig_limit_hugging": trig_dict["limit_hugging"],
            "trig_correlation_break": trig_dict["correlation_break"],
            "trig_copy_paste": trig_dict["copy_paste"],
            "trig_coordinated_missing_data": trig_dict["coordinated_missing_data"],
            "trig_data_integrity": trig_dict["data_integrity"],
            "mag_impossible_ph_pct": mag_dict["impossible_ph_range"],
            "mag_flatline_pct": mag_dict["flatline"],
            "mag_limit_hugging_pct": mag_dict["limit_hugging"],
            "mag_correlation_break_avg": mag_dict["correlation_break"],
            "mag_copy_paste_pct": mag_dict["copy_paste"]
        }
        factory_results.append(result_entry)

    # Rank factories by composite_risk_score descending
    df_clean = pd.DataFrame(factory_results)
    df_clean = df_clean.sort_values(by="composite_risk_score", ascending=False).reset_index(drop=True)
    df_clean["risk_rank"] = df_clean.index + 1

    out_csv = os.path.join(REPO_ROOT, "validation_unseen", "clean_pass_summary.csv")
    df_clean.to_csv(out_csv, index=False)
    print(f"\nSaved clean pass summary to {out_csv}")
    print("\nClean Pass Results Summary:")
    print(df_clean[["risk_rank", "factory_id", "composite_risk_score", "risk_category", "tamper_probability", "norm_anomaly_score", "total_fingerprints_triggered", "flag_rate_pct"]].to_string(index=False))

    return df_clean, feature_matrices

if __name__ == "__main__":
    run_clean_evaluation()
