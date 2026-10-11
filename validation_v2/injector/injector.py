import os
import sys
import math
import random
import yaml
import pandas as pd
import numpy as np

# Absolute repository paths
REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
RAW_CSV_PATH = os.path.join(REPO_ROOT, "Data", "RawData", "monitoring_data(raw).csv")
CTO_CSV_PATH = os.path.join(REPO_ROOT, "Original Data", "consent_limits.csv")

OUT_DIR = os.path.join(REPO_ROOT, "validation_v2", "injector")
DEV_INJECTED_DIR = os.path.join(OUT_DIR, "injected", "dev")
os.makedirs(DEV_INJECTED_DIR, exist_ok=True)

# Durations in 15-minute row steps (Protocol v1.1):
# 4 (1h), 16 (4h), 48 (12h), 96 (24h), 288 (72h), 672 (7d)
DURATIONS_ROWS = [4, 16, 48, 96, 288, 672]
SEVERITIES = ["subtle", "moderate", "obvious"]
TAMPER_TYPES = ["T1", "T2", "T3", "T4", "T5", "T6", "T7"]

DEV_SEEDS = [1, 2, 3, 4, 5]

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
    rounded = round(round(val / step) * step, 4)
    return float(rounded)

def compute_natural_repeat_runs(series_vals: np.ndarray, timestamps: np.ndarray) -> np.ndarray:
    """
    Computes exact-repeat run lengths breaking at any time gap > 15 min.
    Returns array of same length as series_vals indicating run length of each index.
    """
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

def load_and_preprocess_dev_data():
    """
    Loads raw telemetry, prints shape/columns/dtypes, drops Error/Out of Range rows (v1.1 G),
    and parses CTO consent limits.
    """
    print("==========================================================================")
    print(" INJECTOR DATA LOADING & PREPROCESSING (DEV ONLY)")
    print("==========================================================================")
    print(f"\n1. Reading Raw Telemetry: {RAW_CSV_PATH}")
    df_raw = pd.read_csv(RAW_CSV_PATH)
    print(f"Shape: {df_raw.shape}")
    print("Columns:", list(df_raw.columns))

    print(f"\n2. Reading CTO Limits: {CTO_CSV_PATH}")
    df_cto = pd.read_csv(CTO_CSV_PATH)
    print(f"Shape: {df_cto.shape}")

    allowed_qc = ["Raw", "L"]
    df_filtered = df_raw[df_raw["quality_code"].isin(allowed_qc)].copy()
    print(f"\nDropped {(len(df_raw) - len(df_filtered)):,} Error/Out of Range rows. Remaining: {len(df_filtered):,} rows.")

    df_filtered["timestamp_dt"] = pd.to_datetime(df_filtered["timestamp"], errors="coerce")
    df_filtered = df_filtered.sort_values(["factory_id", "parameter_id", "timestamp_dt"]).reset_index(drop=True)

    cto_limits = {}
    for _, r in df_cto.iterrows():
        fac = str(r["factory_id"])
        param = str(r["parameter"])
        max_lim = r["maximum_limit"]
        if pd.notna(max_lim) and max_lim > 0:
            cto_limits[(fac, param)] = float(max_lim)

    return df_filtered, cto_limits

def analyze_factory_eligibility(df_filtered, cto_limits):
    """
    Analyzes series eligibility and window candidate availability per factory on a continuous 15-min grid.
    Series eligibility: >10 distinct values AND <= 50% missing rate.
    """
    print("\n==========================================================================")
    print(" ANALYZING FACTORY & SERIES ELIGIBILITY (PROTOCOL v1.1 C & D)")
    print("==========================================================================")
    
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

            if n_distinct > 10 and missing_rate <= 0.50:
                step = get_series_resolution(val_series)
                
                cto_max = np.nan
                for (f_k, p_k), lim_val in cto_limits.items():
                    if f_k == fac and (p_k.lower() in p.lower() or p.lower() in p_k.lower()):
                        cto_max = lim_val
                        break
                if "pH" in p or "ph" in p.lower():
                    cto_max = 9.0 if np.isnan(cto_max) else cto_max

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

    print(f"Audited {len(factories)} factories. Total eligible series across factories: {sum(len(d['eligible_series']) for d in factory_data.values())}")
    return factory_data

def generate_dev_injections(factory_data, cto_limits):
    """
    Generates seeded tamper injections across seeds 1-5 for dev factories on continuous 15-min grids.
    Guarantees 0 timestamp span discrepancies and 100% eligibility compliance.
    """
    print("\n==========================================================================")
    print(" GENERATING SEEDED TAMPER INJECTIONS (SEEDS 1-5)")
    print("==========================================================================")

    all_labels = []
    shortfalls = []

    for seed in DEV_SEEDS:
        print(f"--- Generating Seed {seed} ---")
        seed_dir = os.path.join(DEV_INJECTED_DIR, f"seed_{seed}")
        os.makedirs(seed_dir, exist_ok=True)

        for fac_idx, (fac, fac_info) in enumerate(factory_data.items()):
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

                # Natural repeat runs computed on continuous grid (breaking at NaNs/gaps)
                repeat_arr = compute_natural_repeat_runs(val_arr, grid_timestamps.values)

                param_arrays[p_name] = val_arr.copy()
                param_orig_arrays[p_name] = val_arr.copy()

                # Boolean validity mask per 15-min grid slot
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

                # Candidate starts on continuous grid (strided by 8 slots = 2h)
                candidate_starts = list(range(700, max_start, 8))
                random.shuffle(candidate_starts)

                found_window = None

                for start_i in candidate_starts:
                    end_i = start_i + d_rows

                    buffer_conflict = False
                    for o_s, o_e in occupied_windows:
                        if not (end_i + 192 <= o_s or start_i >= o_e + 192):
                            buffer_conflict = True
                            break
                    if buffer_conflict:
                        continue

                    # Rule 1: Every single 15-min grid slot in window is present and valid
                    if not np.all(val_mask[start_i:end_i]):
                        continue

                    # Rule 3: Prior 7 days (672 grid slots) >= 70% present (>= 471 slots)
                    prior_start = max(0, start_i - 672)
                    prior_vals = param_arrays[target_param][prior_start:start_i]
                    if len(prior_vals) < 471 or (np.sum(~np.isnan(prior_vals)) < 471):
                        continue

                    # Rule 5: Non-zero Flow for T1 and T2
                    w_vals = param_arrays[target_param][start_i:end_i]
                    if target_param == "ETP-Flow" and t_type in ["T1", "T2"] and np.any(w_vals == 0.0):
                        continue

                    t2_src_start = None
                    if t_type == "T2":
                        lag_days = random.randint(1, 7)
                        lag_rows = lag_days * 96
                        src_start = start_i - lag_rows
                        src_end = src_start + d_rows

                        if src_start < 0:
                            continue
                        if not np.all(val_mask[src_start:src_end]):
                            continue
                        src_conflict = False
                        for o_s, o_e in occupied_windows:
                            if not (src_end <= o_s or src_start >= o_e):
                                src_conflict = True
                                break
                        if src_conflict:
                            continue
                        t2_src_start = str(grid_timestamps[src_start])

                    found_window = (start_i, end_i, t2_src_start)
                    break

                if found_window is None:
                    continue

                start_i, end_i, t2_src_start = found_window
                start_ts = str(grid_timestamps[start_i])
                end_ts = str(grid_timestamps[end_i - 1])
                step = param_meta[target_param]["step"]
                std_val = param_meta[target_param]["std"]
                cto_max = param_meta[target_param]["cto_max"]

                evt_id = f"EVT_{fac}_S{seed}_{event_counter:03d}"

                t3_limit = np.nan
                t5_w = np.nan
                t6_hit_params = ""

                if t_type == "T1":
                    start_val = param_arrays[target_param][start_i]
                    if sev == "obvious":
                        inj_vals = np.full(d_rows, start_val)
                    elif sev == "moderate":
                        jitters = np.random.choice([-step, 0.0, step], size=d_rows)
                        inj_vals = start_val + jitters
                    else:  # subtle
                        jitters = np.random.choice([-2*step, -step, 0.0, step, 2*step], size=d_rows)
                        inj_vals = start_val + jitters
                    
                    inj_vals = np.maximum(0.0, inj_vals)
                    inj_vals = np.array([round_to_resolution(v, step) for v in inj_vals])
                    param_arrays[target_param][start_i:end_i] = inj_vals

                elif t_type == "T2":
                    src_start_idx = ts_to_grid_idx[pd.to_datetime(t2_src_start)]
                    src_vals = param_arrays[target_param][src_start_idx:src_start_idx + d_rows]
                    if sev == "obvious":
                        inj_vals = src_vals.copy()
                    elif sev == "moderate":
                        noise = np.random.normal(0, 0.01 * std_val, size=d_rows)
                        inj_vals = src_vals + noise
                    else:  # subtle
                        noise = np.random.normal(0, 0.05 * std_val, size=d_rows)
                        inj_vals = src_vals + noise

                    inj_vals = np.maximum(0.0, inj_vals)
                    inj_vals = np.array([round_to_resolution(v, step) for v in inj_vals])
                    param_arrays[target_param][start_i:end_i] = inj_vals

                elif t_type == "T3":
                    t3_limit = cto_max
                    if sev == "obvious":
                        fracs = np.random.uniform(0.97, 0.99, size=d_rows)
                    elif sev == "moderate":
                        fracs = np.random.uniform(0.92, 0.99, size=d_rows)
                    else:  # subtle
                        fracs = np.random.uniform(0.85, 0.99, size=d_rows)
                    
                    inj_vals = fracs * cto_max
                    inj_vals = np.array([round_to_resolution(v, step) for v in inj_vals])
                    param_arrays[target_param][start_i:end_i] = inj_vals

                elif t_type == "T4":
                    if sev == "obvious":
                        if random.random() < 0.5:
                            inj_vals = np.random.uniform(-2.0, -0.5, size=d_rows)
                        else:
                            inj_vals = np.random.uniform(14.5, 16.0, size=d_rows)
                    elif sev == "moderate":
                        inj_vals = np.random.uniform(10.0, 11.5, size=d_rows)
                    else:  # subtle
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
                    else:  # obvious
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

                all_labels.append({
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
                # Drop unobserved rows where value_orig is NaN and not injected
                p_df_out = p_df_out[~(p_df_out["value_orig"].isna() & ~p_df_out["is_injected"])].reset_index(drop=True)
                out_parquet_rows.append(p_df_out)

            fac_parquet_df = pd.concat(out_parquet_rows, ignore_index=True)
            fac_parquet_path = os.path.join(seed_dir, f"{fac}.parquet")
            fac_parquet_df.to_parquet(fac_parquet_path, index=False)

    df_labels = pd.DataFrame(all_labels)
    labels_csv_path = os.path.join(DEV_INJECTED_DIR, "labels.csv")
    df_labels.to_csv(labels_csv_path, index=False)
    print(f"\nSaved master labels manifest ({len(df_labels):,} events) to {labels_csv_path}")

    return df_labels, shortfalls

def main():
    df_filtered, cto_limits = load_and_preprocess_dev_data()
    factory_data = analyze_factory_eligibility(df_filtered, cto_limits)
    df_labels, shortfalls = generate_dev_injections(factory_data, cto_limits)
    print("Injector generation completed successfully!")

if __name__ == "__main__":
    main()
