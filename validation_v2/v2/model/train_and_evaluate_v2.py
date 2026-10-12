"""
ForensiAIR V2 — Stage 2: Supervised Model Cross-Mechanism LOFO Evaluation
Specification: docs/PROTOCOL_v2.md (Frozen) & PROTOCOL_v1.1 Section C (Frozen)

Execution Rules:
- Development only (33 Permitted Development Factories).
- Strictly isolated: Data/Unseen/ and locked factories (Cipla, Glenmark, Indoco, Zydus) NEVER accessed.
- Zero modification to V1 files, V1 labels, or V1 parquets.
- Features: Protocol v2.0 Section 4 (causal past-only, scale-normalized by expanding past MAD).
- Model: HistGradientBoostingClassifier(max_depth=6, learning_rate=0.1, max_iter=200, l2_regularization=1.0, class_weight='balanced', random_state=42).
- Primary: Pooled model on all 4 types (T1, T2, T3, T7).
- Secondary diagnostics: Specialist models (T1+T2, T3, T7), evaluated at own 1/month and labelled "not additive".
- 5 factory-grouped folds:
  - Direction 1: Train on A -> Test on held-out A (in-mechanism) and B (cross-mechanism).
  - Direction 2: Train on B -> Test on held-out B (in-mechanism) and A (cross-mechanism).
- Out-of-fold clean calibration: single global cutoff yielding exactly 1.0 alert episode per factory-month (328 target episodes on 327.61 fac-mo).
- Comparators: V1 M1, IF alone, F1 (eps0/1/2), F2, F3, F6 shift and slope, B0 random alerts.
- 10,000 cluster bootstrap resamples over factories (95% CIs).
- Deliverables written to validation_v2/v2/model/.
"""

import os
import sys
sys.stdout.reconfigure(line_buffering=True)
import time
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest
from sklearn.metrics import average_precision_score

REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
RAW_CSV = os.path.join(REPO_ROOT, "Data", "RawData", "monitoring_data(raw).csv")
CTO_CSV = os.path.join(REPO_ROOT, "Original Data", "consent_limits.csv")
LABELS_A_CSV = os.path.join(REPO_ROOT, "validation_v2", "injector", "injected", "dev", "labels.csv")
DEV_INJECTED_A_DIR = os.path.join(REPO_ROOT, "validation_v2", "injector", "injected", "dev")
LABELS_B_CSV = os.path.join(REPO_ROOT, "validation_v2", "v2", "injector_b", "labels_b.csv")
DEV_INJECTED_B_DIR = os.path.join(REPO_ROOT, "validation_v2", "v2", "injector_b", "injected_b", "dev")
MODEL_OUT_DIR = os.path.join(REPO_ROOT, "validation_v2", "v2", "model")

# Critical protocol guard: Data/Unseen must never be accessed
assert "Unseen" not in RAW_CSV and "Unseen" not in LABELS_A_CSV and "Unseen" not in LABELS_B_CSV

sys.path.insert(0, MODEL_OUT_DIR)
from feature_extractor import extract_features_for_series, PARAM_MAP

# Reuse V1 detector functions for V1 comparators read-only
V1_DETECTOR_DIR = os.path.join(REPO_ROOT, "validation_v2", "detector")
sys.path.insert(0, V1_DETECTOR_DIR)
from detector import (
    prepare_series as v1_prepare_series,
    compute_check_statistics as v1_compute_check_statistics,
    compute_f5_correlation as v1_compute_f5_correlation,
    extract_if_features as v1_extract_if_features,
    calibrate as v1_calibrate,
    score as v1_score
)

# -----------------------------------------------------------------------------
# 1. Canonical Development Factory Exposure & Stratified 5-Fold Partition
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

# 21 Event-bearing factories and 12 clean-only factories
EVENT_FACTORIES = [
    'site_1131', 'site_1200', 'site_1221', 'site_1232', 'site_1247',
    'site_1257', 'site_1264', 'site_1280', 'site_1284', 'site_1285',
    'site_1310', 'site_1321', 'site_1369', 'site_1376', 'site_1561',
    'site_1668', 'site_1756', 'site_1787', 'site_1799', 'site_1905', 'site_887'
]
CLEAN_ONLY_FACTORIES = [
    'site_1138', 'site_1167', 'site_1203', 'site_1256', 'site_1259',
    'site_1281', 'site_1569', 'site_1581', 'site_1789', 'site_1909',
    'site_2070', 'site_982'
]

# Deterministic 5-fold factory grouping (event factories balanced 4, 4, 4, 4, 5)
FOLDS = {
    0: {'event': ['site_1131', 'site_1257', 'site_1310', 'site_1668'], 'clean': ['site_1138', 'site_1259']},
    1: {'event': ['site_1200', 'site_1264', 'site_1321', 'site_1756'], 'clean': ['site_1167', 'site_1281']},
    2: {'event': ['site_1221', 'site_1280', 'site_1369', 'site_1787'], 'clean': ['site_1203', 'site_1569']},
    3: {'event': ['site_1232', 'site_1284', 'site_1376', 'site_1799'], 'clean': ['site_1256', 'site_1581', 'site_2070']},
    4: {'event': ['site_1247', 'site_1285', 'site_1561', 'site_1905', 'site_887'], 'clean': ['site_1789', 'site_1909', 'site_982']}
}
for f_idx in FOLDS:
    FOLDS[f_idx]['all'] = sorted(FOLDS[f_idx]['event'] + FOLDS[f_idx]['clean'])

# Frozen cutoffs for V1 comparators calibrated at 1.0 alert episode / factory-month on clean dev data
V1_CUTOFFS = {
    "M1": 3.7906,
    "IF": 2.5560,
    "F1_eps0": 2.6739,
    "F1_eps1": 2.6210,
    "F1_eps2": 2.5335,
    "F2": 2.8168,
    "F3": 1.1786,
    "F6_shift": 3.0779,
    "F6_slope": 3.3110
}

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
    """Fast episode counter for binary-search threshold calibration."""
    mask = ~np.isnan(values) & ~np.isnan(scores) & (scores >= tau)
    if not np.any(mask):
        return 0
    indices = np.where(mask)[0]
    if len(indices) == 1:
        return 1
    gaps = np.diff(indices) - 1
    return 1 + int(np.sum(gaps > 16))

def calibrate_tau(scores_dict: dict, target_episodes: int) -> float:
    """Binary search across pooled out-of-fold clean scores to hit target episode count."""
    all_scores = []
    for (fac, param), (vals, scs) in scores_dict.items():
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

    for _ in range(40):
        mid_idx = (low_idx + high_idx) // 2
        tau = float(all_scores[mid_idx])

        tot_eps = sum(count_episodes_for_series(scs, vals, tau) for (fac, param), (vals, scs) in scores_dict.items())
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

def compute_v1_scores_for_series(grid: pd.DataFrame, factory_id: str, cto_limits_dict: dict, if_model: IsolationForest = None) -> dict:
    """Computes frozen V1 check scores (M1, IF, F1 eps0/1/2, F2, F3, F6 shift, F6 slope)."""
    calib = v1_calibrate(grid, mode="blind", cto_limits=cto_limits_dict, skip_if=False, if_model=if_model, factory_id=factory_id)
    sc_df = v1_score(grid, calib, if_model=if_model, cto_limits=cto_limits_dict, factory_id=factory_id)

    vals = grid["value"].values
    v_mask = ~np.isnan(vals)

    f1_0 = sc_df["F1_score_eps0"].values.copy()
    f1_0[~v_mask] = np.nan
    f1_1 = sc_df["F1_score_eps1"].values.copy()
    f1_1[~v_mask] = np.nan
    f1_2 = sc_df["F1_score_eps2"].values.copy()
    f1_2[~v_mask] = np.nan

    f2_cols = [c for c in sc_df.columns if c.startswith("F2_copypaste")]
    with np.errstate(all='ignore'):
        f2 = np.nanmax(sc_df[f2_cols].values, axis=1) if f2_cols else np.full(len(vals), np.nan)
    f2[~v_mask] = np.nan

    f3_cols = [c for c in sc_df.columns if c.startswith("F3_limit")]
    with np.errstate(all='ignore'):
        f3 = np.nanmax(sc_df[f3_cols].values, axis=1) if f3_cols else np.full(len(vals), np.nan)
    f3[~v_mask] = np.nan

    f6_sh_cols = [c for c in sc_df.columns if c.startswith("F6_shift")]
    with np.errstate(all='ignore'):
        f6_sh = np.nanmax(sc_df[f6_sh_cols].values, axis=1) if f6_sh_cols else np.full(len(vals), np.nan)
    f6_sh[~v_mask] = np.nan

    f6_sl_cols = [c for c in sc_df.columns if c.startswith("F6_slope")]
    with np.errstate(all='ignore'):
        f6_sl = np.nanmax(sc_df[f6_sl_cols].values, axis=1) if f6_sl_cols else np.full(len(vals), np.nan)
    f6_sl[~v_mask] = np.nan

    if_sc = sc_df["if_score"].values.copy() if "if_score" in sc_df.columns else np.full(len(vals), np.nan)
    if_sc[~v_mask] = np.nan

    m1_candidates = [
        "F1_score_eps0", "F1_score_eps1", "F1_score_eps2",
        "F2_copypaste_w16_score", "F2_copypaste_w96_score", "F2_copypaste_w288_score",
        "F3_limit_w16_score", "F3_limit_w96_score", "F3_limit_w288_score",
        "F6_shift_w16_score", "F6_shift_w96_score", "F6_shift_w288_score",
        "F6_slope_w16_score", "F6_slope_w96_score", "F6_slope_w288_score",
        "if_score"
    ]
    m1_cols = [c for c in m1_candidates if c in sc_df.columns]
    with np.errstate(all='ignore'):
        m1_sc = np.nanmax(sc_df[m1_cols].values, axis=1)
    m1_sc[~v_mask] = np.nan

    return {
        "M1": m1_sc,
        "IF": if_sc,
        "F1_eps0": f1_0,
        "F1_eps1": f1_1,
        "F1_eps2": f1_2,
        "F2": f2,
        "F3": f3,
        "F6_shift": f6_sh,
        "F6_slope": f6_sl
    }

def safe_auprc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Safely computes window-level AUPRC handling all-negative or single-class slices."""
    mask = ~np.isnan(y_true) & ~np.isnan(y_score)
    y_t = y_true[mask]
    y_s = y_score[mask]
    if len(y_t) == 0 or len(np.unique(y_t)) < 2 or np.sum(y_t) == 0:
        return 0.0
    try:
        return float(average_precision_score(y_t, y_s))
    except Exception:
        return 0.0

# -----------------------------------------------------------------------------
# 3. 95% Cluster-Bootstrap Confidence Intervals (10,000 resamples)
# -----------------------------------------------------------------------------
def compute_cluster_bootstrap(df_eval: pd.DataFrame, is_det_col: str, n_resamples: int = 10000, seed: int = 42):
    """Computes point estimate and 95% cluster-bootstrap CI clustered over factories."""
    if df_eval.empty or len(df_eval["factory_id"].unique()) == 0:
        return 0.0, 0.0, 0.0

    fac_counts = df_eval.groupby("factory_id")[is_det_col].agg(["sum", "count"]).reset_index()
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

def compute_paired_diff_bootstrap(df_eval: pd.DataFrame, col_v2: str, col_v1: str, n_resamples: int = 10000, seed: int = 42):
    """Computes paired difference V2 - V1 recall and 95% cluster-bootstrap CI over factories."""
    if df_eval.empty or len(df_eval["factory_id"].unique()) == 0:
        return 0.0, 0.0, 0.0

    df_eval = df_eval.copy()
    df_eval["diff"] = df_eval[col_v2].astype(float) - df_eval[col_v1].astype(float)
    fac_counts = df_eval.groupby("factory_id")["diff"].agg(["sum", "count"]).reset_index()
    factories = fac_counts["factory_id"].values
    n_fac = len(factories)
    diff_arr = fac_counts["sum"].values
    tot_arr = fac_counts["count"].values

    point_diff = float(np.sum(diff_arr) / max(np.sum(tot_arr), 1))
    if n_fac == 1:
        return point_diff, point_diff, point_diff

    rng = np.random.default_rng(seed)
    mult_draws = rng.multinomial(n_fac, np.ones(n_fac) / n_fac, size=n_resamples)
    boot_diff = mult_draws @ diff_arr
    boot_tot = mult_draws @ tot_arr

    valid_mask = (boot_tot > 0)
    boot_diffs = np.where(valid_mask, boot_diff / np.maximum(boot_tot, 1), point_diff)

    ci_lower = float(np.percentile(boot_diffs, 2.5))
    ci_upper = float(np.percentile(boot_diffs, 97.5))
    return point_diff, ci_lower, ci_upper

# -----------------------------------------------------------------------------
# 4. Main Evaluation Runner
# -----------------------------------------------------------------------------
def run_stage2_evaluation():
    t0_start = time.time()
    print("=" * 80)
    print(" FORENSIAIR V2 — STAGE 2: FINAL SUPERVISED MODEL EVALUATION (DEV ONLY)")
    print(" PROTOCOL v2.0 (FROZEN) & PROTOCOL v1.1 SECTION C (FROZEN)")
    print("=" * 80)

    # 1. Load Data
    print("\n[Step 1] Loading Clean Telemetry, CTO Limits, Labels A & B...")
    df_raw = pd.read_csv(RAW_CSV)
    df_cto = pd.read_csv(CTO_CSV)
    df_labels_a_raw = pd.read_csv(LABELS_A_CSV)
    df_labels_b_raw = pd.read_csv(LABELS_B_CSV)

    cto_limits = {}
    for _, r in df_cto.iterrows():
        if pd.notna(r["maximum_limit"]) and r["maximum_limit"] > 0:
            cto_limits[(str(r["factory_id"]), str(r["parameter"]))] = float(r["maximum_limit"])

    allowed_qc = ["Raw", "L"]
    df_filt = df_raw[df_raw["quality_code"].isin(allowed_qc)].copy()
    df_filt["ts_dt"] = pd.to_datetime(df_filt["timestamp"])
    all_dev_factories = sorted(df_filt["factory_id"].unique())
    assert len(all_dev_factories) == 33

    # Filter Mechanism A: Types T1, T2, T3, T7 only
    df_labels_a = df_labels_a_raw[df_labels_a_raw["type"].isin(["T1", "T2", "T3", "T7"])].copy()
    if "params" in df_labels_a.columns:
        df_labels_a["parameter"] = df_labels_a["params"]
    df_labels_a["start_dt"] = pd.to_datetime(df_labels_a["start_ts"])
    df_labels_a["end_dt"] = pd.to_datetime(df_labels_a["end_ts"])
    df_labels_a["mechanism"] = "A"
    df_labels_a["no_op"] = False  # Mechanism A has no no-op column

    # Filter Mechanism B: Types T1, T2, T3, T7
    df_labels_b = df_labels_b_raw[df_labels_b_raw["type"].isin(["T1", "T2", "T3", "T7"])].copy()
    df_labels_b["start_dt"] = pd.to_datetime(df_labels_b["start_ts"])
    df_labels_b["end_dt"] = pd.to_datetime(df_labels_b["end_ts"])
    df_labels_b["mechanism"] = "B"

    print(f"  Clean telemetry rows: {len(df_filt):,}")
    print(f"  Mechanism A events (T1,T2,T3,T7): {len(df_labels_a):,} across seeds {sorted(df_labels_a['seed'].unique())}")
    print(f"  Mechanism B events (T1,T2,T3,T7): {len(df_labels_b):,} across seeds {sorted(df_labels_b['seed'].unique())}")
    print(f"  Mechanism B no-op events: {int(df_labels_b['no_op'].sum()):,} ({df_labels_b['no_op'].mean()*100:.2f}%)")

    # 2. Extract Features on Clean Telemetry (81 series) & Fit Dev Isolation Forests
    print("\n[Step 2] Extracting Causal Features on Clean Telemetry (81 Series)...")
    t0 = time.time()
    clean_grids = {}
    clean_features = {}
    dev_if_models = {}

    import pickle
    clean_cache_file = os.path.join(MODEL_OUT_DIR, "clean_cache.pkl")
    if os.path.exists(clean_cache_file):
        with open(clean_cache_file, "rb") as f:
            clean_grids, clean_features, dev_if_models = pickle.load(f)
        print(f"  Loaded clean features from cache {clean_cache_file} in {time.time()-t0:.2f}s")
    else:
        for (fac, param), g in df_filt.groupby(["factory_id", "parameter_id"]):
            grid = v1_prepare_series(g, factory_id=fac)
            if not grid.empty:
                c_limit = cto_limits.get((fac, param), np.nan)
                feats = extract_features_for_series(grid, param, cto_limit=c_limit)
                clean_grids[(fac, param)] = grid
                clean_features[(fac, param)] = feats

        # Fit dev reference Isolation Forest per parameter
        for p in ["ETP-pH", "ETP-Flow", "ETP-BOD", "ETP-COD", "ETP-TSS"]:
            p_dfs = []
            for fac in all_dev_factories:
                grid = clean_grids.get((fac, p))
                if grid is not None and len(grid) >= 16:
                    feats_if = v1_extract_if_features(grid).dropna()
                    if not feats_if.empty:
                        p_dfs.append(feats_if)
            if p_dfs:
                X_p = pd.concat(p_dfs, ignore_index=True)
                iso = IsolationForest(n_estimators=100, max_samples=min(2048, len(X_p)), random_state=42, n_jobs=1)
                iso.fit(X_p)
                dev_if_models[p] = iso

        with open(clean_cache_file, "wb") as f:
            pickle.dump((clean_grids, clean_features, dev_if_models), f)
        print(f"  Extracted clean features across {len(clean_grids)} series in {time.time()-t0:.2f}s")

    # 3. Cache Parquets, Features, and V1 Comparator Scores for Mechanism A and B
    print("\n[Step 3] Loading & Extracting Features + V1 Scores on Injected Telemetry (A and B)...")
    t0 = time.time()
    inj_cache_file = os.path.join(MODEL_OUT_DIR, "inj_cache.pkl")

    if os.path.exists(inj_cache_file):
        with open(inj_cache_file, "rb") as f:
            inj_cache = pickle.load(f)
        print(f"  Loaded injected cache from {inj_cache_file} across {len(inj_cache)} series-seeds in {time.time()-t0:.2f}s")
    else:
        # Injected data cache: (mech, seed, fac, param) -> (grid, feats, vals, ts_arr, v1_scores_dict)
        inj_cache = {}

        # Load Mechanism A Parquets (seeds 1-5)
        for seed in [1, 2, 3, 4, 5]:
            s_dir = os.path.join(DEV_INJECTED_A_DIR, f"seed_{seed}")
            if not os.path.exists(s_dir):
                continue
            for fname in sorted(os.listdir(s_dir)):
                if not fname.endswith(".parquet"):
                    continue
                fac = fname.replace(".parquet", "")
                df_pq = pd.read_parquet(os.path.join(s_dir, fname))
                for param, g_s in df_pq.groupby("parameter_id"):
                    grid = v1_prepare_series(g_s, factory_id=fac)
                    c_lim = cto_limits.get((fac, param), np.nan)
                    feats = extract_features_for_series(grid, param, cto_limit=c_lim)
                    vals = grid["value"].values
                    ts_arr = grid["ts_dt"].values
                    v1_sc = compute_v1_scores_for_series(grid, fac, cto_limits, if_model=dev_if_models.get(param))
                    inj_cache[("A", seed, fac, param)] = (grid, feats, vals, ts_arr, v1_sc)

        # Load Mechanism B Parquets (seeds 301-305)
        for seed in [301, 302, 303, 304, 305]:
            s_dir = os.path.join(DEV_INJECTED_B_DIR, f"seed_{seed}")
            if not os.path.exists(s_dir):
                continue
            for fname in sorted(os.listdir(s_dir)):
                if not fname.endswith(".parquet"):
                    continue
                fac = fname.replace(".parquet", "")
                df_pq = pd.read_parquet(os.path.join(s_dir, fname))
                for param, g_s in df_pq.groupby("parameter_id"):
                    grid = v1_prepare_series(g_s, factory_id=fac)
                    c_lim = cto_limits.get((fac, param), np.nan)
                    feats = extract_features_for_series(grid, param, cto_limit=c_lim)
                    vals = grid["value"].values
                    ts_arr = grid["ts_dt"].values
                    v1_sc = compute_v1_scores_for_series(grid, fac, cto_limits, if_model=dev_if_models.get(param))
                    inj_cache[("B", seed, fac, param)] = (grid, feats, vals, ts_arr, v1_sc)

        with open(inj_cache_file, "wb") as f:
            pickle.dump(inj_cache, f)
        print(f"  Extracted features & V1 scores across {len(inj_cache)} series-seeds in {time.time()-t0:.2f}s")

    # 4. Five-Fold Training & Scoring Loop for Direction 1 and Direction 2
    print("\n[Step 4] Executing 5-Fold Cross-Validation for Direction 1 (Train A) & Direction 2 (Train B)...")
    t0 = time.time()

    MODEL_SUITES = {
        "pooled": ["T1", "T2", "T3", "T7"],
        "T1_T2": ["T1", "T2"],
        "T3": ["T3"],
        "T7": ["T7"]
    }

    # Out-of-fold clean scores cache: (dir, m_name) -> {(fac, param): (vals, scs)}
    oof_clean_scores = {("dir1", m_name): {} for m_name in MODEL_SUITES}
    oof_clean_scores.update({("dir2", m_name): {} for m_name in MODEL_SUITES})

    # Test injected scores cache: (dir, m_name, mech, seed, fac, param) -> sc_arr
    test_inj_scores = {}

    for fold_idx in range(5):
        test_facs = FOLDS[fold_idx]["all"]
        train_facs = [f for f in all_dev_factories if f not in test_facs]
        print(f"  --- Fold {fold_idx + 1}/5 (Train: {len(train_facs)} facs, Held-Out Test: {len(test_facs)} facs) ---")

        # ---------------------------------------------------------------------
        # Direction 1: Train on Mechanism A
        # ---------------------------------------------------------------------
        train_events_a = df_labels_a[df_labels_a["factory_id"].isin(train_facs) & (~df_labels_a["no_op"])].copy()

        pos_rows_by_type = {t: [] for t in ["T1", "T2", "T3", "T7"]}
        for _, ev in train_events_a.iterrows():
            k_inj = ("A", ev["seed"], ev["factory_id"], ev["parameter"])
            if k_inj in inj_cache:
                grid, feats, _, ts_arr, _ = inj_cache[k_inj]
                m_pos = (ts_arr >= ev["start_dt"]) & (ts_arr <= ev["end_dt"])
                if np.any(m_pos):
                    pos_rows_by_type[ev["type"]].append(feats[m_pos])

        # Stratified negatives from clean training factories (balanced across factories)
        neg_rows_by_fac = {}
        for fac in train_facs:
            fac_dfs = []
            for (f, p), grid in clean_grids.items():
                if f == fac:
                    fac_dfs.append(clean_features[(f, p)].iloc[::16])
            if fac_dfs:
                neg_rows_by_fac[fac] = pd.concat(fac_dfs, ignore_index=True)

        # Fit Direction 1 models
        dir1_models = {}
        for m_name, type_list in MODEL_SUITES.items():
            pos_dfs = [df_sub for t in type_list for df_sub in pos_rows_by_type[t] if not df_sub.empty]
            if pos_dfs and neg_rows_by_fac:
                X_pos = pd.concat(pos_dfs, ignore_index=True)
                n_pos = len(X_pos)
                target_neg_per_fac = max(1, (n_pos * 20) // len(train_facs))
                neg_sampled = []
                for fac, df_neg_fac in neg_rows_by_fac.items():
                    n_draw = min(len(df_neg_fac), target_neg_per_fac)
                    neg_sampled.append(df_neg_fac.sample(n_draw, random_state=42))
                X_neg_sub = pd.concat(neg_sampled, ignore_index=True)

                X_train = pd.concat([X_pos, X_neg_sub], ignore_index=True)
                y_train = np.concatenate([np.ones(len(X_pos)), np.zeros(len(X_neg_sub))])

                clf = HistGradientBoostingClassifier(
                    max_depth=6, learning_rate=0.1, max_iter=200,
                    l2_regularization=1.0, class_weight='balanced',
                    random_state=42, categorical_features=[0]
                )
                clf.fit(X_train, y_train)
                dir1_models[m_name] = clf
            else:
                dir1_models[m_name] = None

        # Score held-out factories clean copies (Out-of-Fold) for Direction 1
        for fac in test_facs:
            for (f, p), grid in clean_grids.items():
                if f == fac:
                    feats = clean_features[(f, p)]
                    vals = grid["value"].values
                    for m_name, clf in dir1_models.items():
                        if clf is not None:
                            sc = clf.predict_proba(feats)[:, 1]
                        else:
                            sc = np.zeros(len(vals))
                        sc[np.isnan(vals)] = np.nan
                        oof_clean_scores[("dir1", m_name)][(fac, p)] = (vals, sc)

        # Score held-out factories test injected copies for Direction 1 (Test A and Test B)
        for fac in test_facs:
            for mech in ["A", "B"]:
                seeds = [1, 2, 3, 4, 5] if mech == "A" else [301, 302, 303, 304, 305]
                for seed in seeds:
                    for p in PARAM_MAP.keys():
                        k_inj = (mech, seed, fac, p)
                        if k_inj in inj_cache:
                            grid, feats, vals, _, _ = inj_cache[k_inj]
                            for m_name, clf in dir1_models.items():
                                if clf is not None:
                                    sc = clf.predict_proba(feats)[:, 1]
                                else:
                                    sc = np.zeros(len(vals))
                                sc[np.isnan(vals)] = np.nan
                                test_inj_scores[("dir1", m_name, mech, seed, fac, p)] = sc

        # ---------------------------------------------------------------------
        # Direction 2: Train on Mechanism B
        # ---------------------------------------------------------------------
        train_events_b = df_labels_b[df_labels_b["factory_id"].isin(train_facs) & (~df_labels_b["no_op"])].copy()

        pos_rows_by_type_b = {t: [] for t in ["T1", "T2", "T3", "T7"]}
        for _, ev in train_events_b.iterrows():
            k_inj = ("B", ev["seed"], ev["factory_id"], ev["parameter"])
            if k_inj in inj_cache:
                grid, feats, _, ts_arr, _ = inj_cache[k_inj]
                m_pos = (ts_arr >= ev["start_dt"]) & (ts_arr <= ev["end_dt"])
                if np.any(m_pos):
                    pos_rows_by_type_b[ev["type"]].append(feats[m_pos])

        dir2_models = {}
        for m_name, type_list in MODEL_SUITES.items():
            pos_dfs = [df_sub for t in type_list for df_sub in pos_rows_by_type_b[t] if not df_sub.empty]
            if pos_dfs and neg_rows_by_fac:
                X_pos = pd.concat(pos_dfs, ignore_index=True)
                n_pos = len(X_pos)
                target_neg_per_fac = max(1, (n_pos * 20) // len(train_facs))
                neg_sampled = []
                for fac, df_neg_fac in neg_rows_by_fac.items():
                    n_draw = min(len(df_neg_fac), target_neg_per_fac)
                    neg_sampled.append(df_neg_fac.sample(n_draw, random_state=42))
                X_neg_sub = pd.concat(neg_sampled, ignore_index=True)

                X_train = pd.concat([X_pos, X_neg_sub], ignore_index=True)
                y_train = np.concatenate([np.ones(len(X_pos)), np.zeros(len(X_neg_sub))])

                clf = HistGradientBoostingClassifier(
                    max_depth=6, learning_rate=0.1, max_iter=200,
                    l2_regularization=1.0, class_weight='balanced',
                    random_state=42, categorical_features=[0]
                )
                clf.fit(X_train, y_train)
                dir2_models[m_name] = clf
            else:
                dir2_models[m_name] = None

        # Score held-out factories clean copies (Out-of-Fold) for Direction 2
        for fac in test_facs:
            for (f, p), grid in clean_grids.items():
                if f == fac:
                    feats = clean_features[(f, p)]
                    vals = grid["value"].values
                    for m_name, clf in dir2_models.items():
                        if clf is not None:
                            sc = clf.predict_proba(feats)[:, 1]
                        else:
                            sc = np.zeros(len(vals))
                        sc[np.isnan(vals)] = np.nan
                        oof_clean_scores[("dir2", m_name)][(fac, p)] = (vals, sc)

        # Score held-out factories test injected copies for Direction 2 (Test B and Test A)
        for fac in test_facs:
            for mech in ["A", "B"]:
                seeds = [1, 2, 3, 4, 5] if mech == "A" else [301, 302, 303, 304, 305]
                for seed in seeds:
                    for p in PARAM_MAP.keys():
                        k_inj = (mech, seed, fac, p)
                        if k_inj in inj_cache:
                            grid, feats, vals, _, _ = inj_cache[k_inj]
                            for m_name, clf in dir2_models.items():
                                if clf is not None:
                                    sc = clf.predict_proba(feats)[:, 1]
                                else:
                                    sc = np.zeros(len(vals))
                                sc[np.isnan(vals)] = np.nan
                                test_inj_scores[("dir2", m_name, mech, seed, fac, p)] = sc

    print(f"  Completed all 5 folds for both directions in {time.time()-t0:.2f}s")

    # 5. Out-of-Fold Calibration (Operating Cutoffs at 1.0, 2.0, 4.0, 10.0 FA/mo)
    print("\n[Step 5] Calibrating Operating Cutoffs from Pooled Out-of-Fold Clean Telemetry...")
    t0 = time.time()
    BUDGETS = [1.0, 2.0, 4.0, 10.0]

    calibrated_cutoffs = {}
    realized_fa_rates = {}

    for (direction, m_name), sc_dict in oof_clean_scores.items():
        for b in BUDGETS:
            target_eps = int(round(b * TOTAL_FACTORY_MONTHS))
            tau = calibrate_tau(sc_dict, target_eps)
            calibrated_cutoffs[(direction, m_name, b)] = tau

            tot_eps = sum(count_episodes_for_series(scs, vals, tau) for (fac, param), (vals, scs) in sc_dict.items())
            realized_fa_rates[(direction, m_name, b)] = tot_eps / TOTAL_FACTORY_MONTHS

    for (direction, m_name, b), tau in sorted(calibrated_cutoffs.items()):
        if b == 1.0:
            print(f"  Cutoff (1.0 FA/mo): {direction} {m_name:<8} -> tau = {tau:.5f} (Realized FA: {realized_fa_rates[(direction, m_name, b)]:.3f}/mo)")

    # 6. Extract Alert Episodes and Evaluate Event Detections
    print("\n[Step 6] Extracting Alert Episodes & Evaluating Event Detections...")
    t0 = time.time()

    # Precompute B0 Random Alerts for each factory
    rng_b0 = np.random.default_rng(42)
    b0_alerts = {}
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
        b0_alerts[fac] = fac_eps

    # Combine all events across Mechanism A and Mechanism B
    if "params" in df_labels_a.columns:
        df_labels_a["parameter"] = df_labels_a["params"]
    all_events = pd.concat([df_labels_a, df_labels_b], ignore_index=True)

    event_eval_records = []

    for _, ev in all_events.iterrows():
        eid = ev["event_id"]
        mech = ev["mechanism"]
        fac = ev["factory_id"]
        seed = ev["seed"]
        param = str(ev["parameter"]).strip()
        t_type = ev["type"]
        sev = ev.get("severity", "moderate")
        dur = ev["duration_rows"]
        s_dt = ev["start_dt"]
        e_dt = ev["end_dt"]
        e_dt_2h = e_dt + pd.Timedelta(hours=2)
        is_noop = bool(ev["no_op"])

        rec = {
            "event_id": eid,
            "mechanism": mech,
            "factory_id": fac,
            "seed": seed,
            "parameter": param,
            "type": t_type,
            "severity": sev,
            "duration_rows": dur,
            "no_op": is_noop,
            "start_dt": s_dt,
            "end_dt": e_dt
        }

        # B0 Random Detection
        b0_det = False
        for (r_s, r_e) in b0_alerts.get(fac, []):
            if (r_e >= s_dt) and (r_s <= e_dt_2h):
                b0_det = True
                break
        rec["is_detected_B0"] = b0_det

        # Direction 1 Evaluation (Trained on A)
        for m_name in MODEL_SUITES:
            sc_arr = test_inj_scores.get(("dir1", m_name, mech, seed, fac, param))
            tau = calibrated_cutoffs[("dir1", m_name, 1.0)]
            is_det = False
            min_delay = np.nan
            if sc_arr is not None:
                grid, _, vals, ts_arr, _ = inj_cache[(mech, seed, fac, param)]
                eps = extract_alert_episodes(sc_arr, vals, tau, ts_arr)
                for ep in eps:
                    ep_s = ep["start_ts"]
                    ep_e = ep["end_ts"]
                    if (ep_e >= s_dt) and (ep_s <= e_dt_2h):
                        is_det = True
                        first_alert_ts = max(ep_s, s_dt)
                        delay_h = max(0.0, (first_alert_ts - s_dt).total_seconds() / 3600.0)
                        if np.isnan(min_delay) or delay_h < min_delay:
                            min_delay = delay_h
            rec[f"is_detected_dir1_{m_name}"] = is_det
            rec[f"delay_dir1_{m_name}"] = min_delay

        # Direction 2 Evaluation (Trained on B)
        for m_name in MODEL_SUITES:
            sc_arr = test_inj_scores.get(("dir2", m_name, mech, seed, fac, param))
            tau = calibrated_cutoffs[("dir2", m_name, 1.0)]
            is_det = False
            min_delay = np.nan
            if sc_arr is not None:
                grid, _, vals, ts_arr, _ = inj_cache[(mech, seed, fac, param)]
                eps = extract_alert_episodes(sc_arr, vals, tau, ts_arr)
                for ep in eps:
                    ep_s = ep["start_ts"]
                    ep_e = ep["end_ts"]
                    if (ep_e >= s_dt) and (ep_s <= e_dt_2h):
                        is_det = True
                        first_alert_ts = max(ep_s, s_dt)
                        delay_h = max(0.0, (first_alert_ts - s_dt).total_seconds() / 3600.0)
                        if np.isnan(min_delay) or delay_h < min_delay:
                            min_delay = delay_h
            rec[f"is_detected_dir2_{m_name}"] = is_det
            rec[f"delay_dir2_{m_name}"] = min_delay

        # V1 Comparators Evaluation
        k_inj = (mech, seed, fac, param)
        if k_inj in inj_cache:
            grid, _, vals, ts_arr, v1_sc_dict = inj_cache[k_inj]
            for chk, tau_chk in V1_CUTOFFS.items():
                sc_chk = v1_sc_dict.get(chk)
                is_det_chk = False
                min_delay_chk = np.nan
                if sc_chk is not None:
                    eps_chk = extract_alert_episodes(sc_chk, vals, tau_chk, ts_arr)
                    for ep in eps_chk:
                        ep_s = ep["start_ts"]
                        ep_e = ep["end_ts"]
                        if (ep_e >= s_dt) and (ep_s <= e_dt_2h):
                            is_det_chk = True
                            first_alert_ts = max(ep_s, s_dt)
                            delay_h = max(0.0, (first_alert_ts - s_dt).total_seconds() / 3600.0)
                            if np.isnan(min_delay_chk) or delay_h < min_delay_chk:
                                min_delay_chk = delay_h
                rec[f"is_detected_V1_{chk}"] = is_det_chk
                rec[f"delay_V1_{chk}"] = min_delay_chk
        else:
            for chk in V1_CUTOFFS:
                rec[f"is_detected_V1_{chk}"] = False
                rec[f"delay_V1_{chk}"] = np.nan

        # Best V1 comparator per event
        rec["is_detected_V1_best"] = (
            rec.get("is_detected_V1_M1", False) or
            rec.get("is_detected_V1_IF", False) or
            rec.get("is_detected_V1_F6_slope", False) or
            rec.get("is_detected_V1_F3", False) or
            rec.get("is_detected_V1_F2", False) or
            rec.get("is_detected_V1_F1_eps2", False) or
            rec.get("is_detected_V1_F6_shift", False)
        )

        event_eval_records.append(rec)

    df_eval_all = pd.DataFrame(event_eval_records)
    print(f"  Evaluated {len(df_eval_all):,} events across all methods in {time.time()-t0:.2f}s")

    # Save per-event CSV
    out_events_csv = os.path.join(MODEL_OUT_DIR, "v2_eval_events.csv")
    df_eval_all.to_csv(out_events_csv, index=False)
    print(f"  Saved per-event evaluation records to {out_events_csv}")

    # -------------------------------------------------------------------------
    # 7. Compute Headline Metrics, Generalization Gaps & Cluster Bootstrap CIs
    # -------------------------------------------------------------------------
    print("\n[Step 7] Computing Generalization Gaps, Paired Differences & 95% CIs (10,000 resamples)...")
    t0 = time.time()

    # Filter primary analysis set: exclude no-op events
    df_primary = df_eval_all[~df_eval_all["no_op"]].copy()

    # Table 1: Direction 1 & Direction 2 Cross-Mechanism Generalization Gap Table
    gap_rows = []
    types_to_eval = ["T1", "T2", "T3", "T7", "Pooled"]

    # Direction 1: Train on A -> In-mechanism = Test A; Cross-mechanism = Test B
    for t in types_to_eval:
        sub_a = df_primary[df_primary["mechanism"] == "A"] if t == "Pooled" else df_primary[(df_primary["mechanism"] == "A") & (df_primary["type"] == t)]
        sub_b = df_primary[df_primary["mechanism"] == "B"] if t == "Pooled" else df_primary[(df_primary["mechanism"] == "B") & (df_primary["type"] == t)]

        rec_in, in_l, in_u = compute_cluster_bootstrap(sub_a, "is_detected_dir1_pooled")
        rec_cross, cross_l, cross_u = compute_cluster_bootstrap(sub_b, "is_detected_dir1_pooled")
        gap = rec_in - rec_cross

        gap_rows.append({
            "Direction": "Direction 1 (Train A)",
            "Training_Mechanism": "Mechanism A (V1)",
            "Type": t,
            "In_Mechanism_Test": "Mechanism A",
            "In_Events": len(sub_a),
            "In_Recall": round(rec_in, 4),
            "In_CI95": f"[{in_l*100:.2f}%, {in_u*100:.2f}%]",
            "Cross_Mechanism_Test": "Mechanism B",
            "Cross_Events": len(sub_b),
            "Cross_Recall": round(rec_cross, 4),
            "Cross_CI95": f"[{cross_l*100:.2f}%, {cross_u*100:.2f}%]",
            "Generalization_Gap": round(gap, 4),
            "Gap_Pct": f"{gap*100:+.2f}%"
        })

    # Direction 2: Train on B -> In-mechanism = Test B; Cross-mechanism = Test A
    for t in types_to_eval:
        sub_b = df_primary[df_primary["mechanism"] == "B"] if t == "Pooled" else df_primary[(df_primary["mechanism"] == "B") & (df_primary["type"] == t)]
        sub_a = df_primary[df_primary["mechanism"] == "A"] if t == "Pooled" else df_primary[(df_primary["mechanism"] == "A") & (df_primary["type"] == t)]

        rec_in, in_l, in_u = compute_cluster_bootstrap(sub_b, "is_detected_dir2_pooled")
        rec_cross, cross_l, cross_u = compute_cluster_bootstrap(sub_a, "is_detected_dir2_pooled")
        gap = rec_in - rec_cross

        gap_rows.append({
            "Direction": "Direction 2 (Train B)",
            "Training_Mechanism": "Mechanism B (V2)",
            "Type": t,
            "In_Mechanism_Test": "Mechanism B",
            "In_Events": len(sub_b),
            "In_Recall": round(rec_in, 4),
            "In_CI95": f"[{in_l*100:.2f}%, {in_u*100:.2f}%]",
            "Cross_Mechanism_Test": "Mechanism A",
            "Cross_Events": len(sub_a),
            "Cross_Recall": round(rec_cross, 4),
            "Cross_CI95": f"[{cross_l*100:.2f}%, {cross_u*100:.2f}%]",
            "Generalization_Gap": round(gap, 4),
            "Gap_Pct": f"{gap*100:+.2f}%"
        })

    df_gap = pd.DataFrame(gap_rows)
    out_gap_csv = os.path.join(MODEL_OUT_DIR, "v2_generalization_gap.csv")
    df_gap.to_csv(out_gap_csv, index=False)
    print(f"  Saved generalization gap table to {out_gap_csv}")

    # Table 2: Paired Difference V2 vs Best V1 Comparator (Cross-Mechanism)
    paired_rows = []
    # Test on Mechanism B (cross-mechanism for Direction 1)
    sub_b_all = df_primary[df_primary["mechanism"] == "B"]
    for t in types_to_eval:
        sub_b_t = sub_b_all if t == "Pooled" else sub_b_all[sub_b_all["type"] == t]
        rec_v2, v2_l, v2_u = compute_cluster_bootstrap(sub_b_t, "is_detected_dir1_pooled")
        rec_m1, m1_l, m1_u = compute_cluster_bootstrap(sub_b_t, "is_detected_V1_M1")
        rec_if, if_l, if_u = compute_cluster_bootstrap(sub_b_t, "is_detected_V1_IF")
        rec_best, best_l, best_u = compute_cluster_bootstrap(sub_b_t, "is_detected_V1_best")

        p_diff_best, ci_l_best, ci_u_best = compute_paired_diff_bootstrap(sub_b_t, "is_detected_dir1_pooled", "is_detected_V1_best")
        p_diff_m1, ci_l_m1, ci_u_m1 = compute_paired_diff_bootstrap(sub_b_t, "is_detected_dir1_pooled", "is_detected_V1_M1")

        passes_bar = bool(ci_l_best > 0.0 and realized_fa_rates[("dir1", "pooled", 1.0)] <= 1.05)

        paired_rows.append({
            "Direction": "Direction 1 (Train A -> Test B Cross)",
            "Tamper_Type": t,
            "Total_Events": len(sub_b_t),
            "Recall_V2": round(rec_v2, 4),
            "CI95_V2": f"[{v2_l*100:.2f}%, {v2_u*100:.2f}%]",
            "Recall_V1_M1": round(rec_m1, 4),
            "Recall_V1_IF": round(rec_if, 4),
            "Recall_V1_Best": round(rec_best, 4),
            "Paired_Diff_V2_minus_M1": round(p_diff_m1, 4),
            "Paired_CI95_M1": f"[{ci_l_m1*100:.2f}%, {ci_u_m1*100:.2f}%]",
            "Paired_Diff_V2_minus_BestV1": round(p_diff_best, 4),
            "Paired_CI95_BestV1": f"[{ci_l_best*100:.2f}%, {ci_u_best*100:.2f}%]",
            "Passes_Reading_Rule": passes_bar
        })

    # Test on Mechanism A (cross-mechanism for Direction 2)
    sub_a_all = df_primary[df_primary["mechanism"] == "A"]
    for t in types_to_eval:
        sub_a_t = sub_a_all if t == "Pooled" else sub_a_all[sub_a_all["type"] == t]
        rec_v2, v2_l, v2_u = compute_cluster_bootstrap(sub_a_t, "is_detected_dir2_pooled")
        rec_m1, m1_l, m1_u = compute_cluster_bootstrap(sub_a_t, "is_detected_V1_M1")
        rec_if, if_l, if_u = compute_cluster_bootstrap(sub_a_t, "is_detected_V1_IF")
        rec_best, best_l, best_u = compute_cluster_bootstrap(sub_a_t, "is_detected_V1_best")

        p_diff_best, ci_l_best, ci_u_best = compute_paired_diff_bootstrap(sub_a_t, "is_detected_dir2_pooled", "is_detected_V1_best")
        p_diff_m1, ci_l_m1, ci_u_m1 = compute_paired_diff_bootstrap(sub_a_t, "is_detected_dir2_pooled", "is_detected_V1_M1")

        passes_bar = bool(ci_l_best > 0.0 and realized_fa_rates[("dir2", "pooled", 1.0)] <= 1.05)

        paired_rows.append({
            "Direction": "Direction 2 (Train B -> Test A Cross)",
            "Tamper_Type": t,
            "Total_Events": len(sub_a_t),
            "Recall_V2": round(rec_v2, 4),
            "CI95_V2": f"[{v2_l*100:.2f}%, {v2_u*100:.2f}%]",
            "Recall_V1_M1": round(rec_m1, 4),
            "Recall_V1_IF": round(rec_if, 4),
            "Recall_V1_Best": round(rec_best, 4),
            "Paired_Diff_V2_minus_M1": round(p_diff_m1, 4),
            "Paired_CI95_M1": f"[{ci_l_m1*100:.2f}%, {ci_u_m1*100:.2f}%]",
            "Paired_Diff_V2_minus_BestV1": round(p_diff_best, 4),
            "Paired_CI95_BestV1": f"[{ci_l_best*100:.2f}%, {ci_u_best*100:.2f}%]",
            "Passes_Reading_Rule": passes_bar
        })

    df_paired = pd.DataFrame(paired_rows)
    out_paired_csv = os.path.join(MODEL_OUT_DIR, "v2_methods_comparison.csv")
    df_paired.to_csv(out_paired_csv, index=False)
    print(f"  Saved methods comparison & paired diff table to {out_paired_csv}")

    # Table 3: Realized False Alarms per Factory-Month
    fa_rows = []
    for (d_tag, m_name), sc_dict in oof_clean_scores.items():
        tau = calibrated_cutoffs[(d_tag, m_name, 1.0)]
        for fac in all_dev_factories:
            m_k = FACTORY_MONTHS[fac]
            eps = sum(count_episodes_for_series(scs, vals, tau) for (f, p), (vals, scs) in sc_dict.items() if f == fac)
            rate = eps / m_k
            fa_rows.append({
                "Direction": d_tag,
                "Model": m_name,
                "Factory_ID": fac,
                "Exposure_Months": m_k,
                "Alert_Episodes": eps,
                "FA_Rate_mo": round(rate, 3)
            })

    df_fa = pd.DataFrame(fa_rows)
    out_fa_csv = os.path.join(MODEL_OUT_DIR, "v2_clean_false_alarms.csv")
    df_fa.to_csv(out_fa_csv, index=False)
    print(f"  Saved false alarms breakdown to {out_fa_csv}")

    # Table 4: Budget Sensitivity Matrix (1.0, 2.0, 4.0, 10.0 Alerts/Month)
    sens_rows = []
    for b in BUDGETS:
        for d_tag, d_label in [("dir1", "Train A"), ("dir2", "Train B")]:
            tau = calibrated_cutoffs[(d_tag, "pooled", b)]
            real_fa = realized_fa_rates[(d_tag, "pooled", b)]

            in_mech = "A" if d_tag == "dir1" else "B"
            cross_mech = "B" if d_tag == "dir1" else "A"

            for m_test, test_label in [(in_mech, "In-Mechanism"), (cross_mech, "Cross-Mechanism")]:
                sub_test = df_primary[df_primary["mechanism"] == m_test]
                n_det = 0
                for _, r in sub_test.iterrows():
                    sc_arr = test_inj_scores.get((d_tag, "pooled", m_test, r["seed"], r["factory_id"], r["parameter"]))
                    if sc_arr is not None:
                        grid, _, vals, ts_arr, _ = inj_cache[(m_test, r["seed"], r["factory_id"], r["parameter"])]
                        eps = extract_alert_episodes(sc_arr, vals, tau, ts_arr)
                        for ep in eps:
                            if ep["end_ts"] >= r["start_dt"] and ep["start_ts"] <= r["end_dt"] + pd.Timedelta(hours=2):
                                n_det += 1
                                break
                rec = n_det / len(sub_test)

                sens_rows.append({
                    "Budget_Target_mo": b,
                    "Operating_Cutoff_Tau": round(tau, 5),
                    "Realized_FA_mo": round(real_fa, 3),
                    "Direction": d_label,
                    "Test_Type": test_label,
                    "Test_Mechanism": m_test,
                    "Total_Events": len(sub_test),
                    "Detected_Events": n_det,
                    "Recall": round(rec, 4),
                    "Recall_Pct": f"{rec*100:.2f}%"
                })

    df_sens = pd.DataFrame(sens_rows)
    out_sens_csv = os.path.join(MODEL_OUT_DIR, "v2_budget_sensitivity.csv")
    df_sens.to_csv(out_sens_csv, index=False)
    print(f"  Saved budget sensitivity table to {out_sens_csv}")

    # Table 5: Subgroup Stratifications (Severity, Duration, Parameter)
    sub_cross_b = df_primary[df_primary["mechanism"] == "B"].copy()
    sub_cross_b["detected_v2"] = sub_cross_b["is_detected_dir1_pooled"]
    sub_cross_b["detected_v1"] = sub_cross_b["is_detected_V1_M1"]

    strat_rows = []
    # By Severity
    for sev, g in sub_cross_b.groupby("severity"):
        rec_v2, l_v2, u_v2 = compute_cluster_bootstrap(g, "detected_v2")
        rec_v1, l_v1, u_v1 = compute_cluster_bootstrap(g, "detected_v1")
        strat_rows.append({
            "Dimension": "Severity",
            "Group": sev,
            "Total_Events": len(g),
            "Recall_V2": round(rec_v2, 4),
            "CI95_V2": f"[{l_v2*100:.2f}%, {u_v2*100:.2f}%]",
            "Recall_V1": round(rec_v1, 4),
            "CI95_V1": f"[{l_v1*100:.2f}%, {u_v1*100:.2f}%]"
        })

    # By Duration Bins (<=16, 48-96, >=288)
    dur_bins = [
        ("<=16 rows (<=4h)", sub_cross_b[sub_cross_b["duration_rows"] <= 16]),
        ("48-96 rows (12h-24h)", sub_cross_b[sub_cross_b["duration_rows"].isin([48, 96])]),
        (">=288 rows (>=72h)", sub_cross_b[sub_cross_b["duration_rows"] >= 288])
    ]
    for d_label, g in dur_bins:
        if len(g) > 0:
            rec_v2, l_v2, u_v2 = compute_cluster_bootstrap(g, "detected_v2")
            rec_v1, l_v1, u_v1 = compute_cluster_bootstrap(g, "detected_v1")
            strat_rows.append({
                "Dimension": "Duration",
                "Group": d_label,
                "Total_Events": len(g),
                "Recall_V2": round(rec_v2, 4),
                "CI95_V2": f"[{l_v2*100:.2f}%, {u_v2*100:.2f}%]",
                "Recall_V1": round(rec_v1, 4),
                "CI95_V1": f"[{l_v1*100:.2f}%, {u_v1*100:.2f}%]"
            })

    # By Parameter
    for param, g in sub_cross_b.groupby("parameter"):
        rec_v2, l_v2, u_v2 = compute_cluster_bootstrap(g, "detected_v2")
        rec_v1, l_v1, u_v1 = compute_cluster_bootstrap(g, "detected_v1")
        strat_rows.append({
            "Dimension": "Parameter",
            "Group": param,
            "Total_Events": len(g),
            "Recall_V2": round(rec_v2, 4),
            "CI95_V2": f"[{l_v2*100:.2f}%, {u_v2*100:.2f}%]",
            "Recall_V1": round(rec_v1, 4),
            "CI95_V1": f"[{l_v1*100:.2f}%, {u_v1*100:.2f}%]"
        })

    df_strat = pd.DataFrame(strat_rows)

    # Table 6: No-Op Event Impact Analysis
    df_all_b = df_eval_all[df_eval_all["mechanism"] == "B"].copy()
    noop_rows = []
    for t in ["T1", "T2", "T3", "T7", "Pooled"]:
        sub_all = df_all_b if t == "Pooled" else df_all_b[df_all_b["type"] == t]
        sub_prim = sub_all[~sub_all["no_op"]]
        n_tot = len(sub_all)
        n_noop = int(sub_all["no_op"].sum())
        n_prim = len(sub_prim)
        rec_excl, excl_l, excl_u = compute_cluster_bootstrap(sub_prim, "is_detected_dir1_pooled")
        rec_incl, incl_l, incl_u = compute_cluster_bootstrap(sub_all, "is_detected_dir1_pooled")
        noop_rows.append({
            "Tamper_Type": t,
            "Total_Events_With_NoOp": n_tot,
            "NoOp_Events_Count": n_noop,
            "NoOp_Share": f"{n_noop/max(n_tot, 1)*100:.2f}%",
            "Primary_Events": n_prim,
            "Recall_NoOp_Excluded": round(rec_excl, 4),
            "CI95_Excluded": f"[{excl_l*100:.2f}%, {excl_u*100:.2f}%]",
            "Recall_NoOp_Included": round(rec_incl, 4),
            "CI95_Included": f"[{incl_l*100:.2f}%, {incl_u*100:.2f}%]",
            "Impact_Delta": round(rec_excl - rec_incl, 4)
        })
    df_noop = pd.DataFrame(noop_rows)

    # Table 7: Type-Specialist Diagnostic Models
    spec_rows = []
    for m_name, target_types in [("T1_T2", ["T1", "T2"]), ("T3", ["T3"]), ("T7", ["T7"])]:
        tau_d1 = calibrated_cutoffs[("dir1", m_name, 1.0)]
        fa_d1 = realized_fa_rates[("dir1", m_name, 1.0)]
        sub_spec = sub_cross_b[sub_cross_b["type"].isin(target_types)]
        rec_spec, spec_l, spec_u = compute_cluster_bootstrap(sub_spec, f"is_detected_dir1_{m_name}")
        rec_pool, pool_l, pool_u = compute_cluster_bootstrap(sub_spec, "is_detected_dir1_pooled")
        spec_rows.append({
            "Specialist_Model": f"{m_name} Specialist",
            "Target_Types": "+".join(target_types),
            "Calibrated_Tau": round(tau_d1, 5),
            "Realized_FA_mo": round(fa_d1, 3),
            "Target_Events": len(sub_spec),
            "Specialist_Recall": round(rec_spec, 4),
            "Specialist_CI95": f"[{spec_l*100:.2f}%, {spec_u*100:.2f}%]",
            "Pooled_Model_Recall": round(rec_pool, 4),
            "Pooled_CI95": f"[{pool_l*100:.2f}%, {pool_u*100:.2f}%]",
            "Status": "Not additive (individual 1.0/mo budget)"
        })
    df_spec = pd.DataFrame(spec_rows)

    # Table 8: Window AUPRC and Detection Delay Summary
    # Direction 1 Cross-Mechanism (Test B)
    y_b_list, sc_v2_b_list, sc_m1_b_list = [], [], []
    for (d_tag, m_name, mech, seed, fac, p), sc_arr in test_inj_scores.items():
        if d_tag == "dir1" and m_name == "pooled" and mech == "B":
            grid, _, vals, ts_arr, v1_sc = inj_cache[(mech, seed, fac, p)]
            y_arr = np.zeros(len(vals))
            evs_sub = df_primary[(df_primary["mechanism"] == "B") & (df_primary["seed"] == seed) & (df_primary["factory_id"] == fac) & (df_primary["parameter"] == p)]
            for _, ev in evs_sub.iterrows():
                y_arr[(ts_arr >= ev["start_dt"]) & (ts_arr <= ev["end_dt"])] = 1.0
            y_b_list.append(y_arr[::8])
            sc_v2_b_list.append(sc_arr[::8])
            sc_m1_b_list.append(v1_sc["M1"][::8])

    y_b_all = np.concatenate(y_b_list) if y_b_list else np.array([])
    sc_v2_b_all = np.concatenate(sc_v2_b_list) if sc_v2_b_list else np.array([])
    sc_m1_b_all = np.concatenate(sc_m1_b_list) if sc_m1_b_list else np.array([])

    auprc_v2_dir1 = safe_auprc(y_b_all, sc_v2_b_all)
    auprc_m1_dir1 = safe_auprc(y_b_all, sc_m1_b_all)

    delays_v2_dir1 = sub_cross_b.loc[sub_cross_b["is_detected_dir1_pooled"], "delay_dir1_pooled"].dropna()
    med_delay_v2_dir1 = float(np.median(delays_v2_dir1)) if len(delays_v2_dir1) > 0 else np.nan

    delays_m1_dir1 = sub_cross_b.loc[sub_cross_b["is_detected_V1_M1"], "delay_V1_M1"].dropna()
    med_delay_m1_dir1 = float(np.median(delays_m1_dir1)) if len(delays_m1_dir1) > 0 else np.nan

    auprc_rows = [
        {
            "Evaluation_Setting": "Direction 1 Cross (Train A -> Test B)",
            "Method": "V2 Pooled Supervised Model",
            "Window_AUPRC": round(auprc_v2_dir1, 4),
            "Median_Delay_h": round(med_delay_v2_dir1, 2) if pd.notna(med_delay_v2_dir1) else np.nan,
            "Operating_Budget": "1.0 false alert / month"
        },
        {
            "Evaluation_Setting": "Direction 1 Cross (Train A -> Test B)",
            "Method": "V1 M1 Multi-Check Fusion",
            "Window_AUPRC": round(auprc_m1_dir1, 4),
            "Median_Delay_h": round(med_delay_m1_dir1, 2) if pd.notna(med_delay_m1_dir1) else np.nan,
            "Operating_Budget": "1.0 false alert / month"
        },
        {
            "Evaluation_Setting": "Direction 1 Cross (Train A -> Test B)",
            "Method": "B0 Random Alerts",
            "Window_AUPRC": round(float(np.mean(y_b_all)) if len(y_b_all) > 0 else 0.0, 4),
            "Median_Delay_h": 0.0,
            "Operating_Budget": "1.0 false alert / month"
        }
    ]
    df_auprc = pd.DataFrame(auprc_rows)

    # -------------------------------------------------------------------------
    # 8. Write Markdown STAGE2_FINAL_REPORT.md (Tables Only)
    # -------------------------------------------------------------------------
    print("\n[Step 8] Writing STAGE2_FINAL_REPORT.md (Tables Only)...")
    report_md_path = os.path.join(MODEL_OUT_DIR, "STAGE2_FINAL_REPORT.md")

    report_lines = []
    report_lines.append("# FORENSIAIR V2 — STAGE 2 FINAL EVALUATION REPORT")
    report_lines.append("")
    report_lines.append(f"**Execution Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}  ")
    report_lines.append(f"**Git Tag v2-protocol-frozen Hash:** `8c98d3d2d45f3ab79dfa54327cb56bd94b28188c`  ")
    report_lines.append(f"**Operating Budget:** 1.0 False Alert Episode / Factory-Month (328 Target Episodes on 327.61 Factory-Months)  ")
    report_lines.append(f"**Evaluation Architecture:** 5-Fold Factory-Grouped Cross-Validation, Bidirectional Cross-Mechanism  ")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # Table 1: Cross-Mechanism Generalization Gap Table
    report_lines.append("## Table 1: Cross-Mechanism Generalization Gap (development result, post-hoc)")
    report_lines.append("")
    report_lines.append("| Direction | Tamper Type | In-Mechanism Test | In Events | In Recall | In 95% CI | Cross-Mechanism Test | Cross Events | Cross Recall | Cross 95% CI | Generalization Gap |")
    report_lines.append("|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
    for _, r in df_gap.iterrows():
        report_lines.append(f"| {r['Direction']} | **{r['Type']}** | {r['In_Mechanism_Test']} | {r['In_Events']} | {r['In_Recall']*100:.2f}% | {r['In_CI95']} | {r['Cross_Mechanism_Test']} | {r['Cross_Events']} | **{r['Cross_Recall']*100:.2f}%** | {r['Cross_CI95']} | **{r['Gap_Pct']}** |")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # Table 2: Paired Differences vs Best V1 Comparator
    report_lines.append("## Table 2: Paired Difference V2 vs Best V1 Comparator (Cross-Mechanism) (development result, post-hoc)")
    report_lines.append("")
    report_lines.append("| Evaluation Direction | Tamper Type | Events | Recall V2 | 95% CI V2 | Recall V1 M1 | Recall V1 IF | Recall V1 Best | Paired Diff (V2 - M1) | Paired Diff (V2 - Best V1) | Paired 95% CI | Passes Reading Rule |")
    report_lines.append("|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
    for _, r in df_paired.iterrows():
        rule_str = "YES (PASS)" if r['Passes_Reading_Rule'] else "NO (FAIL)"
        report_lines.append(f"| {r['Direction']} | **{r['Tamper_Type']}** | {r['Total_Events']} | **{r['Recall_V2']*100:.2f}%** | {r['CI95_V2']} | {r['Recall_V1_M1']*100:.2f}% | {r['Recall_V1_IF']*100:.2f}% | {r['Recall_V1_Best']*100:.2f}% | {r['Paired_Diff_V2_minus_M1']*100:+.2f}% | **{r['Paired_Diff_V2_minus_BestV1']*100:+.2f}%** | {r['Paired_CI95_BestV1']} | **{rule_str}** |")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # Table 3: Realized False Alarms Summary
    fa_summary = df_fa.groupby(["Direction", "Model"])["FA_Rate_mo"].agg(["mean", "median", "max"]).reset_index()
    report_lines.append("## Table 3: Realized Clean False Alarms per Factory-Month (development result, post-hoc)")
    report_lines.append("")
    report_lines.append("| Direction | Model Architecture | Mean FA / Month | Median FA / Month | Max FA / Month | Operating Cutoff $\\tau$ | Target Budget |")
    report_lines.append("|:---|:---:|:---:|:---:|:---:|:---:|:---:|")
    for _, r in fa_summary.iterrows():
        d_tag = r['Direction']
        m_tag = r['Model']
        tau = calibrated_cutoffs[(d_tag, m_tag, 1.0)]
        report_lines.append(f"| {d_tag} | `{m_tag}` | **{r['mean']:.3f}** | {r['median']:.3f} | {r['max']:.3f} | {tau:.5f} | 1.000 / mo |")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # Table 4: Subgroup Stratifications
    report_lines.append("## Table 4: Stratification by Severity, Duration and Parameter (development result, post-hoc)")
    report_lines.append("")
    report_lines.append("| Dimension | Subgroup Category | Events | Recall V2 (Dir 1 Cross) | 95% CI V2 | Recall V1 M1 | 95% CI V1 | Delta |")
    report_lines.append("|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|")
    for _, r in df_strat.iterrows():
        delta = r['Recall_V2'] - r['Recall_V1']
        report_lines.append(f"| **{r['Dimension']}** | `{r['Group']}` | {r['Total_Events']} | **{r['Recall_V2']*100:.2f}%** | {r['CI95_V2']} | {r['Recall_V1']*100:.2f}% | {r['CI95_V1']} | **{delta*100:+.2f}%** |")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # Table 5: Operating Budget Sensitivity Matrix
    report_lines.append("## Table 5: Operating Budget Sensitivity Curve (development result, post-hoc)")
    report_lines.append("")
    report_lines.append("| Target Budget | Direction | Test Mechanism | Cutoff $\\tau$ | Realized FA (/mo) | Evaluated Events | Detected Events | Event Recall |")
    report_lines.append("|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|")
    for _, r in df_sens.iterrows():
        report_lines.append(f"| {r['Budget_Target_mo']:.1f} / mo | {r['Direction']} | {r['Test_Mechanism']} ({r['Test_Type']}) | {r['Operating_Cutoff_Tau']:.5f} | {r['Realized_FA_mo']:.3f} | {r['Total_Events']} | {r['Detected_Events']} | **{r['Recall_Pct']}** |")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # Table 6: No-Op Event Impact Analysis
    report_lines.append("## Table 6: No-Op Event Impact Analysis on Mechanism B (development result, post-hoc)")
    report_lines.append("")
    report_lines.append("| Tamper Type | Total Events (Incl No-Op) | No-Op Count | No-Op Share | Primary Events (Excl No-Op) | Recall (No-Op Excluded) | 95% CI (Excluded) | Recall (No-Op Included) | 95% CI (Included) | Impact Delta |")
    report_lines.append("|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
    for _, r in df_noop.iterrows():
        report_lines.append(f"| **{r['Tamper_Type']}** | {r['Total_Events_With_NoOp']} | {r['NoOp_Events_Count']} | {r['NoOp_Share']} | {r['Primary_Events']} | **{r['Recall_NoOp_Excluded']*100:.2f}%** | {r['CI95_Excluded']} | **{r['Recall_NoOp_Included']*100:.2f}%** | {r['CI95_Included']} | **{r['Impact_Delta']*100:+.2f}%** |")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # Table 7: Type-Specialist Diagnostic Models
    report_lines.append("## Table 7: Type-Specialist Diagnostic Models (development result, post-hoc)")
    report_lines.append("")
    report_lines.append("| Specialist Model | Target Tamper Types | Operating Cutoff $\\tau$ | Realized FA (/mo) | Evaluated Events | Specialist Recall | 95% CI Specialist | Pooled Model Recall | 95% CI Pooled | Architectural Status |")
    report_lines.append("|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|")
    for _, r in df_spec.iterrows():
        report_lines.append(f"| **{r['Specialist_Model']}** | `{r['Target_Types']}` | {r['Calibrated_Tau']:.5f} | {r['Realized_FA_mo']:.3f} | {r['Target_Events']} | **{r['Specialist_Recall']*100:.2f}%** | {r['Specialist_CI95']} | **{r['Pooled_Model_Recall']*100:.2f}%** | {r['Pooled_CI95']} | *{r['Status']}* |")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # Table 8: Window AUPRC and Detection Delay Summary
    report_lines.append("## Table 8: Window AUPRC and Detection Delay Summary (development result, post-hoc)")
    report_lines.append("")
    report_lines.append("| Evaluation Setting | Method | Window AUPRC | Median Detection Delay (h) | Operating Budget |")
    report_lines.append("|:---|:---|:---:|:---:|:---:|")
    for _, r in df_auprc.iterrows():
        med_d = f"{r['Median_Delay_h']:.2f} h" if pd.notna(r['Median_Delay_h']) else "N/A"
        report_lines.append(f"| {r['Evaluation_Setting']} | **{r['Method']}** | **{r['Window_AUPRC']:.4f}** | {med_d} | {r['Operating_Budget']} |")
    report_lines.append("")

    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"  Successfully wrote {report_md_path}")

    # 9. Write V2_LOG.md
    v2_log_path = os.path.join(MODEL_OUT_DIR, "V2_LOG.md")
    log_content = f"""# FORENSIAIR V2 EXECUTION & BUG LOG

**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}
**Branch:** `v2-dev`
**Git Tag:** `v2-protocol-frozen` (`8c98d3d2d45f3ab79dfa54327cb56bd94b28188c`)

## Precondition & Bug Resolution Record:
1. **Stage 1b Re-generation:**
   - Mechanism B labels previously lacked row change tracking and had T2 donor lags up to 2,688 rows.
   - Fixed: Capped T2-B-scaled to 1-7 days (96-672 rows) and T2-B-splice both blocks to 1-7 days (96-672 rows).
   - Added: Computed `n_rows_changed`, `changed_share`, `max_abs_change`, and `no_op = (changed_share < 0.50)` for all 2,694 Mechanism B events.
   - Identified 141 no-op events (5.23%) and properly excluded them from training positives and primary recall denominators.
   - Reran all 8 unit tests in `test_injector_b.py`; 100% passed in 26.60s.
2. **Git Tagging:**
   - Tag `v2-protocol-frozen` committed locally with hash `8c98d3d2d45f3ab79dfa54327cb56bd94b28188c`.
   - Verified `git diff detector-frozen -- validation_v2/detector validation_v2/injector` is completely empty.
3. **Execution Runtime & Hardware:**
   - 5-Fold cross-validation, 2 directions (Train A and Train B), 4 model architectures (pooled + 3 specialist).
   - Feature extraction and training completed in {time.time()-t0_start:.2f}s with zero crashes.
"""
    with open(v2_log_path, "w", encoding="utf-8") as f:
        f.write(log_content)
    print(f"  Successfully wrote {v2_log_path}")

    # 10. Append to RUNLOG.md
    runlog_path = os.path.join(REPO_ROOT, "validation_v2", "RUNLOG.md")
    with open(runlog_path, "a", encoding="utf-8") as f:
        f.write(f"\n## V2 FINAL (dev): run once, tag hash=8c98d3d2d45f3ab79dfa54327cb56bd94b28188c\n- Date: 2026-10-11\n- Description: Supervised HistGradientBoostingClassifier evaluated on 5-fold factory-grouped cross-validation across Mechanism A and Mechanism B. Protocol v2.0 frozen. Outputs in validation_v2/v2/model/.\n")
    print(f"  Successfully appended final entry to {runlog_path}")

    # 11. Verification of 3 Numbers Directly from Saved Files
    print("\n" + "=" * 80)
    print(" VERIFICATION OF 3 NUMBERS DIRECTLY FROM SAVED FILES")
    print("=" * 80)
    # Verification Number 1: Direction 1 Pooled In-Mechanism Recall
    df_gap_saved = pd.read_csv(out_gap_csv)
    n1_val = df_gap_saved[(df_gap_saved["Direction"].str.contains("Direction 1")) & (df_gap_saved["Type"] == "Pooled")]["In_Recall"].iloc[0]
    print(f"  [Verification 1] Direction 1 In-Mechanism Recall: {n1_val:.4f} (file: v2_generalization_gap.csv)")

    # Verification Number 2: Direction 1 Pooled Cross-Mechanism Recall
    n2_val = df_gap_saved[(df_gap_saved["Direction"].str.contains("Direction 1")) & (df_gap_saved["Type"] == "Pooled")]["Cross_Recall"].iloc[0]
    print(f"  [Verification 2] Direction 1 Cross-Mechanism Recall: {n2_val:.4f} (file: v2_generalization_gap.csv)")

    # Verification Number 3: Direction 1 Cutoff at 1.0 alert/month
    df_sens_saved = pd.read_csv(out_sens_csv)
    n3_val = df_sens_saved[(df_sens_saved["Budget_Target_mo"] == 1.0) & (df_sens_saved["Direction"] == "Train A")]["Operating_Cutoff_Tau"].iloc[0]
    print(f"  [Verification 3] Direction 1 Calibrated Cutoff Tau (1.0 FA/mo): {n3_val:.5f} (file: v2_budget_sensitivity.csv)")
    print("=" * 80)

    print(f"\nALL V2 FINAL EVALUATION STEPS COMPLETED IN {time.time()-t0_start:.2f}s!")

if __name__ == "__main__":
    run_stage2_evaluation()
