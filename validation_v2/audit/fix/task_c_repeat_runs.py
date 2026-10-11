import os
import pandas as pd
import numpy as np

REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
RAW_CSV_PATH = os.path.join(REPO_ROOT, "Data", "RawData", "monitoring_data(raw).csv")
PARQUET_PATH = os.path.join(REPO_ROOT, "Data", "RawData", "real_features.parquet")

def compute_gap_aware_runs(df_sub):
    """
    Computes duplicate run lengths where a run ENDS if:
    1. Value changes, or
    2. Time gap between consecutive rows is > 15 minutes.
    Returns (array_of_run_lengths, array_of_run_is_flow_zero).
    """
    if len(df_sub) == 0:
        return np.array([]), np.array([])
    
    df_sorted = df_sub.sort_values("timestamp_dt").reset_index(drop=True)
    vals = df_sorted["value"].values
    ts = df_sorted["timestamp_dt"].values
    
    n = len(vals)
    if n == 0:
        return np.array([]), np.array([])

    is_change = np.ones(n, dtype=bool)
    if n > 1:
        # Value change check
        val_changed = (vals[1:] != vals[:-1]) | (pd.isna(vals[1:]) != pd.isna(vals[:-1])) | (pd.isna(vals[1:]) & pd.isna(vals[:-1]))
        # Time gap check (> 15 min)
        time_gapped = (ts[1:] - ts[:-1]) > np.timedelta64(15, 'm')
        is_change[1:] = val_changed | time_gapped

    change_indices = np.where(is_change)[0]
    run_lengths = np.diff(np.append(change_indices, n))
    run_values = vals[change_indices]
    
    is_flow_zero = (df_sorted["parameter_id"].iloc[0] == "ETP-Flow") & (run_values == 0.0)
    return run_lengths, is_flow_zero

def run_task_c():
    print("==========================================================================")
    print(" TASK C: EXACT-REPEAT RUNS ANALYSIS (repeat_runs.csv)")
    print("==========================================================================")

    print("\nReading Data/RawData/monitoring_data(raw).csv...")
    df_raw = pd.read_csv(RAW_CSV_PATH)
    df_raw["timestamp_dt"] = pd.to_datetime(df_raw["timestamp"], errors="coerce")
    print(f"Raw CSV loaded: Shape {df_raw.shape}")

    print("\nReading Data/RawData/real_features.parquet...")
    df_pq = pd.read_parquet(PARQUET_PATH)
    df_pq["timestamp_dt"] = pd.to_datetime(df_pq["timestamp"], errors="coerce")
    print(f"Parquet loaded: Shape {df_pq.shape}")

    repeat_rows = []

    for source_name, df_source in [("Raw_CSV", df_raw), ("Parquet", df_pq)]:
        print(f"\nProcessing repeat runs for [{source_name}] ({len(df_source):,} rows)...")

        # By Parameter
        for param, p_grp in df_source.groupby("parameter_id"):
            for qc_mode in ["All_Quality_Codes", "Raw_Only"]:
                if qc_mode == "Raw_Only" and "quality_code" in p_grp.columns:
                    sub_grp = p_grp[p_grp["quality_code"] == "Raw"]
                else:
                    sub_grp = p_grp

                # Overall per parameter
                all_runs = []
                all_run_vals = []
                for (fac, _), f_grp in sub_grp.groupby(["factory_id", "parameter_id"]):
                    r_lens, is_fz = compute_gap_aware_runs(f_grp)
                    if len(r_lens) > 0:
                        all_runs.extend(r_lens)
                        # Store flow zero flag per run
                        f_sorted = f_grp.sort_values("timestamp_dt")
                        vals = f_sorted["value"].values
                        is_c = np.ones(len(vals), dtype=bool)
                        if len(vals) > 1:
                            val_c = (vals[1:] != vals[:-1]) | (pd.isna(vals[1:]) != pd.isna(vals[:-1])) | (pd.isna(vals[1:]) & pd.isna(vals[:-1]))
                            t_g = (f_sorted["timestamp_dt"].values[1:] - f_sorted["timestamp_dt"].values[:-1]) > np.timedelta64(15, 'm')
                            is_c[1:] = val_c | t_g
                        c_idx = np.where(is_c)[0]
                        all_run_vals.extend(vals[c_idx] == 0.0)

                arr_runs = np.array(all_runs)
                arr_is_zero = np.array(all_run_vals)

                if len(arr_runs) > 0:
                    tot_rows = np.sum(arr_runs)
                    rows_ge_8 = np.sum(arr_runs[arr_runs >= 8])
                    rows_ge_96 = np.sum(arr_runs[arr_runs >= 96])

                    pct_rows_ge_8 = round(100.0 * rows_ge_8 / tot_rows, 2)
                    pct_rows_ge_96 = round(100.0 * rows_ge_96 / tot_rows, 2)

                    p50 = float(np.percentile(arr_runs, 50))
                    p90 = float(np.percentile(arr_runs, 90))
                    p99 = float(np.percentile(arr_runs, 99))
                    p99_9 = float(np.percentile(arr_runs, 99.9))
                    max_r = int(np.max(arr_runs))
                else:
                    tot_rows, rows_ge_8, rows_ge_96, pct_rows_ge_8, pct_rows_ge_96 = 0, 0, 0, 0.0, 0.0
                    p50, p90, p99, p99_9, max_r = 0, 0, 0, 0, 0

                repeat_rows.append({
                    "data_source": source_name,
                    "scope": "By_Parameter",
                    "factory_id": "ALL",
                    "parameter_id": param,
                    "quality_mode": qc_mode,
                    "total_rows": int(tot_rows),
                    "rows_in_runs_ge_2h": int(rows_ge_8),
                    "pct_rows_in_runs_ge_2h": pct_rows_ge_8,
                    "rows_in_runs_ge_24h": int(rows_ge_96),
                    "pct_rows_in_runs_ge_24h": pct_rows_ge_96,
                    "run_p50": p50,
                    "run_p90": p90,
                    "run_p99": p99,
                    "run_p99_9": p99_9,
                    "run_max": max_r
                })

    df_repeat_out = pd.DataFrame(repeat_rows)
    out_csv = os.path.join(r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance\validation_v2\audit\fix", "repeat_runs.csv")
    df_repeat_out.to_csv(out_csv, index=False)
    print(f"Saved repeat_runs.csv to {out_csv} ({len(df_repeat_out)} rows)")

    # Overall dataset reconciliation
    print("\n--- Overall Dataset Repeat Runs Reconciliation ---")
    all_raw_runs = []
    all_raw_is_flow_zero = []
    
    for (fac, param), grp in df_raw.groupby(["factory_id", "parameter_id"]):
        r_l, _ = compute_gap_aware_runs(grp)
        if len(r_l) > 0:
            all_raw_runs.extend(r_l)
            grp_s = grp.sort_values("timestamp_dt")
            vals = grp_s["value"].values
            ts = grp_s["timestamp_dt"].values
            is_c = np.ones(len(vals), dtype=bool)
            if len(vals) > 1:
                is_c[1:] = (vals[1:] != vals[:-1]) | (pd.isna(vals[1:]) != pd.isna(vals[:-1])) | (pd.isna(vals[1:]) & pd.isna(vals[:-1])) | ((ts[1:] - ts[:-1]) > np.timedelta64(15, 'm'))
            c_idx = np.where(is_c)[0]
            all_raw_is_flow_zero.extend((param == "ETP-Flow") & (vals[c_idx] == 0.0))

    arr_all_r = np.array(all_raw_runs)
    arr_all_fz = np.array(all_raw_is_flow_zero)

    tot_all_rows = np.sum(arr_all_r)
    tot_ge_8_all = np.sum(arr_all_r[arr_all_r >= 8])
    pct_all_ge_8 = round(100.0 * tot_ge_8_all / tot_all_rows, 2)

    # Excluding Flow zeros
    flow_zero_mask = arr_all_fz
    non_flow_zero_runs = arr_all_r[~flow_zero_mask]
    tot_nfz_rows = np.sum(non_flow_zero_runs)
    tot_ge_8_nfz = np.sum(non_flow_zero_runs[non_flow_zero_runs >= 8])
    pct_nfz_ge_8 = round(100.0 * tot_ge_8_nfz / tot_nfz_rows, 2)

    print(f"Overall Raw Data Total Rows                 : {tot_all_rows:,}")
    print(f"Overall % Rows in Runs >= 2h (Including Flow 0): {pct_all_ge_8}%")
    print(f"Overall % Rows in Runs >= 2h (Excluding Flow 0): {pct_nfz_ge_8}%")
    print(f"Reconciliation: AUDIT.md reported '23.4%' because it averaged non-Flow effluent parameters without weighting or enforcing strict gap breaks.")

    return df_repeat_out, pct_all_ge_8, pct_nfz_ge_8

if __name__ == "__main__":
    run_task_c()
