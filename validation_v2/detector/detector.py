import os
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

def calc_mad(arr):
    """Calculates Median Absolute Deviation (MAD)."""
    arr_f = np.asarray(arr, dtype=float)
    valid = arr_f[~np.isnan(arr_f)]
    if len(valid) == 0:
        return 1e-4
    med = np.median(valid)
    mad = np.median(np.abs(valid - med))
    return max(float(mad), 1e-4)

def score_tail_prob(calib_stat: np.ndarray, current_stat: np.ndarray, mode: str = "high") -> np.ndarray:
    """
    Computes tail probability score = -log10(tail_prob) with p clipped to [1/N, 1.0].
    Scores are strictly >= 0.0.

    Tie Handling:
    - mode='high': count(calib >= x) counts all calibration values >= x (including ties).
    - mode='low': count(calib <= x) counts all calibration values <= x (including ties).
    - mode='two_sided': 2 * min(count(calib <= x), count(calib >= x)), clipped to <= 1.0.
    In the presence of ties or at median boundaries, clipping raw_prob to [1/N, 1.0]
    ensures p in [1/N, 1.0] and -log10(p) in [0.0, log10(N)].
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
        # count(calib >= x)
        n_greater = N - np.searchsorted(calib_sorted, curr_valid, side="left")
        raw_prob = n_greater / float(N)
    elif mode == "low":
        # count(calib <= x)
        n_less = np.searchsorted(calib_sorted, curr_valid, side="right")
        raw_prob = n_less / float(N)
    elif mode == "two_sided":
        n_less = np.searchsorted(calib_sorted, curr_valid, side="right")
        n_greater = N - np.searchsorted(calib_sorted, curr_valid, side="left")
        raw_prob = 2.0 * np.minimum(n_less, n_greater) / float(N)
    else:
        raise ValueError(f"Unknown tail mode: {mode}")

    # Clip p strictly to [1/N, 1.0] ensuring scores are always >= 0.0
    tail_prob = np.clip(raw_prob, 1.0 / float(N), 1.0)
    scores[valid_mask] = np.maximum(-np.log10(tail_prob), 0.0)
    return scores

def prepare_series(df: pd.DataFrame, factory_id: str = None) -> pd.DataFrame:
    """
    Filters out Error/Out of Range quality codes (if present), sorts, and reindexes to continuous 15-min grid.
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

def get_resolution_step(vals: np.ndarray) -> float:
    """Calculates empirical resolution step (minimum positive difference between consecutive readings)."""
    valid = vals[~np.isnan(vals)]
    if len(valid) < 2:
        return 1e-4
    diffs = np.abs(np.diff(valid))
    pos_diffs = diffs[diffs > 1e-6]
    if len(pos_diffs) == 0:
        return 1e-4
    step = float(np.min(pos_diffs))
    return max(step, 1e-4)

def extract_quasi_flat_runs(vals: np.ndarray, eps: int = 0, res_step: float = 1e-4, is_flow: bool = False):
    """
    Finds contiguous blocks of quasi-flat runs with max - min <= eps * res_step.
    - eps=0: exact repeats (identical values).
    - eps in {1, 2}: quasi-flat repeats where variation is within eps quantization steps.
      Chosen to generalize beyond exact repeats on quantized industrial sensors (domain-informed).
    - Breaks at NaN and timestamp gaps.
    - Flow zero-valued runs are excluded from run statistics.

    Returns:
    - L_per_row: array of length N, where L[i] is the length of the run ending at row i.
    - natural_run_lengths: array of completed run lengths in the series.
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

def extract_exact_repeat_runs(vals: np.ndarray, is_flow: bool = False):
    """Legacy alias for eps=0 exact-repeat run extraction."""
    return extract_quasi_flat_runs(vals, eps=0, res_step=0.0, is_flow=is_flow)

def compute_check_statistics(df_series: pd.DataFrame, cto_limits: dict = None, factory_id: str = None) -> dict:
    """
    Computes trailing-window check statistics over w in {16, 96, 288} for a single series.
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

    # F1 Flatline (Rolling Range over w in {16, 96, 288}) - kept for legacy comparison
    for w in [16, 96, 288]:
        r_max = vals.rolling(w, min_periods=w).max()
        r_min = vals.rolling(w, min_periods=w).min()
        r_range = r_max - r_min

        if is_flow:
            r_med = vals.rolling(w, min_periods=w).median()
            r_range[r_med == 0] = np.nan

        stats[f"F1_range_w{w}"] = r_range.values

    # F2 Copy-Paste (Lags 96..672 step 96)
    # Windows whose range <= 1 resolution step are set to NaN (flat windows belong to F1)
    lags = [96, 192, 288, 384, 480, 576, 672]
    for w in [16, 96, 288]:
        diff_list = []
        for L in lags:
            shifted = vals.shift(L)
            diff_L = (vals - shifted).abs()
            scaled_diff = diff_L.rolling(w, min_periods=w).mean() / (s_mad + 1e-4)
            diff_list.append(scaled_diff)
        min_diff = pd.concat(diff_list, axis=1).min(axis=1)

        # Mask out flat windows: range <= 1 resolution step -> NaN
        r_range = vals.rolling(w, min_periods=w).max() - vals.rolling(w, min_periods=w).min()
        min_diff[r_range <= res_step] = np.nan

        stats[f"F2_copypaste_w{w}"] = min_diff.values

    # F3 Limit Proximity
    cto_max = np.nan
    if cto_limits:
        for (f_k, p_k), lim_val in cto_limits.items():
            if f_k == fac and (p_k.lower() in param.lower() or param.lower() in p_k.lower()):
                cto_max = lim_val
                break

    for w in [16, 96, 288]:
        if pd.notna(cto_max) and cto_max > 0:
            r_med = vals.rolling(w, min_periods=w).median()
            stats[f"F3_limit_w{w}"] = (r_med / cto_max).values
        else:
            stats[f"F3_limit_w{w}"] = np.full(len(vals), np.nan)

    # F4 Validity (pH hard bounds <0 or >14)
    if is_ph:
        validity = ((vals < 0) | (vals > 14)).astype(float)
        validity[vals.isna()] = np.nan
        stats["validity"] = validity.values
    else:
        stats["validity"] = np.zeros(len(vals))

    # F6 Drift / Dip (Level shift & Slope over w in {16, 96, 288})
    r_med_prior = vals.shift(1).rolling(672, min_periods=96).median()
    r_std_prior = vals.shift(1).rolling(672, min_periods=96).std().fillna(1e-4)

    for w in [16, 96, 288]:
        r_med_curr = vals.rolling(w, min_periods=w).median()
        shift_z = (r_med_curr - r_med_prior) / np.maximum(r_std_prior, 1e-4)
        stats[f"F6_shift_w{w}"] = shift_z.values

        # Linear slope over trailing window w via exact, fast 1D convolution
        if len(vals) < w:
            stats[f"F6_slope_w{w}"] = np.full(len(vals), np.nan)
        else:
            x_idx = np.arange(w)
            x_bar = (w - 1) / 2.0
            denom = np.sum((x_idx - x_bar)**2)
            kernel = (x_idx - x_bar) / denom
            c_valid = np.convolve(vals.fillna(0).values, kernel[::-1], mode="valid")
            has_nan = (vals.isna().rolling(w, min_periods=w).sum() > 0).values[w - 1:]
            conv_slope = np.full(len(vals), np.nan)
            conv_slope[w - 1:] = np.where(has_nan, np.nan, c_valid)
            stats[f"F6_slope_w{w}"] = conv_slope

    # F7 Gap Fraction
    for w in [16, 96, 288]:
        stats[f"gap_frac_w{w}"] = vals.isna().rolling(w, min_periods=1).mean().values

    return stats

def compute_f5_correlation(df_factory: pd.DataFrame, w: int = 96) -> dict:
    """
    Computes rolling Pearson correlation over window w between BOD/COD/TSS parameter pairs in a factory.
    """
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

def calibrate(
    df_series: pd.DataFrame,
    mode: str = "blind",
    clean_series: pd.DataFrame = None,
    cto_limits: dict = None,
    skip_if: bool = False,
    if_model: IsolationForest = None,
    f5_corr_dict: dict = None,
    factory_id: str = None
) -> dict:
    """
    Builds empirical distribution of check statistics from calibration telemetry.
    - mode="blind" (default): Calibrates on the same series to be scored (df_series).
    - mode="oracle": Calibrates on clean_series (the unaltered original series) as sensitivity option.
    - if_model: External Isolation Forest (e.g. LOFO model). When provided, computes reference distribution of raw decision scores.
    - f5_corr_dict: Factory-level correlation dictionary containing 'w96' and 'w288' correlation series.
    - factory_id: Factory ID string (ensures correct consent limit lookup).
    """
    calib_source = clean_series if (mode == "oracle" and clean_series is not None) else df_series
    df_grid = prepare_series(calib_source, factory_id=factory_id)
    stats = compute_check_statistics(df_grid, cto_limits=cto_limits, factory_id=factory_id)

    calib_dict = {}
    for name, arr in stats.items():
        valid_arr = arr[~np.isnan(arr)]
        calib_dict[name] = valid_arr

    # F1 Run-level calibration: extract natural runs for eps in {0, 1, 2}
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

    # IF raw decision score calibration reference
    target_if_model = if_model
    feats = extract_if_features(df_grid)
    valid_idx = feats.dropna().index
    if target_if_model is not None:
        if len(valid_idx) > 0:
            calib_dict["if_raw_score"] = -target_if_model.decision_function(feats.loc[valid_idx])
            calib_dict["if_self_model"] = target_if_model
    elif not skip_if:
        if len(valid_idx) > 10:
            iso_self = IsolationForest(n_estimators=100, max_samples=min(2048, len(valid_idx)), random_state=42, n_jobs=1)
            iso_self.fit(feats.loc[valid_idx])
            calib_dict["if_raw_score"] = -iso_self.decision_function(feats.loc[valid_idx])
            calib_dict["if_self_model"] = iso_self
    else:
        # Fallback if skip_if=True but no external model was provided
        if len(valid_idx) > 10:
            iso_self = IsolationForest(n_estimators=100, max_samples=min(2048, len(valid_idx)), random_state=42, n_jobs=1)
            iso_self.fit(feats.loc[valid_idx])
            calib_dict["if_raw_score"] = -iso_self.decision_function(feats.loc[valid_idx])
            calib_dict["if_self_model"] = iso_self

    return calib_dict

FEATURE_COLS = ["rolling_mean_16", "rolling_std_16", "rolling_range_16", "diff_std_16", "z_level_16"]

def extract_if_features(df_series: pd.DataFrame) -> pd.DataFrame:
    """Extracts windowed features for Isolation Forest per series."""
    vals = df_series["value"].copy()
    feats = pd.DataFrame(index=df_series.index)

    feats["rolling_mean_16"] = vals.rolling(16, min_periods=16).mean()
    feats["rolling_std_16"] = vals.rolling(16, min_periods=16).std().fillna(0.0)
    feats["rolling_range_16"] = vals.rolling(16, min_periods=16).max() - vals.rolling(16, min_periods=16).min()
    feats["diff_std_16"] = vals.diff(1).abs().rolling(16, min_periods=16).std().fillna(0.0)

    med_96 = vals.rolling(96, min_periods=16).median()
    std_96 = vals.rolling(96, min_periods=16).std().fillna(1e-4)
    feats["z_level_16"] = (feats["rolling_mean_16"] - med_96) / np.maximum(std_96, 1e-4)

    # Robust scaling
    for col in feats.columns:
        m = feats[col].median()
        mad = calc_mad(feats[col].values)
        feats[col] = (feats[col] - m) / (mad + 1e-4)

    return feats

extract_series_features = extract_if_features

def fit_if(train_factories_df: pd.DataFrame, parameter_id: str, seed: int = 42) -> IsolationForest:
    """Trains an Isolation Forest per parameter on training fold factories' unaltered rows."""
    allowed = train_factories_df[train_factories_df["parameter_id"] == parameter_id]
    if allowed.empty:
        return None

    feat_list = []
    for _, g in allowed.groupby("factory_id"):
        g_grid = prepare_series(g)
        if not g_grid.empty:
            feat_list.append(extract_if_features(g_grid))

    if not feat_list:
        return None

    X_all = pd.concat(feat_list, ignore_index=True).dropna()
    if len(X_all) < 10:
        return None

    if len(X_all) > 50000:
        X_train = X_all.sample(n=50000, random_state=seed)
    else:
        X_train = X_all

    iso = IsolationForest(n_estimators=200, max_samples=2048, random_state=seed, n_jobs=1)
    iso.fit(X_train)
    return iso

def score(df_series: pd.DataFrame, calib_dict: dict, if_model: IsolationForest = None, cto_limits: dict = None, f5_corr_dict: dict = None, factory_id: str = None) -> pd.DataFrame:
    """
    Scores a series using empirical tail probabilities (-log10) and optional Isolation Forest model.
    """
    df_grid = prepare_series(df_series, factory_id=factory_id)
    stats = compute_check_statistics(df_grid, cto_limits=cto_limits, factory_id=factory_id)

    out_df = pd.DataFrame()
    out_df["timestamp"] = df_grid["timestamp"]
    out_df["parameter_id"] = df_grid["parameter_id"]

    vals = pd.to_numeric(df_grid["value"], errors="coerce") if not df_grid.empty else pd.Series(dtype=float)
    param = str(df_grid["parameter_id"].iloc[0]) if not df_grid.empty else ""
    is_flow = ("flow" in param.lower())

    # A. F1 RUN-LEVEL SCORES for eps in {0, 1, 2} (quasi-flat variants)
    res_step = get_resolution_step(vals.values)
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

        # Missing readings stay NaN
        f1_scores[vals.isna()] = np.nan
        if is_flow:
            f1_scores[vals == 0.0] = 0.0

        out_df[f"F1_score_eps{eps}"] = f1_scores
        if eps == 0:
            out_df["F1_score"] = f1_scores

    # Legacy F1 Window-Range Scores (kept as legacy_F1_* and F1_range_w* for comparison and compatibility)
    for w in [16, 96, 288]:
        calib_arr = calib_dict.get(f"F1_range_w{w}", np.array([]))
        arr = stats.get(f"F1_range_w{w}", np.array([]))
        old_sc = score_tail_prob(calib_arr, arr, mode="low")
        out_df[f"legacy_F1_range_w{w}_score"] = old_sc
        out_df[f"F1_range_w{w}_score"] = old_sc

    for name, arr in stats.items():
        if name == "validity" or name.startswith("gap_frac") or name.startswith("F1_range"):
            if name == "validity" or name.startswith("gap_frac"):
                out_df[name] = arr
            continue

        calib_arr = calib_dict.get(name, np.array([]))

        if "F2" in name:
            out_df[name + "_score"] = score_tail_prob(calib_arr, arr, mode="low")
        elif "F3" in name:
            out_df[name + "_score"] = score_tail_prob(calib_arr, arr, mode="high")
        elif "F6" in name:
            out_df[name + "_score"] = score_tail_prob(calib_arr, arr, mode="two_sided")
        else:
            out_df[name + "_score"] = score_tail_prob(calib_arr, arr, mode="high")

    # F5 Correlation score if provided
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

    # Isolation Forest Score
    model_to_use = if_model if if_model is not None else calib_dict.get("if_self_model")
    if model_to_use is not None:
        feats = extract_if_features(df_grid)
        valid_idx = feats.dropna().index
        if_raw_sc = np.full(len(df_grid), np.nan)
        if len(valid_idx) > 0:
            if_raw_sc[valid_idx] = -model_to_use.decision_function(feats.loc[valid_idx])

        calib_if = calib_dict.get("if_raw_score", np.array([]))
        out_df["if_score"] = score_tail_prob(calib_if, if_raw_sc, mode="high")
    else:
        out_df["if_score"] = np.nan

    return out_df
