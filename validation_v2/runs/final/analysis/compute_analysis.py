"""
ForensiAIR FINAL ANALYSIS: Read-Only Empirical Analysis from Saved Outputs
Specification: PROTOCOL_v1.md & PROTOCOL_v1.1.md (Frozen)

Outputs written strictly to: validation_v2/runs/final/analysis/
Rules:
- Read-only from saved outputs.
- Do NOT rerun detector/injector on test set to modify results.
- Do NOT change any cutoffs for the primary result.
- Do NOT edit any existing file.
"""

import os
import sys
sys.stdout.reconfigure(line_buffering=True)
import time
import json
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
ANALYSIS_DIR = os.path.join(REPO_ROOT, "validation_v2", "runs", "final", "analysis")
os.makedirs(ANALYSIS_DIR, exist_ok=True)

FINAL_DIR = os.path.join(REPO_ROOT, "validation_v2", "runs", "final")
DEV_RUN2B_DIR = os.path.join(REPO_ROOT, "validation_v2", "runs", "run2b")
DEV_INJECTED_DIR = os.path.join(REPO_ROOT, "validation_v2", "injector", "injected", "dev")

UNSEEN_DIR = r"c:\Users\gauri\Downloads\validation"
FACTORY_FILES = {
    "Cipla": "Cipla (1).csv",
    "Glenmark": "Glenmark (1).csv",
    "Indoco": "Indoco (1).csv",
    "Zydus": "Zydus (1).csv"
}

DEV_RAW_CSV = os.path.join(REPO_ROOT, "Data", "RawData", "monitoring_data(raw).csv")
DEV_CTO_CSV = os.path.join(REPO_ROOT, "Original Data", "consent_limits.csv")

sys.path.insert(0, os.path.join(REPO_ROOT, "validation_v2", "detector"))
from detector import (
    prepare_series,
    compute_check_statistics,
    compute_f5_correlation,
    calibrate,
    score,
    extract_if_features,
    calc_mad,
    get_resolution_step
)

sys.path.insert(0, os.path.join(REPO_ROOT, "validation_v2", "injector"))
from injector import (
    get_series_resolution,
    compute_natural_repeat_runs,
    round_to_resolution,
    TAMPER_TYPES,
    SEVERITIES,
    DURATIONS_ROWS
)

sys.path.insert(0, os.path.join(REPO_ROOT, "validation_v2", "runs", "final"))
from evaluate_final import (
    DEV_FACTORY_MONTHS,
    TOTAL_DEV_FACTORY_MONTHS,
    METHODS_LIST,
    extract_alert_episodes,
    count_episodes_for_series,
    calibrate_tau_for_training,
    compute_cluster_bootstrap,
    compute_b1_robust_zscore,
    extract_b2_features,
    compute_b4_rules,
    compute_b5_factory_risk,
    get_test_cto_limits
)

# -----------------------------------------------------------------------------
# 1. Dev-calibrated cutoffs from FINAL_LOG.md
# -----------------------------------------------------------------------------
DEV_CUTOFFS_BUDGET1 = {
    "M1_fusion": 3.7955,
    "F1_eps0": 2.6739,
    "F1_eps1": 2.6210,
    "F1_eps2": 2.5335,
    "F2_copypaste": 2.8168,
    "F3_limit": 1.1786,
    "F5_corr": 1.0376,
    "F6_shift": 3.0779,
    "F6_slope": 3.3110,
    "IF_sensor": 2.5100,
    "B1_zscore": 46300.0000,
    "B2_pooled_if": 0.2417,
    "B3_sensor_if": 2.5100,
    "B4_legacy_rules": 0.5000,
    "B0_random": 1.0
}

TOTAL_TEST_MONTHS = 23.91
TEST_MONTHS_BY_FAC = {
    "Cipla": 5.98,
    "Glenmark": 5.98,
    "Indoco": 5.98,
    "Zydus": 5.98
}

print("=== STARTING FINAL ANALYSIS ===")
t_start = time.time()

# -----------------------------------------------------------------------------
# STEP A: Train IF models on Dev (Exact replica from evaluate_final)
# -----------------------------------------------------------------------------
print("\n[Step A] Training reference IF models on 33 Dev factories...")
df_dev_raw = pd.read_csv(DEV_RAW_CSV)
df_dev_filt = df_dev_raw[df_dev_raw["quality_code"].isin(["Raw", "L"])].copy()
df_dev_filt["ts_dt"] = pd.to_datetime(df_dev_filt["timestamp"], errors="coerce")
df_dev_filt = df_dev_filt.dropna(subset=["ts_dt"]).sort_values(["factory_id", "parameter_id", "ts_dt"]).reset_index(drop=True)

df_dev_cto = pd.read_csv(DEV_CTO_CSV)
dev_cto_limits = {}
for _, r in df_dev_cto.iterrows():
    f = str(r["factory_id"])
    p = str(r["parameter"])
    m = r["maximum_limit"]
    if pd.notna(m) and m > 0:
        dev_cto_limits[(f, p)] = float(m)

all_dev_factories = sorted(list(DEV_FACTORY_MONTHS.keys()))
dev_clean_grids = {}
for (fac, param), g in df_dev_filt.groupby(["factory_id", "parameter_id"]):
    g_s = g.sort_values("ts_dt").reset_index(drop=True)
    dev_clean_grids[(fac, param)] = prepare_series(g_s, factory_id=fac)

dev_if_models = {}
for p in ["ETP-pH", "ETP-Flow", "ETP-BOD", "ETP-COD", "ETP-TSS"]:
    p_dfs = []
    for fac in all_dev_factories:
        grid = dev_clean_grids.get((fac, p))
        if grid is not None and len(grid) >= 16:
            feats = extract_if_features(grid).dropna()
            if not feats.empty:
                p_dfs.append(feats)
    if p_dfs:
        X = pd.concat(p_dfs, ignore_index=True)
        iso = IsolationForest(n_estimators=100, max_samples=min(2048, len(X)), random_state=42, n_jobs=1)
        iso.fit(X)
        dev_if_models[p] = iso

b2_dfs = []
for (fac, p), grid in dev_clean_grids.items():
    f = extract_b2_features(grid).dropna()
    if not f.empty:
        b2_dfs.append(f)
X_b2 = pd.concat(b2_dfs, ignore_index=True)
if len(X_b2) > 30000:
    X_b2 = X_b2.sample(30000, random_state=42)
iso_b2 = IsolationForest(n_estimators=100, max_samples=min(2048, len(X_b2)), random_state=42, n_jobs=1)
iso_b2.fit(X_b2)

# -----------------------------------------------------------------------------
# STEP B: Score Test Clean Telemetry & Compute Realized FA for EVERY Method
# -----------------------------------------------------------------------------
print("\n[Step B] Scoring Test Clean Series & Computing Realized False Alarms for all methods...")
test_raw_dict = {}
test_cto_limits = get_test_cto_limits()

for fac, fname in FACTORY_FILES.items():
    csv_path = os.path.join(UNSEEN_DIR, fname)
    df = pd.read_csv(csv_path)
    time_col = None
    for c in df.columns:
        if c.strip().lower() in ["time", "timestamp", "datetime"]:
            time_col = c
            break
    if time_col is None:
        time_col = df.columns[0]
    col_mapping = {time_col: "timestamp"}
    for c in df.columns:
        if c == time_col:
            continue
        c_lower = c.lower()
        if "bod" in c_lower:
            col_mapping[c] = "ETP-BOD"
        elif "cod" in c_lower:
            col_mapping[c] = "ETP-COD"
        elif "ph" in c_lower:
            col_mapping[c] = "ETP-pH"
        elif "flow" in c_lower:
            col_mapping[c] = "ETP-Flow"
        elif "tss" in c_lower:
            col_mapping[c] = "ETP-TSS"
    df = df.rename(columns=col_mapping)
    df["timestamp_dt"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp_dt"]).sort_values("timestamp_dt").reset_index(drop=True)

    for p in ["ETP-BOD", "ETP-COD", "ETP-pH", "ETP-Flow", "ETP-TSS"]:
        if p not in df.columns:
            df[p] = np.nan
        else:
            df[p] = pd.to_numeric(df[p], errors="coerce")

    long_rows = []
    for p in ["ETP-BOD", "ETP-COD", "ETP-pH", "ETP-Flow", "ETP-TSS"]:
        s = df[p]
        if s.notna().sum() > 0:
            sub = pd.DataFrame({
                "factory_id": fac,
                "parameter_id": p,
                "timestamp": df["timestamp"],
                "timestamp_dt": df["timestamp_dt"],
                "value": s,
                "quality_code": "Raw"
            })
            long_rows.append(sub)
    fac_df = pd.concat(long_rows, ignore_index=True)
    test_raw_dict[fac] = fac_df.sort_values(["parameter_id", "timestamp_dt"]).reset_index(drop=True)

test_f5_corr = {}
for fac, fac_df in test_raw_dict.items():
    test_f5_corr[(fac, 96)] = compute_f5_correlation(fac_df, w=96)
    test_f5_corr[(fac, 288)] = compute_f5_correlation(fac_df, w=288)

test_clean_grids = {}
test_clean_scores = {m: {} for m in METHODS_LIST}

for fac, fac_df in test_raw_dict.items():
    for param, g in fac_df.groupby("parameter_id"):
        g_s = g.sort_values("timestamp_dt").reset_index(drop=True)
        grid = prepare_series(g_s, factory_id=fac)
        test_clean_grids[(fac, param)] = grid

        vals = grid["value"].values
        ts_arr = grid["ts_dt"].values
        v_mask = ~np.isnan(vals)
        if_model = dev_if_models.get(param)

        f5_dict = {}
        for k_c, v_c in test_f5_corr.get((fac, 96), {}).items():
            if param in k_c:
                f5_dict["w96"] = v_c.reindex(grid["ts_dt"]).values
        for k_c, v_c in test_f5_corr.get((fac, 288), {}).items():
            if param in k_c:
                f5_dict["w288"] = v_c.reindex(grid["ts_dt"]).values

        calib = calibrate(grid, mode="blind", cto_limits=test_cto_limits, skip_if=False, if_model=if_model, f5_corr_dict=f5_dict, factory_id=fac)
        sc_df = score(grid, calib, if_model=if_model, cto_limits=test_cto_limits, f5_corr_dict=f5_dict, factory_id=fac)

        m1_candidates = [
            "F1_score_eps0", "F1_score_eps1", "F1_score_eps2",
            "F2_copypaste_w16_score", "F2_copypaste_w96_score", "F2_copypaste_w288_score",
            "F3_limit_w16_score", "F3_limit_w96_score", "F3_limit_w288_score",
            "F5_corr_w96_score", "F5_corr_w288_score",
            "F6_shift_w16_score", "F6_shift_w96_score", "F6_shift_w288_score",
            "F6_slope_w16_score", "F6_slope_w96_score", "F6_slope_w288_score",
            "if_score"
        ]
        m1_cols = [c for c in m1_candidates if c in sc_df.columns]
        with np.errstate(all='ignore'):
            m1_sc = np.nanmax(sc_df[m1_cols].values, axis=1)
        m1_sc[~v_mask] = np.nan
        test_clean_scores["M1_fusion"][(fac, param)] = (vals, m1_sc)

        test_clean_scores["F1_eps0"][(fac, param)] = (vals, sc_df["F1_score_eps0"].values)
        test_clean_scores["F1_eps1"][(fac, param)] = (vals, sc_df["F1_score_eps1"].values)
        test_clean_scores["F1_eps2"][(fac, param)] = (vals, sc_df["F1_score_eps2"].values)

        f2_cols = [c for c in sc_df.columns if c.startswith("F2_copypaste")]
        test_clean_scores["F2_copypaste"][(fac, param)] = (vals, np.nanmax(sc_df[f2_cols].values, axis=1) if f2_cols else np.full(len(vals), np.nan))

        f3_cols = [c for c in sc_df.columns if c.startswith("F3_limit")]
        test_clean_scores["F3_limit"][(fac, param)] = (vals, np.nanmax(sc_df[f3_cols].values, axis=1) if f3_cols else np.full(len(vals), np.nan))

        f5_cols = [c for c in sc_df.columns if c.startswith("F5_corr")]
        test_clean_scores["F5_corr"][(fac, param)] = (vals, np.nanmax(sc_df[f5_cols].values, axis=1) if f5_cols else np.full(len(vals), np.nan))

        f6_sh_cols = [c for c in sc_df.columns if c.startswith("F6_shift")]
        test_clean_scores["F6_shift"][(fac, param)] = (vals, np.nanmax(sc_df[f6_sh_cols].values, axis=1) if f6_sh_cols else np.full(len(vals), np.nan))

        f6_sl_cols = [c for c in sc_df.columns if c.startswith("F6_slope")]
        test_clean_scores["F6_slope"][(fac, param)] = (vals, np.nanmax(sc_df[f6_sl_cols].values, axis=1) if f6_sl_cols else np.full(len(vals), np.nan))

        test_clean_scores["IF_sensor"][(fac, param)] = (vals, sc_df["if_score"].values)
        test_clean_scores["B3_sensor_if"][(fac, param)] = (vals, sc_df["if_score"].values)
        test_clean_scores["B1_zscore"][(fac, param)] = (vals, compute_b1_robust_zscore(vals))

        b2_f = extract_b2_features(grid).dropna()
        b2_sc = np.full(len(vals), np.nan)
        if not b2_f.empty:
            b2_sc[b2_f.index] = -iso_b2.decision_function(b2_f)
        b2_sc[~v_mask] = np.nan
        test_clean_scores["B2_pooled_if"][(fac, param)] = (vals, b2_sc)

        cto_m = test_cto_limits.get((fac, param), np.nan)
        test_clean_scores["B4_legacy_rules"][(fac, param)] = (vals, compute_b4_rules(vals, param, cto_m))

# Realized false alarms on test clean copies for each method
method_clean_fa = []
for m in METHODS_LIST:
    tau = DEV_CUTOFFS_BUDGET1[m]
    fac_episodes = {}
    total_eps = 0
    for fac in FACTORY_FILES.keys():
        m_k = TEST_MONTHS_BY_FAC[fac]
        eps = sum(count_episodes_for_series(scs, vals, tau) for (f, p), (vals, scs) in test_clean_scores[m].items() if f == fac)
        fac_episodes[fac] = eps
        total_eps += eps
    realized_rate = total_eps / TOTAL_TEST_MONTHS
    method_clean_fa.append({
        "Method": m,
        "Dev_Calibrated_Tau": tau,
        "Cipla_Episodes": fac_episodes["Cipla"],
        "Glenmark_Episodes": fac_episodes["Glenmark"],
        "Indoco_Episodes": fac_episodes["Indoco"],
        "Zydus_Episodes": fac_episodes["Zydus"],
        "Total_False_Alert_Episodes": total_eps,
        "Realized_FA_per_Factory_Month": round(realized_rate, 3)
    })

df_clean_fa_all = pd.DataFrame(method_clean_fa)
df_clean_fa_all.to_csv(os.path.join(ANALYSIS_DIR, "realized_false_alarms_all_methods.csv"), index=False)
print("Saved realized_false_alarms_all_methods.csv.")
print(df_clean_fa_all[["Method", "Dev_Calibrated_Tau", "Total_False_Alert_Episodes", "Realized_FA_per_Factory_Month"]].to_string(index=False))

# -----------------------------------------------------------------------------
# STEP C: Per-Check x Per-Type Recall Matrix on Test (Seeds 101-105)
# -----------------------------------------------------------------------------
print("\n[Step C] Computing Per-Check x Per-Type Recall Matrix on Test...")
df_test_labels = pd.read_csv(os.path.join(FINAL_DIR, "labels.csv"))
df_test_labels["start_dt"] = pd.to_datetime(df_test_labels["start_ts"])
df_test_labels["end_dt"] = pd.to_datetime(df_test_labels["end_ts"])

test_injected_cache = {}
for seed in [101, 102, 103, 104, 105]:
    seed_dir = os.path.join(FINAL_DIR, "injected", f"seed_{seed}")
    for fac in FACTORY_FILES.keys():
        pq_path = os.path.join(seed_dir, f"{fac}.parquet")
        df_pq = pd.read_parquet(pq_path)
        df_pq["ts_dt"] = pd.to_datetime(df_pq["timestamp"])
        df_pq["factory_id"] = fac

        f5_pq_96 = compute_f5_correlation(df_pq, w=96)
        f5_pq_288 = compute_f5_correlation(df_pq, w=288)

        for param, g in df_pq.groupby("parameter_id"):
            g_s = g.sort_values("ts_dt").reset_index(drop=True)
            grid = prepare_series(g_s, factory_id=fac)
            vals = grid["value"].values
            ts_arr = grid["ts_dt"].values
            v_mask = ~np.isnan(vals)
            if_model = dev_if_models.get(param)

            f5_dict = {}
            for k_c, v_c in f5_pq_96.items():
                if param in k_c:
                    f5_dict["w96"] = v_c.reindex(grid["ts_dt"]).values
            for k_c, v_c in f5_pq_288.items():
                if param in k_c:
                    f5_dict["w288"] = v_c.reindex(grid["ts_dt"]).values

            calib = calibrate(grid, mode="blind", cto_limits=test_cto_limits, skip_if=False, if_model=if_model, f5_corr_dict=f5_dict, factory_id=fac)
            sc_df = score(grid, calib, if_model=if_model, cto_limits=test_cto_limits, f5_corr_dict=f5_dict, factory_id=fac)

            scs_dict = {}
            m1_candidates = [
                "F1_score_eps0", "F1_score_eps1", "F1_score_eps2",
                "F2_copypaste_w16_score", "F2_copypaste_w96_score", "F2_copypaste_w288_score",
                "F3_limit_w16_score", "F3_limit_w96_score", "F3_limit_w288_score",
                "F5_corr_w96_score", "F5_corr_w288_score",
                "F6_shift_w16_score", "F6_shift_w96_score", "F6_shift_w288_score",
                "F6_slope_w16_score", "F6_slope_w96_score", "F6_slope_w288_score",
                "if_score"
            ]
            m1_cols = [c for c in m1_candidates if c in sc_df.columns]
            with np.errstate(all='ignore'):
                m1_sc = np.nanmax(sc_df[m1_cols].values, axis=1)
            m1_sc[~v_mask] = np.nan
            scs_dict["M1_fusion"] = m1_sc

            scs_dict["F1_eps0"] = sc_df["F1_score_eps0"].values
            scs_dict["F1_eps1"] = sc_df["F1_score_eps1"].values
            scs_dict["F1_eps2"] = sc_df["F1_score_eps2"].values

            f2_cols = [c for c in sc_df.columns if c.startswith("F2_copypaste")]
            scs_dict["F2_copypaste"] = np.nanmax(sc_df[f2_cols].values, axis=1) if f2_cols else np.full(len(vals), np.nan)

            f3_cols = [c for c in sc_df.columns if c.startswith("F3_limit")]
            scs_dict["F3_limit"] = np.nanmax(sc_df[f3_cols].values, axis=1) if f3_cols else np.full(len(vals), np.nan)

            f5_cols = [c for c in sc_df.columns if c.startswith("F5_corr")]
            scs_dict["F5_corr"] = np.nanmax(sc_df[f5_cols].values, axis=1) if f5_cols else np.full(len(vals), np.nan)

            f6_sh_cols = [c for c in sc_df.columns if c.startswith("F6_shift")]
            scs_dict["F6_shift"] = np.nanmax(sc_df[f6_sh_cols].values, axis=1) if f6_sh_cols else np.full(len(vals), np.nan)

            f6_sl_cols = [c for c in sc_df.columns if c.startswith("F6_slope")]
            scs_dict["F6_slope"] = np.nanmax(sc_df[f6_sl_cols].values, axis=1) if f6_sl_cols else np.full(len(vals), np.nan)

            scs_dict["IF_sensor"] = sc_df["if_score"].values
            scs_dict["B3_sensor_if"] = sc_df["if_score"].values
            scs_dict["B1_zscore"] = compute_b1_robust_zscore(vals)

            b2_f = extract_b2_features(grid).dropna()
            b2_sc = np.full(len(vals), np.nan)
            if not b2_f.empty:
                b2_sc[b2_f.index] = -iso_b2.decision_function(b2_f)
            b2_sc[~v_mask] = np.nan
            scs_dict["B2_pooled_if"] = b2_sc

            cto_m = test_cto_limits.get((fac, param), np.nan)
            scs_dict["B4_legacy_rules"] = compute_b4_rules(vals, param, cto_m)

            for m_k in scs_dict:
                scs_dict[m_k][~v_mask] = np.nan

            test_injected_cache[(seed, fac, param)] = (ts_arr, vals, scs_dict)

# Match events on Test
test_series_alert_episodes = {m: {} for m in METHODS_LIST}
for m in METHODS_LIST:
    tau = DEV_CUTOFFS_BUDGET1[m]
    for (seed, fac, param), (ts_arr, vals, scs_dict) in test_injected_cache.items():
        sc_arr = scs_dict[m]
        test_series_alert_episodes[m][(seed, fac, param)] = extract_alert_episodes(sc_arr, vals, tau, ts_arr)

test_det_records = {m: [] for m in METHODS_LIST}
labels_records = df_test_labels.to_dict("records")
for row in labels_records:
    seed = row["seed"]
    fac = row["factory_id"]
    params_list = [p.strip() for p in str(row["params"]).split(",")]
    s_dt = row["start_dt"]
    e_dt = row["end_dt"]
    e_dt_2h = e_dt + pd.Timedelta(hours=2)

    for m in METHODS_LIST:
        is_det = False
        for p in params_list:
            eps = test_series_alert_episodes[m].get((seed, fac, p), [])
            for ep in eps:
                if (ep["end_ts"] >= s_dt) and (ep["start_ts"] <= e_dt_2h):
                    is_det = True
                    break
            if is_det:
                break
        test_det_records[m].append(is_det)

for m in METHODS_LIST:
    df_test_labels[f"det_{m}"] = test_det_records[m]

# Compute test per-check x per-type recall matrix
types_list = ["T1", "T2", "T3", "T4", "T5", "T6", "T7"]
test_matrix_rows = []
for m in METHODS_LIST:
    row_dict = {"Method": m}
    for t in types_list:
        sub = df_test_labels[df_test_labels["type"] == t]
        tot = len(sub)
        det = int(sub[f"det_{m}"].sum())
        rec = det / max(tot, 1)
        row_dict[f"{t}_Recall"] = round(rec, 4)
        row_dict[f"{t}_Detected"] = det
        row_dict[f"{t}_Total"] = tot
    # Overall Headline
    head_sub = df_test_labels[df_test_labels["type"] != "T6"]
    tot_h = len(head_sub)
    det_h = int(head_sub[f"det_{m}"].sum())
    row_dict["Headline_Recall"] = round(det_h / max(tot_h, 1), 4)
    row_dict["Headline_Detected"] = det_h
    row_dict["Headline_Total"] = tot_h
    test_matrix_rows.append(row_dict)

df_test_matrix = pd.DataFrame(test_matrix_rows)
df_test_matrix.to_csv(os.path.join(ANALYSIS_DIR, "per_check_per_type_recall_test.csv"), index=False)
print("Saved per_check_per_type_recall_test.csv.")

# -----------------------------------------------------------------------------
# STEP D: Per-Check x Per-Type Recall Matrix on Dev Run 2b (Seeds 1-5)
# -----------------------------------------------------------------------------
print("\n[Step D] Computing Per-Check x Per-Type Recall Matrix on Dev Run 2b...")
df_dev_labels = pd.read_csv(os.path.join(DEV_INJECTED_DIR, "labels.csv"))
df_dev_labels["start_dt"] = pd.to_datetime(df_dev_labels["start_ts"])
df_dev_labels["end_dt"] = pd.to_datetime(df_dev_labels["end_ts"])

# Exclude 10 known violations from T6
known_viol_path = os.path.join(REPO_ROOT, "validation_v2", "injector", "known_violations.csv")
if os.path.exists(known_viol_path):
    df_kv = pd.read_csv(known_viol_path)
    excl_ids = set(df_kv["event_id"].unique())
    df_dev_labels = df_dev_labels[~df_dev_labels["event_id"].isin(excl_ids)].reset_index(drop=True)

# Train 33-fold LOFO models for Dev scoring
lofo_sensor_models = {}
lofo_pooled_models = {}
for held_out_fac in all_dev_factories:
    train_facs = [f for f in all_dev_factories if f != held_out_fac]
    lofo_sensor_models[held_out_fac] = {}
    for p in ["ETP-pH", "ETP-Flow", "ETP-BOD", "ETP-COD", "ETP-TSS"]:
        p_dfs = []
        for f in train_facs:
            grid = dev_clean_grids.get((f, p))
            if grid is not None and len(grid) >= 16:
                feats = extract_if_features(grid).dropna()
                if not feats.empty:
                    p_dfs.append(feats)
        if p_dfs:
            X = pd.concat(p_dfs, ignore_index=True)
            iso = IsolationForest(n_estimators=100, max_samples=min(2048, len(X)), random_state=42, n_jobs=1)
            iso.fit(X)
            lofo_sensor_models[held_out_fac][p] = iso

    b2_train_dfs = []
    for f in train_facs:
        for p in ["ETP-pH", "ETP-Flow", "ETP-BOD", "ETP-COD", "ETP-TSS"]:
            grid = dev_clean_grids.get((f, p))
            if grid is not None:
                feats = extract_b2_features(grid).dropna()
                if not feats.empty:
                    b2_train_dfs.append(feats)
    if b2_train_dfs:
        X_b2 = pd.concat(b2_train_dfs, ignore_index=True)
        if len(X_b2) > 30000:
            X_b2 = X_b2.sample(30000, random_state=42)
        iso_b2 = IsolationForest(n_estimators=100, max_samples=min(2048, len(X_b2)), random_state=42, n_jobs=1)
        iso_b2.fit(X_b2)
        lofo_pooled_models[held_out_fac] = iso_b2

# Score Dev Clean Telemetry
dev_clean_scores = {m: {} for m in METHODS_LIST}
dev_f5_cache = {}
for fac in all_dev_factories:
    sub_fac = df_dev_filt[df_dev_filt["factory_id"] == fac]
    dev_f5_cache[(fac, 96)] = compute_f5_correlation(sub_fac, w=96)
    dev_f5_cache[(fac, 288)] = compute_f5_correlation(sub_fac, w=288)

for (fac, param), grid in dev_clean_grids.items():
    vals = grid["value"].values
    ts_arr = grid["ts_dt"].values
    v_mask = ~np.isnan(vals)
    if_model = lofo_sensor_models[fac].get(param)

    f5_dict = {}
    for k_c, v_c in dev_f5_cache.get((fac, 96), {}).items():
        if param in k_c:
            f5_dict["w96"] = v_c.reindex(grid["ts_dt"]).values
    for k_c, v_c in dev_f5_cache.get((fac, 288), {}).items():
        if param in k_c:
            f5_dict["w288"] = v_c.reindex(grid["ts_dt"]).values

    calib = calibrate(grid, mode="blind", cto_limits=dev_cto_limits, skip_if=False, if_model=if_model, f5_corr_dict=f5_dict, factory_id=fac)
    sc_df = score(grid, calib, if_model=if_model, cto_limits=dev_cto_limits, f5_corr_dict=f5_dict, factory_id=fac)

    m1_candidates = [
        "F1_score_eps0", "F1_score_eps1", "F1_score_eps2",
        "F2_copypaste_w16_score", "F2_copypaste_w96_score", "F2_copypaste_w288_score",
        "F3_limit_w16_score", "F3_limit_w96_score", "F3_limit_w288_score",
        "F5_corr_w96_score", "F5_corr_w288_score",
        "F6_shift_w16_score", "F6_shift_w96_score", "F6_shift_w288_score",
        "F6_slope_w16_score", "F6_slope_w96_score", "F6_slope_w288_score",
        "if_score"
    ]
    m1_cols = [c for c in m1_candidates if c in sc_df.columns]
    with np.errstate(all='ignore'):
        m1_sc = np.nanmax(sc_df[m1_cols].values, axis=1)
    m1_sc[~v_mask] = np.nan
    dev_clean_scores["M1_fusion"][(fac, param)] = (vals, m1_sc)

    dev_clean_scores["F1_eps0"][(fac, param)] = (vals, sc_df["F1_score_eps0"].values)
    dev_clean_scores["F1_eps1"][(fac, param)] = (vals, sc_df["F1_score_eps1"].values)
    dev_clean_scores["F1_eps2"][(fac, param)] = (vals, sc_df["F1_score_eps2"].values)

    f2_cols = [c for c in sc_df.columns if c.startswith("F2_copypaste")]
    dev_clean_scores["F2_copypaste"][(fac, param)] = (vals, np.nanmax(sc_df[f2_cols].values, axis=1) if f2_cols else np.full(len(vals), np.nan))

    f3_cols = [c for c in sc_df.columns if c.startswith("F3_limit")]
    dev_clean_scores["F3_limit"][(fac, param)] = (vals, np.nanmax(sc_df[f3_cols].values, axis=1) if f3_cols else np.full(len(vals), np.nan))

    f5_cols = [c for c in sc_df.columns if c.startswith("F5_corr")]
    dev_clean_scores["F5_corr"][(fac, param)] = (vals, np.nanmax(sc_df[f5_cols].values, axis=1) if f5_cols else np.full(len(vals), np.nan))

    f6_sh_cols = [c for c in sc_df.columns if c.startswith("F6_shift")]
    dev_clean_scores["F6_shift"][(fac, param)] = (vals, np.nanmax(sc_df[f6_sh_cols].values, axis=1) if f6_sh_cols else np.full(len(vals), np.nan))

    f6_sl_cols = [c for c in sc_df.columns if c.startswith("F6_slope")]
    dev_clean_scores["F6_slope"][(fac, param)] = (vals, np.nanmax(sc_df[f6_sl_cols].values, axis=1) if f6_sl_cols else np.full(len(vals), np.nan))

    dev_clean_scores["IF_sensor"][(fac, param)] = (vals, sc_df["if_score"].values)
    dev_clean_scores["B3_sensor_if"][(fac, param)] = (vals, sc_df["if_score"].values)
    dev_clean_scores["B1_zscore"][(fac, param)] = (vals, compute_b1_robust_zscore(vals))

    b2_m = lofo_pooled_models[fac]
    b2_f = extract_b2_features(grid).dropna()
    b2_sc = np.full(len(vals), np.nan)
    if b2_m is not None and not b2_f.empty:
        b2_sc[b2_f.index] = -b2_m.decision_function(b2_f)
    b2_sc[~v_mask] = np.nan
    dev_clean_scores["B2_pooled_if"][(fac, param)] = (vals, b2_sc)

    cto_m = dev_cto_limits.get((fac, param), np.nan)
    dev_clean_scores["B4_legacy_rules"][(fac, param)] = (vals, compute_b4_rules(vals, param, cto_m))

# Calibrate dev thresholds for budget 1 (target eps = 328)
dev_run2b_taus = {}
target_eps_dev = int(round(1.0 * TOTAL_DEV_FACTORY_MONTHS))
for m in METHODS_LIST:
    dev_run2b_taus[m] = calibrate_tau_for_training(dev_clean_scores[m], target_eps_dev)

# Score Dev Injected Series
dev_injected_cache = {}
for seed in range(1, 6):
    seed_dir = os.path.join(DEV_INJECTED_DIR, f"seed_{seed}")
    for fname in os.listdir(seed_dir):
        if not fname.endswith(".parquet"):
            continue
        fac = fname.replace(".parquet", "")
        pq_path = os.path.join(seed_dir, fname)
        df_pq = pd.read_parquet(pq_path)
        df_pq["ts_dt"] = pd.to_datetime(df_pq["timestamp"])
        df_pq["factory_id"] = fac

        f5_pq_96 = compute_f5_correlation(df_pq, w=96)
        f5_pq_288 = compute_f5_correlation(df_pq, w=288)

        for param, g in df_pq.groupby("parameter_id"):
            g_s = g.sort_values("ts_dt").reset_index(drop=True)
            grid = prepare_series(g_s, factory_id=fac)
            vals = grid["value"].values
            ts_arr = grid["ts_dt"].values
            v_mask = ~np.isnan(vals)
            if_model = lofo_sensor_models[fac].get(param)

            f5_dict = {}
            for k_c, v_c in f5_pq_96.items():
                if param in k_c:
                    f5_dict["w96"] = v_c.reindex(grid["ts_dt"]).values
            for k_c, v_c in f5_pq_288.items():
                if param in k_c:
                    f5_dict["w288"] = v_c.reindex(grid["ts_dt"]).values

            calib = calibrate(grid, mode="blind", cto_limits=dev_cto_limits, skip_if=False, if_model=if_model, f5_corr_dict=f5_dict, factory_id=fac)
            sc_df = score(grid, calib, if_model=if_model, cto_limits=dev_cto_limits, f5_corr_dict=f5_dict, factory_id=fac)

            scs_dict = {}
            m1_candidates = [
                "F1_score_eps0", "F1_score_eps1", "F1_score_eps2",
                "F2_copypaste_w16_score", "F2_copypaste_w96_score", "F2_copypaste_w288_score",
                "F3_limit_w16_score", "F3_limit_w96_score", "F3_limit_w288_score",
                "F5_corr_w96_score", "F5_corr_w288_score",
                "F6_shift_w16_score", "F6_shift_w96_score", "F6_shift_w288_score",
                "F6_slope_w16_score", "F6_slope_w96_score", "F6_slope_w288_score",
                "if_score"
            ]
            m1_cols = [c for c in m1_candidates if c in sc_df.columns]
            with np.errstate(all='ignore'):
                m1_sc = np.nanmax(sc_df[m1_cols].values, axis=1)
            m1_sc[~v_mask] = np.nan
            scs_dict["M1_fusion"] = m1_sc

            scs_dict["F1_eps0"] = sc_df["F1_score_eps0"].values
            scs_dict["F1_eps1"] = sc_df["F1_score_eps1"].values
            scs_dict["F1_eps2"] = sc_df["F1_score_eps2"].values

            f2_cols = [c for c in sc_df.columns if c.startswith("F2_copypaste")]
            scs_dict["F2_copypaste"] = np.nanmax(sc_df[f2_cols].values, axis=1) if f2_cols else np.full(len(vals), np.nan)

            f3_cols = [c for c in sc_df.columns if c.startswith("F3_limit")]
            scs_dict["F3_limit"] = np.nanmax(sc_df[f3_cols].values, axis=1) if f3_cols else np.full(len(vals), np.nan)

            f5_cols = [c for c in sc_df.columns if c.startswith("F5_corr")]
            scs_dict["F5_corr"] = np.nanmax(sc_df[f5_cols].values, axis=1) if f5_cols else np.full(len(vals), np.nan)

            f6_sh_cols = [c for c in sc_df.columns if c.startswith("F6_shift")]
            scs_dict["F6_shift"] = np.nanmax(sc_df[f6_sh_cols].values, axis=1) if f6_sh_cols else np.full(len(vals), np.nan)

            f6_sl_cols = [c for c in sc_df.columns if c.startswith("F6_slope")]
            scs_dict["F6_slope"] = np.nanmax(sc_df[f6_sl_cols].values, axis=1) if f6_sl_cols else np.full(len(vals), np.nan)

            scs_dict["IF_sensor"] = sc_df["if_score"].values
            scs_dict["B3_sensor_if"] = sc_df["if_score"].values
            scs_dict["B1_zscore"] = compute_b1_robust_zscore(vals)

            b2_m = lofo_pooled_models[fac]
            b2_f = extract_b2_features(grid).dropna()
            b2_sc = np.full(len(vals), np.nan)
            if b2_m is not None and not b2_f.empty:
                b2_sc[b2_f.index] = -b2_m.decision_function(b2_f)
            b2_sc[~v_mask] = np.nan
            scs_dict["B2_pooled_if"] = b2_sc

            cto_m = dev_cto_limits.get((fac, param), np.nan)
            scs_dict["B4_legacy_rules"] = compute_b4_rules(vals, param, cto_m)

            for m_k in scs_dict:
                scs_dict[m_k][~v_mask] = np.nan

            dev_injected_cache[(seed, fac, param)] = (ts_arr, vals, scs_dict)

# Match events on Dev
dev_series_alert_episodes = {m: {} for m in METHODS_LIST}
for m in METHODS_LIST:
    tau = dev_run2b_taus[m]
    for (seed, fac, param), (ts_arr, vals, scs_dict) in dev_injected_cache.items():
        sc_arr = scs_dict[m]
        dev_series_alert_episodes[m][(seed, fac, param)] = extract_alert_episodes(sc_arr, vals, tau, ts_arr)

dev_det_records = {m: [] for m in METHODS_LIST}
labels_records_dev = df_dev_labels.to_dict("records")
for row in labels_records_dev:
    seed = row["seed"]
    fac = row["factory_id"]
    params_list = [p.strip() for p in str(row["params"]).split(",")]
    s_dt = row["start_dt"]
    e_dt = row["end_dt"]
    e_dt_2h = e_dt + pd.Timedelta(hours=2)

    for m in METHODS_LIST:
        is_det = False
        for p in params_list:
            eps = dev_series_alert_episodes[m].get((seed, fac, p), [])
            for ep in eps:
                if (ep["end_ts"] >= s_dt) and (ep["start_ts"] <= e_dt_2h):
                    is_det = True
                    break
            if is_det:
                break
        dev_det_records[m].append(is_det)

for m in METHODS_LIST:
    df_dev_labels[f"det_{m}"] = dev_det_records[m]

# Compute dev per-check x per-type recall matrix
dev_matrix_rows = []
for m in METHODS_LIST:
    row_dict = {"Method": m}
    for t in types_list:
        sub = df_dev_labels[df_dev_labels["type"] == t]
        tot = len(sub)
        det = int(sub[f"det_{m}"].sum())
        rec = det / max(tot, 1)
        row_dict[f"{t}_Recall"] = round(rec, 4)
        row_dict[f"{t}_Detected"] = det
        row_dict[f"{t}_Total"] = tot
    head_sub = df_dev_labels[df_dev_labels["type"] != "T6"]
    tot_h = len(head_sub)
    det_h = int(head_sub[f"det_{m}"].sum())
    row_dict["Headline_Recall"] = round(det_h / max(tot_h, 1), 4)
    row_dict["Headline_Detected"] = det_h
    row_dict["Headline_Total"] = tot_h
    dev_matrix_rows.append(row_dict)

df_dev_matrix = pd.DataFrame(dev_matrix_rows)
df_dev_matrix.to_csv(os.path.join(ANALYSIS_DIR, "per_check_per_type_recall_dev_run2b.csv"), index=False)
print("Saved per_check_per_type_recall_dev_run2b.csv.")

# -----------------------------------------------------------------------------
# STEP E: Post-Hoc Sensitivity Analysis on Test Telemetry
# -----------------------------------------------------------------------------
print("\n[Step E] Computing Post-Hoc Test Cutoff (1 alert/month on test clean copies)...")
target_eps_test = int(round(1.0 * TOTAL_TEST_MONTHS))  # 24 episodes
post_hoc_tau_m1 = calibrate_tau_for_training(test_clean_scores["M1_fusion"], target_eps_test)

# Realized episodes on clean copies at post-hoc tau
post_hoc_clean_eps = sum(count_episodes_for_series(scs, vals, post_hoc_tau_m1) for (f, p), (vals, scs) in test_clean_scores["M1_fusion"].items())
post_hoc_realized_rate = post_hoc_clean_eps / TOTAL_TEST_MONTHS

# Extract alert episodes on injected test copies using post-hoc tau
post_hoc_injected_episodes = {}
for (seed, fac, param), (ts_arr, vals, scs_dict) in test_injected_cache.items():
    sc_arr = scs_dict["M1_fusion"]
    post_hoc_injected_episodes[(seed, fac, param)] = extract_alert_episodes(sc_arr, vals, post_hoc_tau_m1, ts_arr)

post_hoc_det = []
for row in labels_records:
    seed = row["seed"]
    fac = row["factory_id"]
    params_list = [p.strip() for p in str(row["params"]).split(",")]
    s_dt = row["start_dt"]
    e_dt = row["end_dt"]
    e_dt_2h = e_dt + pd.Timedelta(hours=2)

    is_det = False
    for p in params_list:
        eps = post_hoc_injected_episodes.get((seed, fac, p), [])
        for ep in eps:
            if (ep["end_ts"] >= s_dt) and (ep["start_ts"] <= e_dt_2h):
                is_det = True
                break
        if is_det:
            break
    post_hoc_det.append(is_det)

df_test_labels["det_m1_post_hoc"] = post_hoc_det
df_head_post = df_test_labels[df_test_labels["type"] != "T6"].assign(is_detected=df_test_labels[df_test_labels["type"] != "T6"]["det_m1_post_hoc"])
pt_post, low_post, high_post = compute_cluster_bootstrap(df_head_post)

post_hoc_summary = pd.DataFrame([{
    "Evaluation_Type": "POST-HOC SENSITIVITY (Clean Test Calibrated; not replacing primary)",
    "Target_Budget_alerts_mo": 1.0,
    "Post_Hoc_Tau": round(post_hoc_tau_m1, 4),
    "Clean_False_Alert_Episodes": post_hoc_clean_eps,
    "Realized_FA_Rate_per_Month": round(post_hoc_realized_rate, 3),
    "Headline_Events_Total": len(df_head_post),
    "Headline_Events_Detected": int(df_head_post["is_detected"].sum()),
    "Headline_Recall": round(pt_post, 4),
    "95% CI Lower": round(low_post, 4),
    "95% CI Upper": round(high_post, 4)
}])
post_hoc_summary.to_csv(os.path.join(ANALYSIS_DIR, "post_hoc_sensitivity.csv"), index=False)
print("Saved post_hoc_sensitivity.csv.")
print(post_hoc_summary.to_string(index=False))

print(f"\nAll calculations completed in {time.time()-t_start:.2f}s.")
