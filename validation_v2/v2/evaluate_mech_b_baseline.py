"""
ForensiAIR V2 — Stage 2, Part 2.1: Pre-Intervention Benchmark: Frozen V1 on Mechanism B
Protocol: PROTOCOL v2.0 (Frozen) & PROTOCOL v1.1 Section C (Frozen)

Strict Requirements:
- Read-only reuse of existing V1 detector (validation_v2/detector/detector.py).
- Do NOT modify any V1 files, labels, thresholds, or existing evaluation evidence.
- Never access Data/Unseen/ or the 4 locked test factories.
- Use only the 33 development factories.
- Blind empirical calibration on the series being scored.
- Target false-alarm budget: 1.0 alert episode per factory-month (328 target episodes on 327.61 fac-mo).
- Alert episodes: contiguous score >= tau, merging gaps <= 16 rows (4 hours).
- Missing readings (value is NaN) cannot start or continue alerts.
- Event matching: alert episode overlaps event window or starts <= 2h after event ends.
- Evaluates all 2,698 events across seeds 301-305 from validation_v2/v2/injector_b/labels_b.csv.
- Reports recall separately for all 7 Mechanism B variants.
- Outputs baseline results to validation_v2/v2/MECH_B_V1_BASELINE.csv.
"""

import os
import sys
sys.stdout.reconfigure(line_buffering=True)
import time
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
RAW_CSV = os.path.join(REPO_ROOT, "Data", "RawData", "monitoring_data(raw).csv")
CTO_CSV = os.path.join(REPO_ROOT, "Original Data", "consent_limits.csv")
LABELS_B_CSV = os.path.join(REPO_ROOT, "validation_v2", "v2", "injector_b", "labels_b.csv")
DEV_INJECTED_B_DIR = os.path.join(REPO_ROOT, "validation_v2", "v2", "injector_b", "injected_b", "dev")
V2_DIR = os.path.join(REPO_ROOT, "validation_v2", "v2")
OUT_BASELINE_CSV = os.path.join(V2_DIR, "MECH_B_V1_BASELINE.csv")

# Ensure Data/Unseen is NEVER imported or referenced
assert "Unseen" not in RAW_CSV and "Unseen" not in LABELS_B_CSV

# Reuse existing detector from validation_v2/detector/
DETECTOR_DIR = os.path.join(REPO_ROOT, "validation_v2", "detector")
sys.path.insert(0, DETECTOR_DIR)
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

# -----------------------------------------------------------------------------
# 1. Canonical Development Factory Months (Audited LOFO Exposure)
# -----------------------------------------------------------------------------
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
TOTAL_FACTORY_MONTHS = sum(FACTORY_MONTHS.values())  # 327.61 fac-mo

# -----------------------------------------------------------------------------
# 2. Episode Extraction and Merging (gap <= 16 rows / 4h)
# -----------------------------------------------------------------------------
def extract_alert_episodes(scores: np.ndarray, values: np.ndarray, tau: float, timestamps: np.ndarray):
    """
    Finds alert episodes:
    Contiguous rows with score >= tau, merging gaps <= 16 rows (4 hours).
    Missing readings (value is NaN or score is NaN) cannot trigger or continue alerts.
    """
    mask = ~np.isnan(values) & ~np.isnan(scores) & (scores >= tau)
    if not np.any(mask):
        return []

    indices = np.where(mask)[0]
    episodes = []

    ep_start = indices[0]
    ep_end = indices[0]

    for idx in indices[1:]:
        if idx - ep_end - 1 <= 16:  # Gap <= 16 rows
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

def count_episodes_for_series(scores: np.ndarray, values: np.ndarray, tau: float) -> int:
    """Fast episode counter for threshold calibration."""
    mask = ~np.isnan(values) & ~np.isnan(scores) & (scores >= tau)
    if not np.any(mask):
        return 0
    indices = np.where(mask)[0]
    if len(indices) == 1:
        return 1
    gaps = np.diff(indices) - 1
    return 1 + int(np.sum(gaps > 16))

# -----------------------------------------------------------------------------
# 3. Calibration on Training Clean Telemetry (Binary Search)
# -----------------------------------------------------------------------------
def calibrate_tau_for_training(training_scores_dict: dict, target_episodes: int) -> float:
    """
    Binary search for threshold tau across training series clean scores
    such that total alert episodes == target_episodes.
    """
    all_scores = []
    for (fac, param), (vals, scs) in training_scores_dict.items():
        v = scs[~np.isnan(vals) & ~np.isnan(scs)]
        if len(v) > 0:
            if len(v) > 10000:
                step = len(v) // 10000
                all_scores.extend(v[::step])
            else:
                all_scores.extend(v)

    if not all_scores:
        return 1.0

    all_scores = np.sort(np.array(all_scores))
    low_idx = 0
    high_idx = len(all_scores) - 1
    best_tau = float(all_scores[-1])
    best_diff = 999999

    for _ in range(35):
        mid_idx = (low_idx + high_idx) // 2
        tau = float(all_scores[mid_idx])

        tot_eps = 0
        for (fac, param), (vals, scs) in training_scores_dict.items():
            tot_eps += count_episodes_for_series(scs, vals, tau)

        diff = abs(tot_eps - target_episodes)
        if diff < best_diff:
            best_diff = diff
            best_tau = tau

        if tot_eps > target_episodes:
            low_idx = mid_idx + 1
        else:
            high_idx = mid_idx - 1

        if low_idx >= high_idx:
            break

    return best_tau

# -----------------------------------------------------------------------------
# 4. Cluster Bootstrap Confidence Interval (10,000 resamples over factories)
# -----------------------------------------------------------------------------
def compute_cluster_bootstrap(df_eval: pd.DataFrame, n_resamples: int = 10000, seed: int = 42):
    """
    Computes 95% cluster bootstrap CI over factories with 10,000 resamples.
    """
    if df_eval.empty or len(df_eval["factory_id"].unique()) == 0:
        return 0.0, 0.0, 0.0

    fac_counts = df_eval.groupby("factory_id")["is_detected"].agg(["sum", "count"]).reset_index()
    factories = fac_counts["factory_id"].values
    n_fac = len(factories)
    det_arr = fac_counts["sum"].values
    tot_arr = fac_counts["count"].values

    point_recall = float(np.sum(det_arr) / max(np.sum(tot_arr), 1))

    if n_fac == 1:
        return point_recall, point_recall, point_recall

    rng = np.random.default_rng(seed)
    mult_draws = rng.multinomial(n_fac, np.ones(n_fac) / n_fac, size=n_resamples)
    boot_det = mult_draws @ det_arr
    boot_tot = mult_draws @ tot_arr

    valid_mask = (boot_tot > 0)
    boot_recalls = np.where(valid_mask, boot_det / np.maximum(boot_tot, 1), point_recall)

    ci_lower = float(np.percentile(boot_recalls, 2.5))
    ci_upper = float(np.percentile(boot_recalls, 97.5))

    return point_recall, ci_lower, ci_upper

# -----------------------------------------------------------------------------
# 5. Baselines
# -----------------------------------------------------------------------------
def compute_b1_robust_zscore(vals: np.ndarray) -> np.ndarray:
    valid = vals[~np.isnan(vals)]
    if len(valid) == 0:
        return np.full(len(vals), np.nan)
    med = np.median(valid)
    mad = calc_mad(valid)
    sc = np.abs(vals - med) / (mad + 1e-4)
    sc[np.isnan(vals)] = np.nan
    return sc

def extract_b2_features(df_series: pd.DataFrame) -> pd.DataFrame:
    vals = df_series["value"].copy()
    feats = pd.DataFrame(index=df_series.index)
    feats["val"] = vals
    feats["rolling_mean_16"] = vals.rolling(16, min_periods=1).mean()
    feats["rolling_std_16"] = vals.rolling(16, min_periods=1).std().fillna(0.0)
    feats["diff_1"] = vals.diff(1).abs().fillna(0.0)
    feats["z_16"] = (vals - feats["rolling_mean_16"]) / (feats["rolling_std_16"] + 1e-4)
    return feats

def compute_b4_rules(vals: np.ndarray, param: str, cto_max: float = np.nan) -> np.ndarray:
    s = pd.Series(vals)
    N = len(vals)
    scores = np.zeros(N)

    r_std = s.rolling(16, min_periods=16).std()
    is_flow = ("flow" in param.lower())
    if is_flow:
        r_med = s.rolling(16, min_periods=16).median()
        flat_mask = (r_std < 1e-6) & (r_med > 0)
    else:
        flat_mask = (r_std < 1e-6)

    hug_mask = pd.Series(False, index=s.index)
    if pd.notna(cto_max) and cto_max > 0:
        within_2pct = (s >= 0.98 * cto_max) & (s <= 1.02 * cto_max)
        hug_mask = (within_2pct.rolling(16, min_periods=16).sum() >= 16)

    s_lag1 = s.shift(1)
    r_corr = s.rolling(96, min_periods=96).corr(s_lag1)
    autocorr_mask = (r_corr > 0.95)

    ph_mask = pd.Series(False, index=s.index)
    if "ph" in param.lower():
        ph_mask = (s < 0) | (s > 14)

    combined = flat_mask.fillna(False) | hug_mask.fillna(False) | autocorr_mask.fillna(False) | ph_mask.fillna(False)
    scores = combined.astype(float).values
    scores[np.isnan(vals)] = np.nan
    return scores

# -----------------------------------------------------------------------------
# 6. Main Execution Pipeline
# -----------------------------------------------------------------------------
def run_benchmark():
    print("=" * 80)
    print(" FORENSIAIR V2 — STAGE 2, PART 2.1: PRE-INTERVENTION BENCHMARK")
    print(" FROZEN V1 DETECTOR ON MECHANISM B INJECTIONS (DEV ONLY)")
    print("=" * 80)

    # 1. Load Data
    t0_all = time.time()
    print("\n[Step 1] Loading Development Telemetry, CTO Limits, and Labels...")
    df_raw = pd.read_csv(RAW_CSV)
    df_cto = pd.read_csv(CTO_CSV)
    df_labels = pd.read_csv(LABELS_B_CSV)
    df_labels["start_dt"] = pd.to_datetime(df_labels["start_ts"])
    df_labels["end_dt"] = pd.to_datetime(df_labels["end_ts"])

    print(f"  Raw telemetry rows: {len(df_raw):,}")
    print(f"  CTO limits records: {len(df_cto)}")
    print(f"  Mechanism B labels: {len(df_labels):,} events across seeds {sorted(df_labels['seed'].unique())}")
    print(f"  Variants in labels: {sorted(df_labels['variant'].unique())}")

    cto_limits = {}
    for _, r in df_cto.iterrows():
        if pd.notna(r["maximum_limit"]) and r["maximum_limit"] > 0:
            cto_limits[(str(r["factory_id"]), str(r["parameter"]))] = float(r["maximum_limit"])

    allowed_qc = ["Raw", "L"]
    df_filt = df_raw[df_raw["quality_code"].isin(allowed_qc)].copy()
    df_filt["ts_dt"] = pd.to_datetime(df_filt["timestamp"])
    all_dev_factories = sorted(df_filt["factory_id"].unique())
    print(f"  Total dev factories: {len(all_dev_factories)}")
    assert len(all_dev_factories) == 33, f"Expected 33 dev factories, found {len(all_dev_factories)}"

    sensors = ["ETP-pH", "ETP-Flow", "ETP-BOD", "ETP-COD", "ETP-TSS"]

    # 2. Pre-extract Clean Telemetry Features
    print("\n[Step 2] Pre-extracting Clean Telemetry Features (33 Factories)...")
    t0 = time.time()
    clean_series_dict = {}
    clean_if_feats = {}
    clean_b2_feats = {}

    for (fac, param), g in df_filt.groupby(["factory_id", "parameter_id"]):
        grid = prepare_series(g, factory_id=fac)
        if not grid.empty:
            clean_series_dict[(fac, param)] = grid
            clean_if_feats[(fac, param)] = extract_if_features(grid).dropna()
            clean_b2_feats[(fac, param)] = extract_b2_features(grid).dropna()

    print(f"  Pre-extracted {len(clean_series_dict)} clean series in {time.time()-t0:.2f}s")

    # 3. Train 33-Fold LOFO Isolation Forests (Identical to Run 2b)
    print("\n[Step 3] Fitting 33-Fold LOFO Sensor Isolation Forests & Pooled IF...")
    t0 = time.time()
    lofo_sensor_models = {}
    lofo_pooled_models = {}

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

        b2_train_dfs = [clean_b2_feats[(f, s)] for f in train_facs for s in sensors if (f, s) in clean_b2_feats]
        if b2_train_dfs:
            X_b2 = pd.concat(b2_train_dfs, ignore_index=True)
            if len(X_b2) > 30000:
                X_b2 = X_b2.sample(30000, random_state=42)
            iso_b2 = IsolationForest(n_estimators=100, max_samples=min(2048, len(X_b2)), random_state=42, n_jobs=1)
            iso_b2.fit(X_b2)
            lofo_pooled_models[held_out_fac] = iso_b2

    print(f"  Trained 33-fold LOFO models in {time.time()-t0:.2f}s")

    # 4. Score All Clean Series with LOFO Models & Blind Calibration
    print("\n[Step 4] Scoring Clean Telemetry & Computing Calibrated Thresholds...")
    t0 = time.time()

    f5_corr_cache = {}
    for fac in all_dev_factories:
        sub_fac = df_filt[df_filt["factory_id"] == fac]
        f5_corr_cache[(fac, 96)] = compute_f5_correlation(sub_fac, w=96)
        f5_corr_cache[(fac, 288)] = compute_f5_correlation(sub_fac, w=288)

    METHODS_LIST = [
        "M1_fusion",
        "F1_eps0", "F1_eps1", "F1_eps2",
        "F2_copypaste", "F3_limit", "F5_corr", "F6_shift", "F6_slope", "IF_sensor",
        "B1_zscore", "B2_pooled_if", "B3_sensor_if", "B4_legacy_rules"
    ]

    clean_scores = {m: {} for m in METHODS_LIST}

    for (fac, param), grid in clean_series_dict.items():
        vals = grid["value"].values
        v_mask = ~np.isnan(vals)

        if_model = lofo_sensor_models[fac].get(param)
        f5_dict = {}
        for k_c, v_c in f5_corr_cache.get((fac, 96), {}).items():
            if param in k_c:
                f5_dict["w96"] = v_c.reindex(grid["ts_dt"]).values
        for k_c, v_c in f5_corr_cache.get((fac, 288), {}).items():
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

        # M1 Max Fusion
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
        clean_scores["M1_fusion"][(fac, param)] = (vals, m1_sc)

        # Checks
        for eps in [0, 1, 2]:
            s_f1 = sc_df[f"F1_score_eps{eps}"].values.copy()
            s_f1[~v_mask] = np.nan
            clean_scores[f"F1_eps{eps}"][(fac, param)] = (vals, s_f1)

        f2_cols = [c for c in sc_df.columns if c.startswith("F2_copypaste")]
        with np.errstate(all='ignore'):
            f2_sc = np.nanmax(sc_df[f2_cols].values, axis=1) if f2_cols else np.full(len(vals), np.nan)
        f2_sc[~v_mask] = np.nan
        clean_scores["F2_copypaste"][(fac, param)] = (vals, f2_sc)

        f3_cols = [c for c in sc_df.columns if c.startswith("F3_limit")]
        with np.errstate(all='ignore'):
            f3_sc = np.nanmax(sc_df[f3_cols].values, axis=1) if f3_cols else np.full(len(vals), np.nan)
        f3_sc[~v_mask] = np.nan
        clean_scores["F3_limit"][(fac, param)] = (vals, f3_sc)

        f5_cols = [c for c in sc_df.columns if c.startswith("F5_corr")]
        with np.errstate(all='ignore'):
            f5_sc = np.nanmax(sc_df[f5_cols].values, axis=1) if f5_cols else np.full(len(vals), np.nan)
        f5_sc[~v_mask] = np.nan
        clean_scores["F5_corr"][(fac, param)] = (vals, f5_sc)

        f6_sh_cols = [c for c in sc_df.columns if c.startswith("F6_shift")]
        with np.errstate(all='ignore'):
            f6_sh = np.nanmax(sc_df[f6_sh_cols].values, axis=1) if f6_sh_cols else np.full(len(vals), np.nan)
        f6_sh[~v_mask] = np.nan
        clean_scores["F6_shift"][(fac, param)] = (vals, f6_sh)

        f6_sl_cols = [c for c in sc_df.columns if c.startswith("F6_slope")]
        with np.errstate(all='ignore'):
            f6_sl = np.nanmax(sc_df[f6_sl_cols].values, axis=1) if f6_sl_cols else np.full(len(vals), np.nan)
        f6_sl[~v_mask] = np.nan
        clean_scores["F6_slope"][(fac, param)] = (vals, f6_sl)

        if_sc = sc_df["if_score"].values.copy()
        if_sc[~v_mask] = np.nan
        clean_scores["IF_sensor"][(fac, param)] = (vals, if_sc)
        clean_scores["B3_sensor_if"][(fac, param)] = (vals, if_sc)

        b1_sc = compute_b1_robust_zscore(vals)
        clean_scores["B1_zscore"][(fac, param)] = (vals, b1_sc)

        b2_model = lofo_pooled_models[fac]
        b2_feats = clean_b2_feats.get((fac, param))
        if b2_model is not None and b2_feats is not None and not b2_feats.empty:
            b2_sc = np.full(len(vals), np.nan)
            b2_sc[b2_feats.index] = -b2_model.decision_function(b2_feats)
        else:
            b2_sc = np.zeros(len(vals))
        b2_sc[~v_mask] = np.nan
        clean_scores["B2_pooled_if"][(fac, param)] = (vals, b2_sc)

        cto_m = cto_limits.get((fac, param), np.nan)
        b4_sc = compute_b4_rules(vals, param, cto_m)
        clean_scores["B4_legacy_rules"][(fac, param)] = (vals, b4_sc)

    print(f"  Scored clean telemetry in {time.time()-t0:.2f}s")

    # 5. Calibrate Tau Thresholds at Target 1.0 alert / factory-month (328 target episodes)
    print("\n[Step 5] Calibrating Thresholds at Target 1.0 alert / factory-month...")
    target_episodes = int(round(1.0 * TOTAL_FACTORY_MONTHS))  # 328
    calibrated_taus = {}
    realized_fa_rates = {}

    for m in METHODS_LIST:
        tau = calibrate_tau_for_training(clean_scores[m], target_episodes)
        calibrated_taus[m] = tau
        tot_eps = sum(
            count_episodes_for_series(scs, vals, tau)
            for (f, p), (vals, scs) in clean_scores[m].items()
        )
        realized_fa_rates[m] = tot_eps / TOTAL_FACTORY_MONTHS

    print(f"  Calibrated M1_fusion tau: {calibrated_taus['M1_fusion']:.4f} (Realized FA: {realized_fa_rates['M1_fusion']:.3f}/mo)")
    for m in ["F1_eps0", "F1_eps1", "F1_eps2", "F2_copypaste", "F3_limit", "F5_corr", "F6_shift", "F6_slope", "IF_sensor"]:
        print(f"    - {m:<14}: tau = {calibrated_taus[m]:.4f} (Realized FA: {realized_fa_rates[m]:.3f}/mo)")

    # 6. Score Mechanism B Injected Parquets (Seeds 301-305, 110 Parquets)
    print("\n[Step 6] Scoring Mechanism B Injected Telemetry (Seeds 301-305)...")
    t0 = time.time()
    injected_score_cache = {}  # (seed, fac, param) -> (ts_arr, val_arr, {m: sc_arr})
    nan_tracking = {m: {"total": 0, "nan": 0} for m in METHODS_LIST}

    SEEDS = [301, 302, 303, 304, 305]
    total_parquets_scored = 0

    for seed in SEEDS:
        seed_dir = os.path.join(DEV_INJECTED_B_DIR, f"seed_{seed}")
        if not os.path.exists(seed_dir):
            continue

        for fname in sorted(os.listdir(seed_dir)):
            if not fname.endswith(".parquet"):
                continue
            fac = fname.replace(".parquet", "")
            pq_path = os.path.join(seed_dir, fname)
            df_pq = pd.read_parquet(pq_path)
            df_pq["ts_dt"] = pd.to_datetime(df_pq["timestamp"])
            df_pq["factory_id"] = fac

            f5_pq_96 = compute_f5_correlation(df_pq, w=96)
            f5_pq_288 = compute_f5_correlation(df_pq, w=288)

            total_parquets_scored += 1

            for param, g_s in df_pq.groupby("parameter_id"):
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

                calib = calibrate(
                    grid, mode="blind", cto_limits=cto_limits, skip_if=False,
                    if_model=if_model, f5_corr_dict=f5_dict, factory_id=fac
                )
                sc_df = score(
                    grid, calib, if_model=if_model, cto_limits=cto_limits,
                    f5_corr_dict=f5_dict, factory_id=fac
                )

                scores_dict = {}

                # M1 Max Fusion
                m1_cols = [c for c in m1_candidates if c in sc_df.columns]
                with np.errstate(all='ignore'):
                    m1_sc = np.nanmax(sc_df[m1_cols].values, axis=1)
                m1_sc[~v_mask] = np.nan
                scores_dict["M1_fusion"] = m1_sc

                # Checks
                for eps in [0, 1, 2]:
                    s_f1 = sc_df[f"F1_score_eps{eps}"].values.copy()
                    s_f1[~v_mask] = np.nan
                    scores_dict[f"F1_eps{eps}"] = s_f1

                f2_cols = [c for c in sc_df.columns if c.startswith("F2_copypaste")]
                with np.errstate(all='ignore'):
                    f2_sc = np.nanmax(sc_df[f2_cols].values, axis=1) if f2_cols else np.full(len(vals), np.nan)
                f2_sc[~v_mask] = np.nan
                scores_dict["F2_copypaste"] = f2_sc

                f3_cols = [c for c in sc_df.columns if c.startswith("F3_limit")]
                with np.errstate(all='ignore'):
                    f3_sc = np.nanmax(sc_df[f3_cols].values, axis=1) if f3_cols else np.full(len(vals), np.nan)
                f3_sc[~v_mask] = np.nan
                scores_dict["F3_limit"] = f3_sc

                f5_cols = [c for c in sc_df.columns if c.startswith("F5_corr")]
                with np.errstate(all='ignore'):
                    f5_sc = np.nanmax(sc_df[f5_cols].values, axis=1) if f5_cols else np.full(len(vals), np.nan)
                f5_sc[~v_mask] = np.nan
                scores_dict["F5_corr"] = f5_sc

                f6_sh_cols = [c for c in sc_df.columns if c.startswith("F6_shift")]
                with np.errstate(all='ignore'):
                    f6_sh = np.nanmax(sc_df[f6_sh_cols].values, axis=1) if f6_sh_cols else np.full(len(vals), np.nan)
                f6_sh[~v_mask] = np.nan
                scores_dict["F6_shift"] = f6_sh

                f6_sl_cols = [c for c in sc_df.columns if c.startswith("F6_slope")]
                with np.errstate(all='ignore'):
                    f6_sl = np.nanmax(sc_df[f6_sl_cols].values, axis=1) if f6_sl_cols else np.full(len(vals), np.nan)
                f6_sl[~v_mask] = np.nan
                scores_dict["F6_slope"] = f6_sl

                if_sc = sc_df["if_score"].values.copy()
                if_sc[~v_mask] = np.nan
                scores_dict["IF_sensor"] = if_sc
                scores_dict["B3_sensor_if"] = if_sc

                b1_sc = compute_b1_robust_zscore(vals)
                scores_dict["B1_zscore"] = b1_sc

                b2_m = lofo_pooled_models[fac]
                b2_f = extract_b2_features(grid).dropna()
                if b2_m is not None and not b2_f.empty:
                    b2_sc = np.full(len(vals), np.nan)
                    b2_sc[b2_f.index] = -b2_m.decision_function(b2_f)
                else:
                    b2_sc = np.zeros(len(vals))
                b2_sc[~v_mask] = np.nan
                scores_dict["B2_pooled_if"] = b2_sc

                cto_m = cto_limits.get((fac, param), np.nan)
                b4_sc = compute_b4_rules(vals, param, cto_m)
                scores_dict["B4_legacy_rules"] = b4_sc

                # Ensure mask
                for m_k in scores_dict:
                    scores_dict[m_k][~v_mask] = np.nan
                    nan_tracking[m_k]["total"] += int(np.sum(v_mask))
                    nan_tracking[m_k]["nan"] += int(np.sum(v_mask & np.isnan(scores_dict[m_k])))

                injected_score_cache[(seed, fac, param)] = (ts_arr, vals, scores_dict)

    print(f"  Scored {total_parquets_scored} parquet files ({len(injected_score_cache)} series-seeds) in {time.time()-t0:.2f}s")

    # 7. Pre-extract Alert Episodes & Match Events
    print("\n[Step 7] Extracting Alert Episodes & Matching Mechanism B Events...")
    t0 = time.time()

    # Pre-extract alert episodes for all series for each method
    series_alert_episodes = {m: {} for m in METHODS_LIST}
    for m in METHODS_LIST:
        tau = calibrated_taus[m]
        for (seed, fac, param), (ts_arr, vals, scores_dict) in injected_score_cache.items():
            sc_arr = scores_dict[m]
            series_alert_episodes[m][(seed, fac, param)] = extract_alert_episodes(sc_arr, vals, tau, ts_arr)

    # B0 Random Alerts (1.0 alert / factory-month)
    rng_b0 = np.random.default_rng(42)
    b0_alerts_cache = {}
    for fac in all_dev_factories:
        m_k = FACTORY_MONTHS[fac]
        n_alerts = int(round(1.0 * m_k))
        sub_fac = df_filt[df_filt["factory_id"] == fac]
        t_min = sub_fac["ts_dt"].min()
        t_max = sub_fac["ts_dt"].max()
        span_sec = max((t_max - t_min).total_seconds(), 3600.0)
        fac_eps = []
        for _ in range(n_alerts):
            rand_start = t_min + pd.Timedelta(seconds=float(rng_b0.uniform(0, span_sec)))
            rand_end = rand_start + pd.Timedelta(hours=4)
            fac_eps.append((rand_start, rand_end))
        b0_alerts_cache[fac] = fac_eps

    # Match each event in df_labels
    labels_records = df_labels.to_dict("records")
    eval_records = []

    for row in labels_records:
        eid = row["event_id"]
        seed = row["seed"]
        fac = row["factory_id"]
        param = str(row["parameter"]).strip()
        t_type = row["type"]
        variant = row["variant"]
        severity = row["severity"]
        duration = row["duration_rows"]
        s_dt = row["start_dt"]
        e_dt = row["end_dt"]
        e_dt_2h = e_dt + pd.Timedelta(hours=2)

        ev_res = {
            "event_id": eid,
            "factory_id": fac,
            "seed": seed,
            "parameter": param,
            "type": t_type,
            "variant": variant,
            "severity": severity,
            "duration_rows": duration,
            "start_dt": s_dt,
            "end_dt": e_dt
        }

        # B0 detection
        b0_det = False
        for (r_s, r_e) in b0_alerts_cache.get(fac, []):
            if (r_e >= s_dt) and (r_s <= e_dt_2h):
                b0_det = True
                break
        ev_res["is_detected_B0"] = b0_det

        # Method detections
        for m in METHODS_LIST:
            is_det = False
            min_delay = np.nan
            eps = series_alert_episodes[m].get((seed, fac, param), [])
            for ep in eps:
                ep_s = ep["start_ts"]
                ep_e = ep["end_ts"]
                if (ep_e >= s_dt) and (ep_s <= e_dt_2h):
                    is_det = True
                    first_alert_ts = max(ep_s, s_dt)
                    delay_h = max(0.0, (first_alert_ts - s_dt).total_seconds() / 3600.0)
                    if np.isnan(min_delay) or delay_h < min_delay:
                        min_delay = delay_h

            ev_res[f"is_detected_{m}"] = is_det
            ev_res[f"delay_{m}"] = min_delay

        eval_records.append(ev_res)

    df_eval = pd.DataFrame(eval_records)
    print(f"  Matched {len(df_eval):,} events in {time.time()-t0:.2f}s")

    # -------------------------------------------------------------------------
    # 8. Compute Breakdown Metrics
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print(" BASELINE RESULTS: FROZEN V1 ON MECHANISM B DEVELOPMENT INJECTIONS")
    print("=" * 80)

    # A. Variant Breakdown (The Primary Deliverable)
    variant_rows = []
    for var, g_v in df_eval.groupby("variant"):
        t_type = g_v["type"].iloc[0]
        n_tot = len(g_v)
        n_det_m1 = int(g_v["is_detected_M1_fusion"].sum())
        rec_m1, ci_low, ci_high = compute_cluster_bootstrap(g_v.rename(columns={"is_detected_M1_fusion": "is_detected"}))
        delays = g_v.loc[g_v["is_detected_M1_fusion"], "delay_M1_fusion"].dropna()
        med_delay = float(np.median(delays)) if len(delays) > 0 else np.nan

        row = {
            "Type": t_type,
            "Variant": var,
            "Total_Events": n_tot,
            "Detected_M1": n_det_m1,
            "Recall_M1": round(rec_m1, 4),
            "CI95_Lower": round(ci_low, 4),
            "CI95_Upper": round(ci_high, 4),
            "Median_Delay_h": round(med_delay, 2) if pd.notna(med_delay) else np.nan,
            "Calibrated_Tau": calibrated_taus["M1_fusion"],
            "Target_Budget_fa_mo": 1.0,
            "Realized_FA_Rate_mo": round(realized_fa_rates["M1_fusion"], 3),
            "Evaluated_Factories": len(g_v["factory_id"].unique()),
            "Total_Dev_Exposure_fac_mo": TOTAL_FACTORY_MONTHS
        }
        # Add single check recalls
        for chk in ["F1_eps0", "F1_eps1", "F1_eps2", "F2_copypaste", "F3_limit", "F5_corr", "F6_shift", "F6_slope", "IF_sensor"]:
            n_det_chk = int(g_v[f"is_detected_{chk}"].sum())
            row[f"Recall_{chk}"] = round(n_det_chk / n_tot, 4)

        variant_rows.append(row)

    df_variant_summary = pd.DataFrame(variant_rows).sort_values(["Type", "Variant"])
    print("\n--- TABLE 1: RECALL BY MECHANISM B VARIANT (M1 FUSION AT 1.0 ALERT/MONTH) ---")
    print(df_variant_summary[["Type", "Variant", "Total_Events", "Detected_M1", "Recall_M1", "CI95_Lower", "CI95_Upper", "Median_Delay_h"]].to_string(index=False))

    # B. Overall Headline Summary & Method Comparison Table
    method_rows = []
    headline_methods = [
        ("M1: Multi-Check Max Fusion", "M1_fusion"),
        ("F1: Exact Repeat Run-Level (eps=0)", "F1_eps0"),
        ("F1: 1-Step Quasi-Flat (eps=1)", "F1_eps1"),
        ("F1: 2-Step Quasi-Flat (eps=2)", "F1_eps2"),
        ("F2: Copy-Paste Replay", "F2_copypaste"),
        ("F3: Consent Limit Proximity", "F3_limit"),
        ("F5: Correlation Break", "F5_corr"),
        ("F6: Level Shift Drift", "F6_shift"),
        ("F6: Linear Slope Drift", "F6_slope"),
        ("IF: Sensor Isolation Forest", "IF_sensor"),
        ("B0: Random Alerts (1.0 alert/mo)", "B0"),
        ("B1: Robust Z-Score", "B1_zscore"),
        ("B2: Pooled Isolation Forest", "B2_pooled_if"),
        ("B3: Sensor IF alone", "B3_sensor_if"),
        ("B4: Legacy Fingerprint Rules", "B4_legacy_rules")
    ]

    for label, m_key in headline_methods:
        det_col = "is_detected_B0" if m_key == "B0" else f"is_detected_{m_key}"
        n_tot = len(df_eval)
        n_det = int(df_eval[det_col].sum())
        rec, ci_l, ci_u = compute_cluster_bootstrap(df_eval.rename(columns={det_col: "is_detected"}))
        del_col = f"delay_{m_key}" if m_key != "B0" else None
        if del_col and del_col in df_eval.columns:
            delays = df_eval.loc[df_eval[det_col], del_col].dropna()
            med_del = float(np.median(delays)) if len(delays) > 0 else np.nan
        else:
            med_del = 0.0

        method_rows.append({
            "Method": label,
            "Method_Key": m_key,
            "Total_Events": n_tot,
            "Detected_Events": n_det,
            "Recall": round(rec, 4),
            "CI95_Lower": round(ci_l, 4),
            "CI95_Upper": round(ci_u, 4),
            "Median_Delay_h": round(med_del, 2) if pd.notna(med_del) else np.nan,
            "Calibrated_Tau": calibrated_taus.get(m_key, np.nan),
            "Realized_FA_mo": round(realized_fa_rates.get(m_key, 1.0), 3)
        })

    df_method_summary = pd.DataFrame(method_rows)
    print("\n--- TABLE 2: ALL METHODS COMPARISON ON MECHANISM B (BUDGET 1.0 ALERT/MONTH) ---")
    print(df_method_summary[["Method", "Total_Events", "Detected_Events", "Recall", "CI95_Lower", "CI95_Upper", "Calibrated_Tau", "Realized_FA_mo"]].to_string(index=False))

    # C. Breakdown by Severity (M1 Fusion)
    severity_rows = []
    for sev, g_s in df_eval.groupby("severity"):
        n_tot = len(g_s)
        n_det = int(g_s["is_detected_M1_fusion"].sum())
        rec, ci_l, ci_u = compute_cluster_bootstrap(g_s.rename(columns={"is_detected_M1_fusion": "is_detected"}))
        severity_rows.append({
            "Severity": sev,
            "Total_Events": n_tot,
            "Detected_Events": n_det,
            "Recall": round(rec, 4),
            "CI95_Lower": round(ci_l, 4),
            "CI95_Upper": round(ci_u, 4)
        })
    df_sev_summary = pd.DataFrame(severity_rows)
    print("\n--- TABLE 3: RECALL BY SEVERITY (M1 FUSION) ---")
    print(df_sev_summary.to_string(index=False))

    # D. Breakdown by Duration (M1 Fusion)
    duration_rows = []
    for dur, g_d in df_eval.groupby("duration_rows"):
        n_tot = len(g_d)
        n_det = int(g_d["is_detected_M1_fusion"].sum())
        rec, ci_l, ci_u = compute_cluster_bootstrap(g_d.rename(columns={"is_detected_M1_fusion": "is_detected"}))
        duration_rows.append({
            "Duration_Rows": dur,
            "Duration_Time": f"{dur*15//60}h" if dur < 96 else f"{dur*15//1440}d",
            "Total_Events": n_tot,
            "Detected_Events": n_det,
            "Recall": round(rec, 4),
            "CI95_Lower": round(ci_l, 4),
            "CI95_Upper": round(ci_u, 4)
        })
    df_dur_summary = pd.DataFrame(duration_rows)
    print("\n--- TABLE 4: RECALL BY DURATION (M1 FUSION) ---")
    print(df_dur_summary.to_string(index=False))

    # E. Save Required Output: MECH_B_V1_BASELINE.csv
    print(f"\n[Step 8] Saving Baseline Output to {OUT_BASELINE_CSV}...")
    df_variant_summary.to_csv(OUT_BASELINE_CSV, index=False)
    print(f"  Successfully wrote {OUT_BASELINE_CSV} ({len(df_variant_summary)} variant rows)")

    # Also save detailed event-level and method-level evaluation tables
    detailed_csv = os.path.join(V2_DIR, "MECH_B_V1_METHODS_COMPARISON.csv")
    df_method_summary.to_csv(detailed_csv, index=False)
    print(f"  Successfully wrote {detailed_csv} ({len(df_method_summary)} method rows)")

    events_csv = os.path.join(V2_DIR, "MECH_B_V1_EVENTS_EVALUATED.csv")
    df_eval.to_csv(events_csv, index=False)
    print(f"  Successfully wrote {events_csv} ({len(df_eval)} event records)")

    print("\n" + "=" * 80)
    print(f" BENCHMARK COMPLETE! Total Execution Time: {time.time()-t0_all:.2f}s")
    print("=" * 80)

if __name__ == "__main__":
    run_benchmark()
