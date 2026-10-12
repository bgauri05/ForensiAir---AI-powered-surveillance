"""
ForensiAIR V2 — Stage 2: Detector Components (detector_b.py)
Specification: Protocol v2.0 (Frozen) & Protocol v1.1 Section C (Frozen)

Component Suite:
- F1B: Dither-resistant freeze detection (local variance collapse, unique value ratio)
- F2B: Replay and splice detection (shape-normalized z-normalized distance across candidate lags)
- F3B: Near-limit persistence & variance clamping detection (statutory CTO limit constrained)
- F7B: Transient relaxation & nonlinear drift detection (matched triangular filter, step jump, peak deviation)
- IF_B: Enhanced per-sensor Isolation Forest with 9 causal window features
- Full backward compatibility with V1 checks and M2 composite max fusion

Strict Rules:
- Inputs: Timestamps and values only (Protocol v1.1 G). Zero quality code features.
- Causal: Strictly backward-looking windows. No future observations used.
- Grid: Regular 15-minute time grid. Missing readings represented as NaN.
- Missing Safety: Missing readings produce NaN score; never trigger or continue alert episodes.
- Unsupervised: Blind empirical calibration on the series being scored. Zero label leakage.
"""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

# -----------------------------------------------------------------------------
# 1. Statistical & Utility Primitives
# -----------------------------------------------------------------------------
def calc_mad(arr) -> float:
    """Calculates Median Absolute Deviation (MAD), bounded from below by 1e-4."""
    arr_f = np.asarray(arr, dtype=float)
    valid = arr_f[~np.isnan(arr_f)]
    if len(valid) == 0:
        return 1e-4
    med = np.median(valid)
    mad = np.median(np.abs(valid - med))
    return max(float(mad), 1e-4)

def get_resolution_step(vals: np.ndarray) -> float:
    """Calculates empirical resolution step (minimum positive difference between readings)."""
    valid = vals[~np.isnan(vals)]
    if len(valid) < 2:
        return 1e-4
    diffs = np.abs(np.diff(valid))
    pos_diffs = diffs[diffs > 1e-6]
    if len(pos_diffs) == 0:
        return 1e-4
    step = float(np.min(pos_diffs))
    return max(step, 1e-4)

def score_tail_prob(calib_stat: np.ndarray, current_stat: np.ndarray, mode: str = "high") -> np.ndarray:
    """
    Computes tail probability score = -log10(tail_prob) with p clipped to [1/N, 1.0].
    Scores are strictly >= 0.0.
    
    Modes:
    - 'high': count(calib >= x) / N. High score when current_stat is unusually large.
    - 'low': count(calib <= x) / N. High score when current_stat is unusually small.
    - 'two_sided': 2 * min(count(calib <= x), count(calib >= x)) / N.
    """
    calib_f = np.asarray(calib_stat, dtype=float)
    valid_calib = calib_f[~np.isnan(calib_f)]
    N = len(valid_calib)
    if N == 0:
        return np.full(len(current_stat), np.nan)

    calib_sorted = np.sort(valid_calib)
    scores = np.full(len(current_stat), np.nan)

    curr_f = np.asarray(current_stat, dtype=float)
    valid_mask = ~np.isnan(curr_f)
    curr_valid = curr_f[valid_mask]

    if len(curr_valid) == 0:
        return scores

    if mode == "high":
        n_greater = N - np.searchsorted(calib_sorted, curr_valid, side="left")
        raw_prob = n_greater / float(N)
    elif mode == "low":
        n_less = np.searchsorted(calib_sorted, curr_valid, side="right")
        raw_prob = n_less / float(N)
    elif mode == "two_sided":
        n_less = np.searchsorted(calib_sorted, curr_valid, side="right")
        n_greater = N - np.searchsorted(calib_sorted, curr_valid, side="left")
        raw_prob = 2.0 * np.minimum(n_less, n_greater) / float(N)
    else:
        raise ValueError(f"Unknown tail mode: {mode}")

    # Clip p strictly to [1/N, 1.0] ensuring scores are always finite and >= 0.0
    tail_prob = np.clip(raw_prob, 1.0 / float(N), 1.0)
    scores[valid_mask] = np.maximum(-np.log10(tail_prob), 0.0)
    return scores

def prepare_series(df: pd.DataFrame, factory_id: str = None) -> pd.DataFrame:
    """
    Filters out Error/Out of Range quality codes (if present), sorts, and reindexes to a continuous 15-min grid.
    Missing readings are represented as NaN.
    """
    if "quality_code" in df.columns:
        df_clean = df[~df["quality_code"].isin(["Error", "Out of Range"])].copy()
    else:
        df_clean = df.copy()

    df_clean["ts_dt"] = pd.to_datetime(df_clean["timestamp"])
    df_clean = df_clean.sort_values("ts_dt").drop_duplicates(subset=["ts_dt"]).reset_index(drop=True)

    if df_clean.empty:
        return pd.DataFrame({
            "timestamp": pd.Series(dtype=str),
            "ts_dt": pd.Series(dtype="datetime64[ns]"),
            "value": pd.Series(dtype=float),
            "parameter_id": pd.Series(dtype=str),
            "factory_id": pd.Series(dtype=str)
        })

    df_clean["value"] = pd.to_numeric(df_clean["value"], errors="coerce")

    min_ts = df_clean["ts_dt"].min()
    max_ts = df_clean["ts_dt"].max()
    full_grid = pd.date_range(start=min_ts, end=max_ts, freq="15min")

    df_grid = pd.DataFrame({"ts_dt": full_grid})
    merged = pd.merge(df_grid, df_clean, on="ts_dt", how="left")
    merged["timestamp"] = merged["ts_dt"].dt.strftime("%Y-%m-%d %H:%M:%S")
    merged["value"] = pd.to_numeric(merged["value"], errors="coerce")
    merged["parameter_id"] = df_clean["parameter_id"].iloc[0] if "parameter_id" in df_clean else "UNKNOWN"
    if factory_id is not None:
        merged["factory_id"] = factory_id
    elif "factory_id" in df_clean.columns and not df_clean.empty:
        merged["factory_id"] = df_clean["factory_id"].iloc[0]
    else:
        merged["factory_id"] = "UNKNOWN"

    return merged

# -----------------------------------------------------------------------------
# 2. V1 Legacy Run Extraction (eps in {0, 1, 2})
# -----------------------------------------------------------------------------
def extract_quasi_flat_runs(vals: np.ndarray, eps: int = 0, res_step: float = 1e-4, is_flow: bool = False):
    """
    Finds contiguous blocks of quasi-flat runs with max - min <= eps * res_step.
    - eps=0: exact repeats.
    - eps in {1, 2}: quasi-flat repeats where variation is within eps quantization steps.
    """
    N = len(vals)
    L_per_row = np.zeros(N, dtype=int)
    run_lengths = []
    threshold = eps * res_step

    curr_len = 0
    curr_min = np.nan
    curr_max = np.nan
    in_run = False

    for i in range(N):
        v = vals[i]
        if np.isnan(v):
            if in_run:
                run_lengths.append(curr_len)
                in_run = False
                curr_len = 0
                curr_min = np.nan
                curr_max = np.nan
            continue

        if is_flow and v == 0.0:
            if in_run:
                run_lengths.append(curr_len)
                in_run = False
                curr_len = 0
                curr_min = np.nan
                curr_max = np.nan
            continue

        if not in_run:
            in_run = True
            curr_min = v
            curr_max = v
            curr_len = 1
        else:
            new_min = min(curr_min, v)
            new_max = max(curr_max, v)
            if (new_max - new_min) <= (threshold + 1e-9):
                curr_min = new_min
                curr_max = new_max
                curr_len += 1
            else:
                run_lengths.append(curr_len)
                curr_min = v
                curr_max = v
                curr_len = 1
        L_per_row[i] = curr_len

    if in_run:
        run_lengths.append(curr_len)

    return L_per_row, np.array(run_lengths, dtype=int)

# -----------------------------------------------------------------------------
# 3. Component Statistics Engine (V1 + V2 Components)
# -----------------------------------------------------------------------------
def compute_check_statistics_b(df_series: pd.DataFrame, cto_limits: dict = None, factory_id: str = None) -> dict:
    """
    Computes trailing-window check statistics for both V1 baseline checks and V2 components.
    
    Components Included:
    - F1 (V1): Legacy range over w in {16, 96, 288}
    - F1B (V2): Local variance collapse and unique value ratio over w in {16, 96, 288}
    - F2 (V1): Absolute difference copy-paste over w in {16, 96, 288}
    - F2B (V2): Shape-normalized z-normalized distance over w in {16, 96, 288} across lags 96..672
    - F3 (V1): Limit proximity over w in {16, 96, 288}
    - F3B (V2): Near-limit persistence fraction and variance clamp over w in {16, 96, 288}
    - F6 (V1): Level shift z-score and linear convolution slope
    - F7B (V2): Matched triangular filter, step-jump contrast, and peak transient deviation
    - Validity (pH bounds) and Gap fractions
    """
    vals = pd.to_numeric(df_series["value"], errors="coerce") if not df_series.empty else pd.Series(dtype=float)
    param = str(df_series["parameter_id"].iloc[0]) if not df_series.empty else ""
    if factory_id is not None:
        fac = str(factory_id)
    elif "factory_id" in df_series and not df_series.empty:
        fac = str(df_series["factory_id"].iloc[0])
    else:
        fac = ""
    is_flow = ("flow" in param.lower())
    is_ph = ("ph" in param.lower())

    s_mad = calc_mad(vals.values)
    res_step = get_resolution_step(vals.values)
    stats = {}

    # -------------------------------------------------------------------------
    # A. F1 (V1 Legacy) & F1B (V2 Dither-Resistant Freeze Detection)
    # -------------------------------------------------------------------------
    r_std_prior_672 = vals.shift(1).rolling(672, min_periods=96).std().fillna(s_mad)

    for w in [16, 96, 288]:
        # V1 Rolling Range
        r_max = vals.rolling(w, min_periods=w).max()
        r_min = vals.rolling(w, min_periods=w).min()
        r_range = r_max - r_min

        # Rolling Std
        r_std = vals.rolling(w, min_periods=w).std()

        if is_flow:
            r_med = vals.rolling(w, min_periods=w).median()
            r_range[r_med <= 0] = np.nan
            r_std[r_med <= 0] = np.nan

        stats[f"F1_range_w{w}"] = r_range.values

        # F1B: Local Variance Collapse Ratio (Low Tail)
        # std_w / (std_prior + 1e-4) -> drops toward 0 during frozen baseline (even with +/-1 step dither)
        var_collapse = r_std / np.maximum(r_std_prior_672, 1e-4)
        stats[f"F1B_var_collapse_w{w}"] = var_collapse.values

    # F1B: Unique Value Fraction (Low Tail) over w in {96, 288}
    # During dithered freeze, nunique is <= 3, whereas normal variation has high nunique
    for w in [96, 288]:
        count_u = lambda arr: float(len(np.unique(arr[~np.isnan(arr)]))) / float(w) if len(arr[~np.isnan(arr)]) >= (w // 2) else np.nan
        unique_ratio = vals.rolling(w, min_periods=w // 2).apply(count_u, raw=True)
        if is_flow:
            r_med = vals.rolling(w, min_periods=w // 2).median()
            unique_ratio[r_med <= 0] = np.nan
        stats[f"F1B_unique_ratio_w{w}"] = unique_ratio.values

    # -------------------------------------------------------------------------
    # B. F2 (V1) & F2B (V2 Shape-Normalized Replay & Splice Detection)
    # -------------------------------------------------------------------------
    lags = [96, 192, 288, 384, 480, 576, 672]

    for w in [16, 96, 288]:
        diff_list = []
        znorm_dist_list = []

        for L in lags:
            shifted = vals.shift(L)

            # V1 absolute difference
            diff_L = (vals - shifted).abs()
            scaled_diff = diff_L.rolling(w, min_periods=w).mean() / (s_mad + 1e-4)
            diff_list.append(scaled_diff)

            # V2 Shape-normalized z-normalized distance:
            # RMSD_znorm = sqrt(max(2 * (1 - rolling_corr(vals, shifted)), 0.0))
            # Completely invariant to gain scaling s != 1.0
            r_corr = vals.rolling(w, min_periods=w).corr(shifted)
            # Clip correlation to [-1.0, 1.0] and compute z-normalized RMS distance
            clipped_corr = np.clip(r_corr, -1.0, 1.0)
            znorm_dist = np.sqrt(np.maximum(2.0 * (1.0 - clipped_corr), 0.0))
            znorm_dist_list.append(znorm_dist)

        min_diff = pd.concat(diff_list, axis=1).min(axis=1)
        min_znorm_dist = pd.concat(znorm_dist_list, axis=1).min(axis=1)

        # Resolution Mask: Windows whose range <= 1 resolution step are set to NaN (flat windows belong to F1/F1B)
        r_range = vals.rolling(w, min_periods=w).max() - vals.rolling(w, min_periods=w).min()
        min_diff[r_range <= res_step] = np.nan
        min_znorm_dist[r_range <= res_step] = np.nan

        stats[f"F2_copypaste_w{w}"] = min_diff.values
        stats[f"F2B_znorm_dist_w{w}"] = min_znorm_dist.values

    # -------------------------------------------------------------------------
    # C. F3 (V1) & F3B (V2 Near-Limit Persistence & Variance Clamping)
    # -------------------------------------------------------------------------
    cto_max = np.nan
    if cto_limits:
        for (f_k, p_k), lim_val in cto_limits.items():
            if f_k == fac and (p_k.lower() in param.lower() or param.lower() in p_k.lower()):
                cto_max = lim_val
                break

    for w in [16, 96, 288]:
        if pd.notna(cto_max) and cto_max > 0:
            r_med = vals.rolling(w, min_periods=w).median()
            r_std = vals.rolling(w, min_periods=w).std()

            # V1 Limit Proximity
            stats[f"F3_limit_w{w}"] = (r_med / cto_max).values

            # F3B: Near-Limit Persistence Fraction (High Tail)
            # Fraction of rows in window >= 85% of CTO limit
            is_near_limit = (vals >= 0.85 * cto_max).astype(float)
            hug_frac = is_near_limit.rolling(w, min_periods=w).mean()
            hug_persist = hug_frac * (r_med / cto_max)
            stats[f"F3B_hug_persist_w{w}"] = hug_persist.values

            # F3B: Variance Clamping Near Limit (High Tail)
            # When median >= 80% limit, high ratio of proximity to std
            clamp_ratio = np.where(
                r_med >= 0.80 * cto_max,
                (r_med / cto_max) / (r_std / (s_mad + 1e-4) + 0.1),
                0.0
            )
            stats[f"F3B_var_clamp_w{w}"] = clamp_ratio
        else:
            stats[f"F3_limit_w{w}"] = np.full(len(vals), np.nan)
            stats[f"F3B_hug_persist_w{w}"] = np.full(len(vals), np.nan)
            stats[f"F3B_var_clamp_w{w}"] = np.full(len(vals), np.nan)

    # -------------------------------------------------------------------------
    # D. F4 Validity (Hard Boolean Physical Bounds)
    # -------------------------------------------------------------------------
    if is_ph:
        validity = ((vals < 0) | (vals > 14)).astype(float)
        validity[vals.isna()] = np.nan
        stats["validity"] = validity.values
    else:
        stats["validity"] = np.zeros(len(vals))

    # -------------------------------------------------------------------------
    # E. F6 (V1 Drift) & F7B (V2 Transient Matched Filter & Drift)
    # -------------------------------------------------------------------------
    r_med_prior = vals.shift(1).rolling(672, min_periods=96).median()
    r_std_prior = vals.shift(1).rolling(672, min_periods=96).std().fillna(1e-4)

    for w in [16, 96, 288]:
        r_med_curr = vals.rolling(w, min_periods=w).median()
        shift_z = (r_med_curr - r_med_prior) / np.maximum(r_std_prior, 1e-4)
        stats[f"F6_shift_w{w}"] = shift_z.values

        # V1 Linear convolution slope
        if len(vals) < w:
            stats[f"F6_slope_w{w}"] = np.full(len(vals), np.nan)
            stats[f"F7B_tri_conv_w{w}"] = np.full(len(vals), np.nan)
        else:
            x_idx = np.arange(w)
            x_bar = (w - 1) / 2.0
            denom = np.sum((x_idx - x_bar)**2)
            kernel_linear = (x_idx - x_bar) / denom
            c_valid = np.convolve(vals.fillna(0).values, kernel_linear[::-1], mode="valid")
            has_nan = (vals.isna().rolling(w, min_periods=w).sum() > 0).values[w - 1:]
            conv_slope = np.full(len(vals), np.nan)
            conv_slope[w - 1:] = np.where(has_nan, np.nan, c_valid)
            stats[f"F6_slope_w{w}"] = conv_slope

            # F7B: Matched Triangular Filter (High Tail)
            # Matched to triangular bias ramps peaking at midpoint
            k_raw = 1.0 - np.abs(2.0 * x_idx - (w - 1)) / (w - 1)
            k_tri = (k_raw - np.mean(k_raw)) / np.sum(np.abs(k_raw - np.mean(k_raw)))
            c_tri = np.convolve(vals.fillna(0).values, k_tri[::-1], mode="valid")
            tri_resp = np.full(len(vals), np.nan)
            tri_resp[w - 1:] = np.where(has_nan, np.nan, np.abs(c_tri) / (s_mad + 1e-4))
            stats[f"F7B_tri_conv_w{w}"] = tri_resp

        # F7B: Abrupt Step-Jump Contrast (High Tail)
        # Difference between second half and first half of window w
        w_half = max(w // 2, 4)
        mean_recent = vals.rolling(w_half, min_periods=w_half).mean()
        mean_prior = vals.shift(w_half).rolling(w_half, min_periods=w_half).mean()
        step_jump = (mean_recent - mean_prior).abs() / np.maximum(r_std_prior, 1e-4)
        stats[f"F7B_step_jump_w{w}"] = step_jump.values

        # F7B: Peak Transient Deviation from Rolling Median (High Tail)
        r_max = vals.rolling(w, min_periods=w).max()
        r_min = vals.rolling(w, min_periods=w).min()
        peak_dev = np.maximum(r_max - r_med_curr, r_med_curr - r_min) / (s_mad + 1e-4)
        stats[f"F7B_transient_dev_w{w}"] = peak_dev.values

    # F7 Gap Fraction
    for w in [16, 96, 288]:
        stats[f"gap_frac_w{w}"] = vals.isna().rolling(w, min_periods=1).mean().values

    return stats

def compute_f5_correlation(df_factory: pd.DataFrame, w: int = 96) -> dict:
    """Computes rolling Pearson correlation over window w between BOD/COD/TSS pairs."""
    params = ["ETP-BOD", "ETP-COD", "ETP-TSS"]
    present = [p for p in params if p in df_factory["parameter_id"].unique()]
    if len(present) < 2:
        return {}

    grid_dict = {}
    for p in present:
        sub = df_factory[df_factory["parameter_id"] == p]
        grid = prepare_series(sub)
        if not grid.empty:
            grid_dict[p] = grid.set_index("ts_dt")["value"]

    if len(grid_dict) < 2:
        return {}

    df_pairs = pd.DataFrame(grid_dict)
    corr_dict = {}
    keys = list(grid_dict.keys())
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            p1, p2 = keys[i], keys[j]
            pair_key = f"F5_corr_{p1}_{p2}_w{w}"
            r_corr = df_pairs[p1].rolling(w, min_periods=w).corr(df_pairs[p2])
            corr_dict[pair_key] = r_corr

    return corr_dict

# -----------------------------------------------------------------------------
# 4. IF_B: Enhanced Per-Sensor Isolation Forest Feature Pipeline
# -----------------------------------------------------------------------------
FEATURE_COLS_B = [
    "rolling_mean_16",
    "rolling_std_16",
    "rolling_range_16",
    "diff_std_16",
    "diff_mean_16",
    "z_level_16",
    "var_ratio_16_96",
    "tri_conv_16",
    "unique_ratio_16"
]

def extract_if_b_features(df_series: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts 9 strictly causal backward-looking window features for IF_B:
    1. rolling_mean_16: 4-hour rolling mean
    2. rolling_std_16: 4-hour rolling standard deviation
    3. rolling_range_16: 4-hour rolling range (max - min)
    4. diff_std_16: standard deviation of consecutive differences
    5. diff_mean_16: mean absolute 1-step difference normalized by MAD
    6. z_level_16: level shift z-score relative to prior 96 rows
    7. var_ratio_16_96: ratio of 16-row std to 96-row std (variance collapse / burst)
    8. tri_conv_16: 16-row triangular filter response (acute transient impulse)
    9. unique_ratio_16: distinct value fraction in 16 rows (dither/quantization proxy)
    """
    vals = df_series["value"].copy()
    s_mad = calc_mad(vals.values)
    feats = pd.DataFrame(index=df_series.index)

    feats["rolling_mean_16"] = vals.rolling(16, min_periods=16).mean()
    feats["rolling_std_16"] = vals.rolling(16, min_periods=16).std().fillna(0.0)
    feats["rolling_range_16"] = vals.rolling(16, min_periods=16).max() - vals.rolling(16, min_periods=16).min()
    feats["diff_std_16"] = vals.diff(1).abs().rolling(16, min_periods=16).std().fillna(0.0)
    feats["diff_mean_16"] = vals.diff(1).abs().rolling(16, min_periods=16).mean().fillna(0.0)

    med_96 = vals.rolling(96, min_periods=16).median()
    std_96 = vals.rolling(96, min_periods=16).std().fillna(1e-4)
    feats["z_level_16"] = (feats["rolling_mean_16"] - med_96) / np.maximum(std_96, 1e-4)

    # Variance ratio 16 vs 96
    feats["var_ratio_16_96"] = feats["rolling_std_16"] / np.maximum(std_96, 1e-4)

    # 16-row triangular filter (strictly causal, trailing past window)
    w_tri = 16
    tri_resp = np.full(len(vals), np.nan)
    if len(vals) >= w_tri:
        x_idx = np.arange(w_tri)
        k_raw = 1.0 - np.abs(2.0 * x_idx - (w_tri - 1)) / (w_tri - 1)
        k_tri = (k_raw - np.mean(k_raw)) / np.sum(np.abs(k_raw - np.mean(k_raw)))
        c_tri = np.convolve(vals.fillna(0).values, k_tri[::-1], mode="valid")
        has_nan_16 = (vals.isna().rolling(w_tri, min_periods=w_tri).sum() > 0).values[w_tri - 1:]
        local_scale = np.maximum(feats["rolling_std_16"].iloc[w_tri - 1:].values, 1e-4)
        tri_resp[w_tri - 1:] = np.where(has_nan_16, np.nan, np.abs(c_tri) / local_scale)
    feats["tri_conv_16"] = tri_resp

    # Unique ratio in 16 rows (strictly causal, trailing past window)
    count_u16 = lambda arr: float(len(np.unique(arr[~np.isnan(arr)]))) / 16.0 if len(arr[~np.isnan(arr)]) >= 8 else np.nan
    feats["unique_ratio_16"] = vals.rolling(16, min_periods=8).apply(count_u16, raw=True)

    return feats

def fit_if_b(train_factories_df: pd.DataFrame, parameter_id: str, seed: int = 42) -> IsolationForest:
    """Trains an enhanced Isolation Forest per parameter on training fold factories' unaltered rows."""
    allowed = train_factories_df[train_factories_df["parameter_id"] == parameter_id]
    if allowed.empty:
        return None

    feat_list = []
    for _, g in allowed.groupby("factory_id"):
        g_grid = prepare_series(g)
        if not g_grid.empty:
            feat_list.append(extract_if_b_features(g_grid))

    if not feat_list:
        return None

    X_all = pd.concat(feat_list, ignore_index=True).dropna()
    if len(X_all) < 10:
        return None

    if len(X_all) > 50000:
        X_train = X_all.sample(n=50000, random_state=seed)
    else:
        X_train = X_all

    iso = IsolationForest(n_estimators=100, max_samples=min(2048, len(X_train)), random_state=seed, n_jobs=1)
    iso.fit(X_train)
    return iso

# -----------------------------------------------------------------------------
# 5. Calibration & Scoring Contracts (V2)
# -----------------------------------------------------------------------------
def calibrate_b(
    df_series: pd.DataFrame,
    mode: str = "blind",
    clean_series: pd.DataFrame = None,
    cto_limits: dict = None,
    skip_if: bool = False,
    if_b_model: IsolationForest = None,
    f5_corr_dict: dict = None,
    factory_id: str = None
) -> dict:
    """
    Builds empirical distribution of check statistics from calibration telemetry.
    - mode="blind" (default): Calibrates directly on the series being scored.
    - mode="oracle": Calibrates on clean unaltered telemetry (sensitivity option).
    """
    calib_source = clean_series if (mode == "oracle" and clean_series is not None) else df_series
    df_grid = prepare_series(calib_source, factory_id=factory_id)
    stats = compute_check_statistics_b(df_grid, cto_limits=cto_limits, factory_id=factory_id)

    calib_dict = {}
    for name, arr in stats.items():
        valid_arr = arr[~np.isnan(arr)]
        calib_dict[name] = valid_arr

    # F1 Run-level calibration for eps in {0, 1, 2}
    vals = pd.to_numeric(df_grid["value"], errors="coerce") if not df_grid.empty else pd.Series(dtype=float)
    param = str(df_grid["parameter_id"].iloc[0]) if not df_grid.empty else ""
    is_flow = ("flow" in param.lower())
    res_step = get_resolution_step(vals.values)

    for eps in [0, 1, 2]:
        _, nat_run_lens = extract_quasi_flat_runs(vals.values, eps=eps, res_step=res_step, is_flow=is_flow)
        calib_dict[f"f1_run_lengths_eps{eps}"] = nat_run_lens
        calib_dict[f"f1_total_runs_eps{eps}"] = len(nat_run_lens)

    calib_dict["f1_run_lengths"] = calib_dict["f1_run_lengths_eps0"]
    calib_dict["f1_total_runs"] = calib_dict["f1_total_runs_eps0"]

    # F5 factory correlation reference distribution
    if f5_corr_dict:
        for w in [96, 288]:
            k_w = f"w{w}"
            if k_w in f5_corr_dict:
                c_vals = f5_corr_dict[k_w]
                if isinstance(c_vals, pd.Series):
                    valid_c = c_vals.dropna().values
                elif isinstance(c_vals, np.ndarray):
                    valid_c = c_vals[~np.isnan(c_vals)]
                else:
                    valid_c = np.array([])
                if len(valid_c) > 0:
                    calib_dict[f"F5_corr_w{w}"] = valid_c

    # IF_B raw decision score calibration reference
    target_if_model = if_b_model
    feats = extract_if_b_features(df_grid)
    valid_idx = feats.dropna().index
    if target_if_model is not None:
        if len(valid_idx) > 0:
            calib_dict["if_b_raw_score"] = -target_if_model.decision_function(feats.loc[valid_idx])
            calib_dict["if_b_model"] = target_if_model
    elif not skip_if:
        if len(valid_idx) > 10:
            iso_self = IsolationForest(n_estimators=100, max_samples=min(2048, len(valid_idx)), random_state=42, n_jobs=1)
            iso_self.fit(feats.loc[valid_idx])
            calib_dict["if_b_raw_score"] = -iso_self.decision_function(feats.loc[valid_idx])
            calib_dict["if_b_model"] = iso_self
    else:
        if len(valid_idx) > 10:
            iso_self = IsolationForest(n_estimators=100, max_samples=min(2048, len(valid_idx)), random_state=42, n_jobs=1)
            iso_self.fit(feats.loc[valid_idx])
            calib_dict["if_b_raw_score"] = -iso_self.decision_function(feats.loc[valid_idx])
            calib_dict["if_b_model"] = iso_self

    return calib_dict

def score_b(
    df_series: pd.DataFrame,
    calib_dict: dict,
    if_b_model: IsolationForest = None,
    cto_limits: dict = None,
    f5_corr_dict: dict = None,
    factory_id: str = None
) -> pd.DataFrame:
    """
    Scores a series using empirical tail probabilities (-log10) across V1 checks, V2 components, and M2 fusion.
    """
    df_grid = prepare_series(df_series, factory_id=factory_id)
    stats = compute_check_statistics_b(df_grid, cto_limits=cto_limits, factory_id=factory_id)

    out_df = pd.DataFrame()
    out_df["timestamp"] = df_grid["timestamp"]
    out_df["parameter_id"] = df_grid["parameter_id"]

    vals = pd.to_numeric(df_grid["value"], errors="coerce") if not df_grid.empty else pd.Series(dtype=float)
    param = str(df_grid["parameter_id"].iloc[0]) if not df_grid.empty else ""
    is_flow = ("flow" in param.lower())
    res_step = get_resolution_step(vals.values)
    v_mask = ~vals.isna()

    # 1. F1 Run-Level Scores (eps in {0, 1, 2})
    for eps in [0, 1, 2]:
        L_row, _ = extract_quasi_flat_runs(vals.values, eps=eps, res_step=res_step, is_flow=is_flow)
        f1_run_lens = calib_dict.get(f"f1_run_lengths_eps{eps}", calib_dict.get("f1_run_lengths", np.array([], dtype=int)))
        tot_runs = calib_dict.get(f"f1_total_runs_eps{eps}", calib_dict.get("f1_total_runs", len(f1_run_lens)))

        f1_scores = np.zeros(len(vals))
        sorted_lens = np.sort(f1_run_lens)
        ge8_mask = (L_row >= 8)
        if np.any(ge8_mask) and tot_runs > 0:
            k_ge_L = len(sorted_lens) - np.searchsorted(sorted_lens, L_row[ge8_mask], side="left")
            p_run = (1.0 + k_ge_L) / (1.0 + tot_runs)
            p_run = np.clip(p_run, 1.0 / (1.0 + tot_runs), 1.0)
            f1_scores[ge8_mask] = -np.log10(p_run)

        f1_scores[~v_mask] = np.nan
        if is_flow:
            f1_scores[vals == 0.0] = 0.0

        out_df[f"F1_score_eps{eps}"] = f1_scores
        if eps == 0:
            out_df["F1_score"] = f1_scores

    # 2. Score Empirical Tail Probabilities
    for name, arr in stats.items():
        if name == "validity" or name.startswith("gap_frac"):
            out_df[name] = arr
            continue

        calib_arr = calib_dict.get(name, np.array([]))

        # Tail mode mapping
        if "var_collapse" in name or "unique_ratio" in name:
            out_df[name + "_score"] = score_tail_prob(calib_arr, arr, mode="low")
        elif "znorm_dist" in name or "F2" in name:
            out_df[name + "_score"] = score_tail_prob(calib_arr, arr, mode="low")
        elif "F1_range" in name:
            out_df[name + "_score"] = score_tail_prob(calib_arr, arr, mode="low")
        elif "hug_persist" in name or "var_clamp" in name or "F3" in name:
            out_df[name + "_score"] = score_tail_prob(calib_arr, arr, mode="high")
        elif "tri_conv" in name or "step_jump" in name or "transient_dev" in name:
            out_df[name + "_score"] = score_tail_prob(calib_arr, arr, mode="high")
        elif "F6" in name:
            out_df[name + "_score"] = score_tail_prob(calib_arr, arr, mode="two_sided")
        else:
            out_df[name + "_score"] = score_tail_prob(calib_arr, arr, mode="high")

    # 3. F5 Correlation Break Scores
    for w in [96, 288]:
        col_name = f"F5_corr_w{w}_score"
        if f5_corr_dict and f"w{w}" in f5_corr_dict:
            curr_corr = f5_corr_dict[f"w{w}"]
            if isinstance(curr_corr, pd.Series):
                curr_corr = curr_corr.reindex(df_grid["ts_dt"]).values
            elif len(curr_corr) != len(df_grid):
                curr_corr_arr = np.full(len(df_grid), np.nan)
                min_l = min(len(curr_corr), len(df_grid))
                curr_corr_arr[:min_l] = curr_corr[:min_l]
                curr_corr = curr_corr_arr
            calib_corr = calib_dict.get(f"F5_corr_w{w}", np.array([]))
            out_df[col_name] = score_tail_prob(calib_corr, curr_corr, mode="two_sided")
        else:
            out_df[col_name] = np.nan

    # 4. IF_B Isolation Forest Scores
    model_to_use = if_b_model if if_b_model is not None else calib_dict.get("if_b_model")
    if model_to_use is not None:
        feats = extract_if_b_features(df_grid)
        valid_idx = feats.dropna().index
        if_raw_sc = np.full(len(df_grid), np.nan)
        if len(valid_idx) > 0:
            if_raw_sc[valid_idx] = -model_to_use.decision_function(feats.loc[valid_idx])

        calib_if = calib_dict.get("if_b_raw_score", np.array([]))
        out_df["if_b_score"] = score_tail_prob(calib_if, if_raw_sc, mode="high")
        out_df["if_score"] = out_df["if_b_score"]
    else:
        out_df["if_b_score"] = np.nan
        out_df["if_score"] = np.nan

    # Ensure NaN semantics for all score columns
    for c in out_df.columns:
        if c.endswith("_score") or c in ["F1_score", "if_score"]:
            out_df.loc[~v_mask, c] = np.nan

    # -------------------------------------------------------------------------
    # 5. Composite Max Fusions (M1 Legacy vs M2 Enhanced)
    # -------------------------------------------------------------------------
    # M1 Candidate list (V1 checks only)
    m1_candidates = [
        "F1_score_eps0", "F1_score_eps1", "F1_score_eps2",
        "F2_copypaste_w16_score", "F2_copypaste_w96_score", "F2_copypaste_w288_score",
        "F3_limit_w16_score", "F3_limit_w96_score", "F3_limit_w288_score",
        "F5_corr_w96_score", "F5_corr_w288_score",
        "F6_shift_w16_score", "F6_shift_w96_score", "F6_shift_w288_score",
        "F6_slope_w16_score", "F6_slope_w96_score", "F6_slope_w288_score",
        "if_score"
    ]
    import warnings
    m1_cols = [c for c in m1_candidates if c in out_df.columns]
    if m1_cols:
        m1_arr = out_df[m1_cols].values
        has_any1 = np.any(~np.isnan(m1_arr), axis=1)
        m1_sc = np.full(len(vals), np.nan)
        if np.any(has_any1):
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=RuntimeWarning)
                m1_sc[has_any1] = np.nanmax(m1_arr[has_any1], axis=1)
    else:
        m1_sc = np.full(len(vals), np.nan)
    m1_sc[~v_mask] = np.nan
    out_df["M1_fusion"] = m1_sc

    # M2 Candidate list (V1 checks + V2 components: F1B, F2B, F3B, F7B, IF_B)
    m2_candidates = m1_candidates + [
        "F1B_var_collapse_w16_score", "F1B_var_collapse_w96_score", "F1B_var_collapse_w288_score",
        "F1B_unique_ratio_w96_score", "F1B_unique_ratio_w288_score",
        "F2B_znorm_dist_w16_score", "F2B_znorm_dist_w96_score", "F2B_znorm_dist_w288_score",
        "F3B_hug_persist_w16_score", "F3B_hug_persist_w96_score", "F3B_hug_persist_w288_score",
        "F3B_var_clamp_w96_score", "F3B_var_clamp_w288_score",
        "F7B_tri_conv_w16_score", "F7B_tri_conv_w96_score", "F7B_tri_conv_w288_score",
        "F7B_step_jump_w16_score", "F7B_step_jump_w96_score", "F7B_step_jump_w288_score",
        "F7B_transient_dev_w16_score", "F7B_transient_dev_w96_score", "F7B_transient_dev_w288_score",
        "if_b_score"
    ]
    m2_cols = [c for c in m2_candidates if c in out_df.columns]
    if m2_cols:
        m2_arr = out_df[m2_cols].values
        has_any2 = np.any(~np.isnan(m2_arr), axis=1)
        m2_sc = np.full(len(vals), np.nan)
        if np.any(has_any2):
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=RuntimeWarning)
                m2_sc[has_any2] = np.nanmax(m2_arr[has_any2], axis=1)
    else:
        m2_sc = np.full(len(vals), np.nan)
    m2_sc[~v_mask] = np.nan
    out_df["M2_fusion"] = m2_sc

    return out_df
