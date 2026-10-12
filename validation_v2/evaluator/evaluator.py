import os
import sys
import warnings
warnings.filterwarnings("ignore")
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest

REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
RAW_CSV = os.path.join(REPO_ROOT, "Data", "RawData", "monitoring_data(raw).csv")
CTO_CSV = os.path.join(REPO_ROOT, "Original Data", "consent_limits.csv")
LABELS_CSV = os.path.join(REPO_ROOT, "validation_v2", "injector", "injected", "dev", "labels.csv")
DEV_INJECTED_DIR = os.path.join(REPO_ROOT, "validation_v2", "injector", "injected", "dev")
INJECTED_SHARE_CSV = os.path.join(REPO_ROOT, "validation_v2", "injected_share.csv")
KNOWN_VIOLATIONS_CSV = os.path.join(REPO_ROOT, "validation_v2", "injector", "known_violations.csv")

EVAL_DIR = os.path.join(REPO_ROOT, "validation_v2", "evaluator")
os.makedirs(EVAL_DIR, exist_ok=True)

sys.path.insert(0, os.path.join(REPO_ROOT, "validation_v2", "detector"))
from detector import extract_series_features, FEATURE_COLS

def load_and_prep_labels(labels_csv_path: str = LABELS_CSV) -> pd.DataFrame:
    """
    Loads labels and enriches with:
    - excluded_from_T6: True for the 10 known rule-violating events (skipped in T6 tables).
    - share_bin: Stratification bins (<=2%, 2-10%, >10%) based on injected share per series-seed.
    """
    df_labels = pd.read_csv(labels_csv_path)

    # 1. Add excluded_from_T6 column
    if os.path.exists(KNOWN_VIOLATIONS_CSV):
        kv_df = pd.read_csv(KNOWN_VIOLATIONS_CSV)
        known_ids = set(kv_df["event_id"].dropna().unique())
        df_labels["excluded_from_T6"] = df_labels["event_id"].isin(known_ids)
    else:
        df_labels["excluded_from_T6"] = False

    # 2. Add stratification bins
    if os.path.exists(INJECTED_SHARE_CSV):
        share_df = pd.read_csv(INJECTED_SHARE_CSV)
        df_labels["primary_param"] = df_labels["params"].astype(str).str.split(",").str[0].str.strip()
        df_labels = df_labels.merge(
            share_df[["factory_id", "parameter_id", "seed", "share_present", "share_bin_present", "share_grid", "share_bin_grid"]],
            left_on=["factory_id", "primary_param", "seed"],
            right_on=["factory_id", "parameter_id", "seed"],
            how="left"
        )
        df_labels.rename(columns={"share_bin_present": "share_bin"}, inplace=True)
        if "parameter_id" in df_labels.columns:
            df_labels.drop(columns=["parameter_id"], inplace=True)
    else:
        df_labels["share_bin"] = "unknown"

    return df_labels


def count_false_alarm_episodes(scores: np.ndarray, values: np.ndarray, threshold: float) -> int:
    """
    Vectorized false alarm episode counter.
    - Missing readings (value is NaN or score is NaN) are excluded.
    - Consecutive readings > threshold separated by < 8 rows (2h) belong to 1 episode.
    """
    mask = ~np.isnan(values) & ~np.isnan(scores) & (scores > threshold)
    if not np.any(mask):
        return 0

    indices = np.where(mask)[0]
    if len(indices) == 1:
        return 1

    gaps = np.diff(indices)
    return 1 + int(np.sum(gaps >= 8))

def calibrate_global_threshold(method_name: str, score_dict: dict, raw_dict: dict, target_episodes: int = 328) -> float:
    """
    Calibrates global threshold tau on un-injected telemetry to hit target_episodes false alarms across all 33 dev factories.
    Zero injected labels or detection outcomes are used.
    """
    all_scores = []
    for key, sc in score_dict.items():
        v = raw_dict[key]["value"].values
        valid_sc = sc[~np.isnan(v) & ~np.isnan(sc)]
        if len(valid_sc) > 0:
            all_scores.extend(valid_sc)

    if not all_scores:
        return 0.0

    all_scores = np.sort(all_scores)
    
    low_idx = 0
    high_idx = len(all_scores) - 1
    best_tau = float(all_scores[-1])
    best_diff = 999999
    final_episodes = 0

    for _ in range(30):
        mid_idx = (low_idx + high_idx) // 2
        tau = float(all_scores[mid_idx])

        tot_episodes = 0
        for key, sc in score_dict.items():
            v = raw_dict[key]["value"].values
            tot_episodes += count_false_alarm_episodes(sc, v, tau)

        diff = abs(tot_episodes - target_episodes)
        if diff < best_diff:
            best_diff = diff
            best_tau = tau
            final_episodes = tot_episodes

        if tot_episodes > target_episodes:
            low_idx = mid_idx + 1
        else:
            high_idx = mid_idx - 1

        if low_idx >= high_idx:
            break

    print(f"[{method_name}] Calibrated Tau = {best_tau:.6f} | Achieved False Alarm Episodes = {final_episodes} (Target = {target_episodes})")
    return best_tau

def train_lofo_33_fold_models(df_raw):
    """
    Pre-trains 33 LOFO fold models ONCE across all 33 dev factories.
    In fold k, fits 5 pooled sensor Isolation Forests on the 32 training factories using sub-sampling for maximum speed.
    """
    allowed_qc = ["Raw", "L"]
    df_filt = df_raw[df_raw["quality_code"].isin(allowed_qc)].copy()
    df_filt["ts_dt"] = pd.to_datetime(df_filt["timestamp"])

    all_factories = sorted(df_filt["factory_id"].unique())
    sensors = ["ETP-pH", "ETP-Flow", "ETP-BOD", "ETP-COD", "ETP-TSS"]

    print("\n1. Pre-computing un-injected series features across all 33 factories...", flush=True)
    feats_dict = {}
    raw_dict = {}
    for (fac, p), g in df_filt.groupby(["factory_id", "parameter_id"]):
        g_s = g.sort_values("ts_dt").reset_index(drop=True)
        feats_dict[(fac, p)] = extract_series_features(g_s)
        raw_dict[(fac, p)] = g_s

    lofo_fold_models = {}
    lofo_uninjected_scores = {}
    lofo_uninjected_raw = {}

    print("Pre-Training 33-Fold LOFO Sensor Isolation Forests (Fast Sub-sampled Fit)...", flush=True)

    for k, held_out_fac in enumerate(all_factories, 1):
        train_facs = [f for f in all_factories if f != held_out_fac]
        sensor_models = {}

        for s in sensors:
            train_feats = [feats_dict[(f, s)] for f in train_facs if (f, s) in feats_dict and not feats_dict[(f, s)].empty]
            if not train_feats:
                continue

            X_train = pd.concat(train_feats, ignore_index=True)
            if len(X_train) < 10:
                continue

            if len(X_train) > 30000:
                X_train_sub = X_train.sample(n=30000, random_state=42)
            else:
                X_train_sub = X_train

            iso = IsolationForest(n_estimators=50, max_samples=2048, random_state=42, n_jobs=1)
            iso.fit(X_train_sub)
            sensor_models[s] = iso

        lofo_fold_models[held_out_fac] = sensor_models

        # Score held-out Factory k on un-injected telemetry
        for s in sensors:
            key = (held_out_fac, s)
            if key in feats_dict:
                X_eval = feats_dict[key]
                g_s = raw_dict[key]
                model = sensor_models.get(s)

                if model is not None and not X_eval.empty:
                    sc = -model.decision_function(X_eval)
                else:
                    sc = np.zeros(len(g_s))

                sc[g_s["value"].isna()] = np.nan
                lofo_uninjected_scores[key] = sc
                lofo_uninjected_raw[key] = g_s

    print(f"Pre-trained 33 LOFO fold models successfully.", flush=True)
    return lofo_fold_models, lofo_uninjected_scores, lofo_uninjected_raw

def compute_rolling_zscore_scores(df_raw):
    """Method 2: Rolling 16-row (4h) Z-score baseline."""
    df_filt = df_raw[df_raw["quality_code"].isin(["Raw", "L"])].copy()
    df_filt["ts_dt"] = pd.to_datetime(df_filt["timestamp"])

    scores = {}
    raw = {}

    for (fac, p), g in df_filt.groupby(["factory_id", "parameter_id"]):
        g_s = g.sort_values("ts_dt").reset_index(drop=True)
        vals = g_s["value"]

        r_mean = vals.rolling(16, min_periods=1).mean()
        r_std = vals.rolling(16, min_periods=1).std().fillna(0.0)

        z = np.abs(vals - r_mean) / np.maximum(r_std, 1e-4)
        sc = z.values
        sc[vals.isna()] = np.nan

        key = (fac, p)
        scores[key] = sc
        raw[key] = g_s

    return scores, raw

def compute_static_limit_scores(df_raw, cto_limits):
    """Method 3: Distance to CTO consent limit / static 3-sigma baseline."""
    df_filt = df_raw[df_raw["quality_code"].isin(["Raw", "L"])].copy()
    df_filt["ts_dt"] = pd.to_datetime(df_filt["timestamp"])

    scores = {}
    raw = {}

    for (fac, p), g in df_filt.groupby(["factory_id", "parameter_id"]):
        g_s = g.sort_values("ts_dt").reset_index(drop=True)
        vals = g_s["value"].values

        cto_max = np.nan
        for (f_k, p_k), lim_val in cto_limits.items():
            if f_k == fac and (p_k.lower() in p.lower() or p.lower() in p_k.lower()):
                cto_max = lim_val
                break
        if "pH" in p or "ph" in p.lower():
            cto_max = 9.0 if np.isnan(cto_max) else cto_max

        if pd.notna(cto_max) and cto_max > 0:
            sc = vals / cto_max
        else:
            std = np.nanstd(vals) if len(vals) > 1 else 1.0
            mean = np.nanmean(vals) if len(vals) > 0 else 0.0
            sc = np.abs(vals - mean) / max(std, 1e-4)

        sc[pd.isna(vals)] = np.nan
        key = (fac, p)
        scores[key] = sc
        raw[key] = g_s

    return scores, raw

def compute_legacy_scores(df_raw):
    """Method 4: Legacy rolling covariance / flatline heuristic baseline."""
    df_filt = df_raw[df_raw["quality_code"].isin(["Raw", "L"])].copy()
    df_filt["ts_dt"] = pd.to_datetime(df_filt["timestamp"])

    scores = {}
    raw = {}

    for (fac, p), g in df_filt.groupby(["factory_id", "parameter_id"]):
        g_s = g.sort_values("ts_dt").reset_index(drop=True)
        vals = g_s["value"]

        r_std_4 = vals.rolling(4, min_periods=1).std().fillna(0.0)
        r_diff_1 = vals.diff(1).abs().fillna(0.0)

        sc = (1.0 / (r_std_4 + 1e-4)) + r_diff_1.values
        sc[vals.isna()] = np.nan

        key = (fac, p)
        scores[key] = sc
        raw[key] = g_s

    return scores, raw

def evaluate_method_fast(method_name: str, tau: float, lofo_fold_models: dict, df_raw, df_labels, cto_limits):
    """
    Ultra-fast evaluation using full continuous injected series scoring across all 2,511 injected events (Seeds 1–5).
    Full continuous series scoring ensures rolling features (16-row std/mean/z-score) have full historical context.
    """
    df_labels_eval = df_labels.copy()
    df_labels_eval["start_dt"] = pd.to_datetime(df_labels_eval["start_ts"])
    df_labels_eval["end_dt"] = pd.to_datetime(df_labels_eval["end_ts"])

    series_score_cache = {}

    # Pre-score all injected series for all (seed, fac, param)
    for seed in range(1, 6):
        seed_dir = os.path.join(DEV_INJECTED_DIR, f"seed_{seed}")
        if not os.path.exists(seed_dir):
            continue
        for fname in os.listdir(seed_dir):
            if not fname.endswith(".parquet"):
                continue
            fac = fname.replace(".parquet", "")
            pq_path = os.path.join(seed_dir, fname)
            df_pq = pd.read_parquet(pq_path)
            df_pq["ts_dt"] = pd.to_datetime(df_pq["timestamp"])

            for param, g in df_pq.groupby("parameter_id"):
                g_s = g.sort_values("ts_dt").reset_index(drop=True)
                
                if "LOFO" in method_name:
                    X_g = extract_series_features(g_s)
                    sensor_models = lofo_fold_models.get(fac, {})
                    model = sensor_models.get(param)
                    if model is not None and not X_g.empty:
                        sc = -model.decision_function(X_g)
                    else:
                        sc = np.zeros(len(g_s))

                elif "Z-Score" in method_name:
                    vals = g_s["value"]
                    r_m = vals.rolling(16, min_periods=1).mean()
                    r_s = vals.rolling(16, min_periods=1).std().fillna(0.0)
                    sc = (np.abs(vals - r_m) / np.maximum(r_s, 1e-4)).values

                elif "Static" in method_name:
                    vals = g_s["value"].values
                    cto_max = cto_limits.get((fac, param), np.nan)
                    if "pH" in param or "ph" in param.lower():
                        cto_max = 9.0 if np.isnan(cto_max) else cto_max
                    if pd.notna(cto_max) and cto_max > 0:
                        sc = vals / cto_max
                    else:
                        mean_v = np.nanmean(vals) if len(vals) > 0 else 0.0
                        std_v = np.nanstd(vals) if len(vals) > 1 else 1.0
                        sc = np.abs(vals - mean_v) / max(std_v, 1e-4)

                else:  # Legacy
                    vals = g_s["value"]
                    r_s4 = vals.rolling(4, min_periods=1).std().fillna(0.0)
                    r_d1 = vals.diff(1).abs().fillna(0.0)
                    sc = ((1.0 / (r_s4 + 1e-4)) + r_d1).values

                sc[g_s["value"].isna()] = np.nan
                series_score_cache[(seed, fac, param)] = (g_s["ts_dt"].values, g_s["value"].values, sc)

    detected_flags = []
    for _, row in df_labels_eval.iterrows():
        seed = row["seed"]
        fac = row["factory_id"]
        param = str(row["params"]).split(",")[0].strip()
        s_dt = row["start_dt"]
        e_dt = row["end_dt"]

        cache_entry = series_score_cache.get((seed, fac, param))
        if cache_entry is None:
            detected_flags.append(False)
            continue

        ts_arr, val_arr, sc_arr = cache_entry
        mask = (ts_arr >= np.datetime64(s_dt)) & (ts_arr <= np.datetime64(e_dt))

        if not np.any(mask):
            detected_flags.append(False)
            continue

        w_vals = val_arr[mask]
        w_scores = sc_arr[mask]

        is_detected = np.any(~np.isnan(w_vals) & ~np.isnan(w_scores) & (w_scores > tau))
        detected_flags.append(bool(is_detected))

    df_labels_eval["is_detected"] = detected_flags
    return df_labels_eval

def compute_cluster_bootstrap_ci(df_labels_eval, n_bootstraps: int = 1000, seed: int = 42):
    """
    Computes 95% cluster bootstrap confidence interval over factories for headline recall.
    Excludes T6 from headline recall.
    """
    np.random.seed(seed)
    headline_df = df_labels_eval[df_labels_eval["type"] != "T6"].copy()
    factories = headline_df["factory_id"].unique()

    boot_recalls = []
    for _ in range(n_bootstraps):
        boot_facs = np.random.choice(factories, size=len(factories), replace=True)
        boot_rows = []
        for bf in boot_facs:
            boot_rows.append(headline_df[headline_df["factory_id"] == bf])
        boot_sample = pd.concat(boot_rows, ignore_index=True)
        rec = float(boot_sample["is_detected"].mean())
        boot_recalls.append(rec)

    ci_lower = float(np.percentile(boot_recalls, 2.5))
    ci_upper = float(np.percentile(boot_recalls, 97.5))
    mean_recall = float(headline_df["is_detected"].mean())

    return mean_recall, ci_lower, ci_upper

def main():
    print("==========================================================================")
    print(" FORENSIAIR STEP 4 DEV SET EVALUATION & BASELINE COMPARISON")
    print("==========================================================================")

    df_raw = pd.read_csv(RAW_CSV)
    df_cto = pd.read_csv(CTO_CSV)
    df_labels = load_and_prep_labels(LABELS_CSV)

    cto_limits = {}
    for _, r in df_cto.iterrows():
        if pd.notna(r["maximum_limit"]) and r["maximum_limit"] > 0:
            cto_limits[(str(r["factory_id"]), str(r["parameter"]))] = float(r["maximum_limit"])

    lofo_fold_models, lofo_scores, lofo_raw = train_lofo_33_fold_models(df_raw)

    print("\n2. Extracting Un-injected Scores & Calibrating Thresholds (Target = 328 episodes)...")
    zscore_scores, zscore_raw = compute_rolling_zscore_scores(df_raw)
    static_scores, static_raw = compute_static_limit_scores(df_raw, cto_limits)
    legacy_scores, legacy_raw = compute_legacy_scores(df_raw)

    tau_lofo = calibrate_global_threshold("New 33-Fold LOFO Detector", lofo_scores, lofo_raw, 328)
    tau_zscore = calibrate_global_threshold("Rolling Z-Score Baseline", zscore_scores, zscore_raw, 328)
    tau_static = calibrate_global_threshold("Static Limit Baseline", static_scores, static_raw, 328)
    tau_legacy = calibrate_global_threshold("Legacy Baseline", legacy_scores, legacy_raw, 328)

    print("\n3. Evaluating Injected Tamper Events across Seeds 1-5...")
    res_lofo = evaluate_method_fast("LOFO Detector", tau_lofo, lofo_fold_models, df_raw, df_labels, cto_limits)
    res_zscore = evaluate_method_fast("Rolling Z-Score", tau_zscore, lofo_fold_models, df_raw, df_labels, cto_limits)
    res_static = evaluate_method_fast("Static Limit", tau_static, lofo_fold_models, df_raw, df_labels, cto_limits)
    res_legacy = evaluate_method_fast("Legacy Baseline", tau_legacy, lofo_fold_models, df_raw, df_labels, cto_limits)

    methods = [
        ("New 33-Fold LOFO Detector", res_lofo, tau_lofo),
        ("Rolling Z-Score Baseline", res_zscore, tau_zscore),
        ("Static Limit Baseline", res_static, tau_static),
        ("Legacy Baseline", res_legacy, tau_legacy)
    ]

    summary_rows = []
    print("\n==========================================================================")
    print(" SUMMARY EVALUATION RESULTS (HEADLINE EXCLUDES T6)")
    print("==========================================================================")

    for name, df_res, tau in methods:
        h_rec, ci_l, ci_u = compute_cluster_bootstrap_ci(df_res)
        # T6 evaluation excludes known violations flagged in excluded_from_T6
        t6_mask = (df_res["type"] == "T6")
        if "excluded_from_T6" in df_res.columns:
            t6_mask = t6_mask & (~df_res["excluded_from_T6"])
        t6_sub = df_res[t6_mask]
        t6_rec = float(t6_sub["is_detected"].mean()) if len(t6_sub) > 0 else 0.0

        pass_status = "PASSED" if (h_rec >= 0.70 and ci_l >= 0.50) else "FAILED"

        summary_rows.append({
            "Method": name,
            "Calibrated Tau": round(tau, 6),
            "Headline Recall": round(h_rec, 4),
            "95% CI Lower": round(ci_l, 4),
            "95% CI Upper": round(ci_u, 4),
            "T6 Recall (Separate)": round(t6_rec, 4),
            "Pass Status": pass_status
        })

    df_summary = pd.DataFrame(summary_rows)
    print(df_summary.to_string(index=False))

    summary_path = os.path.join(EVAL_DIR, "evaluation_summary.csv")
    df_summary.to_csv(summary_path, index=False)

    headline_lofo = res_lofo[res_lofo["type"] != "T6"]
    
    print("\n--- Detailed Recall Breakdown by Type for New 33-Fold LOFO Detector ---")
    type_df = headline_lofo.groupby("type")["is_detected"].agg(["count", "sum", "mean"]).reset_index()
    type_df.columns = ["Tamper Type", "Total Events", "Detected Events", "Recall"]
    print(type_df.to_string(index=False))

    print("\n--- Detailed Recall Breakdown by Severity for New 33-Fold LOFO Detector ---")
    sev_df = headline_lofo.groupby("severity")["is_detected"].agg(["count", "sum", "mean"]).reset_index()
    sev_df.columns = ["Severity", "Total Events", "Detected Events", "Recall"]
    print(sev_df.to_string(index=False))

    print("\n--- Detailed Recall Breakdown by Duration (Rows) for New 33-Fold LOFO Detector ---")
    dur_df = headline_lofo.groupby("duration_rows")["is_detected"].agg(["count", "sum", "mean"]).reset_index()
    dur_df.columns = ["Duration Rows", "Total Events", "Detected Events", "Recall"]
    print(dur_df.to_string(index=False))

    # Stratification by Injected Share Bins (<=2%, 2-10%, >10%)
    if "share_bin" in headline_lofo.columns:
        print("\n--- Detailed Recall Breakdown by Injected Share Bin for New 33-Fold LOFO Detector ---")
        share_df = headline_lofo.groupby("share_bin")["is_detected"].agg(["count", "sum", "mean"]).reset_index()
        share_df.columns = ["Injected Share Bin", "Total Events", "Detected Events", "Recall"]
        print(share_df.to_string(index=False))
        share_df.to_csv(os.path.join(EVAL_DIR, "lofo_recall_by_share_bin.csv"), index=False)

    type_df.to_csv(os.path.join(EVAL_DIR, "lofo_recall_by_type.csv"), index=False)
    sev_df.to_csv(os.path.join(EVAL_DIR, "lofo_recall_by_severity.csv"), index=False)
    dur_df.to_csv(os.path.join(EVAL_DIR, "lofo_recall_by_duration.csv"), index=False)
    res_lofo.to_csv(os.path.join(EVAL_DIR, "lofo_detailed_eval.csv"), index=False)

    print(f"\nSaved all evaluation artifacts to {EVAL_DIR}")
    return df_summary

if __name__ == "__main__":
    main()
