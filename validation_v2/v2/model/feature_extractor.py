"""
ForensiAIR V2 — Stage 2: Feature Extraction Pipeline
Protocol: Protocol v2.0 (Frozen) Section 4

Features:
- Past readings only (strictly causal, zero future leakage).
- Evaluated on regular 15-minute grid per parameter.
- Multi-scale windows: w in {16, 48, 96, 288} rows (4h, 12h, 24h, 72h).
- Per window w:
  1. range: rolling max - min, divided by expanding past MAD
  2. std: rolling sample standard deviation, divided by expanding past MAD
  3. repeat_len: past-only contiguous run length where value == previous value
  4. unique_count: number of distinct finite readings in window w
  5. unchanged_frac: fraction of steps where |x_i - x_{i-1}| < 1e-6
  6. level_shift: |mean_w - mean_prior_672|, divided by expanding past MAD
  7. slope: linear regression slope over window w, divided by expanding past MAD
  8. min_lag_sim: min absolute difference over lags in {96, 192, 288, 384, 480, 576, 672}, divided by expanding past MAD
  9. missing_frac: fraction of missing (NaN) readings in window w
  10. limit_ratio: rolling median_w / limit (NaN if no parsed limit)
  11. frac_above_85: fraction of values in window w >= 0.85 * limit (NaN if no parsed limit)
- Parameter identity as categorical feature.
- Zero quality codes, zero V1 scores.
"""

import numpy as np
import pandas as pd

WINDOWS = [16, 48, 96, 288]
LAGS = [96, 192, 288, 384, 480, 576, 672]

PARAM_MAP = {
    "ETP-pH": 0,
    "ETP-Flow": 1,
    "ETP-BOD": 2,
    "ETP-COD": 3,
    "ETP-TSS": 4
}

def get_resolution_step(vals: np.ndarray) -> float:
    """Calculates empirical resolution step (minimum positive difference)."""
    valid = vals[~np.isnan(vals)]
    if len(valid) < 2:
        return 1e-4
    diffs = np.abs(np.diff(valid))
    pos_diffs = diffs[diffs > 1e-6]
    if len(pos_diffs) == 0:
        return 1e-4
    step = float(np.min(pos_diffs))
    return max(step, 1e-4)

def compute_rolling_unique(vals: np.ndarray, w: int) -> np.ndarray:
    """Computes number of unique finite values in past window w."""
    N = len(vals)
    out = np.full(N, np.nan, dtype=float)
    # Fast windowed approach using pandas rolling apply with raw=True
    s = pd.Series(vals)
    # Using pandas rolling apply with numpy unique
    res = s.rolling(w, min_periods=1).apply(lambda arr: len(np.unique(arr[~np.isnan(arr)])), raw=True)
    return res.values

def compute_repeat_runs(vals: np.ndarray) -> np.ndarray:
    """Computes past-only contiguous exact-repeat run length."""
    N = len(vals)
    runs = np.zeros(N, dtype=float)
    for i in range(1, N):
        v_curr = vals[i]
        v_prev = vals[i - 1]
        if np.isnan(v_curr) or np.isnan(v_prev):
            runs[i] = 0.0
        elif abs(v_curr - v_prev) < 1e-6:
            runs[i] = runs[i - 1] + 1.0
        else:
            runs[i] = 0.0
    return runs

def compute_linear_slopes(vals: np.ndarray, w: int) -> np.ndarray:
    """Computes linear regression slope over trailing window w using FIR filter."""
    N = len(vals)
    x_coord = np.arange(w, dtype=float)
    weights = (x_coord - (w - 1) / 2.0) / (w * (w**2 - 1) / 12.0)
    # Flip weights for convolution
    kernel = weights[::-1]
    
    # Fill short missing gaps with forward fill for slope calculation
    s = pd.Series(vals).ffill().bfill().values
    slopes = np.full(N, np.nan, dtype=float)
    if N >= w:
        conv = np.convolve(s, kernel, mode="valid")
        slopes[w - 1:] = conv
    return slopes

def extract_features_for_series(
    df_grid: pd.DataFrame,
    param: str,
    cto_limit: float = np.nan
) -> pd.DataFrame:
    """
    Extracts all Protocol v2.0 Section 4 features for a single continuous series on a 15-min grid.
    Strictly causal (past readings only).
    """
    vals = pd.to_numeric(df_grid["value"], errors="coerce").values
    N = len(vals)
    s_val = pd.Series(vals)
    res_step = get_resolution_step(vals)

    # 1. Expanding Past MAD (Strictly Causal Scaling)
    exp_med = s_val.expanding(min_periods=16).median()
    exp_dev = (s_val - exp_med).abs()
    exp_mad = exp_dev.expanding(min_periods=16).median()
    # Floor expanding MAD by 1 resolution step
    mad_scale = np.maximum(exp_mad.fillna(res_step).values, res_step)

    # Precompute repeat runs once
    repeat_runs = compute_repeat_runs(vals)

    # Prior 672-row rolling mean for level shift (7 days)
    prior_672_mean = s_val.rolling(672, min_periods=48).mean().values

    # Precompute lag differences for min lagged similarity
    lag_diff_series = {}
    for L in LAGS:
        lag_diff_series[L] = (s_val - s_val.shift(L)).abs()

    features_dict = {}

    # Parameter categorical encoding
    p_cat_val = PARAM_MAP.get(param, 0)
    features_dict["param_cat"] = np.full(N, p_cat_val, dtype=int)

    for w in WINDOWS:
        prefix = f"w{w}_"

        # 1. Range (max - min) / expanding MAD
        r_max = s_val.rolling(w, min_periods=max(2, w // 4)).max()
        r_min = s_val.rolling(w, min_periods=max(2, w // 4)).min()
        r_range = (r_max - r_min).values / mad_scale
        features_dict[prefix + "range"] = r_range

        # 2. Std / expanding MAD
        r_std = s_val.rolling(w, min_periods=max(2, w // 4)).std(ddof=1).values / mad_scale
        features_dict[prefix + "std"] = r_std

        # 3. Exact repeat run length (clipped to window w)
        features_dict[prefix + "repeat_len"] = np.minimum(repeat_runs, float(w))

        # 4. Unique value count
        features_dict[prefix + "unique_count"] = compute_rolling_unique(vals, w)

        # 5. Fraction of unchanged steps
        diff_zero = (s_val.diff(1).abs() < 1e-6).astype(float)
        features_dict[prefix + "unchanged_frac"] = diff_zero.rolling(w, min_periods=max(2, w // 4)).mean().values

        # 6. Level shift vs prior 672 rows / expanding MAD
        w_mean = s_val.rolling(w, min_periods=max(2, w // 4)).mean().values
        features_dict[prefix + "level_shift"] = np.abs(w_mean - prior_672_mean) / mad_scale

        # 7. Linear slope / expanding MAD
        w_slope = compute_linear_slopes(vals, w) / mad_scale
        features_dict[prefix + "slope"] = w_slope

        # 8. Minimum lagged similarity over lags 96-672 / expanding MAD
        sim_list = []
        for L in LAGS:
            sim_L = lag_diff_series[L].rolling(w, min_periods=max(4, w // 4)).mean().values
            sim_list.append(sim_L)
        with np.errstate(all="ignore"):
            min_sim = np.nanmin(sim_list, axis=0) / mad_scale
        features_dict[prefix + "min_lag_sim"] = min_sim

        # 9. Missing fraction
        features_dict[prefix + "missing_frac"] = s_val.isna().rolling(w, min_periods=1).mean().values

        # 10. Limit ratio & Fraction above 85% of limit
        if pd.notna(cto_limit) and cto_limit > 0:
            w_med = s_val.rolling(w, min_periods=max(2, w // 4)).median().values
            features_dict[prefix + "limit_ratio"] = w_med / cto_limit
            above_85 = (s_val >= 0.85 * cto_limit).astype(float)
            features_dict[prefix + "frac_above_85"] = above_85.rolling(w, min_periods=max(2, w // 4)).mean().values
        else:
            features_dict[prefix + "limit_ratio"] = np.full(N, np.nan, dtype=float)
            features_dict[prefix + "frac_above_85"] = np.full(N, np.nan, dtype=float)

    feat_df = pd.DataFrame(features_dict, index=df_grid.index)
    return feat_df
