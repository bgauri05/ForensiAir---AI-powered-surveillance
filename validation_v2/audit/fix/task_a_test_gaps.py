import os
import pandas as pd
import numpy as np

UNSEEN_DIR = r"c:\Users\gauri\Downloads\validation"
UNSEEN_FILES = {
    "Cipla": os.path.join(UNSEEN_DIR, "Cipla (1).csv"),
    "Glenmark": os.path.join(UNSEEN_DIR, "Glenmark (1).csv"),
    "Indoco": os.path.join(UNSEEN_DIR, "Indoco (1).csv"),
    "Zydus": os.path.join(UNSEEN_DIR, "Zydus (1).csv")
}

CANONICAL_PARAMS = ["ETP-BOD", "ETP-COD", "ETP-pH", "ETP-Flow", "ETP-TSS"]

def compute_missing_runs(series_is_na):
    """Computes contiguous missing runs."""
    vals = series_is_na.values
    if len(vals) == 0 or not np.any(vals):
        return 0, 0.0
    
    # Run length encoding on boolean is_na
    is_change = np.ones(len(vals), dtype=bool)
    is_change[1:] = (vals[1:] != vals[:-1])
    change_indices = np.where(is_change)[0]
    run_lengths = np.diff(np.append(change_indices, len(vals)))
    run_vals = vals[change_indices]
    
    na_run_lengths = run_lengths[run_vals]
    n_runs = len(na_run_lengths)
    max_run_steps = int(np.max(na_run_lengths)) if n_runs > 0 else 0
    max_run_hours = round(max_run_steps * 15.0 / 60.0, 2)
    return n_runs, max_run_hours

def compute_leading_trailing_na(series_is_na):
    vals = series_is_na.values
    n = len(vals)
    leading = 0
    for v in vals:
        if v:
            leading += 1
        else:
            break
    trailing = 0
    for v in reversed(vals):
        if v:
            trailing += 1
        else:
            break
    return leading, trailing

def run_task_a():
    print("==========================================================================")
    print(" TASK A: TEST-SET GAPS ANALYSIS (audit_test_v2.csv)")
    print("==========================================================================")

    test_v2_rows = []
    factory_multi_missing = {}

    for f_name, f_path in UNSEEN_FILES.items():
        df_raw = pd.read_csv(f_path)
        print(f"\nSource File [{f_name}]: Shape {df_raw.shape}, Columns: {list(df_raw.columns)}")
        
        # Parse timestamp
        time_col = df_raw.columns[0]
        df_raw["timestamp_dt"] = pd.to_datetime(df_raw[time_col], errors="coerce")
        df_raw = df_raw.sort_values("timestamp_dt").reset_index(drop=True)

        # Map parameters and coerce numeric (treating 'NA', blanks as NaN)
        param_series = {}
        for c in df_raw.columns:
            if c == time_col or c == "timestamp_dt":
                continue
            c_lower = c.lower()
            if "bod" in c_lower:
                param_series["ETP-BOD"] = pd.to_numeric(df_raw[c], errors="coerce")
            elif "cod" in c_lower:
                param_series["ETP-COD"] = pd.to_numeric(df_raw[c], errors="coerce")
            elif "ph" in c_lower:
                param_series["ETP-pH"] = pd.to_numeric(df_raw[c], errors="coerce")
            elif "flow" in c_lower:
                param_series["ETP-Flow"] = pd.to_numeric(df_raw[c], errors="coerce")
            elif "tss" in c_lower:
                param_series["ETP-TSS"] = pd.to_numeric(df_raw[c], errors="coerce")

        # Build wide parameter dataframe to compute multi-parameter missing timestamps
        wide_missing_df = pd.DataFrame()
        available_params_in_fac = list(param_series.keys())

        for p_name in CANONICAL_PARAMS:
            if p_name in param_series:
                s = param_series[p_name]
                is_na = s.isna()
                wide_missing_df[p_name] = is_na
                
                n_rows = len(df_raw)
                n_missing = int(is_na.sum())
                pct_missing = round(100.0 * n_missing / n_rows, 2)
                
                n_missing_runs, max_missing_hours = compute_missing_runs(is_na)
                leading_na, trailing_na = compute_leading_trailing_na(is_na)

                valid_ts = df_raw.loc[~is_na, "timestamp_dt"]
                first_valid_ts = str(valid_ts.min()) if len(valid_ts) > 0 else "N/A"
                last_valid_ts = str(valid_ts.max()) if len(valid_ts) > 0 else "N/A"

                test_v2_rows.append({
                    "factory_id": f_name,
                    "parameter_id": p_name,
                    "n_rows": n_rows,
                    "n_missing": n_missing,
                    "pct_missing": pct_missing,
                    "n_missing_runs": n_missing_runs,
                    "longest_missing_run_hours": max_missing_hours,
                    "leading_na_rows": leading_na,
                    "trailing_na_rows": trailing_na,
                    "first_non_na_timestamp": first_valid_ts,
                    "last_non_na_timestamp": last_valid_ts,
                    "parameter_status": "Present"
                })
            else:
                test_v2_rows.append({
                    "factory_id": f_name,
                    "parameter_id": p_name,
                    "n_rows": len(df_raw),
                    "n_missing": len(df_raw),
                    "pct_missing": 100.0,
                    "n_missing_runs": 1,
                    "longest_missing_run_hours": round(len(df_raw) * 15.0 / 60.0, 2),
                    "leading_na_rows": len(df_raw),
                    "trailing_na_rows": len(df_raw),
                    "first_non_na_timestamp": "N/A",
                    "last_non_na_timestamp": "N/A",
                    "parameter_status": "Not Monitored"
                })

        # Calculate % of timestamps where >= 2 available parameters are missing together
        if len(available_params_in_fac) >= 2:
            multi_missing_cnt = int((wide_missing_df[available_params_in_fac].sum(axis=1) >= 2).sum())
            pct_multi_missing = round(100.0 * multi_missing_cnt / len(df_raw), 2)
        else:
            multi_missing_cnt = 0
            pct_multi_missing = 0.0

        factory_multi_missing[f_name] = {
            "available_params": ", ".join(available_params_in_fac),
            "multi_missing_cnt": multi_missing_cnt,
            "pct_multi_missing": pct_multi_missing
        }

    df_test_v2 = pd.DataFrame(test_v2_rows)
    out_csv = os.path.join(r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance\validation_v2\audit\fix", "audit_test_v2.csv")
    df_test_v2.to_csv(out_csv, index=False)
    print(f"\nSaved audit_test_v2.csv to {out_csv} ({len(df_test_v2)} rows)")

    print("\nMulti-Parameter Coordinated Missing Timestamps (% of timestamps with >=2 params missing):")
    for f, d in factory_multi_missing.items():
        print(f"  [{f:<10}]: {d['pct_multi_missing']:>6.2f}% ({d['multi_missing_cnt']:,} timestamps) | Monitored: {d['available_params']}")

    return df_test_v2, factory_multi_missing

if __name__ == "__main__":
    run_task_a()
