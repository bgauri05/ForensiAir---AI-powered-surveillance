"""
ANALYSIS 2B (read-only, dev only).
Development Diagnostic for Step 4+5 (Run 2b).
Evaluates M1 at frozen cutoff tau = 3.7955 on dev clean telemetry under:
1. KEEP ERROR ROWS: Error / Out of Range rows kept as-is (as in test CSVs).
2. SHORT SERIES: Truncated to first 6 months.
3. DISPERSION: Per-factory dispersion on default run.
"""

import os
import sys
import time
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
RAW_CSV = os.path.join(REPO_ROOT, "Data", "RawData", "monitoring_data(raw).csv")
CTO_CSV = os.path.join(REPO_ROOT, "Original Data", "consent_limits.csv")
RUN2B_DIR = os.path.join(REPO_ROOT, "validation_v2", "runs", "run2b")
OUT_DIR = os.path.join(RUN2B_DIR, "analysis")
os.makedirs(OUT_DIR, exist_ok=True)

sys.path.insert(0, os.path.join(REPO_ROOT, "validation_v2", "detector"))
from detector import (
    prepare_series,
    compute_check_statistics,
    compute_f5_correlation,
    calibrate,
    score,
    extract_if_features,
    calc_mad,
    get_resolution_step,
    extract_quasi_flat_runs
)

FACTORY_MONTHS = {
    'site_1131': 12.02, 'site_1138': 11.77, 'site_1167': 10.01, 'site_1200': 11.88,
    'site_1203': 12.02, 'site_1221': 11.95, 'site_1232': 11.43, 'site_1247': 12.02,
    'site_1256': 0.75,  'site_1257': 12.02, 'site_1259': 4.76,  'site_1264': 12.02,
    'site_1280': 11.98, 'site_1281': 12.02, 'site_1284': 11.51, 'site_1285': 12.02,
    'site_1310': 12.02, 'site_1321': 12.02, 'site_1369': 12.02, 'site_1376': 12.02,
    'site_1561': 12.02, 'site_1569': 1.91,  'site_1581': 11.24, 'site_1668': 12.02,
    'site_1756': 12.02, 'site_1787': 12.02, 'site_1789': 12.02, 'site_1799': 12.02,
    'site_1905': 8.13,  'site_1909': 2.80,  'site_2070': 0.11,  'site_887': 12.02,
    'site_982': 1.02
}
TOTAL_FACTORY_MONTHS = sum(FACTORY_MONTHS.values())  # 327.61
FROZEN_TAU = 3.7955

def extract_alert_episodes(scores: np.ndarray, values: np.ndarray, tau: float, timestamps: np.ndarray):
    """Contiguous rows with score >= tau, merging gaps <= 16 rows."""
    mask = ~np.isnan(values) & ~np.isnan(scores) & (scores >= tau)
    if not np.any(mask):
        return []
    indices = np.where(mask)[0]
    episodes = []
    ep_start = indices[0]
    ep_end = indices[0]
    for idx in indices[1:]:
        if idx - ep_end - 1 <= 16:
            ep_end = idx
        else:
            episodes.append({
                'start_idx': ep_start,
                'end_idx': ep_end,
                'start_ts': timestamps[ep_start],
                'end_ts': timestamps[ep_end]
            })
            ep_start = idx
            ep_end = idx
    episodes.append({
        'start_idx': ep_start,
        'end_idx': ep_end,
        'start_ts': timestamps[ep_start],
        'end_ts': timestamps[ep_end]
    })
    return episodes

def extract_b2_features(df_series: pd.DataFrame) -> pd.DataFrame:
    vals = df_series["value"].copy()
    feats = pd.DataFrame(index=df_series.index)
    feats["val"] = vals
    feats["rolling_mean_16"] = vals.rolling(16, min_periods=1).mean()
    feats["rolling_std_16"] = vals.rolling(16, min_periods=1).std().fillna(0.0)
    feats["diff_1"] = vals.diff(1).abs().fillna(0.0)
    feats["z_16"] = (vals - feats["rolling_mean_16"]) / (feats["rolling_std_16"] + 1e-4)
    return feats

def main():
    print("==========================================================================")
    print(" ANALYSIS 2B: DEVELOPMENT DIAGNOSTIC (RUN 2B POST-HOC AUDIT)")
    print(f" Frozen M1 Dev Cutoff: tau = {FROZEN_TAU}")
    print("==========================================================================")

    # 1. Load Data & CTO Limits
    print("\n1. Loading Raw Data & CTO Limits...")
    t0 = time.time()
    df_raw = pd.read_csv(RAW_CSV)
    df_cto = pd.read_csv(CTO_CSV)
    cto_limits = {}
    for _, r in df_cto.iterrows():
        if pd.notna(r["maximum_limit"]) and r["maximum_limit"] > 0:
            cto_limits[(str(r["factory_id"]), str(r["parameter"]))] = float(r["maximum_limit"])

    df_raw["ts_dt"] = pd.to_datetime(df_raw["timestamp"])
    df_raw = df_raw.sort_values(["factory_id", "parameter_id", "ts_dt"]).reset_index(drop=True)

    # Clean subset (default filtering)
    allowed_qc = ["Raw", "L"]
    df_clean = df_raw[df_raw["quality_code"].isin(allowed_qc)].copy()
    all_dev_factories = sorted(df_clean["factory_id"].unique())
    sensors = ["ETP-pH", "ETP-Flow", "ETP-BOD", "ETP-COD", "ETP-TSS"]
    print(f"Loaded raw data ({len(df_raw)} rows) in {time.time()-t0:.2f}s across {len(all_dev_factories)} factories.")

    # 2. Pre-extract clean features & Train 33 LOFO Models
    print("\n2. Pre-extracting Clean Features & Training 33 LOFO Models...")
    t0 = time.time()
    clean_series_dict = {}
    clean_if_feats = {}
    for (fac, param), g in df_clean.groupby(["factory_id", "parameter_id"]):
        grid = prepare_series(g, factory_id=fac)
        if not grid.empty:
            clean_series_dict[(fac, param)] = grid
            clean_if_feats[(fac, param)] = extract_if_features(grid).dropna()

    lofo_sensor_models = {}
    for k, held_out_fac in enumerate(all_dev_factories, 1):
        train_facs = [f for f in all_dev_factories if f != held_out_fac]
        s_models = {}
        for s in sensors:
            train_dfs = [clean_if_feats[(f, s)] for f in train_facs if (f, s) in clean_if_feats]
            if train_dfs:
                X_train = pd.concat(train_dfs, ignore_index=True)
                if len(X_train) > 25000:
                    X_train = X_train.sample(25000, random_state=42)
                iso = IsolationForest(n_estimators=100, max_samples=min(2048, len(X_train)), random_state=42, n_jobs=1)
                iso.fit(X_train)
                s_models[s] = iso
        lofo_sensor_models[held_out_fac] = s_models
    print(f"Trained 33 LOFO models in {time.time()-t0:.2f}s.")

    # Helper function to score a set of series grids and extract M1
    def score_factories_m1(factory_grids_dict, corr_df):
        # Pre-compute correlation caches
        f5_cache = {}
        for fac in all_dev_factories:
            sub = corr_df[corr_df["factory_id"] == fac]
            if not sub.empty:
                f5_cache[(fac, 96)] = compute_f5_correlation(sub, w=96)
                f5_cache[(fac, 288)] = compute_f5_correlation(sub, w=288)

        m1_scores = {}
        m1_candidates = [
            "F1_score_eps0", "F1_score_eps1", "F1_score_eps2",
            "F2_copypaste_w16_score", "F2_copypaste_w96_score", "F2_copypaste_w288_score",
            "F3_limit_w16_score", "F3_limit_w96_score", "F3_limit_w288_score",
            "F5_corr_w96_score", "F5_corr_w288_score",
            "F6_shift_w16_score", "F6_shift_w96_score", "F6_shift_w288_score",
            "F6_slope_w16_score", "F6_slope_w96_score", "F6_slope_w288_score",
            "if_score"
        ]

        for (fac, param), grid in factory_grids_dict.items():
            vals = grid["value"].values
            v_mask = ~np.isnan(vals)
            if not np.any(v_mask):
                continue
            if_model = lofo_sensor_models[fac].get(param)

            f5_dict = {}
            for k_c, v_c in f5_cache.get((fac, 96), {}).items():
                if param in k_c:
                    f5_dict["w96"] = v_c.reindex(grid["ts_dt"]).values
            for k_c, v_c in f5_cache.get((fac, 288), {}).items():
                if param in k_c:
                    f5_dict["w288"] = v_c.reindex(grid["ts_dt"]).values

            calib = calibrate(
                grid, mode="blind", cto_limits=cto_limits, skip_if=False,
                if_model=if_model, f5_corr_dict=f5_dict, factory_id=fac
            )
            sc_df = score(
                grid, calib, if_model=if_model, cto_limits=cto_limits,
                f5_corr_dict=f5_dict, factory_id=fac
            )
            m1_cols = [c for c in m1_candidates if c in sc_df.columns]
            with np.errstate(all='ignore'):
                m1_arr = np.nanmax(sc_df[m1_cols].values, axis=1)
            m1_arr[~v_mask] = np.nan
            m1_scores[(fac, param)] = (grid, m1_arr)

        return m1_scores

    # 3. BASELINE (DEFAULT DEV RUN): Score clean series at tau = FROZEN_TAU
    print("\n3. Evaluating Baseline Clean Run at frozen tau = 3.7955...")
    t0 = time.time()
    baseline_scores = score_factories_m1(clean_series_dict, df_clean)
    baseline_episodes_by_fac = {f: [] for f in all_dev_factories}
    for (fac, param), (grid, sc_arr) in baseline_scores.items():
        eps = extract_alert_episodes(sc_arr, grid["value"].values, FROZEN_TAU, grid["ts_dt"].values)
        for ep in eps:
            ep["param"] = param
            ep["factory_id"] = fac
            baseline_episodes_by_fac[fac].append(ep)

    baseline_records = []
    for fac in all_dev_factories:
        n_eps = len(baseline_episodes_by_fac[fac])
        mo = FACTORY_MONTHS[fac]
        rate = n_eps / mo
        baseline_records.append({
            "factory_id": fac, "factory_months": mo,
            "episodes": n_eps, "rate_per_month": rate
        })
    df_base = pd.DataFrame(baseline_records)
    print(f"Baseline evaluated in {time.time()-t0:.2f}s:")
    print(f"  Total alert episodes: {df_base['episodes'].sum()}")
    print(f"  Unweighted rate per month: mean={df_base['rate_per_month'].mean():.4f}, median={df_base['rate_per_month'].median():.4f}, min={df_base['rate_per_month'].min():.4f}, max={df_base['rate_per_month'].max():.4f}")

    # 4. TASK 1: KEEP ERROR ROWS
    print("\n4. Running Task 1: KEEP ERROR ROWS (Error / Out of Range rows kept as-is)...")
    t0 = time.time()
    # Mark which rows in df_raw have quality_code in Error / Out of Range
    df_raw["is_error_qc"] = df_raw["quality_code"].isin(["Error", "Out of Range"])

    # Build grids keeping all rows (drop quality_code column so prepare_series keeps all rows)
    keep_error_grids = {}
    error_qc_timestamps = {}
    for (fac, param), g in df_raw.groupby(["factory_id", "parameter_id"]):
        err_ts = set(g.loc[g["is_error_qc"], "ts_dt"])
        error_qc_timestamps[(fac, param)] = err_ts
        # Pass dataframe without quality_code column
        g_for_grid = g.drop(columns=["quality_code"]).copy()
        grid = prepare_series(g_for_grid, factory_id=fac)
        if not grid.empty:
            keep_error_grids[(fac, param)] = grid

    # Score with error rows kept
    keep_error_scores = score_factories_m1(keep_error_grids, df_raw.drop(columns=["quality_code"]))
    keep_error_episodes_by_fac = {f: [] for f in all_dev_factories}
    for (fac, param), (grid, sc_arr) in keep_error_scores.items():
        eps = extract_alert_episodes(sc_arr, grid["value"].values, FROZEN_TAU, grid["ts_dt"].values)
        err_ts_set = error_qc_timestamps.get((fac, param), set())
        for ep in eps:
            ep["param"] = param
            ep["factory_id"] = fac
            # Check overlap with kept Error-tagged rows
            # Episode range [start_ts, end_ts]
            ep_grid = grid.iloc[ep["start_idx"]:ep["end_idx"]+1]
            ep_ts_list = set(ep_grid["ts_dt"])
            ep["overlaps_error_row"] = bool(ep_ts_list.intersection(err_ts_set))
            keep_error_episodes_by_fac[fac].append(ep)

    # Analysis of Task 1 alerts vs Baseline
    task1_records = []
    all_keep_error_episodes = []
    for fac in all_dev_factories:
        eps = keep_error_episodes_by_fac[fac]
        all_keep_error_episodes.extend(eps)
        n_eps = len(eps)
        mo = FACTORY_MONTHS[fac]
        rate = n_eps / mo
        n_overlap_err = sum(1 for e in eps if e["overlaps_error_row"])
        base_n = len(baseline_episodes_by_fac[fac])
        task1_records.append({
            "factory_id": fac,
            "factory_months": mo,
            "baseline_episodes": base_n,
            "keep_error_episodes": n_eps,
            "extra_episodes": n_eps - base_n,
            "episodes_overlapping_error_rows": n_overlap_err,
            "realized_rate_per_month": rate
        })
    df_task1 = pd.DataFrame(task1_records)

    # Detailed extra alert overlap calculation
    # Check each keep_error episode against baseline episodes for that factory/param
    extra_episodes_list = []
    for ep in all_keep_error_episodes:
        fac = ep["factory_id"]
        param = ep["param"]
        base_eps_for_fac_param = [be for be in baseline_episodes_by_fac[fac] if be["param"] == param]
        # An episode is overlapping baseline if [start_ts, end_ts] overlaps any baseline [start_ts, end_ts]
        s_ts = ep["start_ts"]
        e_ts = ep["end_ts"]
        is_in_base = any(not (e_ts < be["start_ts"] or s_ts > be["end_ts"]) for be in base_eps_for_fac_param)
        if not is_in_base:
            extra_episodes_list.append(ep)

    total_extra_by_diff = df_task1["keep_error_episodes"].sum() - df_task1["baseline_episodes"].sum()
    n_extra_episodes = len(extra_episodes_list)
    n_extra_overlap_err = sum(1 for e in extra_episodes_list if e["overlaps_error_row"])
    n_all_overlap_err = sum(1 for e in all_keep_error_episodes if e["overlaps_error_row"])

    print(f"Task 1 evaluated in {time.time()-t0:.2f}s:")
    print(f"  Total alert episodes: {df_task1['keep_error_episodes'].sum()} (vs baseline {df_task1['baseline_episodes'].sum()})")
    print(f"  Net extra episodes: {total_extra_by_diff}")
    print(f"  New (disjoint) extra episodes identified: {n_extra_episodes}")
    print(f"  Extra episodes overlapping kept Error-tagged rows: {n_extra_overlap_err} / {n_extra_episodes} ({n_extra_overlap_err/max(n_extra_episodes,1)*100:.1f}%)")
    print(f"  Total episodes overlapping kept Error-tagged rows: {n_all_overlap_err} / {len(all_keep_error_episodes)} ({n_all_overlap_err/max(len(all_keep_error_episodes),1)*100:.1f}%)")
    print(f"  Unweighted rate per month: mean={df_task1['realized_rate_per_month'].mean():.4f}, median={df_task1['realized_rate_per_month'].median():.4f}, min={df_task1['realized_rate_per_month'].min():.4f}, max={df_task1['realized_rate_per_month'].max():.4f}")

    # 5. TASK 2: SHORT SERIES (First 6 months, default rows dropped)
    print("\n5. Running Task 2: SHORT SERIES (First 6 months, default rows dropped)...")
    t0 = time.time()
    # Truncate clean telemetry to first 6 months for each factory
    short_series_dict = {}
    short_factory_months = {}
    df_clean_short_list = []

    for fac, g in df_clean.groupby("factory_id"):
        min_ts = g["ts_dt"].min()
        cutoff_6mo = min_ts + pd.DateOffset(months=6)
        g_short = g[g["ts_dt"] <= cutoff_6mo].copy()
        df_clean_short_list.append(g_short)

        span_days = (g_short["ts_dt"].max() - min_ts).total_seconds() / 86400.0
        # Factory months for the short period
        # Standard: span_days / 30.4375, capped at FACTORY_MONTHS[fac]
        mo_short = min(span_days / 30.4375, FACTORY_MONTHS[fac])
        short_factory_months[fac] = round(mo_short, 2)

        for param, gp in g_short.groupby("parameter_id"):
            grid_s = prepare_series(gp, factory_id=fac)
            if not grid_s.empty:
                short_series_dict[(fac, param)] = grid_s

    df_clean_short = pd.concat(df_clean_short_list, ignore_index=True)
    short_scores = score_factories_m1(short_series_dict, df_clean_short)

    short_episodes_by_fac = {f: [] for f in all_dev_factories}
    for (fac, param), (grid, sc_arr) in short_scores.items():
        eps = extract_alert_episodes(sc_arr, grid["value"].values, FROZEN_TAU, grid["ts_dt"].values)
        for ep in eps:
            ep["param"] = param
            ep["factory_id"] = fac
            short_episodes_by_fac[fac].append(ep)

    task2_records = []
    for fac in all_dev_factories:
        n_eps = len(short_episodes_by_fac[fac])
        mo = short_factory_months[fac]
        rate = n_eps / mo if mo > 0 else 0.0
        task2_records.append({
            "factory_id": fac,
            "short_factory_months": mo,
            "short_episodes": n_eps,
            "realized_rate_per_month": rate
        })
    df_task2 = pd.DataFrame(task2_records)
    print(f"Task 2 evaluated in {time.time()-t0:.2f}s:")
    print(f"  Total short exposure: {df_task2['short_factory_months'].sum():.2f} factory-months")
    print(f"  Total alert episodes: {df_task2['short_episodes'].sum()}")
    print(f"  Unweighted rate per month: mean={df_task2['realized_rate_per_month'].mean():.4f}, median={df_task2['realized_rate_per_month'].median():.4f}, min={df_task2['realized_rate_per_month'].min():.4f}, max={df_task2['realized_rate_per_month'].max():.4f}")

    # 6. TASK 3: DISPERSION (on default dev run)
    print("\n6. Running Task 3: DISPERSION (Default Run 2b)...")
    run2b_fa_csv = os.path.join(RUN2B_DIR, "false_alarms.csv")
    df_fa_run2b = pd.read_csv(run2b_fa_csv)
    rates = df_fa_run2b["realized_rate_per_month"]
    min_rate = rates.min()
    med_rate = rates.median()
    max_rate = rates.max()
    mean_rate = rates.mean()
    above_2 = df_fa_run2b[df_fa_run2b["realized_rate_per_month"] > 2.0]
    n_above_2 = len(above_2)

    print(f"Default Run 2b Dispersion across 33 factories:")
    print(f"  Min: {min_rate:.4f}")
    print(f"  Median: {med_rate:.4f}")
    print(f"  Mean: {mean_rate:.4f}")
    print(f"  Max: {max_rate:.4f} ({df_fa_run2b.loc[rates.idxmax(), 'factory_id']})")
    print(f"  Factories above 2.0 alerts/month: {n_above_2}")
    for _, r in above_2.iterrows():
        print(f"    - {r['factory_id']}: {r['realized_rate_per_month']:.3f} alerts/mo ({r['false_alert_episodes']} episodes / {r['factory_months']} mo)")

    # 7. Write Summary Files to validation_v2/runs/run2b/analysis/
    df_task1.to_csv(os.path.join(OUT_DIR, "task1_keep_error_rows.csv"), index=False)
    df_task2.to_csv(os.path.join(OUT_DIR, "task2_short_series.csv"), index=False)
    df_fa_run2b.to_csv(os.path.join(OUT_DIR, "task3_dispersion_run2b.csv"), index=False)

    # Detailed summary table
    summary_df = pd.DataFrame([
        {
            "Condition": "Baseline Dev Run (tau=3.7955)",
            "Total_Episodes": df_base["episodes"].sum(),
            "Total_Exposure_Months": df_base["factory_months"].sum(),
            "Pooled_Rate": df_base["episodes"].sum() / df_base["factory_months"].sum(),
            "Mean_Rate": df_base["rate_per_month"].mean(),
            "Median_Rate": df_base["rate_per_month"].median(),
            "Min_Rate": df_base["rate_per_month"].min(),
            "Max_Rate": df_base["rate_per_month"].max()
        },
        {
            "Condition": "Task 1: KEEP ERROR ROWS (tau=3.7955)",
            "Total_Episodes": df_task1["keep_error_episodes"].sum(),
            "Total_Exposure_Months": df_task1["factory_months"].sum(),
            "Pooled_Rate": df_task1["keep_error_episodes"].sum() / df_task1["factory_months"].sum(),
            "Mean_Rate": df_task1["realized_rate_per_month"].mean(),
            "Median_Rate": df_task1["realized_rate_per_month"].median(),
            "Min_Rate": df_task1["realized_rate_per_month"].min(),
            "Max_Rate": df_task1["realized_rate_per_month"].max()
        },
        {
            "Condition": "Task 2: SHORT SERIES (6 Months, tau=3.7955)",
            "Total_Episodes": df_task2["short_episodes"].sum(),
            "Total_Exposure_Months": df_task2["short_factory_months"].sum(),
            "Pooled_Rate": df_task2["short_episodes"].sum() / df_task2["short_factory_months"].sum(),
            "Mean_Rate": df_task2["realized_rate_per_month"].mean(),
            "Median_Rate": df_task2["realized_rate_per_month"].median(),
            "Min_Rate": df_task2["realized_rate_per_month"].min(),
            "Max_Rate": df_task2["realized_rate_per_month"].max()
        }
    ])
    summary_df.to_csv(os.path.join(OUT_DIR, "summary_comparison.csv"), index=False)
    print("\nSaved all CSV outputs to validation_v2/runs/run2b/analysis/.")

if __name__ == "__main__":
    main()
