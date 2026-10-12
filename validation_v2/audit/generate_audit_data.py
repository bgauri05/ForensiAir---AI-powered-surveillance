import os
import sys
import sqlite3
import random
import pandas as pd
import numpy as np

REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
RAW_CSV_PATH = os.path.join(REPO_ROOT, "Data", "RawData", "monitoring_data(raw).csv")
PARQUET_PATH = os.path.join(REPO_ROOT, "Data", "RawData", "real_features.parquet")
DB_PATH = os.path.join(REPO_ROOT, "forensier.db")
CTO_CSV_PATH = os.path.join(REPO_ROOT, "Original Data", "consent_limits.csv")
MISSING_CSV_PATH = os.path.join(REPO_ROOT, "Original Data", "dataset_missing_summary.csv")

UNSEEN_DIR = r"c:\Users\gauri\Downloads\validation"
UNSEEN_FILES = {
    "Cipla": os.path.join(UNSEEN_DIR, "Cipla (1).csv"),
    "Glenmark": os.path.join(UNSEEN_DIR, "Glenmark (1).csv"),
    "Indoco": os.path.join(UNSEEN_DIR, "Indoco (1).csv"),
    "Zydus": os.path.join(UNSEEN_DIR, "Zydus (1).csv")
}

OUT_DIR = os.path.join(REPO_ROOT, "validation_v2", "audit")
os.makedirs(OUT_DIR, exist_ok=True)

def get_decimals(series):
    """Computes decimal places for numeric values represented as float or string."""
    def _count_dec(val):
        if pd.isna(val):
            return 0
        s = f"{val}".rstrip('0').rstrip('.')
        if '.' in s:
            return len(s.split('.')[1])
        return 0
    return max([_count_dec(v) for v in series.dropna().iloc[:1000]]) if len(series.dropna()) > 0 else 0

def compute_run_lengths(series):
    """Returns array of consecutive duplicate run lengths."""
    vals = series.values
    if len(vals) == 0:
        return np.array([])
    # Mask changes
    is_change = np.ones(len(vals), dtype=bool)
    is_change[1:] = (vals[1:] != vals[:-1]) | (pd.isna(vals[1:]) != pd.isna(vals[:-1])) | (pd.isna(vals[1:]) & pd.isna(vals[:-1]))
    change_indices = np.where(is_change)[0]
    run_lengths = np.diff(np.append(change_indices, len(vals)))
    return run_lengths

def audit_dev():
    print("\n==========================================================================")
    print(" 1. AUDITING 33 DEV FACTORIES FROM DATA/RAWDATA/MONITORING_DATA(RAW).CSV")
    print("==========================================================================")

    df_raw = pd.read_csv(RAW_CSV_PATH)
    df_raw["timestamp_dt"] = pd.to_datetime(df_raw["timestamp"], errors="coerce")
    
    # Load CTO limits
    df_cto = pd.read_csv(CTO_CSV_PATH)
    # Deduplicate CTO limits per factory_id and parameter
    cto_dict = {}
    for _, r in df_cto.iterrows():
        fac = str(r["factory_id"])
        param = str(r["parameter"])
        if (fac, param) not in cto_dict:
            cto_dict[(fac, param)] = (r["minimum_limit"], r["maximum_limit"])

    dev_audit_rows = []

    grouped = df_raw.groupby(["factory_id", "parameter_id"])
    print(f"Total (factory, parameter) pairs to audit: {len(grouped)}")

    for (fac, param), grp in grouped:
        grp = grp.sort_values("timestamp_dt").reset_index(drop=True)
        n_rows = len(grp)

        ts_min = grp["timestamp_dt"].min()
        ts_max = grp["timestamp_dt"].max()

        if pd.notna(ts_min) and pd.notna(ts_max):
            expected_15min_rows = int((ts_max - ts_min) / pd.Timedelta(minutes=15)) + 1
            time_diffs = grp["timestamp_dt"].diff()
            time_diff_hours = time_diffs / pd.Timedelta(hours=1)
            longest_gap_hours = float(time_diff_hours.max()) if len(time_diff_hours) > 1 else 0.0
            gap_count = int((time_diffs > pd.Timedelta(minutes=15)).sum())
            
            # Non-15min steps count
            non_15min_steps = int(((time_diffs.notna()) & (time_diffs != pd.Timedelta(minutes=15))).sum())
            out_of_order_count = int((time_diffs < pd.Timedelta(seconds=0)).sum())
        else:
            expected_15min_rows = n_rows
            longest_gap_hours = 0.0
            gap_count = 0
            non_15min_steps = 0
            out_of_order_count = 0

        pct_missing = round(100.0 * max(0, expected_15min_rows - n_rows) / expected_15min_rows, 2) if expected_15min_rows > 0 else 0.0

        # Monthly row count average
        grp["month"] = grp["timestamp_dt"].dt.to_period("M")
        rows_per_month = round(float(grp.groupby("month").size().mean()), 1)

        # Duplicate timestamps
        duplicate_ts = int(grp["timestamp_dt"].duplicated().sum())

        # Quality code breakdown
        qc_counts = grp["quality_code"].value_counts(dropna=False)
        pct_raw = round(100.0 * qc_counts.get("Raw", 0) / n_rows, 2)
        pct_error = round(100.0 * qc_counts.get("Error", 0) / n_rows, 2)
        pct_oor = round(100.0 * qc_counts.get("Out of Range", 0) / n_rows, 2)
        pct_l = round(100.0 * qc_counts.get("L", 0) / n_rows, 2)
        pct_other_qc = round(100.0 * (n_rows - (qc_counts.get("Raw", 0) + qc_counts.get("Error", 0) + qc_counts.get("Out of Range", 0) + qc_counts.get("L", 0))) / n_rows, 2)

        non_raw_grp = grp[grp["quality_code"] != "Raw"]
        non_raw_has_value = int(non_raw_grp["value"].notna().sum())

        # Impossible / invalid value checks
        vals = grp["value"]
        val_non_na = vals.dropna()

        if "pH" in param or "ph" in param.lower():
            impossible_ph_cnt = int(((val_non_na < 0) | (val_non_na > 14)).sum())
        else:
            impossible_ph_cnt = 0

        # CTO Limit Check
        cto_min, cto_max = np.nan, np.nan
        for (f_k, p_k), (c_min, c_max) in cto_dict.items():
            if f_k == fac and (p_k.lower() in param.lower() or param.lower() in p_k.lower()):
                cto_min, cto_max = c_min, c_max
                break

        cto_violations = 0
        if pd.notna(cto_min):
            cto_violations += int((val_non_na < cto_min).sum())
        if pd.notna(cto_max):
            cto_violations += int((val_non_na > cto_max).sum())

        negative_cnt = int((val_non_na < 0).sum()) if "pH" not in param else int((val_non_na < 0).sum())
        sentinel_cnt = int(val_non_na.isin([-999, -9999, 9999, 99999, -99]).sum())

        med_val = val_non_na.median() if len(val_non_na) > 0 else 0
        if med_val > 0:
            extreme_outliers = int((val_non_na > 10 * med_val).sum())
        else:
            extreme_outliers = int((val_non_na > 1000).sum())

        # Resolution & Stepping
        n_decimals = get_decimals(vals)
        val_diffs = np.abs(np.diff(val_non_na.values))
        nonzero_diffs = val_diffs[val_diffs > 1e-6]
        smallest_step = round(float(np.min(nonzero_diffs)), 6) if len(nonzero_diffs) > 0 else 0.0
        distinct_vals = int(val_non_na.nunique())

        pct_equal_prev = round(100.0 * int((grp["value"] == grp["value"].shift(1)).sum()) / n_rows, 2) if n_rows > 0 else 0.0

        # Exact-repeat runs (All rows)
        all_runs = compute_run_lengths(grp["value"])
        if len(all_runs) > 0:
            p50_run = float(np.percentile(all_runs, 50))
            p90_run = float(np.percentile(all_runs, 90))
            p99_run = float(np.percentile(all_runs, 99))
            max_run = int(np.max(all_runs))
            runs_ge_8 = int((all_runs >= 8).sum())
            runs_ge_96 = int((all_runs >= 96).sum())
        else:
            p50_run, p90_run, p99_run, max_run, runs_ge_8, runs_ge_96 = 0, 0, 0, 0, 0, 0

        # Exact-repeat runs (Raw-only rows)
        raw_only_grp = grp[grp["quality_code"] == "Raw"]
        raw_runs = compute_run_lengths(raw_only_grp["value"])
        if len(raw_runs) > 0:
            raw_p50_run = float(np.percentile(raw_runs, 50))
            raw_p90_run = float(np.percentile(raw_runs, 90))
            raw_p99_run = float(np.percentile(raw_runs, 99))
            raw_max_run = int(np.max(raw_runs))
            raw_runs_ge_8 = int((raw_runs >= 8).sum())
            raw_runs_ge_96 = int((raw_runs >= 96).sum())
        else:
            raw_p50_run, raw_p90_run, raw_p99_run, raw_max_run, raw_runs_ge_8, raw_runs_ge_96 = 0, 0, 0, 0, 0, 0

        # Non-zero vs zero runs
        zero_grp = grp[grp["value"] == 0.0]
        pct_zero = round(100.0 * len(zero_grp) / n_rows, 2) if n_rows > 0 else 0.0

        dev_audit_rows.append({
            "factory_id": fac,
            "parameter_id": param,
            "n_rows": n_rows,
            "first_timestamp": str(ts_min),
            "last_timestamp": str(ts_max),
            "expected_15min_rows": expected_15min_rows,
            "pct_missing": pct_missing,
            "longest_gap_hours": round(longest_gap_hours, 2),
            "gap_count": gap_count,
            "rows_per_month": rows_per_month,
            "duplicate_timestamps": duplicate_ts,
            "non_15min_steps": non_15min_steps,
            "out_of_order_count": out_of_order_count,
            "pct_Raw": pct_raw,
            "pct_Error": pct_error,
            "pct_Out_of_Range": pct_oor,
            "pct_L": pct_l,
            "pct_other_qc": pct_other_qc,
            "non_raw_has_value_count": non_raw_has_value,
            "impossible_ph_count": impossible_ph_cnt,
            "cto_limit_violations": cto_violations,
            "negative_value_count": negative_cnt,
            "sentinel_value_count": sentinel_cnt,
            "extreme_outliers_10x_median": extreme_outliers,
            "decimals": n_decimals,
            "smallest_nonzero_step": smallest_step,
            "distinct_values_count": distinct_vals,
            "pct_equal_to_prev": pct_equal_prev,
            "all_runs_p50": p50_run,
            "all_runs_p90": p90_run,
            "all_runs_p99": p99_run,
            "all_runs_max": max_run,
            "all_runs_ge_8_cnt": runs_ge_8,
            "all_runs_ge_96_cnt": runs_ge_96,
            "raw_runs_max": raw_max_run,
            "raw_runs_ge_8_cnt": raw_runs_ge_8,
            "raw_runs_ge_96_cnt": raw_runs_ge_96,
            "pct_zero": pct_zero,
            "cto_min_limit": cto_min,
            "cto_max_limit": cto_max
        })

    df_dev_audit = pd.DataFrame(dev_audit_rows)
    out_dev_csv = os.path.join(OUT_DIR, "audit_dev.csv")
    df_dev_audit.to_csv(out_dev_csv, index=False)
    print(f"Saved dev audit to {out_dev_csv} ({len(df_dev_audit)} rows)")
    return df_dev_audit, df_raw

if __name__ == "__main__":
    audit_dev()
