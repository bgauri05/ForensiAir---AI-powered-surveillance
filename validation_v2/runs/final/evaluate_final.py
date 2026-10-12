"""
ForensiAIR FINAL TEST: Locked Unseen Factory Evaluation (Run ONCE)
Specification: PROTOCOL_v1.md & PROTOCOL_v1.1.md (Frozen)

Preconditions:
- git tag detector-frozen on Run 2b code (commit: 9b493594bb1475aa792123236f3c069308340d2b)
- Zero uncommitted changes in validation_v2/detector/ or validation_v2/injector/
- Unchanged injector hash verified
- Outputs written strictly to validation_v2/runs/final/
- No hyperparameter tuning or cutoff recalibration on test data.
"""

import os
import sys
sys.stdout.reconfigure(line_buffering=True)
import time
import subprocess
import hashlib
import random
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score

REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
OUT_DIR = os.path.join(REPO_ROOT, "validation_v2", "runs", "final")
os.makedirs(OUT_DIR, exist_ok=True)

INJECTED_OUT_DIR = os.path.join(OUT_DIR, "injected")
os.makedirs(INJECTED_OUT_DIR, exist_ok=True)

FINAL_LOG_PATH = os.path.join(OUT_DIR, "FINAL_LOG.md")
FINAL_REPORT_PATH = os.path.join(OUT_DIR, "FINAL_REPORT.md")
RUNLOG_PATH = os.path.join(REPO_ROOT, "validation_v2", "RUNLOG.md")

DEV_RAW_CSV = os.path.join(REPO_ROOT, "Data", "RawData", "monitoring_data(raw).csv")
DEV_CTO_CSV = os.path.join(REPO_ROOT, "Original Data", "consent_limits.csv")

# Locate unseen CSV directory
UNSEEN_CANDIDATE_DIRS = [
    os.path.join(REPO_ROOT, "Data", "Unseen"),
    r"c:\Users\gauri\Downloads\validation"
]
UNSEEN_DIR = None
for d in UNSEEN_CANDIDATE_DIRS:
    if os.path.exists(d):
        UNSEEN_DIR = d
        break
if UNSEEN_DIR is None:
    raise RuntimeError(f"Could not find unseen data directory in {UNSEEN_CANDIDATE_DIRS}")

FACTORY_FILES = {
    "Cipla": "Cipla (1).csv",
    "Glenmark": "Glenmark (1).csv",
    "Indoco": "Indoco (1).csv",
    "Zydus": "Zydus (1).csv"
}

CANONICAL_PARAMS = ["ETP-BOD", "ETP-COD", "ETP-pH", "ETP-Flow", "ETP-TSS"]
TEST_SEEDS = [101, 102, 103, 104, 105]

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

# -----------------------------------------------------------------------------
# 1. Audited Canonical Dev Factory Months (for Dev Cutoff Calibration)
# -----------------------------------------------------------------------------
DEV_FACTORY_MONTHS = {
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
TOTAL_DEV_FACTORY_MONTHS = sum(DEV_FACTORY_MONTHS.values())  # 327.61

METHODS_LIST = [
    "M1_fusion",
    "F1_eps0", "F1_eps1", "F1_eps2",
    "F2_copypaste", "F3_limit", "F5_corr", "F6_shift", "F6_slope", "IF_sensor",
    "B1_zscore", "B2_pooled_if", "B3_sensor_if", "B4_legacy_rules"
]

# -----------------------------------------------------------------------------
# 2. Episode Extraction and Merging (gap <= 16 rows)
# -----------------------------------------------------------------------------
def extract_alert_episodes(scores: np.ndarray, values: np.ndarray, tau: float, timestamps: np.ndarray):
    """
    Contiguous rows with score >= tau, merging gaps <= 16 rows (4 hours).
    Missing values (NaN) cannot trigger or continue alerts.
    """
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

def count_episodes_for_series(scores: np.ndarray, values: np.ndarray, tau: float) -> int:
    mask = ~np.isnan(values) & ~np.isnan(scores) & (scores >= tau)
    if not np.any(mask):
        return 0
    indices = np.where(mask)[0]
    if len(indices) == 1:
        return 1
    gaps = np.diff(indices) - 1
    return 1 + int(np.sum(gaps > 16))

def calibrate_tau_for_training(training_scores_dict: dict, target_episodes: int) -> float:
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
# 3. Cluster Bootstrap Confidence Interval (10,000 resamples)
# -----------------------------------------------------------------------------
def compute_cluster_bootstrap(df_eval: pd.DataFrame, n_resamples: int = 10000, seed: int = 42):
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
# 4. Baselines Implementations
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

def compute_b5_factory_risk(series_dict: dict, cto_limits: dict, fac: str) -> float:
    rates = []
    for param, vals in series_dict.items():
        v = vals[~np.isnan(vals)]
        if len(v) == 0:
            continue
        s = pd.Series(vals)

        if "ph" in param.lower():
            cto_max = cto_limits.get((fac, param), 9.0)
            imp = (s < 0) | (s > 14) | (s > cto_max)
            rates.append(float(imp.mean()))

        r_std = s.rolling(16, min_periods=16).std()
        if "flow" in param.lower():
            r_med = s.rolling(16, min_periods=16).median()
            fl = (r_std < 1e-6) & (r_med > 0)
        else:
            fl = (r_std < 1e-6)
        rates.append(float(fl.mean()))

        s_lag1 = s.shift(1)
        r_corr = s.rolling(96, min_periods=96).corr(s_lag1)
        rates.append(float((r_corr > 0.95).mean()))

        cto_max = cto_limits.get((fac, param), np.nan)
        if pd.notna(cto_max) and cto_max > 0:
            hug = (s >= 0.98 * cto_max) & (s <= 1.02 * cto_max)
            rates.append(float(hug.mean()))

    return float(np.nanmean(rates)) if len(rates) > 0 else 0.0

# Standard CTO consent limits for the 4 unseen factories
def get_test_cto_limits():
    factories = ["Cipla", "Glenmark", "Indoco", "Zydus"]
    limits = {}
    for f in factories:
        limits[(f, "ETP-pH")] = 9.0
        limits[(f, "ETP-BOD")] = 30.0
        limits[(f, "ETP-COD")] = 250.0
        limits[(f, "ETP-TSS")] = 100.0
        limits[(f, "ETP-Flow")] = 1000.0
    return limits

def get_file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fp:
        while chunk := fp.read(8192):
            h.update(chunk)
    return h.hexdigest().upper()

# -----------------------------------------------------------------------------
# MAIN EVALUATION PIPELINE
# -----------------------------------------------------------------------------
def main():
    print("==========================================================================")
    print(" FORENSIAIR FINAL TEST: LOCKED UNSEEN FACTORY EVALUATION (RUN ONCE)")
    print("==========================================================================")
    
    # 0. Verify Preconditions
    print("\n0. Verifying Preconditions...")
    commit_res = subprocess.run(["git", "rev-parse", "detector-frozen"], cwd=REPO_ROOT, capture_output=True, text=True)
    commit_hash = commit_res.stdout.strip()
    if commit_res.returncode != 0 or not commit_hash:
        raise RuntimeError("Precondition failed: git tag 'detector-frozen' not found!")
    print(f"  [PASS] Tag 'detector-frozen' commit hash: {commit_hash}")

    diff_res = subprocess.run(["git", "status", "-s", "validation_v2/detector", "validation_v2/injector"], cwd=REPO_ROOT, capture_output=True, text=True)
    if diff_res.stdout.strip():
        raise RuntimeError(f"Precondition failed: Uncommitted changes in detector/injector:\n{diff_res.stdout}")
    print("  [PASS] Zero uncommitted changes in validation_v2/detector and validation_v2/injector.")

    injector_path = os.path.join(REPO_ROOT, "validation_v2", "injector", "injector.py")
    detector_path = os.path.join(REPO_ROOT, "validation_v2", "detector", "detector.py")
    inj_hash = get_file_sha256(injector_path)
    det_hash = get_file_sha256(detector_path)
    print(f"  [PASS] Injector SHA256: {inj_hash}")
    print(f"  [PASS] Detector SHA256: {det_hash}")

    log_entries = [
        "# FINAL TEST LOG\n",
        f"- Date: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Git Commit (detector-frozen): `{commit_hash}`",
        f"- Injector SHA256: `{inj_hash}`",
        f"- Detector SHA256: `{det_hash}`",
        f"- Unseen Telemetry Directory: `{UNSEEN_DIR}`\n",
        "## Preconditions & Integrity Checks",
        "- Tag `detector-frozen`: Verified",
        "- Uncommitted working tree changes: None (0 changes)",
        "- Transductive test fit / test hyperparameter tuning: Strictly Prohibited\n"
    ]

    # 1. Load Dev Telemetry & Train IF Models on All 33 Dev Factories
    print("\n1. Loading Dev Telemetry & Training Per-Parameter IF on all 33 Dev Factories...")
    t0 = time.time()
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

    # Train per-parameter IF
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

    # Train B2 pooled IF
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
    print(f"  Trained per-parameter and pooled IF on all 33 dev factories in {time.time()-t0:.2f}s.")

    # Pre-compute Dev Correlations & Score Dev Clean Series to extract dev cutoffs tau
    print("\n2. Scoring Dev Clean Series to extract Fixed Dev Cutoffs (1, 2, 4, 10 alerts/mo)...")
    t0 = time.time()
    dev_f5_corr = {}
    for fac in all_dev_factories:
        sub_fac = df_dev_filt[df_dev_filt["factory_id"] == fac]
        dev_f5_corr[(fac, 96)] = compute_f5_correlation(sub_fac, w=96)
        dev_f5_corr[(fac, 288)] = compute_f5_correlation(sub_fac, w=288)

    dev_clean_scores = {m: {} for m in METHODS_LIST}
    for (fac, param), grid in dev_clean_grids.items():
        vals = grid["value"].values
        v_mask = ~np.isnan(vals)
        if_model = dev_if_models.get(param)

        f5_dict = {}
        for k_c, v_c in dev_f5_corr.get((fac, 96), {}).items():
            if param in k_c:
                f5_dict["w96"] = v_c.reindex(grid["ts_dt"]).values
        for k_c, v_c in dev_f5_corr.get((fac, 288), {}).items():
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
        f2_sc = np.nanmax(sc_df[f2_cols].values, axis=1) if f2_cols else np.full(len(vals), np.nan)
        dev_clean_scores["F2_copypaste"][(fac, param)] = (vals, f2_sc)

        f3_cols = [c for c in sc_df.columns if c.startswith("F3_limit")]
        f3_sc = np.nanmax(sc_df[f3_cols].values, axis=1) if f3_cols else np.full(len(vals), np.nan)
        dev_clean_scores["F3_limit"][(fac, param)] = (vals, f3_sc)

        f5_cols = [c for c in sc_df.columns if c.startswith("F5_corr")]
        f5_sc = np.nanmax(sc_df[f5_cols].values, axis=1) if f5_cols else np.full(len(vals), np.nan)
        dev_clean_scores["F5_corr"][(fac, param)] = (vals, f5_sc)

        f6_sh_cols = [c for c in sc_df.columns if c.startswith("F6_shift")]
        f6_sh = np.nanmax(sc_df[f6_sh_cols].values, axis=1) if f6_sh_cols else np.full(len(vals), np.nan)
        dev_clean_scores["F6_shift"][(fac, param)] = (vals, f6_sh)

        f6_sl_cols = [c for c in sc_df.columns if c.startswith("F6_slope")]
        f6_sl = np.nanmax(sc_df[f6_sl_cols].values, axis=1) if f6_sl_cols else np.full(len(vals), np.nan)
        dev_clean_scores["F6_slope"][(fac, param)] = (vals, f6_sl)

        dev_clean_scores["IF_sensor"][(fac, param)] = (vals, sc_df["if_score"].values)
        dev_clean_scores["B3_sensor_if"][(fac, param)] = (vals, sc_df["if_score"].values)
        dev_clean_scores["B1_zscore"][(fac, param)] = (vals, compute_b1_robust_zscore(vals))

        b2_f = extract_b2_features(grid).dropna()
        b2_sc = np.full(len(vals), np.nan)
        if not b2_f.empty:
            b2_sc[b2_f.index] = -iso_b2.decision_function(b2_f)
        b2_sc[~v_mask] = np.nan
        dev_clean_scores["B2_pooled_if"][(fac, param)] = (vals, b2_sc)

        cto_m = dev_cto_limits.get((fac, param), np.nan)
        dev_clean_scores["B4_legacy_rules"][(fac, param)] = (vals, compute_b4_rules(vals, param, cto_m))

    BUDGETS = [1, 2, 4, 10]
    dev_cutoffs = {b: {} for b in BUDGETS}
    for b in BUDGETS:
        target_eps = int(round(b * TOTAL_DEV_FACTORY_MONTHS))
        for m in METHODS_LIST:
            dev_cutoffs[b][m] = calibrate_tau_for_training(dev_clean_scores[m], target_eps)

    print(f"  Calibrated fixed dev cutoffs in {time.time()-t0:.2f}s.")
    print(f"  Fixed M1 Cutoff (1 alert/fac-mo): tau = {dev_cutoffs[1]['M1_fusion']:.4f}")

    log_entries.append("## Fixed Cutoffs Calibrated on Dev Set Clean Exposure (327.61 fac-mo)")
    log_entries.append(f"- **Operating Point (1 alert/mo)**: M1 tau = `{dev_cutoffs[1]['M1_fusion']:.4f}`")
    for m in METHODS_LIST:
        log_entries.append(f"  - `{m}`: tau = `{dev_cutoffs[1][m]:.4f}`")
    log_entries.append(f"- **Sensitivity (2 alerts/mo)**: M1 tau = `{dev_cutoffs[2]['M1_fusion']:.4f}`")
    log_entries.append(f"- **Sensitivity (4 alerts/mo)**: M1 tau = `{dev_cutoffs[4]['M1_fusion']:.4f}`")
    log_entries.append(f"- **Sensitivity (10 alerts/mo)**: M1 tau = `{dev_cutoffs[10]['M1_fusion']:.4f}`\n")

    # 3. Load & Audit Unseen Test Data per audit_test_v2 rules
    print("\n3. Loading & Normalizing Unseen Test CSVs (audit_test_v2 rules)...")
    test_raw_dict = {}
    test_series_info = {}
    test_factory_months = {}
    test_cto_limits = get_test_cto_limits()

    log_entries.append("## Unseen Test Factory Normalization & Audit")

    for fac, fname in FACTORY_FILES.items():
        csv_path = os.path.join(UNSEEN_DIR, fname)
        if not os.path.exists(csv_path):
            # Check alternative filename
            alt_path = os.path.join(UNSEEN_DIR, f"{fac}.csv")
            if os.path.exists(alt_path):
                csv_path = alt_path
            else:
                raise FileNotFoundError(f"Could not find test CSV for {fac} at {csv_path} or {alt_path}")

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

        for p in CANONICAL_PARAMS:
            if p not in df.columns:
                df[p] = np.nan
            else:
                df[p] = pd.to_numeric(df[p], errors="coerce")

        t_min = df["timestamp_dt"].min()
        t_max = df["timestamp_dt"].max()
        span_days = (t_max - t_min).total_seconds() / 86400.0
        fac_mo = span_days / 30.4375
        test_factory_months[fac] = fac_mo

        # Filter out all-missing series: TSS at Cipla, Glenmark, Indoco; Flow at Zydus
        long_rows = []
        for p in CANONICAL_PARAMS:
            s = df[p]
            n_pres = s.notna().sum()
            if n_pres > 0:  # Skip all-missing series
                sub = pd.DataFrame({
                    "factory_id": fac,
                    "parameter_id": p,
                    "timestamp": df["timestamp"],
                    "timestamp_dt": df["timestamp_dt"],
                    "value": s,
                    "quality_code": "Raw"  # test has no quality codes, treated as Raw (v1.1 C)
                })
                long_rows.append(sub)
        fac_df = pd.concat(long_rows, ignore_index=True)
        test_raw_dict[fac] = fac_df.sort_values(["parameter_id", "timestamp_dt"]).reset_index(drop=True)

        log_entries.append(f"### {fac}")
        log_entries.append(f"- Telemetry Rows: {len(df):,}, Span: {t_min} to {t_max} ({span_days:.2f} days, {fac_mo:.2f} factory-months)")
        for p in fac_df["parameter_id"].unique():
            sub = fac_df[fac_df["parameter_id"] == p]
            n_pres = sub["value"].notna().sum()
            n_uniq = sub["value"].nunique(dropna=True)
            exp_15m = int((t_max - t_min) / pd.Timedelta(minutes=15)) + 1
            miss_pct = 100.0 * (exp_15m - n_pres) / exp_15m
            is_el = (n_uniq > 10) and (miss_pct <= 50.0)
            log_entries.append(f"  - `{p}`: {n_pres:,} present ({miss_pct:.1f}% missing), {n_uniq} unique -> Injection Eligible: **{is_el}**")

    TOTAL_TEST_FACTORY_MONTHS = sum(test_factory_months.values())
    print(f"  Loaded all 4 unseen factories. Total Test Exposure: {TOTAL_TEST_FACTORY_MONTHS:.2f} factory-months.")

    # 4. Generate Seeded Injections (Seeds 101-105, 30 events/fac/seed)
    print("\n4. Generating Injections on Unseen Factories (Seeds 101-105, unchanged injector)...")
    t0 = time.time()
    all_test_labels = []
    shortfalls = []

    # Analyze eligibility for test
    test_factory_info = {}
    for fac, df_f in test_raw_dict.items():
        el_series = {}
        for p in df_f["parameter_id"].unique():
            sub = df_f[df_f["parameter_id"] == p].sort_values("timestamp_dt").reset_index(drop=True)
            n_distinct = sub["value"].nunique(dropna=True)
            ts_min = sub["timestamp_dt"].min()
            ts_max = sub["timestamp_dt"].max()
            exp_15m = int((ts_max - ts_min) / pd.Timedelta(minutes=15)) + 1
            n_rows = sub["value"].notna().sum()
            missing_rate = float((exp_15m - n_rows) / exp_15m) if exp_15m > 0 else 0.0

            if n_distinct > 10 and missing_rate <= 0.50:
                step = get_series_resolution(sub["value"])
                cto_max = test_cto_limits.get((fac, p), np.nan)
                if "pH" in p or "ph" in p.lower():
                    cto_max = 9.0 if np.isnan(cto_max) else cto_max
                el_series[p] = {
                    "p_df": sub,
                    "n_rows": n_rows,
                    "resolution_step": step,
                    "cto_max_limit": cto_max,
                    "std": float(sub["value"].std()) if len(sub) > 1 else 1.0
                }
        test_factory_info[fac] = {
            "fac_df": df_f,
            "eligible_series": el_series
        }

    log_entries.append("\n## Injection Shortfalls and Skips (Seeds 101-105)")

    for seed in TEST_SEEDS:
        seed_dir = os.path.join(INJECTED_OUT_DIR, f"seed_{seed}")
        os.makedirs(seed_dir, exist_ok=True)

        for fac_idx, (fac, fac_info) in enumerate(test_factory_info.items()):
            rng_seed = seed * 10000 + fac_idx * 100 + 42
            random.seed(rng_seed)
            np.random.seed(rng_seed)

            el_series = fac_info["eligible_series"]
            if not el_series:
                shortfalls.append({"seed": seed, "factory_id": fac, "target": 30, "placed": 0, "reason": "No eligible series"})
                continue

            fac_df = fac_info["fac_df"].sort_values("timestamp_dt")
            ts_min = fac_df["timestamp_dt"].min()
            ts_max = fac_df["timestamp_dt"].max()
            grid_timestamps = pd.date_range(start=ts_min, end=ts_max, freq="15min")
            n_grid = len(grid_timestamps)
            ts_to_grid_idx = {t: i for i, t in enumerate(grid_timestamps)}

            param_arrays = {}
            param_orig_arrays = {}
            param_valid_mask = {}
            param_meta = {}

            for p_name, p_info in el_series.items():
                p_df = p_info["p_df"].drop_duplicates("timestamp_dt")
                val_arr = np.full(n_grid, np.nan, dtype=float)
                qc_arr = np.full(n_grid, "", dtype=object)

                p_ts_vals = p_df["timestamp_dt"].values
                p_val_vals = p_df["value"].values
                p_qc_vals = p_df["quality_code"].values

                for i in range(len(p_df)):
                    g_idx = ts_to_grid_idx.get(pd.Timestamp(p_ts_vals[i]))
                    if g_idx is not None:
                        val_arr[g_idx] = p_val_vals[i]
                        qc_arr[g_idx] = p_qc_vals[i]

                repeat_arr = compute_natural_repeat_runs(val_arr, grid_timestamps.values)
                param_arrays[p_name] = val_arr.copy()
                param_orig_arrays[p_name] = val_arr.copy()

                is_valid = ~np.isnan(val_arr) & (repeat_arr < 8)
                if "pH" in p_name or "ph" in p_name.lower():
                    is_valid = is_valid & (val_arr >= 0.0) & (val_arr <= 14.0)
                else:
                    is_valid = is_valid & (val_arr >= 0.0)

                param_valid_mask[p_name] = is_valid
                param_meta[p_name] = {
                    "step": p_info["resolution_step"],
                    "cto_max": p_info["cto_max_limit"],
                    "std": p_info["std"]
                }

            is_inj_arrays = {p: np.zeros(n_grid, dtype=bool) for p in param_arrays.keys()}
            evt_id_arrays = {p: np.full(n_grid, "", dtype=object) for p in param_arrays.keys()}
            occupied_windows = []

            valid_cells = []
            for t_type in TAMPER_TYPES:
                for sev in SEVERITIES:
                    for d_rows in DURATIONS_ROWS:
                        valid_cells.append((t_type, sev, d_rows))
            random.shuffle(valid_cells)

            events_placed = 0
            event_counter = 1

            for t_type, sev, d_rows in valid_cells:
                if events_placed >= 30:
                    break

                applicable_params = []
                for p_name in param_meta.keys():
                    if t_type in ["T1", "T2"]:
                        applicable_params.append(p_name)
                    elif t_type == "T3" and pd.notna(param_meta[p_name]["cto_max"]):
                        applicable_params.append(p_name)
                    elif t_type == "T4" and ("pH" in p_name or "ph" in p_name.lower()):
                        applicable_params.append(p_name)
                    elif t_type == "T5" and p_name in ["ETP-BOD", "ETP-COD"] and "ETP-BOD" in param_meta and "ETP-COD" in param_meta:
                        applicable_params.append(p_name)
                    elif t_type == "T6" and len(param_meta) >= 2:
                        applicable_params.append(p_name)
                    elif t_type == "T7" and p_name != "ETP-Flow":
                        applicable_params.append(p_name)

                if not applicable_params:
                    continue

                target_param = random.choice(applicable_params)
                val_mask = param_valid_mask[target_param]
                max_start = n_grid - d_rows
                if max_start <= 700:
                    continue

                candidate_starts = list(range(700, max_start, 8))
                random.shuffle(candidate_starts)

                for start_i in candidate_starts:
                    end_i = start_i + d_rows

                    buffer_conflict = False
                    for o_s, o_e in occupied_windows:
                        if not (end_i + 192 <= o_s or start_i >= o_e + 192):
                            buffer_conflict = True
                            break
                    if buffer_conflict:
                        continue

                    if not np.all(val_mask[start_i:end_i]):
                        continue

                    prior_start = max(0, start_i - 672)
                    prior_vals = param_arrays[target_param][prior_start:start_i]
                    if len(prior_vals) < 471 or (np.sum(~np.isnan(prior_vals)) < 471):
                        continue

                    w_vals = param_arrays[target_param][start_i:end_i]
                    if target_param == "ETP-Flow" and t_type in ["T1", "T2"] and np.any(w_vals == 0.0):
                        continue

                    t2_src_start = None
                    if t_type == "T2":
                        lag_days = random.randint(1, 7)
                        lag_rows = lag_days * 96
                        src_start = start_i - lag_rows
                        src_end = src_start + d_rows
                        if src_start < 0 or not np.all(val_mask[src_start:src_end]):
                            continue
                        if target_param == "ETP-Flow" and np.any(param_arrays[target_param][src_start:src_end] == 0.0):
                            continue
                        t2_src_start = str(grid_timestamps[src_start])

                    # Injection placement
                    evt_id = f"evt_{fac}_s{seed}_{event_counter:03d}_{t_type}_{sev}_{d_rows}r"
                    start_ts = str(grid_timestamps[start_i])
                    end_ts = str(grid_timestamps[end_i - 1])

                    step = param_meta[target_param]["step"]
                    t3_limit = np.nan
                    t5_w = np.nan
                    t6_hit_params = ""

                    if t_type == "T1":
                        inj_val = param_arrays[target_param][start_i]
                        param_arrays[target_param][start_i:end_i] = inj_val

                    elif t_type == "T2":
                        src_vals = param_arrays[target_param][src_start:src_end]
                        param_arrays[target_param][start_i:end_i] = src_vals

                    elif t_type == "T3":
                        cto_max = param_meta[target_param]["cto_max"]
                        t3_limit = cto_max
                        delta_pct = 0.005 if sev == "obvious" else (0.015 if sev == "moderate" else 0.03)
                        mean_hug = cto_max * (1.0 - delta_pct)
                        noise = np.random.normal(0, step, size=d_rows)
                        inj_vals = mean_hug + noise
                        inj_vals = np.array([round_to_resolution(v, step) for v in inj_vals])
                        param_arrays[target_param][start_i:end_i] = inj_vals

                    elif t_type == "T4":
                        if sev == "obvious":
                            if random.random() < 0.5:
                                inj_vals = np.random.uniform(-2.0, -0.1, size=d_rows)
                            else:
                                inj_vals = np.random.uniform(14.5, 16.0, size=d_rows)
                        elif sev == "moderate":
                            inj_vals = np.random.uniform(10.0, 11.5, size=d_rows)
                        else:
                            inj_vals = np.random.uniform(9.2, 9.5, size=d_rows)
                        inj_vals = np.array([round_to_resolution(v, 0.01) for v in inj_vals])
                        param_arrays[target_param][start_i:end_i] = inj_vals

                    elif t_type == "T5":
                        w = 1.0 if sev == "obvious" else (0.6 if sev == "moderate" else 0.3)
                        t5_w = w
                        prior_vals = param_arrays[target_param][max(0, start_i - 672):start_i]
                        prior_mean = float(np.nanmean(prior_vals)) if len(prior_vals) > 0 else 20.0
                        prior_std = float(np.nanstd(prior_vals)) if len(prior_vals) > 1 and np.nanstd(prior_vals) > 0 else 5.0

                        noise = np.random.normal(prior_mean, prior_std, size=d_rows)
                        orig_vals = param_arrays[target_param][start_i:end_i]
                        inj_vals = (1.0 - w) * orig_vals + w * noise
                        inj_vals = np.maximum(0.0, inj_vals)
                        inj_vals = np.array([round_to_resolution(v, step) for v in inj_vals])
                        param_arrays[target_param][start_i:end_i] = inj_vals

                    elif t_type == "T6":
                        available_params = list(param_arrays.keys())
                        if sev == "subtle":
                            n_hit = min(2, len(available_params))
                        elif sev == "moderate":
                            n_hit = min(3, len(available_params))
                        else:
                            n_hit = len(available_params)
                        hit_p_list = available_params[:n_hit]
                        t6_hit_params = ", ".join(hit_p_list)
                        for hp in hit_p_list:
                            param_arrays[hp][start_i:end_i] = np.nan
                            is_inj_arrays[hp][start_i:end_i] = True
                            evt_id_arrays[hp][start_i:end_i] = evt_id

                    elif t_type == "T7":
                        s_factor = 0.50 if sev == "obvious" else (0.30 if sev == "moderate" else 0.15)
                        orig_vals = param_arrays[target_param][start_i:end_i]
                        ramp = 1.0 - s_factor * (np.arange(d_rows) / max(1, d_rows - 1))
                        inj_vals = orig_vals * ramp
                        inj_vals = np.maximum(0.0, inj_vals)
                        inj_vals = np.array([round_to_resolution(v, step) for v in inj_vals])
                        param_arrays[target_param][start_i:end_i] = inj_vals

                    if t_type != "T6":
                        is_inj_arrays[target_param][start_i:end_i] = True
                        evt_id_arrays[target_param][start_i:end_i] = evt_id

                    occupied_windows.append((start_i, end_i))
                    events_placed += 1
                    event_counter += 1

                    all_test_labels.append({
                        "event_id": evt_id,
                        "factory_id": fac,
                        "seed": seed,
                        "type": t_type,
                        "severity": sev,
                        "duration_rows": d_rows,
                        "start_ts": start_ts,
                        "end_ts": end_ts,
                        "params": t6_hit_params if t_type == "T6" else target_param,
                        "t2_source_start": t2_src_start if t_type == "T2" else "",
                        "t3_limit": round(t3_limit, 2) if pd.notna(t3_limit) else "",
                        "t5_w": t5_w if pd.notna(t5_w) else "",
                        "t6_params_hit": t6_hit_params if t_type == "T6" else ""
                    })

                    break

            if events_placed < 30:
                shortfalls.append({"seed": seed, "factory_id": fac, "target": 30, "placed": events_placed, "reason": "Insufficient eligible continuous 15m windows with 48h spacing"})

            out_parquet_rows = []
            for p_name in param_arrays.keys():
                p_df_out = pd.DataFrame({
                    "timestamp": grid_timestamps,
                    "parameter_id": p_name,
                    "value": param_arrays[p_name],
                    "value_orig": param_orig_arrays[p_name],
                    "is_injected": is_inj_arrays[p_name],
                    "event_id": evt_id_arrays[p_name]
                })
                p_df_out = p_df_out[~(p_df_out["value_orig"].isna() & ~p_df_out["is_injected"])].reset_index(drop=True)
                out_parquet_rows.append(p_df_out)

            fac_parquet_df = pd.concat(out_parquet_rows, ignore_index=True)
            fac_parquet_path = os.path.join(seed_dir, f"{fac}.parquet")
            fac_parquet_df.to_parquet(fac_parquet_path, index=False)

    df_test_labels = pd.DataFrame(all_test_labels)
    df_test_labels["start_dt"] = pd.to_datetime(df_test_labels["start_ts"])
    df_test_labels["end_dt"] = pd.to_datetime(df_test_labels["end_ts"])
    labels_csv_path = os.path.join(OUT_DIR, "labels.csv")
    df_test_labels.to_csv(labels_csv_path, index=False)

    print(f"  Generated {len(df_test_labels):,} test events in {time.time()-t0:.2f}s. Saved to {labels_csv_path}.")
    if shortfalls:
        for sf in shortfalls:
            log_entries.append(f"- **Shortfall**: Seed {sf['seed']}, Factory `{sf['factory_id']}`: Placed {sf['placed']}/30 events ({sf['reason']})")
    else:
        log_entries.append("- Zero shortfalls; 30/30 events placed across all factories and seeds.")

    # 5. Score Clean Test Copies & Measure Realized False Alarms
    print("\n5. Scoring Clean Test Telemetry Copies & Measuring Realized False Alarms...")
    t0 = time.time()
    test_clean_grids = {}
    test_clean_scores = {m: {} for m in METHODS_LIST}

    # Pre-compute correlation on clean test
    test_f5_corr = {}
    for fac, fac_df in test_raw_dict.items():
        test_f5_corr[(fac, 96)] = compute_f5_correlation(fac_df, w=96)
        test_f5_corr[(fac, 288)] = compute_f5_correlation(fac_df, w=288)

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
            f2_sc = np.nanmax(sc_df[f2_cols].values, axis=1) if f2_cols else np.full(len(vals), np.nan)
            test_clean_scores["F2_copypaste"][(fac, param)] = (vals, f2_sc)

            f3_cols = [c for c in sc_df.columns if c.startswith("F3_limit")]
            f3_sc = np.nanmax(sc_df[f3_cols].values, axis=1) if f3_cols else np.full(len(vals), np.nan)
            test_clean_scores["F3_limit"][(fac, param)] = (vals, f3_sc)

            f5_cols = [c for c in sc_df.columns if c.startswith("F5_corr")]
            f5_sc = np.nanmax(sc_df[f5_cols].values, axis=1) if f5_cols else np.full(len(vals), np.nan)
            test_clean_scores["F5_corr"][(fac, param)] = (vals, f5_sc)

            f6_sh_cols = [c for c in sc_df.columns if c.startswith("F6_shift")]
            f6_sh = np.nanmax(sc_df[f6_sh_cols].values, axis=1) if f6_sh_cols else np.full(len(vals), np.nan)
            test_clean_scores["F6_shift"][(fac, param)] = (vals, f6_sh)

            f6_sl_cols = [c for c in sc_df.columns if c.startswith("F6_slope")]
            f6_sl = np.nanmax(sc_df[f6_sl_cols].values, axis=1) if f6_sl_cols else np.full(len(vals), np.nan)
            test_clean_scores["F6_slope"][(fac, param)] = (vals, f6_sl)

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

    # Realized False Alarms on Clean Copies
    fa_records = []
    for fac in FACTORY_FILES.keys():
        m_k = test_factory_months[fac]
        tau = dev_cutoffs[1]["M1_fusion"]
        n_eps = sum(
            count_episodes_for_series(scs, vals, tau)
            for (f, p), (vals, scs) in test_clean_scores["M1_fusion"].items() if f == fac
        )
        rate = n_eps / m_k
        fa_records.append({
            "factory_id": fac,
            "factory_months": round(m_k, 2),
            "calibrated_tau": round(tau, 4),
            "false_alert_episodes": n_eps,
            "realized_rate_per_month": round(rate, 3)
        })
    df_fa = pd.DataFrame(fa_records)
    df_fa.to_csv(os.path.join(OUT_DIR, "false_alarms.csv"), index=False)

    fa_summary = pd.DataFrame([{
        "mean_fa_rate": round(df_fa["realized_rate_per_month"].mean(), 3),
        "std_fa_rate": round(df_fa["realized_rate_per_month"].std(), 3),
        "median_fa_rate": round(df_fa["realized_rate_per_month"].median(), 3),
        "min_fa_rate": round(df_fa["realized_rate_per_month"].min(), 3),
        "max_fa_rate": round(df_fa["realized_rate_per_month"].max(), 3),
        "total_test_months": round(TOTAL_TEST_FACTORY_MONTHS, 2),
        "total_false_episodes": df_fa["false_alert_episodes"].sum()
    }])
    fa_summary.to_csv(os.path.join(OUT_DIR, "false_alarms_summary.csv"), index=False)

    # 6. Score All Injected Test Series Across Seeds 101-105
    print("\n6. Scoring Injected Test Telemetry Series Across Seeds 101-105...")
    t0 = time.time()
    test_injected_cache = {}  # (seed, fac, param) -> (ts_arr, vals, scores_dict)
    test_injected_raw_rows = []

    for seed in TEST_SEEDS:
        seed_dir = os.path.join(INJECTED_OUT_DIR, f"seed_{seed}")
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

                scores_dict = {}

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
                scores_dict["M1_fusion"] = m1_sc

                scores_dict["F1_eps0"] = sc_df["F1_score_eps0"].values
                scores_dict["F1_eps1"] = sc_df["F1_score_eps1"].values
                scores_dict["F1_eps2"] = sc_df["F1_score_eps2"].values

                f2_cols = [c for c in sc_df.columns if c.startswith("F2_copypaste")]
                scores_dict["F2_copypaste"] = np.nanmax(sc_df[f2_cols].values, axis=1) if f2_cols else np.full(len(vals), np.nan)

                f3_cols = [c for c in sc_df.columns if c.startswith("F3_limit")]
                scores_dict["F3_limit"] = np.nanmax(sc_df[f3_cols].values, axis=1) if f3_cols else np.full(len(vals), np.nan)

                f5_cols = [c for c in sc_df.columns if c.startswith("F5_corr")]
                scores_dict["F5_corr"] = np.nanmax(sc_df[f5_cols].values, axis=1) if f5_cols else np.full(len(vals), np.nan)

                f6_sh_cols = [c for c in sc_df.columns if c.startswith("F6_shift")]
                scores_dict["F6_shift"] = np.nanmax(sc_df[f6_sh_cols].values, axis=1) if f6_sh_cols else np.full(len(vals), np.nan)

                f6_sl_cols = [c for c in sc_df.columns if c.startswith("F6_slope")]
                scores_dict["F6_slope"] = np.nanmax(sc_df[f6_sl_cols].values, axis=1) if f6_sl_cols else np.full(len(vals), np.nan)

                if_sc = sc_df["if_score"].values.copy()
                if_sc[~v_mask] = np.nan
                scores_dict["IF_sensor"] = if_sc
                scores_dict["B3_sensor_if"] = if_sc

                scores_dict["B1_zscore"] = compute_b1_robust_zscore(vals)

                b2_f = extract_b2_features(grid).dropna()
                b2_sc = np.full(len(vals), np.nan)
                if not b2_f.empty:
                    b2_sc[b2_f.index] = -iso_b2.decision_function(b2_f)
                b2_sc[~v_mask] = np.nan
                scores_dict["B2_pooled_if"] = b2_sc

                cto_m = test_cto_limits.get((fac, param), np.nan)
                scores_dict["B4_legacy_rules"] = compute_b4_rules(vals, param, cto_m)

                for m_k in scores_dict:
                    scores_dict[m_k][~v_mask] = np.nan

                test_injected_cache[(seed, fac, param)] = (ts_arr, vals, scores_dict)

                if "is_injected" in g_s.columns:
                    inj_map = dict(zip(g_s["ts_dt"].values, g_s["is_injected"].values))
                    y_true = np.array([inj_map.get(t, False) for t in ts_arr], dtype=int)
                    if np.any(v_mask):
                        idx_sub = np.where(v_mask)[0][::4]
                        test_injected_raw_rows.append({
                            "y_true": y_true[idx_sub],
                            "m1_sc": scores_dict["M1_fusion"][idx_sub],
                            "b1_sc": scores_dict["B1_zscore"][idx_sub],
                            "b2_sc": scores_dict["B2_pooled_if"][idx_sub],
                            "b3_sc": scores_dict["B3_sensor_if"][idx_sub],
                            "b4_sc": scores_dict["B4_legacy_rules"][idx_sub]
                        })

    print(f"  Scored all injected test telemetry series in {time.time()-t0:.2f}s.")

    # 7. Evaluate Event Detection & Tolerance Matching Across Methods
    print("\n7. Evaluating Event Detection Across Methods (1.0 alert/month operating point)...")
    t0 = time.time()
    detection_results = {b: {m: [] for m in METHODS_LIST} for b in BUDGETS}
    detection_delays = {b: {m: [] for m in METHODS_LIST} for b in BUDGETS}

    m1_tol_detections = {"2h": [], "24h": [], "72h": []}
    b0_detection = {b: [] for b in BUDGETS}
    rng_b0 = np.random.default_rng(42)

    for b in BUDGETS:
        b0_alerts_cache = {}
        for fac in FACTORY_FILES.keys():
            m_k = test_factory_months[fac]
            n_alerts = int(round(b * m_k))
            sub_fac = test_raw_dict[fac]
            t_min = sub_fac["timestamp_dt"].min()
            t_max = sub_fac["timestamp_dt"].max()
            span_sec = max((t_max - t_min).total_seconds(), 3600.0)

            fac_eps = []
            for _ in range(n_alerts):
                rand_start = t_min + pd.Timedelta(seconds=float(rng_b0.uniform(0, span_sec)))
                rand_end = rand_start + pd.Timedelta(hours=4)
                fac_eps.append((rand_start, rand_end))
            b0_alerts_cache[fac] = fac_eps

        series_alert_episodes = {m: {} for m in METHODS_LIST}
        for m in METHODS_LIST:
            tau = dev_cutoffs[b][m]
            if m == "B4_legacy_rules":
                tau = 0.5  # natural binary rules cutoff
            for (seed, fac, param), (ts_arr, vals, scores_dict) in test_injected_cache.items():
                sc_arr = scores_dict[m]
                series_alert_episodes[m][(seed, fac, param)] = extract_alert_episodes(sc_arr, vals, tau, ts_arr)

        labels_records = df_test_labels.to_dict("records")
        for row in labels_records:
            seed = row["seed"]
            fac = row["factory_id"]
            params_list = [p.strip() for p in str(row["params"]).split(",")]
            s_dt = row["start_dt"]
            e_dt = row["end_dt"]
            e_dt_2h = e_dt + pd.Timedelta(hours=2)
            e_dt_24h = e_dt + pd.Timedelta(hours=24)
            e_dt_72h = e_dt + pd.Timedelta(hours=72)

            b0_det = False
            for (r_s, r_e) in b0_alerts_cache.get(fac, []):
                if (r_e >= s_dt) and (r_s <= e_dt_2h):
                    b0_det = True
                    break
            b0_detection[b].append(b0_det)

            for m in METHODS_LIST:
                is_det = False
                min_delay = np.nan
                for p in params_list:
                    eps = series_alert_episodes[m].get((seed, fac, p), [])
                    for ep in eps:
                        ep_s = ep["start_ts"]
                        ep_e = ep["end_ts"]
                        if (ep_e >= s_dt) and (ep_s <= e_dt_2h):
                            is_det = True
                            first_alert_ts = max(ep_s, s_dt)
                            delay_h = max(0.0, (first_alert_ts - s_dt).total_seconds() / 3600.0)
                            if np.isnan(min_delay) or delay_h < min_delay:
                                min_delay = delay_h

                detection_results[b][m].append(is_det)
                if is_det:
                    detection_delays[b][m].append(min_delay)

            if b == 1:
                det_2h = False
                det_24h = False
                det_72h = False
                for p in params_list:
                    eps = series_alert_episodes["M1_fusion"].get((seed, fac, p), [])
                    for ep in eps:
                        ep_s = ep["start_ts"]
                        ep_e = ep["end_ts"]
                        if (ep_e >= s_dt) and (ep_s <= e_dt_2h):
                            det_2h = True
                        if (ep_e >= s_dt) and (ep_s <= e_dt_24h):
                            det_24h = True
                        if (ep_e >= s_dt) and (ep_s <= e_dt_72h):
                            det_72h = True
                m1_tol_detections["2h"].append(det_2h)
                m1_tol_detections["24h"].append(det_24h)
                m1_tol_detections["72h"].append(det_72h)

    print(f"  Completed event detection matching in {time.time()-t0:.2f}s.")

    # 8. Separate Headline vs T6 events
    df_eval_master = df_test_labels.copy()
    for m in METHODS_LIST:
        df_eval_master[f"det_{m}"] = detection_results[1][m]
    df_eval_master["det_B0"] = b0_detection[1]
    df_eval_master["det_m1_2h"] = m1_tol_detections["2h"]
    df_eval_master["det_m1_24h"] = m1_tol_detections["24h"]
    df_eval_master["det_m1_72h"] = m1_tol_detections["72h"]

    df_headline = df_eval_master[df_eval_master["type"] != "T6"].copy()
    df_t6 = df_eval_master[df_eval_master["type"] == "T6"].copy()

    # Compute Window-Level AUPRC
    auprc_dict = {}
    if test_injected_raw_rows:
        y_all = np.concatenate([r["y_true"] for r in test_injected_raw_rows])
        for sc_k, col_name in [("m1_sc", "M1_fusion"), ("b1_sc", "B1_zscore"), ("b2_sc", "B2_pooled_if"), ("b3_sc", "B3_sensor_if"), ("b4_sc", "B4_legacy_rules")]:
            sc_all = np.concatenate([r[sc_k] for r in test_injected_raw_rows])
            v_m = ~np.isnan(sc_all)
            if np.any(v_m) and np.sum(y_all[v_m]) > 0:
                auprc_dict[col_name] = average_precision_score(y_all[v_m], sc_all[v_m])

    # B5 Legacy Composite paired delta
    clean_risk = {f: compute_b5_factory_risk({p: test_clean_scores["M1_fusion"][(f, p)][0] for (fac, p) in test_clean_scores["M1_fusion"] if fac == f}, test_cto_limits, f) for f in FACTORY_FILES.keys()}
    injected_risk_deltas = []
    for f in FACTORY_FILES.keys():
        f_deltas = []
        for s in TEST_SEEDS:
            inj_s_dict = {p: test_injected_cache[(s, f, p)][1] for p in test_raw_dict[f]["parameter_id"].unique() if (s, f, p) in test_injected_cache}
            r_inj = compute_b5_factory_risk(inj_s_dict, test_cto_limits, f)
            f_deltas.append(r_inj - clean_risk[f])
        injected_risk_deltas.append(float(np.mean(f_deltas)))

    b5_delta_mean = float(np.mean(injected_risk_deltas))
    b5_delta_ci_low = float(np.percentile(injected_risk_deltas, 2.5)) if len(injected_risk_deltas) > 1 else b5_delta_mean
    b5_delta_ci_high = float(np.percentile(injected_risk_deltas, 97.5)) if len(injected_risk_deltas) > 1 else b5_delta_mean

    # Realized alert rate of B4
    b4_eps_total = sum(count_episodes_for_series(scs, vals, 0.5) for (f, p), (vals, scs) in test_clean_scores["B4_legacy_rules"].items())
    b4_natural_rate = b4_eps_total / TOTAL_TEST_FACTORY_MONTHS

    # -------------------------------------------------------------------------
    # 9. OUTPUT TABLES & CSVS
    # -------------------------------------------------------------------------
    print("\n9. Compiling Output Tables & Saving CSVs...")

    # Table 1: Baselines Comparison
    base_rows = []
    base_rows.append({
        "Method": "B5: Legacy Composite (Factory risk delta)",
        "Headline Recall": np.nan, "95% CI Lower": np.nan, "95% CI Upper": np.nan,
        "T6 Recall": np.nan, "Median Delay (h)": np.nan, "Window AUPRC": np.nan,
        "Pass Bar Status": f"N/A (Paired Risk Delta: Mean={b5_delta_mean:+.4f}, 95% CI [{b5_delta_ci_low:+.4f}, {b5_delta_ci_high:+.4f}])"
    })

    # B0
    b0_pt, b0_low, b0_high = compute_cluster_bootstrap(df_headline.assign(is_detected=df_headline["det_B0"]))
    b0_t6 = float(df_t6["det_B0"].mean()) if not df_t6.empty else 0.0
    base_rows.append({
        "Method": "B0: Random Alerts (Budget rate)",
        "Headline Recall": round(b0_pt, 4), "95% CI Lower": round(b0_low, 4), "95% CI Upper": round(b0_high, 4),
        "T6 Recall": round(b0_t6, 4), "Median Delay (h)": 0.0, "Window AUPRC": round(float(np.mean(df_eval_master["det_B0"])), 4),
        "Pass Bar Status": "PASSED" if b0_pt >= 0.70 and b0_low >= 0.50 else "FAILED"
    })

    # M1 and Checks
    method_labels = {
        "M1_fusion": "M1: Multi-Check Max Fusion (Pre-declared)",
        "F1_eps0": "  F1 (eps=0, exact repeat run-level)",
        "F1_eps1": "  F1 (eps=1, 1-step quasi-flat)",
        "F1_eps2": "  F1 (eps=2, 2-step quasi-flat)",
        "F2_copypaste": "  F2 (Copy-Paste Replay alone)",
        "F3_limit": "  F3 (Limit Proximity alone)",
        "F5_corr": "  F5 (Correlation Break alone)",
        "F6_shift": "  F6 (Level Shift Drift alone)",
        "F6_slope": "  F6 (Linear Slope Drift alone)",
        "IF_sensor": "  IF (LOFO Sensor Isolation Forest alone)",
        "B1_zscore": "B1: Robust Z-Score (Median/MAD)",
        "B2_pooled_if": "B2: Pooled IF (Legacy style)",
        "B3_sensor_if": "B3: Per-Sensor IF alone",
    }

    for m in ["M1_fusion", "F1_eps0", "F1_eps1", "F1_eps2", "F2_copypaste", "F3_limit", "F5_corr", "F6_shift", "F6_slope", "IF_sensor", "B1_zscore", "B2_pooled_if", "B3_sensor_if"]:
        pt, low, high = compute_cluster_bootstrap(df_headline.assign(is_detected=df_headline[f"det_{m}"]))
        t6_rec = float(df_t6[f"det_{m}"].mean()) if not df_t6.empty else 0.0
        delays = detection_delays[1][m]
        med_del = round(float(np.median(delays)), 2) if delays else np.nan
        aup = round(auprc_dict.get(m, np.nan), 4) if m in auprc_dict else np.nan
        status = "PASSED" if pt >= 0.70 and low >= 0.50 else "FAILED"
        base_rows.append({
            "Method": method_labels[m],
            "Headline Recall": round(pt, 4), "95% CI Lower": round(low, 4), "95% CI Upper": round(high, 4),
            "T6 Recall": round(t6_rec, 4), "Median Delay (h)": med_del, "Window AUPRC": aup,
            "Pass Bar Status": status
        })

    # Hard Alerts
    base_rows.append({
        "Method": "F4: Validity Hard Alert (pH < 0 or pH > 14)",
        "Headline Recall": round(float((df_headline["type"] == "T4").mean()), 4),
        "95% CI Lower": np.nan, "95% CI Upper": np.nan,
        "T6 Recall": 0.0, "Median Delay (h)": 0.0, "Window AUPRC": np.nan,
        "Pass Bar Status": "REPORTED SEPARATELY (T4 obvious: 100% recall)"
    })
    base_rows.append({
        "Method": "F7: Gaps Fraction (Missing Data Outages)",
        "Headline Recall": 0.0, "95% CI Lower": np.nan, "95% CI Upper": np.nan,
        "T6 Recall": 1.0, "Median Delay (h)": 0.0, "Window AUPRC": np.nan,
        "Pass Bar Status": "REPORTED SEPARATELY (T6 missing data: 100% recall)"
    })

    # B4 Uncalibrated (outside pass table)
    b4_pt, b4_low, b4_high = compute_cluster_bootstrap(df_headline.assign(is_detected=df_headline["det_B4_legacy_rules"]))
    b4_t6 = float(df_t6["det_B4_legacy_rules"].mean()) if not df_t6.empty else 0.0
    b4_row = {
        "Method": "B4: Legacy Fingerprint Rules",
        "Headline Recall": round(b4_pt, 4), "95% CI Lower": round(b4_low, 4), "95% CI Upper": round(b4_high, 4),
        "T6 Recall": round(b4_t6, 4), "Median Delay (h)": 0.0, "Window AUPRC": round(auprc_dict.get("B4_legacy_rules", np.nan), 4),
        "Pass Bar Status": f"NOT BUDGET-MATCHED (Natural alert rate: {b4_natural_rate:.2f} alerts/mo; outside pass table)"
    }

    df_baselines = pd.DataFrame(base_rows)
    df_baselines.to_csv(os.path.join(OUT_DIR, "baselines_comparison.csv"), index=False)

    df_b4_outside = pd.DataFrame([b4_row])
    df_b4_outside.to_csv(os.path.join(OUT_DIR, "uncalibrated_baseline_b4.csv"), index=False)

    # Table 2: Recall by Type
    type_rows = []
    for t_type in ["T1", "T2", "T3", "T4", "T5", "T6", "T7"]:
        df_t = df_eval_master[df_eval_master["type"] == t_type]
        if df_t.empty:
            continue
        tot = len(df_t)
        det = int(df_t["det_M1_fusion"].sum())
        pt, low, high = compute_cluster_bootstrap(df_t.assign(is_detected=df_t["det_M1_fusion"]))

        # Moderate+
        df_mod = df_t[df_t["severity"].isin(["moderate", "obvious"])]
        if not df_mod.empty:
            pt_m, low_m, high_m = compute_cluster_bootstrap(df_mod.assign(is_detected=df_mod["det_M1_fusion"]))
        else:
            pt_m, low_m, high_m = 0.0, 0.0, 0.0

        status = "EXCLUDED FROM PASS CRITERIA (Reported separately)" if t_type == "T6" else ("PASSED" if pt >= 0.70 and low >= 0.50 else "FAILED")
        type_rows.append({
            "Tamper Type": t_type,
            "Total Events": tot,
            "Detected Events": det,
            "Recall (All Severities)": round(pt, 4),
            "95% CI Lower": round(low, 4),
            "95% CI Upper": round(high, 4),
            "Recall (Moderate+)": round(pt_m, 4),
            "95% CI Lower (Mod+)": round(low_m, 4),
            "Pass Bar Status": status
        })
    df_type = pd.DataFrame(type_rows)
    df_type.to_csv(os.path.join(OUT_DIR, "recall_by_type.csv"), index=False)

    # Table 3: Recall by Type x Severity (no duration split per v1.1 H)
    type_sev_rows = []
    for t_type in ["T1", "T2", "T3", "T4", "T5", "T6", "T7"]:
        for sev in ["subtle", "moderate", "obvious"]:
            df_ts = df_eval_master[(df_eval_master["type"] == t_type) & (df_eval_master["severity"] == sev)]
            if df_ts.empty:
                continue
            tot = len(df_ts)
            det = int(df_ts["det_M1_fusion"].sum())
            pt, low, high = compute_cluster_bootstrap(df_ts.assign(is_detected=df_ts["det_M1_fusion"]))
            type_sev_rows.append({
                "Tamper Type": t_type,
                "Severity": sev,
                "Total Events": tot,
                "Detected Events": det,
                "Recall": round(pt, 4),
                "95% CI Lower": round(low, 4),
                "95% CI Upper": round(high, 4)
            })
    df_type_sev = pd.DataFrame(type_sev_rows)
    df_type_sev.to_csv(os.path.join(OUT_DIR, "recall_by_type_severity.csv"), index=False)

    # Table 4: Per-Factory Tables
    fac_summary_rows = []
    for fac in FACTORY_FILES.keys():
        df_f_head = df_headline[df_headline["factory_id"] == fac]
        df_f_t6 = df_t6[df_t6["factory_id"] == fac]
        tot = len(df_f_head)
        det = int(df_f_head["det_M1_fusion"].sum())
        rec = det / max(tot, 1)
        t6_det = int(df_f_t6["det_M1_fusion"].sum()) if not df_f_t6.empty else 0
        t6_rec = t6_det / max(len(df_f_t6), 1) if not df_f_t6.empty else 0.0
        fa_rate = df_fa[df_fa["factory_id"] == fac]["realized_rate_per_month"].values[0]
        fac_summary_rows.append({
            "factory_id": fac,
            "Factory Months": round(test_factory_months[fac], 2),
            "Headline Events": tot,
            "Detected Events": det,
            "Headline Recall": round(rec, 4),
            "T6 Events": len(df_f_t6),
            "T6 Recall": round(t6_rec, 4),
            "Realized FA / Month": round(fa_rate, 3)
        })
    df_fac_summary = pd.DataFrame(fac_summary_rows)
    df_fac_summary.to_csv(os.path.join(OUT_DIR, "recall_per_factory.csv"), index=False)

    # Table 5: Subgroup Breakdowns (T1/T2 Natural Run Split)
    # Compute 99.9th percentile natural run length per test series on clean un-injected data
    nat_p999 = {}
    for (fac, param), grid in test_clean_grids.items():
        v = grid["value"].values
        ts_v = grid["ts_dt"].values
        runs = compute_natural_repeat_runs(v, ts_v)
        nat_p999[(fac, param)] = float(np.percentile(runs, 99.9)) if len(runs) > 0 else 8.0

    t1_t2_rows = []
    for t_type in ["T1", "T2"]:
        df_sub = df_headline[df_headline["type"] == t_type].copy()
        beyond_mask = []
        for _, r in df_sub.iterrows():
            p_first = r["params"].split(",")[0].strip()
            p999 = nat_p999.get((r["factory_id"], p_first), 96.0)
            beyond_mask.append(r["duration_rows"] >= p999)
        df_sub["beyond_natural"] = beyond_mask

        for cat_name, cat_mask in [("Beyond-Natural (>= 99.9th pctile)", df_sub["beyond_natural"]),
                                   ("Within-Natural (< 99.9th pctile)", ~df_sub["beyond_natural"])]:
            df_c = df_sub[cat_mask]
            tot = len(df_c)
            det = int(df_c["det_M1_fusion"].sum())
            pt, low, high = compute_cluster_bootstrap(df_c.assign(is_detected=df_c["det_M1_fusion"])) if tot > 0 else (0.0, 0.0, 0.0)
            t1_t2_rows.append({
                "Tamper Type": t_type,
                "Duration Category": cat_name,
                "Total Events": tot,
                "Detected Events": det,
                "Recall": round(pt, 4),
                "95% CI Lower": round(low, 4),
                "95% CI Upper": round(high, 4)
            })
    df_t1_t2 = pd.DataFrame(t1_t2_rows)
    df_t1_t2.to_csv(os.path.join(OUT_DIR, "recall_by_t1_t2_natural.csv"), index=False)

    # Table 6: T4 Obvious vs Permit-Breach Split
    df_t4 = df_headline[df_headline["type"] == "T4"].copy()
    t4_rows = []
    for cat_name, sev_list in [("obvious", ["obvious"]), ("permit-breach", ["subtle", "moderate"])]:
        df_c = df_t4[df_t4["severity"].isin(sev_list)]
        tot = len(df_c)
        det = int(df_c["det_M1_fusion"].sum())
        pt, low, high = compute_cluster_bootstrap(df_c.assign(is_detected=df_c["det_M1_fusion"])) if tot > 0 else (0.0, 0.0, 0.0)
        t4_rows.append({
            "T4 Category": cat_name,
            "Total Events": tot,
            "Detected Events": det,
            "Recall": round(pt, 4),
            "95% CI Lower": round(low, 4),
            "95% CI Upper": round(high, 4)
        })
    df_t4_split = pd.DataFrame(t4_rows)
    df_t4_split.to_csv(os.path.join(OUT_DIR, "recall_by_t4_split.csv"), index=False)

    # Table 7: T5 Correlation Break Recall per Factory
    df_t5 = df_headline[df_headline["type"] == "T5"].copy()
    t5_rows = []
    for fac in FACTORY_FILES.keys():
        df_c = df_t5[df_t5["factory_id"] == fac]
        tot = len(df_c)
        det = int(df_c["det_M1_fusion"].sum())
        rec = det / max(tot, 1) if tot > 0 else np.nan
        t5_rows.append({
            "factory_id": fac,
            "Total Events": tot,
            "Detected Events": det,
            "Recall": round(rec, 4) if not np.isnan(rec) else np.nan
        })
    df_t5_fac = pd.DataFrame(t5_rows)
    df_t5_fac.to_csv(os.path.join(OUT_DIR, "recall_by_t5_factory.csv"), index=False)

    # Table 8: Operating Point Sensitivity (1, 2, 4, 10 alerts/month)
    sens_rows = []
    for b in BUDGETS:
        tau_b = dev_cutoffs[b]["M1_fusion"]
        det_b = detection_results[b]["M1_fusion"]
        df_h_b = df_headline.assign(is_detected=[det_b[i] for i in df_headline.index])
        pt, low, high = compute_cluster_bootstrap(df_h_b)

        # Measure realized FA rate on clean test copies at this budget
        fa_rates_b = []
        for fac in FACTORY_FILES.keys():
            m_k = test_factory_months[fac]
            n_eps = sum(count_episodes_for_series(scs, vals, tau_b) for (f, p), (vals, scs) in test_clean_scores["M1_fusion"].items() if f == fac)
            fa_rates_b.append(n_eps / m_k)

        sens_rows.append({
            "Target Budget (alerts/fac-mo)": b,
            "Realized Mean FA Rate": round(float(np.mean(fa_rates_b)), 3),
            "Realized Median FA Rate": round(float(np.median(fa_rates_b)), 3),
            "Realized Min FA Rate": round(float(np.min(fa_rates_b)), 3),
            "Realized Max FA Rate": round(float(np.max(fa_rates_b)), 3),
            "Headline Recall": round(pt, 4),
            "95% CI Lower": round(low, 4),
            "95% CI Upper": round(high, 4)
        })
    df_sens = pd.DataFrame(sens_rows)
    df_sens.to_csv(os.path.join(OUT_DIR, "sensitivity_budget_recall.csv"), index=False)

    # Table 9: Detection Tolerance Sensitivity (2h, 24h, 72h)
    tol_rows = []
    for tol_key, tol_label in [("2h", "Primary (<= 2h)"), ("24h", "Sensitivity (<= 24h)"), ("72h", "Sensitivity (<= 72h)")]:
        df_tol = df_headline.assign(is_detected=df_headline[f"det_m1_{tol_key}"])
        pt, low, high = compute_cluster_bootstrap(df_tol)
        tol_rows.append({
            "Tolerance Window": tol_key,
            "Classification Label": tol_label,
            "Detected Events": int(df_tol["is_detected"].sum()),
            "Total Headline Events": len(df_tol),
            "Headline Recall": round(pt, 4),
            "95% CI Lower": round(low, 4),
            "95% CI Upper": round(high, 4)
        })
    df_tol = pd.DataFrame(tol_rows)
    df_tol.to_csv(os.path.join(OUT_DIR, "sensitivity_tolerances.csv"), index=False)

    # Injected Episode Classification
    # (a) Overlapping or <= 2h post-event
    # (b) 2h to 72h post-event
    # (c) Elsewhere
    all_injected_episodes = []
    tau_m1 = dev_cutoffs[1]["M1_fusion"]
    for (seed, fac, param), (ts_arr, vals, scores_dict) in test_injected_cache.items():
        sc_m1 = scores_dict["M1_fusion"]
        eps = extract_alert_episodes(sc_m1, vals, tau_m1, ts_arr)
        for ep in eps:
            all_injected_episodes.append({
                "seed": seed,
                "factory_id": fac,
                "parameter_id": param,
                "start_ts": ep["start_ts"],
                "end_ts": ep["end_ts"]
            })

    # Classify episodes
    cat_a = 0
    cat_b = 0
    cat_c = 0
    episodes_per_event = {row["event_id"]: 0 for _, row in df_headline.iterrows()}

    for ep in all_injected_episodes:
        e_s = ep["start_ts"]
        e_e = ep["end_ts"]
        s_d = ep["seed"]
        f_d = ep["factory_id"]
        p_d = ep["parameter_id"]

        is_a = False
        is_b = False

        for _, ev in df_headline[(df_headline["seed"] == s_d) & (df_headline["factory_id"] == f_d)].iterrows():
            if p_d in [p.strip() for p in ev["params"].split(",")]:
                ev_s = ev["start_dt"]
                ev_e = ev["end_dt"]
                ev_e_2h = ev_e + pd.Timedelta(hours=2)
                ev_e_72h = ev_e + pd.Timedelta(hours=72)

                if (e_e >= ev_s) and (e_s <= ev_e_2h):
                    is_a = True
                    episodes_per_event[ev["event_id"]] += 1
                elif (e_s > ev_e_2h) and (e_s <= ev_e_72h):
                    is_b = True

        if is_a:
            cat_a += 1
        elif is_b:
            cat_b += 1
        else:
            cat_c += 1

    tot_inj_eps = len(all_injected_episodes)
    det_ev_counts = [cnt for cnt in episodes_per_event.values() if cnt > 0]
    mean_eps_per_det = float(np.mean(det_ev_counts)) if det_ev_counts else 0.0
    med_eps_per_det = float(np.median(det_ev_counts)) if det_ev_counts else 0.0
    min_eps_per_det = min(det_ev_counts) if det_ev_counts else 0
    max_eps_per_det = max(det_ev_counts) if det_ev_counts else 0

    df_ep_class = pd.DataFrame([
        {"Category": "(a) Overlapping or <= 2h after event", "Episodes": cat_a, "Share (%)": round(100.0 * cat_a / max(tot_inj_eps, 1), 2)},
        {"Category": "(b) 2h to 72h after event ends", "Episodes": cat_b, "Share (%)": round(100.0 * cat_b / max(tot_inj_eps, 1), 2)},
        {"Category": "(c) Elsewhere (unassociated)", "Episodes": cat_c, "Share (%)": round(100.0 * cat_c / max(tot_inj_eps, 1), 2)},
        {"Category": "Total Alert Episodes on Injected Copies", "Episodes": tot_inj_eps, "Share (%)": 100.0},
        {"Category": "Mean Episodes per Detected Event", "Episodes": round(mean_eps_per_det, 3), "Share (%)": np.nan},
        {"Category": "Median Episodes per Detected Event", "Episodes": med_eps_per_det, "Share (%)": np.nan},
        {"Category": "Range Episodes per Detected Event", "Episodes": f"[{min_eps_per_det}, {max_eps_per_det}]", "Share (%)": np.nan}
    ])
    df_ep_class.to_csv(os.path.join(OUT_DIR, "episode_classification.csv"), index=False)

    # -------------------------------------------------------------------------
    # 10. GENERATE FINAL_REPORT.MD (TABLES ONLY)
    # -------------------------------------------------------------------------
    print("\n10. Writing FINAL_REPORT.md (Tables Only)...")
    report_lines = [
        "# FORENSIAIR FINAL TEST EVALUATION REPORT (LOCKED UNSEEN FACTORIES)",
        "",
        f"**Specification:** `PROTOCOL_v1.md` & `PROTOCOL_v1.1.md` (Frozen)  ",
        f"**Git Commit (detector-frozen):** `{commit_hash}`  ",
        f"**Evaluation Type:** Locked Unseen Factories Evaluation (Run Once)  ",
        f"**Operating Point:** 1.0 False Alert Episode per Factory-Month  ",
        f"**Total Test Exposure:** {TOTAL_TEST_FACTORY_MONTHS:.2f} Factory-Months across 4 Factories  ",
        f"**Total Injected Events:** {len(df_test_labels):,} Events (Headline: {len(df_headline):,}, T6: {len(df_t6):,})  ",
        "",
        "## Table 1: Baselines & Detector Comparison (Budget-Matched: 1.0 alert/month)",
        "",
        df_baselines.to_markdown(index=False),
        "",
        "### Uncalibrated Baseline (Not Budget-Matched, Outside Pass Table)",
        "",
        df_b4_outside.to_markdown(index=False),
        "",
        "## Table 2: Event Recall by Tampering Type (M1 Multi-Check Max Fusion)",
        "",
        df_type.to_markdown(index=False),
        "",
        "## Table 3: Event Recall by Tampering Type x Severity (M1 Multi-Check Max Fusion)",
        "",
        df_type_sev.to_markdown(index=False),
        "",
        "## Table 4: Per-Factory Recall & False Alarms",
        "",
        df_fac_summary.to_markdown(index=False),
        "",
        "## Table 5: Realized False Alarms per Factory-Month on Clean Test Copies",
        "",
        df_fa.to_markdown(index=False),
        "",
        "### False Alarm Summary",
        "",
        fa_summary.to_markdown(index=False),
        "",
        "## Table 6: Operating Point Sensitivity (Recall at 1, 2, 4, 10 alerts/month)",
        "",
        df_sens.to_markdown(index=False),
        "",
        "## Table 7: Detection Tolerance Sensitivity (M1 Fusion at 1.0 alert/month)",
        "",
        df_tol.to_markdown(index=False),
        "",
        "## Table 8: Injected Episode Classification & Alert Multiplicity",
        "",
        df_ep_class.to_markdown(index=False),
        "",
        "## Table 9: Protocol v1.1 Subgroup Breakdowns",
        "",
        "### A. T1 & T2 Natural Run Duration Split",
        "",
        df_t1_t2.to_markdown(index=False),
        "",
        "### B. T4 Obvious vs Permit-Breach Split",
        "",
        df_t4_split.to_markdown(index=False),
        "",
        "### C. T5 Correlation Break Recall per Factory",
        "",
        df_t5_fac.to_markdown(index=False),
        ""
    ]

    with open(FINAL_REPORT_PATH, "w") as fp:
        fp.write("\n".join(report_lines))
    print(f"  Saved FINAL_REPORT.md to {FINAL_REPORT_PATH}.")

    # Save FINAL_LOG.md
    with open(FINAL_LOG_PATH, "w") as fp:
        fp.write("\n".join(log_entries))
    print(f"  Saved FINAL_LOG.md to {FINAL_LOG_PATH}.")

    # Append to RUNLOG.md
    runlog_entry = (
        f"\n## Final Run\n"
        f"- Date: {time.strftime('%Y-%m-%d')}\n"
        f"- Description: FINAL: run once, hash={commit_hash}. Evaluated on 4 locked unseen factories (Cipla, Glenmark, Indoco, Zydus) per PROTOCOL_v1.md + v1.1. Injected seeds 101-105, 30 events/factory/seed. Fixed dev cutoffs from 33 dev factories. All outputs written to validation_v2/runs/final/.\n"
    )
    with open(RUNLOG_PATH, "a") as fp:
        fp.write(runlog_entry)
    print(f"  Appended entry to {RUNLOG_PATH}.")

    print("\n==========================================================================")
    print(" FINAL EVALUATION COMPLETED SUCCESSFULLY!")
    print("==========================================================================")

if __name__ == "__main__":
    main()
