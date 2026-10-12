import os
import sys
import pandas as pd
import numpy as np
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_FE_DIR = os.path.join(REPO_ROOT, "Feature Engineering", "Raw Data Feature Engineering")
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if RAW_FE_DIR not in sys.path:
    sys.path.insert(0, RAW_FE_DIR)

from loader import normalize_csv, convert_to_long_format, get_default_cto_limits, FACTORY_FILES, DATA_DIR
from injector import generate_all_injections
from features import assemble_feature_matrix
from ml_pipeline.inference import ForensierInference
from ml_pipeline.risk_engine import calculate_composite_risk
from run_clean_pass import run_clean_evaluation, compute_factory_fingerprints, CONFIG

def run_pipeline_evaluation():
    print("=== STARTING FULL PIPELINE VALIDATION ON INJECTED SEEDED TELEMETRY ===")

    # Step 1 & 2: Clean Pass
    df_clean_summary, clean_feat_matrices = run_clean_evaluation()
    clean_risk_map = dict(zip(df_clean_summary["factory_id"], df_clean_summary["composite_risk_score"]))

    # Step 3: Injection Pass
    injected_dfs, labels_df = generate_all_injections(seeds=[42, 43, 44, 45])
    
    inference_engine = ForensierInference()
    cto_limits = get_default_cto_limits()

    injected_factory_results = []
    
    # Store row-level labels and predictions for evaluation
    # Checks: flatline, copy_paste, limit_hugging, impossible_pH, gradual_drift
    row_eval_data = {
        "flatline": {"y_true": [], "y_pred": []},
        "copy_paste": {"y_true": [], "y_pred": []},
        "limit_hugging": {"y_true": [], "y_pred": []},
        "impossible_pH": {"y_true": [], "y_pred": []},
        "gradual_drift": {"y_true": [], "y_pred": []},
    }

    # Store row-level Isolation Forest scores for ROC AUC
    all_row_if_scores = []
    all_row_labels = []

    for key, inj_wide_df in injected_dfs.items():
        parts = key.split("_seed_")
        f_name = parts[0]
        seed = int(parts[1])

        # Filter ground-truth labels for this seeded run
        run_labels = labels_df[(labels_df["factory"] == f_name) & (labels_df["seed"] == seed)]

        long_df = convert_to_long_format(f_name, inj_wide_df)
        feat_df = assemble_feature_matrix(long_df, cto_limits, CONFIG)

        # Compute factory fingerprints & model predictions
        mag_dict, trig_dict, total_trig = compute_factory_fingerprints(long_df, feat_df)
        tamper_prob = inference_engine.predict_factory_tamper_probability(feat_df)

        X_iso = feat_df.reindex(columns=inference_engine.feature_cols).fillna(0.0)
        X_iso_scaled = inference_engine.iso_scaler.transform(X_iso)
        raw_if_scores = inference_engine.iso_forest.score_samples(X_iso_scaled)
        mean_if_score = float(np.mean(raw_if_scores))

        risk_res = calculate_composite_risk(tamper_prob, mean_if_score, trig_dict)
        clean_risk = clean_risk_map[f_name]
        risk_delta = risk_res["risk_score"] - clean_risk

        injected_factory_results.append({
            "key": key,
            "factory_id": f_name,
            "seed": seed,
            "clean_risk_score": clean_risk,
            "injected_risk_score": risk_res["risk_score"],
            "risk_delta": round(risk_delta, 2),
            "tamper_probability": round(tamper_prob, 4),
            "norm_anomaly_score": risk_res["anomaly_score"],
            "total_fingerprints_triggered": total_trig,
            "trig_impossible_ph_range": trig_dict["impossible_ph_range"],
            "trig_flatline": trig_dict["flatline"],
            "trig_limit_hugging": trig_dict["limit_hugging"],
            "trig_correlation_break": trig_dict["correlation_break"],
            "trig_copy_paste": trig_dict["copy_paste"],
            "trig_coordinated_missing_data": trig_dict["coordinated_missing_data"],
            "trig_data_integrity": trig_dict["data_integrity"]
        })

        # Process Row-Level Ground Truth vs Predictions
        n_wide_rows = len(inj_wide_df)
        
        # Build binary masks for each tamper type in this wide dataframe
        masks = {t: np.zeros(n_wide_rows, dtype=int) for t in row_eval_data.keys()}
        
        for _, lbl in run_labels.iterrows():
            t_type = lbl["type"]
            if t_type in masks:
                s_idx = int(lbl["start_idx"])
                e_idx = int(lbl["end_idx"])
                masks[t_type][s_idx:e_idx] = 1

        # Flatten features to wide timestamp alignment
        piv_flatline = feat_df[feat_df["parameter_id"] == "ETP-BOD"]["flatline_flag"].fillna(0.0).values
        piv_hugging = feat_df[feat_df["parameter_id"] == "ETP-BOD"]["limit_hugging"].fillna(0.0).values
        piv_autocorr = feat_df[feat_df["parameter_id"] == "ETP-COD"]["autocorrelation"].fillna(0.0).values
        
        # pH impossible check
        ph_vals = inj_wide_df["ETP-pH"].values
        piv_ph_pred = np.where(pd.notna(ph_vals) & ((ph_vals < 5.5) | (ph_vals > 9.0) | (ph_vals < 0) | (ph_vals > 14)), 1, 0)
        
        # Match array lengths carefully
        length = min(n_wide_rows, len(piv_flatline))

        # Flatline prediction
        pred_flatline = np.where(piv_flatline[:length] == 1.0, 1, 0)
        row_eval_data["flatline"]["y_true"].extend(masks["flatline"][:length])
        row_eval_data["flatline"]["y_pred"].extend(pred_flatline)

        # Limit Hugging prediction
        pred_hugging = np.where(piv_hugging[:length] == 1.0, 1, 0)
        row_eval_data["limit_hugging"]["y_true"].extend(masks["limit_hugging"][:length])
        row_eval_data["limit_hugging"]["y_pred"].extend(pred_hugging)

        # Copy-paste prediction (autocorrelation > 0.95)
        pred_copy = np.where(piv_autocorr[:length] > 0.95, 1, 0)
        row_eval_data["copy_paste"]["y_true"].extend(masks["copy_paste"][:length])
        row_eval_data["copy_paste"]["y_pred"].extend(pred_copy)

        # Impossible pH prediction
        row_eval_data["impossible_pH"]["y_true"].extend(masks["impossible_pH"][:length])
        row_eval_data["impossible_pH"]["y_pred"].extend(piv_ph_pred[:length])

        # Gradual Drift prediction (Isolation Forest score < normal anchor)
        # Average IF scores across parameters per row
        if_reshaped = raw_if_scores[:length * 4].reshape(-1, 4).mean(axis=1) if len(raw_if_scores) >= length * 4 else raw_if_scores[:length]
        pred_drift = np.where(if_reshaped < -0.45, 1, 0)
        row_eval_data["gradual_drift"]["y_true"].extend(masks["gradual_drift"][:length])
        row_eval_data["gradual_drift"]["y_pred"].extend(pred_drift[:length])

        # Overall row-level labels & anomaly scores for ROC AUC
        any_injected = np.zeros(length, dtype=int)
        for m in masks.values():
            any_injected = any_injected | m[:length]
            
        all_row_labels.extend(any_injected)
        all_row_if_scores.extend(-if_reshaped)  # Negate so higher value = more anomalous

    # Compute Row-Level Metrics
    row_metrics = []
    for check_name, data in row_eval_data.items():
        y_true = np.array(data["y_true"])
        y_pred = np.array(data["y_pred"])
        
        prec = precision_score(y_true, y_pred, zero_division=0)
        rec = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        
        tp = int(np.sum((y_true == 1) & (y_pred == 1)))
        fp = int(np.sum((y_true == 0) & (y_pred == 1)))
        fn = int(np.sum((y_true == 1) & (y_pred == 0)))
        tn = int(np.sum((y_true == 0) & (y_pred == 0)))

        row_metrics.append({
            "check_name": check_name,
            "total_positive_rows": int(np.sum(y_true == 1)),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4)
        })

    df_row_metrics = pd.DataFrame(row_metrics)
    out_row_csv = os.path.join(REPO_ROOT, "validation_unseen", "row_level_metrics.csv")
    df_row_metrics.to_csv(out_row_csv, index=False)
    print(f"\nSaved row-level metrics to {out_row_csv}")

    # Compute Factory-Level Metrics for correlation_break, coordinated_missing_data, and overall
    df_inj_res = pd.DataFrame(injected_factory_results)
    n_injected = len(df_inj_res)  # 16 runs

    factory_metrics = []
    for fp_check, trig_col in [("correlation_break", "trig_correlation_break"),
                              ("coordinated_missing_data", "trig_coordinated_missing_data"),
                              ("impossible_pH", "trig_impossible_ph_range"),
                              ("flatline", "trig_flatline"),
                              ("limit_hugging", "trig_limit_hugging"),
                              ("copy_paste", "trig_copy_paste")]:
        # Every injected run contains an injection of each tamper type
        tp = int(df_inj_res[trig_col].sum())
        fn = n_injected - tp
        # Clean runs triggering this fingerprint count as FP
        clean_trigs = int(df_clean_summary[f"trig_{fp_check}"].sum()) if f"trig_{fp_check}" in df_clean_summary.columns else 0
        fp = clean_trigs
        tn = 4 - clean_trigs  # 4 clean factories

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

        factory_metrics.append({
            "fingerprint_check": fp_check,
            "injected_runs_eval": n_injected,
            "clean_factories_eval": 4,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4)
        })

    df_fac_metrics = pd.DataFrame(factory_metrics)
    out_fac_csv = os.path.join(REPO_ROOT, "validation_unseen", "factory_level_metrics.csv")
    df_fac_metrics.to_csv(out_fac_csv, index=False)
    print(f"Saved factory-level metrics to {out_fac_csv}")

    # Risk Score Delta & AUC calculation
    df_risk_delta = df_inj_res[["factory_id", "seed", "clean_risk_score", "injected_risk_score", "risk_delta"]].copy()
    out_risk_csv = os.path.join(REPO_ROOT, "validation_unseen", "risk_score_deltas.csv")
    df_risk_delta.to_csv(out_risk_csv, index=False)

    # Compute overall Summary Metrics (AUC, Clean FP rate, mean risk delta)
    clean_risk_scores = df_clean_summary["composite_risk_score"].values
    inj_risk_scores = df_inj_res["injected_risk_score"].values
    
    y_factory_auc = np.array([0]*len(clean_risk_scores) + [1]*len(inj_risk_scores))
    scores_factory_auc = np.array(list(clean_risk_scores) + list(inj_risk_scores))
    factory_auc = float(roc_auc_score(y_factory_auc, scores_factory_auc))

    row_auc = float(roc_auc_score(all_row_labels, all_row_if_scores))

    # Clean False Positive Rate (fraction of clean readings with any anomaly flag)
    clean_fp_rates = df_clean_summary["flag_rate_pct"].values
    mean_clean_fp_rate = float(np.mean(clean_fp_rates))

    summary_metrics = {
        "metric_name": [
            "Clean Pass Mean Risk Score",
            "Injected Pass Mean Risk Score",
            "Mean Risk Score Delta (Injected vs Clean)",
            "Factory-Level Risk Score ROC AUC",
            "Row-Level Anomaly Score ROC AUC",
            "Clean Data False Positive Flag Rate (%)"
        ],
        "value": [
            round(float(np.mean(clean_risk_scores)), 2),
            round(float(np.mean(inj_risk_scores)), 2),
            round(float(np.mean(df_inj_res["risk_delta"])), 2),
            round(factory_auc, 4),
            round(row_auc, 4),
            round(mean_clean_fp_rate, 2)
        ]
    }
    df_summary = pd.DataFrame(summary_metrics)
    out_summary_csv = os.path.join(REPO_ROOT, "validation_unseen", "validation_metrics_summary.csv")
    df_summary.to_csv(out_summary_csv, index=False)

    print("\n=== PIPELINE METRICS SUMMARY ===")
    print(df_summary.to_string(index=False))
    print("\nRow-Level Metrics:")
    print(df_row_metrics[["check_name", "precision", "recall", "f1_score", "tp", "fp", "fn"]].to_string(index=False))
    print("\nFactory-Level Metrics:")
    print(df_fac_metrics[["fingerprint_check", "precision", "recall", "f1_score", "tp", "fp", "fn"]].to_string(index=False))

    return df_clean_summary, df_inj_res, df_row_metrics, df_fac_metrics, df_summary

if __name__ == "__main__":
    run_pipeline_evaluation()
