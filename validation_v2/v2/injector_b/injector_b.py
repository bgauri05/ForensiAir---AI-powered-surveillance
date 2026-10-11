"""
ForensiAIR Mechanism B Injector (Dev Only)
Protocol v2.0 & Protocol v1.1 Section C (Eligibility)

Generates subtle/evasive tamper injections for Types T1, T2, T3, T7 across seeds 301-305.
- Dev only: monitoring_data(raw).csv with Error/Out of Range rows dropped.
- 15-minute continuous grid, missing stays NaN.
- Parsed upper consent limits from consent_limits.csv only (no defaults).
- Durations: 4, 16, 48, 96, 288, 672 rows.
- 48h spacing (192 grid slots) buffer between all occupied windows.
- Physical guards: rounded to series resolution step, non-negative, pH within 0-14.
- Outputs: injected_b/dev/seed_{s}/{factory}.parquet and labels_b.csv
"""

import os
import sys
import math
import random
import numpy as np
import pandas as pd

REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
RAW_CSV_PATH = os.path.join(REPO_ROOT, "Data", "RawData", "monitoring_data(raw).csv")
CTO_CSV_PATH = os.path.join(REPO_ROOT, "Original Data", "consent_limits.csv")

OUT_DIR = os.path.join(REPO_ROOT, "validation_v2", "v2", "injector_b")
DEV_INJECTED_DIR = os.path.join(OUT_DIR, "injected_b", "dev")
os.makedirs(DEV_INJECTED_DIR, exist_ok=True)

DURATIONS_ROWS = [4, 16, 48, 96, 288, 672]
SEVERITIES = ["subtle", "moderate", "obvious"]
TYPES = ["T1", "T2", "T3", "T7"]
SEEDS = [301, 302, 303, 304, 305]

VARIANTS_BY_TYPE = {
    "T1": ["T1-B-freeze"],
    "T2": ["T2-B-scaled", "T2-B-splice"],
    "T3": ["T3-B-ar1", "T3-B-pull"],
    "T7": ["T7-B-step", "T7-B-tri"]
}

def get_series_resolution(values_series: pd.Series) -> float:
    """Computes smallest non-zero step |v[i] - v[i-1]| > 0 for a series."""
    vals = values_series.dropna().values
    if len(vals) < 2:
        return 0.01
    diffs = np.abs(np.diff(vals))
    nonzero_diffs = diffs[diffs > 1e-6]
    if len(nonzero_diffs) > 0:
        step = float(np.min(nonzero_diffs))
        return round(step, 4)
    return 0.01

def round_to_resolution(val: float, step: float) -> float:
    """Rounds numeric value to series resolution step."""
    if pd.isna(val):
        return np.nan
    if step <= 0:
        step = 0.01
    return float(round(round(val / step) * step, 4))

def compute_natural_repeat_runs(series_vals: np.ndarray, timestamps: np.ndarray) -> np.ndarray:
    """Computes exact-repeat run lengths breaking at any time gap > 15 min or NaN."""
    n = len(series_vals)
    if n == 0:
        return np.array([], dtype=int)

    is_change = np.ones(n, dtype=bool)
    if n > 1:
        val_changed = (series_vals[1:] != series_vals[:-1]) | (pd.isna(series_vals[1:]) != pd.isna(series_vals[:-1])) | (pd.isna(series_vals[1:]) & pd.isna(series_vals[:-1]))
        time_gapped = (timestamps[1:] - timestamps[:-1]) > np.timedelta64(15, 'm')
        is_change[1:] = val_changed | time_gapped

    change_indices = np.where(is_change)[0]
    run_lengths = np.diff(np.append(change_indices, n))

    row_run_lengths = np.zeros(n, dtype=int)
    for idx, r_len in zip(change_indices, run_lengths):
        row_run_lengths[idx:idx + r_len] = r_len
    return row_run_lengths

def match_param_cto(factory_id: str, param_id: str, cto_limits_df: pd.DataFrame) -> float:
    """Matches only parsed statutory upper consent limits from consent_limits.csv (no defaults)."""
    fac_df = cto_limits_df[cto_limits_df["factory_id"] == factory_id]
    if fac_df.empty:
        return np.nan
    param_clean = param_id.upper().replace("ETP-", "").replace("ETP_", "").strip()

    for _, r in fac_df.iterrows():
        p_raw = str(r["parameter"]).strip()
        p_upper = p_raw.upper()
        max_lim = r["maximum_limit"]
        if pd.isna(max_lim) or max_lim <= 0:
            continue

        if param_clean == "PH":
            if p_upper in ["PH", "PH VALUE"]:
                return float(max_lim)
        elif param_clean == "BOD":
            if "BOD" in p_upper:
                return float(max_lim)
        elif param_clean == "COD":
            if "COD" in p_upper:
                return float(max_lim)
        elif param_clean == "TSS":
            if any(term in p_upper for term in ["TSS", "SUSPENDED SOLID", "SUSPENDED SOLIDS"]):
                return float(max_lim)
        elif param_clean == "FLOW":
            if any(term in p_upper for term in ["FLOW", "TRADE EFFLUENT", "EFFLUENT"]):
                return float(max_lim)
    return np.nan

def load_and_preprocess_dev_data():
    """Loads raw telemetry, drops Error/Out of Range rows, and parses true consent limits."""
    print("==========================================================================")
    print(" MECHANISM B INJECTOR: DATA LOADING & PREPROCESSING (DEV ONLY)")
    print("==========================================================================")
    df_raw = pd.read_csv(RAW_CSV_PATH)
    df_cto = pd.read_csv(CTO_CSV_PATH)

    allowed_qc = ["Raw", "L"]
    df_filtered = df_raw[df_raw["quality_code"].isin(allowed_qc)].copy()
    print(f"Loaded raw data. Dropped {(len(df_raw) - len(df_filtered)):,} Error rows. Kept {len(df_filtered):,} clean rows.")

    df_filtered["timestamp_dt"] = pd.to_datetime(df_filtered["timestamp"], errors="coerce")
    df_filtered = df_filtered.sort_values(["factory_id", "parameter_id", "timestamp_dt"]).reset_index(drop=True)

    return df_filtered, df_cto

def analyze_factory_eligibility(df_filtered, df_cto):
    """Analyzes series eligibility and parsed CTO limits per factory."""
    factories = sorted(df_filtered["factory_id"].unique())
    factory_data = {}

    for fac in factories:
        fac_df = df_filtered[df_filtered["factory_id"] == fac].copy()
        params = sorted(fac_df["parameter_id"].unique())
        eligible_series = {}

        for p in params:
            p_df = fac_df[fac_df["parameter_id"] == p].sort_values("timestamp_dt").reset_index(drop=True)
            n_rows = len(p_df)
            val_series = p_df["value"]
            n_distinct = val_series.nunique(dropna=True)

            ts_min = p_df["timestamp_dt"].min()
            ts_max = p_df["timestamp_dt"].max()
            exp_15m = int((ts_max - ts_min) / pd.Timedelta(minutes=15)) + 1 if pd.notna(ts_min) else n_rows
            missing_rate = float((exp_15m - n_rows) / exp_15m) if exp_15m > 0 else 0.0

            # Protocol v1.1 Sec C: >10 distinct values and <= 50% missingness
            if n_distinct > 10 and missing_rate <= 0.50:
                step = get_series_resolution(val_series)
                cto_max = match_param_cto(fac, p, df_cto)

                eligible_series[p] = {
                    "p_df": p_df,
                    "n_rows": n_rows,
                    "resolution_step": step,
                    "cto_max_limit": cto_max,
                    "std": float(val_series.std()) if len(val_series) > 1 else 1.0
                }

        factory_data[fac] = {
            "fac_df": fac_df,
            "eligible_series": eligible_series
        }

    return factory_data

def generate_mechanism_b_injections(factory_data):
    """
    Generates Mechanism B tamper injections across seeds 301-305.
    Types: T1, T2, T3, T7.
    Variants alternate evenly within their type.
    Balanced sampling across (variant, strength, duration).
    """
    print("\n==========================================================================")
    print(" GENERATING MECHANISM B TAMPER INJECTIONS (SEEDS 301-305)")
    print("==========================================================================")

    all_labels = []
    shortfalls = []

    for seed in SEEDS:
        print(f"--- Generating Seed {seed} ---")
        seed_dir = os.path.join(DEV_INJECTED_DIR, f"seed_{seed}")
        os.makedirs(seed_dir, exist_ok=True)

        for fac_idx, (fac, fac_info) in enumerate(factory_data.items()):
            rng_seed = seed * 10000 + fac_idx * 100 + 42
            rng = np.random.default_rng(rng_seed)
            py_rng = random.Random(rng_seed)

            el_series = fac_info["eligible_series"]
            if not el_series:
                shortfalls.append({
                    "seed": seed, "factory_id": fac, "target": 30, "placed": 0,
                    "reason": "No eligible series"
                })
                continue

            fac_df = fac_info["fac_df"].sort_values("timestamp_dt")
            ts_min = fac_df["timestamp_dt"].min()
            ts_max = fac_df["timestamp_dt"].max()

            # Continuous 15-minute datetime grid
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

                is_valid = ~np.isnan(val_arr) & np.isin(qc_arr, ["Raw", "L"]) & (repeat_arr < 8)
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

            # Check which types are eligible for this factory
            has_t3 = any(pd.notna(meta["cto_max"]) and meta["cto_max"] > 0 for meta in param_meta.values())
            has_non_flow = any(p != "ETP-Flow" for p in param_meta.keys())

            eligible_types = ["T1", "T2"]
            if has_t3:
                eligible_types.append("T3")
            if has_non_flow:
                eligible_types.append("T7")
            elif "ETP-Flow" in param_meta:
                eligible_types.append("T7")

            # Build balanced plan of up to 60 candidate slots to draw 30 events
            variant_iter = {
                "T1": 0,
                "T2": 0,
                "T3": 0,
                "T7": 0
            }
            plan_slots = []
            dur_cycle = list(DURATIONS_ROWS)
            sev_cycle = list(SEVERITIES)
            py_rng.shuffle(dur_cycle)
            py_rng.shuffle(sev_cycle)

            slot_idx = 0
            while len(plan_slots) < 120:
                t_type = eligible_types[slot_idx % len(eligible_types)]
                v_list = VARIANTS_BY_TYPE[t_type]
                v_name = v_list[variant_iter[t_type] % len(v_list)]
                variant_iter[t_type] += 1

                sev = sev_cycle[slot_idx % len(sev_cycle)]
                dur = dur_cycle[slot_idx % len(dur_cycle)]
                plan_slots.append((t_type, v_name, sev, dur))
                slot_idx += 1

            py_rng.shuffle(plan_slots)

            events_placed = 0
            event_counter = 1

            for t_type, v_name, sev, d_rows in plan_slots:
                if events_placed >= 30:
                    break

                applicable_params = []
                for p_name in param_meta.keys():
                    if t_type in ["T1", "T2"]:
                        applicable_params.append(p_name)
                    elif t_type == "T3" and pd.notna(param_meta[p_name]["cto_max"]) and param_meta[p_name]["cto_max"] > 0:
                        applicable_params.append(p_name)
                    elif t_type == "T7":
                        if p_name != "ETP-Flow" or len(param_meta) == 1:
                            applicable_params.append(p_name)

                if not applicable_params:
                    continue

                target_param = py_rng.choice(applicable_params)
                val_mask = param_valid_mask[target_param]
                step = param_meta[target_param]["step"]
                series_std = param_meta[target_param]["std"]
                cto_max = param_meta[target_param]["cto_max"]
                is_flow = ("flow" in target_param.lower())

                max_start = n_grid - d_rows
                if max_start <= 700:
                    continue

                candidate_starts = list(range(700, max_start, 8))
                py_rng.shuffle(candidate_starts)

                found_window = None

                for start_i in candidate_starts:
                    end_i = start_i + d_rows

                    # 48h spacing (192 grid slots) buffer between all occupied event windows
                    buffer_conflict = False
                    for o_s, o_e in occupied_windows:
                        if not (end_i + 192 <= o_s or start_i >= o_e + 192):
                            buffer_conflict = True
                            break
                    if buffer_conflict:
                        continue

                    # Rule 1: Every 15-min slot in window is present and valid
                    if not np.all(val_mask[start_i:end_i]):
                        continue

                    # Rule 3: Prior 7 days (672 grid slots) >= 70% present (>= 471 slots)
                    prior_start = max(0, start_i - 672)
                    prior_vals = param_arrays[target_param][prior_start:start_i]
                    if len(prior_vals) < 471 or (np.sum(~np.isnan(prior_vals)) < 471):
                        continue

                    # Rule 5: Non-zero Flow for T1 and T2
                    w_vals = param_arrays[target_param][start_i:end_i]
                    if is_flow and t_type in ["T1", "T2"] and np.any(w_vals == 0.0):
                        continue

                    # Specific checks for T2 donors
                    donor_info = None
                    if v_name == "T2-B-scaled":
                        # Donor lag in 1-7 days (96 to 672 rows)
                        lag_days = py_rng.randint(1, 7)
                        lag_rows = lag_days * 96
                        src_start = start_i - lag_rows
                        src_end = src_start + d_rows
                        if src_start < 0:
                            continue
                        if not np.all(val_mask[src_start:src_end]):
                            continue
                        if is_flow and np.any(param_arrays[target_param][src_start:src_end] == 0.0):
                            continue
                        src_conflict = False
                        for o_s, o_e in occupied_windows:
                            if not (src_end <= o_s or src_start >= o_e):
                                src_conflict = True
                                break
                        if src_conflict:
                            continue
                        donor_info = {"type": "scaled", "src_start": src_start, "src_end": src_end, "lag_rows": lag_rows}

                    elif v_name == "T2-B-splice":
                        d1 = d_rows // 2
                        d2 = d_rows - d1
                        # Donor 1 from lag 1-7 days (96 to 672 rows)
                        lag1_days = py_rng.randint(1, 7)
                        lag1_rows = lag1_days * 96
                        src1_s = start_i - lag1_rows
                        src1_e = src1_s + d1
                        if src1_s < 0 or not np.all(val_mask[src1_s:src1_e]):
                            continue
                        if is_flow and np.any(param_arrays[target_param][src1_s:src1_e] == 0.0):
                            continue

                        # Donor 2 from lag 1-7 days (96 to 672 rows)
                        lag2_days = py_rng.randint(1, 7)
                        lag2_rows = lag2_days * 96
                        src2_s = start_i - lag2_rows + d1
                        src2_e = src2_s + d2
                        if src2_s < 0 or not np.all(val_mask[src2_s:src2_e]):
                            continue
                        if is_flow and np.any(param_arrays[target_param][src2_s:src2_e] == 0.0):
                            continue

                        src_conflict = False
                        for o_s, o_e in occupied_windows:
                            if not (src1_e <= o_s or src1_s >= o_e) or not (src2_e <= o_s or src2_s >= o_e):
                                src_conflict = True
                                break
                        if src_conflict:
                            continue
                        donor_info = {"type": "splice", "src1": (src1_s, src1_e), "src2": (src2_s, src2_e), "lags": f"{lag1_rows},{lag2_rows}"}

                    found_window = (start_i, end_i, donor_info)
                    break

                if found_window is None:
                    continue

                start_i, end_i, donor_info = found_window
                start_ts = str(grid_timestamps[start_i])
                end_ts = str(grid_timestamps[end_i - 1])
                orig_vals = param_arrays[target_param][start_i:end_i].copy()

                # Generate Injected Values based on Mechanism B Variant
                extras = {
                    "lag_rows": "", "scale": np.nan, "lam": np.nan, "c": np.nan,
                    "sign": np.nan, "limit_used": np.nan, "noise_pct": np.nan, "p_flicker": np.nan
                }

                if v_name == "T1-B-freeze":
                    # Lookback median of prior 672 rows
                    p_start = max(0, start_i - 672)
                    p_vals = param_arrays[target_param][p_start:start_i]
                    v_prior = p_vals[~np.isnan(p_vals)]
                    if is_flow:
                        nz = v_prior[v_prior > 0]
                        med_val = float(np.median(nz)) if len(nz) > 0 else float(np.median(v_prior))
                    else:
                        med_val = float(np.median(v_prior))
                    med_val = round_to_resolution(med_val, step)

                    p_flicker = 0.15 if sev == "subtle" else (0.05 if sev == "moderate" else 0.0)
                    extras["p_flicker"] = p_flicker

                    injected_arr = np.full(d_rows, med_val, dtype=float)
                    if p_flicker > 0:
                        f_mask = rng.uniform(0, 1, size=d_rows) < p_flicker
                        f_dirs = rng.choice([-1.0, 1.0], size=d_rows)
                        injected_arr[f_mask] += f_dirs[f_mask] * step

                elif v_name == "T2-B-scaled":
                    src_s = donor_info["src_start"]
                    src_e = donor_info["src_end"]
                    extras["lag_rows"] = str(donor_info["lag_rows"])
                    donor_vals = param_arrays[target_param][src_s:src_e]

                    if sev == "subtle":
                        delta = float(rng.uniform(0.05, 0.10))
                        s_mult = 1.0 + float(rng.choice([-1.0, 1.0])) * delta
                    elif sev == "moderate":
                        delta = float(rng.uniform(0.01, 0.05))
                        s_mult = 1.0 + float(rng.choice([-1.0, 1.0])) * delta
                    else:
                        s_mult = 1.00
                    extras["scale"] = round(s_mult, 4)
                    injected_arr = donor_vals * s_mult

                elif v_name == "T2-B-splice":
                    src1_s, src1_e = donor_info["src1"]
                    src2_s, src2_e = donor_info["src2"]
                    extras["lag_rows"] = donor_info["lags"]
                    spliced = np.concatenate([
                        param_arrays[target_param][src1_s:src1_e],
                        param_arrays[target_param][src2_s:src2_e]
                    ])
                    noise_pct = 0.05 if sev == "subtle" else (0.01 if sev == "moderate" else 0.0)
                    extras["noise_pct"] = noise_pct
                    if noise_pct > 0:
                        noise = rng.normal(0.0, noise_pct * series_std, size=d_rows)
                        injected_arr = spliced + noise
                    else:
                        injected_arr = spliced.copy()

                elif v_name == "T3-B-ar1":
                    extras["limit_used"] = float(cto_max)
                    if sev == "subtle":
                        c_val = float(rng.uniform(0.85, 0.92))
                    elif sev == "moderate":
                        c_val = float(rng.uniform(0.90, 0.96))
                    else:
                        c_val = float(rng.uniform(0.96, 0.99))
                    extras["c"] = round(c_val, 4)

                    mu_lvl = c_val * cto_max
                    ar_arr = np.zeros(d_rows, dtype=float)
                    ar_arr[0] = mu_lvl + float(rng.normal(0.0, 0.01 * cto_max))
                    for t_idx in range(1, d_rows):
                        ar_arr[t_idx] = mu_lvl + 0.90 * (ar_arr[t_idx - 1] - mu_lvl) + float(rng.normal(0.0, 0.01 * cto_max))
                    injected_arr = ar_arr

                elif v_name == "T3-B-pull":
                    extras["limit_used"] = float(cto_max)
                    lam_val = 0.30 if sev == "subtle" else (0.60 if sev == "moderate" else 0.90)
                    extras["lam"] = lam_val
                    injected_arr = orig_vals + lam_val * (0.95 * cto_max - orig_vals)

                elif v_name == "T7-B-step":
                    s_amp = 0.15 if sev == "subtle" else (0.30 if sev == "moderate" else 0.50)
                    sign_val = float(rng.choice([-1.0, 1.0]))
                    extras["scale"] = s_amp
                    extras["sign"] = int(sign_val)

                    t_seq = np.arange(d_rows, dtype=float)
                    tau = d_rows / 3.0
                    mult_step = 1.0 + sign_val * s_amp * np.exp(-t_seq / tau)
                    injected_arr = orig_vals * mult_step

                elif v_name == "T7-B-tri":
                    s_amp = 0.15 if sev == "subtle" else (0.30 if sev == "moderate" else 0.50)
                    sign_val = float(rng.choice([-1.0, 1.0]))
                    extras["scale"] = s_amp
                    extras["sign"] = int(sign_val)

                    t_seq = np.arange(d_rows, dtype=float)
                    tri_wave = 1.0 - np.abs(2.0 * t_seq - (d_rows - 1)) / max(d_rows - 1, 1)
                    mult_tri = 1.0 + sign_val * s_amp * tri_wave
                    injected_arr = orig_vals * mult_tri

                # Boundary clamps & resolution rounding
                injected_arr = np.maximum(0.0, injected_arr)
                if "ph" in target_param.lower():
                    injected_arr = np.clip(injected_arr, 0.0, 14.0)
                final_injected = np.array([round_to_resolution(v, step) for v in injected_arr])

                # Compute differing rows and no-op metrics
                diff_mask = (final_injected != orig_vals)
                n_rows_changed = int(np.sum(diff_mask))
                changed_share = float(n_rows_changed / d_rows)
                max_abs_change = float(np.max(np.abs(final_injected - orig_vals)))
                no_op = bool(changed_share < 0.50)

                # Apply injection
                evt_id = f"EVT_B_{fac}_S{seed}_{event_counter:03d}_{t_type}_{sev}_{d_rows}r"
                param_arrays[target_param][start_i:end_i] = final_injected
                is_inj_arrays[target_param][start_i:end_i] = True
                evt_id_arrays[target_param][start_i:end_i] = evt_id

                occupied_windows.append((start_i, end_i))
                events_placed += 1
                event_counter += 1

                all_labels.append({
                    "event_id": evt_id,
                    "factory_id": fac,
                    "seed": seed,
                    "type": t_type,
                    "variant": v_name,
                    "severity": sev,
                    "duration_rows": d_rows,
                    "start_ts": start_ts,
                    "end_ts": end_ts,
                    "parameter": target_param,
                    "lag_rows": extras["lag_rows"],
                    "scale": extras["scale"],
                    "lam": extras["lam"],
                    "c": extras["c"],
                    "sign": extras["sign"],
                    "limit_used": extras["limit_used"],
                    "noise_pct": extras["noise_pct"],
                    "p_flicker": extras["p_flicker"],
                    "n_rows_changed": n_rows_changed,
                    "changed_share": round(changed_share, 4),
                    "max_abs_change": round(max_abs_change, 4),
                    "no_op": no_op,
                    "start_dt": pd.to_datetime(start_ts),
                    "end_dt": pd.to_datetime(end_ts)
                })

            if events_placed < 30:
                shortfalls.append({
                    "seed": seed, "factory_id": fac, "target": 30, "placed": events_placed,
                    "reason": "Insufficient eligible continuous 15m windows with 48h spacing"
                })

            # Save Factory Parquet
            out_parquet_rows = []
            for p_name in sorted(param_arrays.keys()):
                p_df_out = pd.DataFrame({
                    "timestamp": grid_timestamps,
                    "parameter_id": p_name,
                    "value": param_arrays[p_name],
                    "value_orig": param_orig_arrays[p_name],
                    "is_injected": is_inj_arrays[p_name],
                    "event_id": evt_id_arrays[p_name]
                })
                # Retain all grid rows where either value is observed or value_orig is observed
                # Drop only rows where both value_orig and value are NaN (unobserved missing grid points)
                p_df_out = p_df_out[~(p_df_out["value_orig"].isna() & ~p_df_out["is_injected"])].reset_index(drop=True)
                out_parquet_rows.append(p_df_out)

            fac_parquet_df = pd.concat(out_parquet_rows, ignore_index=True)
            fac_parquet_path = os.path.join(seed_dir, f"{fac}.parquet")
            fac_parquet_df.to_parquet(fac_parquet_path, index=False)

    df_labels = pd.DataFrame(all_labels)
    labels_csv_path = os.path.join(OUT_DIR, "labels_b.csv")
    df_labels.to_csv(labels_csv_path, index=False)
    print(f"\nSaved master Mechanism B labels manifest ({len(df_labels):,} events) to {labels_csv_path}")

    return df_labels, shortfalls

def main():
    df_filtered, df_cto = load_and_preprocess_dev_data()
    factory_data = analyze_factory_eligibility(df_filtered, df_cto)
    df_labels, shortfalls = generate_mechanism_b_injections(factory_data)
    print(f"\nCompleted Mechanism B Generation:")
    print(f"Total events placed: {len(df_labels)}")
    print(f"Total shortfalls logged: {len(shortfalls)}")
    for sf in shortfalls:
        print(f"  Shortfall: Seed {sf['seed']}, {sf['factory_id']}: {sf['placed']}/{sf['target']} ({sf['reason']})")

if __name__ == "__main__":
    main()
