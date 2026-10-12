import os
import json
import sqlite3
import pandas as pd
import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXTRACT_DIR = r"C:\Users\gauri\.gemini\antigravity-ide\brain\cce24d3d-74f1-4565-b5c1-6c1e9d618d6d\scratch\output_rar"
HYBRID_DIR = os.path.join(REPO_ROOT, "Data", "OutputRar_Hybrid")
DB_PATH = os.path.join(REPO_ROOT, "forensier.db")
REAL_PARQUET = os.path.join(REPO_ROOT, "Data", "RawData", "real_features.parquet")

def run_phase_a_audit():
    results = {}
    
    # ----------------------------------------------------
    # 1. Actual Schema & Grain of cleaned_output_rar_telemetry
    # ----------------------------------------------------
    clean_path = os.path.join(HYBRID_DIR, "cleaned_output_rar_telemetry.parquet")
    df_clean = pd.read_parquet(clean_path)
    df_clean["timestamp"] = pd.to_datetime(df_clean["timestamp"])
    
    grain_check = df_clean.groupby(["factory_id", "timestamp", "parameter_id"]).size()
    is_unique_grain = (grain_check.max() == 1)
    
    results["schema_columns"] = list(df_clean.columns)
    results["schema_dtypes"] = {c: str(df_clean[c].dtype) for c in df_clean.columns}
    results["total_clean_rows"] = len(df_clean)
    results["is_unique_grain"] = is_unique_grain
    
    # Row counts per site, per parameter, per month
    df_clean["month"] = df_clean["timestamp"].dt.to_period("M").astype(str)
    
    site_counts = df_clean.groupby("factory_id").size().to_dict()
    param_counts = df_clean.groupby("parameter_id").size().to_dict()
    site_param_counts = {f"{k[0]}___{k[1]}": int(v) for k, v in df_clean.groupby(["factory_id", "parameter_id"]).size().items()}
    site_month_counts = {f"{k[0]}___{k[1]}": int(v) for k, v in df_clean.groupby(["factory_id", "month"]).size().items()}
    
    results["site_counts"] = site_counts
    results["param_counts"] = param_counts
    results["site_param_counts"] = site_param_counts
    results["site_month_counts"] = site_month_counts
    
    # ----------------------------------------------------
    # 2. Dedupe Audit of 140,640 raw rows
    # ----------------------------------------------------
    file1 = os.path.join(EXTRACT_DIR, "mpcb_etp_data.csv")
    file2 = os.path.join(EXTRACT_DIR, "mpcb_etp_dataII.csv")
    
    raw1 = pd.read_csv(file1)
    raw2 = pd.read_csv(file2)
    
    total_raw_rows = len(raw1) + len(raw2) # 120,096 + 20,544 = 140,640
    
    # Analyze raw unpivoted total cells vs dropped cells
    param_cols_1 = [c for c in raw1.columns if c.startswith("ETP-") and "_" in c]
    
    # Count null / NA cells vs valid cells
    valid_cells = 0
    na_cells = 0
    
    def parse_cell_test(cell_str):
        if pd.isna(cell_str) or not str(cell_str).strip():
            return None, None
        s = str(cell_str).strip()
        if s.startswith("['NA'") or s.startswith("[\"NA\"") or s.startswith("['NA\",") or s.startswith("[\"NA',"):
            return None, None
        cleaned = s.strip("[]")
        parts = cleaned.split(",")
        if len(parts) == 2:
            val_str = parts[0].strip(" '\"")
            code_str = parts[1].strip(" '\"")
            try:
                return float(val_str), code_str
            except ValueError:
                return None, None
        return None, None

    rows1_extracted = []
    for idx, r in raw1.iterrows():
        ts_str = r["Time"]
        site_id = r["site_id"]
        for col in param_cols_1:
            val, code = parse_cell_test(r[col])
            if val is not None:
                rows1_extracted.append((site_id, col.split("_")[0], ts_str, val, code))
            else:
                na_cells += 1
                
    rows2_extracted = []
    param_cols_2 = [c for c in raw2.columns if c.startswith("ETP-") and "_" in c]
    for idx, r in raw2.iterrows():
        ts_str = r["Time"]
        site_id = r["site_id"]
        for col in param_cols_2:
            val, code = parse_cell_test(r[col])
            if val is not None:
                rows2_extracted.append((site_id, col.split("_")[0], ts_str, val, code))
            else:
                na_cells += 1

    df_ext1 = pd.DataFrame(rows1_extracted, columns=["factory_id", "parameter_id", "timestamp", "value", "quality_code"])
    df_ext2 = pd.DataFrame(rows2_extracted, columns=["factory_id", "parameter_id", "timestamp", "value", "quality_code"])
    
    len1 = len(df_ext1) # 151,137
    len2 = len(df_ext2) # 82,940
    combined_raw_extracted = len1 + len2 # 234,077
    
    # Check overlap between file1 and file2
    df_ext1["timestamp"] = pd.to_datetime(df_ext1["timestamp"])
    df_ext2["timestamp"] = pd.to_datetime(df_ext2["timestamp"])
    
    overlap_mask = df_ext2.set_index(["factory_id", "parameter_id", "timestamp"]).index.isin(
        df_ext1.set_index(["factory_id", "parameter_id", "timestamp"]).index
    )
    overlap_count = int(overlap_mask.sum()) # rows in file2 that were identical timestamp/factory/param in file1
    
    df_combined_ext = pd.concat([df_ext1, df_ext2], ignore_index=True)
    deduped_df = df_combined_ext.drop_duplicates(subset=["factory_id", "parameter_id", "timestamp"])
    duplicates_dropped = len(df_combined_ext) - len(deduped_df)
    
    results["dedupe_audit"] = {
        "raw_csv_rows_file1": len(raw1),
        "raw_csv_rows_file2": len(raw2),
        "total_raw_csv_rows": total_raw_rows,
        "extracted_valid_records_file1": len1,
        "extracted_valid_records_file2": len2,
        "total_extracted_records": combined_raw_extracted,
        "overlap_file2_in_file1": overlap_count,
        "duplicate_timestamps_dropped": duplicates_dropped,
        "null_na_cells_filtered": na_cells,
        "final_clean_rows": len(deduped_df)
    }

    # ----------------------------------------------------
    # 3. Baseline Quality per Site & Parameter
    # ----------------------------------------------------
    quality_summary = {}
    excluded_windows = []

    for (fac, param), grp in df_clean.groupby(["factory_id", "parameter_id"]):
        grp = grp.sort_values("timestamp").copy()
        
        # Missing percentage
        min_ts, max_ts = grp["timestamp"].min(), grp["timestamp"].max()
        expected_steps = int((max_ts - min_ts) / pd.Timedelta(minutes=15)) + 1
        actual_steps = len(grp)
        missing_count = expected_steps - actual_steps
        missing_pct = round((missing_count / max_ts.timestamp()) * 100, 2) if max_ts.timestamp() else 0
        missing_rate_internal = round((missing_count / expected_steps) * 100, 2) if expected_steps > 0 else 0
        
        # Quality code distribution
        qc_dist = grp["quality_code"].value_counts().to_dict()
        
        # Existing flatline runs (variance == 0 over >= 6h / 24 steps)
        grp["var_24"] = grp["value"].rolling(window=24, min_periods=24).var()
        flatline_runs = (grp["var_24"] < 1e-5).sum()
        
        # Impossible pH (< 2.0 or > 12.0)
        if param == "ETP-pH":
            imp_ph_count = int(((grp["value"] < 2.0) | (grp["value"] > 12.0)).sum())
        else:
            imp_ph_count = 0

        # Gaps longer than 1h (4 steps of 15 min)
        grp["time_diff"] = grp["timestamp"].diff()
        gaps_gt_1h = grp[grp["time_diff"] > pd.Timedelta(hours=1)]
        
        gap_windows = []
        for idx, row in gaps_gt_1h.iterrows():
            prev_ts = grp.loc[idx - 1, "timestamp"] if (idx - 1) in grp.index else row["timestamp"] - row["time_diff"]
            gap_duration_hrs = round(row["time_diff"].total_seconds() / 3600.0, 2)
            gap_windows.append({
                "gap_start": str(prev_ts),
                "gap_end": str(row["timestamp"]),
                "duration_hours": gap_duration_hrs
            })
            # Add to excluded windows
            excluded_windows.append({
                "factory_id": fac,
                "parameter_id": param,
                "reason": f"Data Gap > 1h ({gap_duration_hrs}h)",
                "start_timestamp": str(prev_ts),
                "end_timestamp": str(row["timestamp"])
            })
            
        quality_summary[f"{fac}___{param}"] = {
            "min_timestamp": str(min_ts),
            "max_timestamp": str(max_ts),
            "expected_steps": expected_steps,
            "actual_steps": actual_steps,
            "missing_steps": missing_count,
            "missing_percentage": missing_rate_internal,
            "quality_code_dist": qc_dist,
            "flatline_runs_6h": int(flatline_runs),
            "impossible_ph_count": imp_ph_count,
            "gaps_gt_1h_count": len(gaps_gt_1h),
            "gaps_gt_1h_details": gap_windows
        }

    results["quality_summary"] = quality_summary
    results["excluded_windows_count"] = len(excluded_windows)
    results["excluded_windows"] = excluded_windows[:20] # preview first 20

    # ----------------------------------------------------
    # 4. CTO Limits & Inspection Dates check for the 5 sites
    # ----------------------------------------------------
    sites_5 = ["site_1129", "site_1307", "site_1458", "site_1629", "site_1631"]
    cto_info = {}
    inspection_info = {}

    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        # Check consent_limits
        try:
            cl = pd.read_sql("SELECT * FROM consent_limits WHERE factory_id IN ('site_1129', 'site_1307', 'site_1458', 'site_1629', 'site_1631')", conn)
            cto_info["db_consent_limits_count"] = len(cl)
            cto_info["db_consent_limits_sites"] = cl["factory_id"].unique().tolist() if not cl.empty else []
            cto_info["db_consent_limits_data"] = cl.to_dict(orient="records") if not cl.empty else []
        except Exception as e:
            cto_info["db_consent_limits_error"] = str(e)
            
        # Check inspection_events
        try:
            ie = pd.read_sql("SELECT * FROM inspection_events WHERE factory_id IN ('site_1129', 'site_1307', 'site_1458', 'site_1629', 'site_1631')", conn)
            inspection_info["db_inspections_count"] = len(ie)
            inspection_info["db_inspections_sites"] = ie["factory_id"].unique().tolist() if not ie.empty else []
            inspection_info["db_inspections_data"] = ie.to_dict(orient="records") if not ie.empty else []
        except Exception as e:
            inspection_info["db_inspections_error"] = str(e)

        # Check factories table
        try:
            f_db = pd.read_sql("SELECT factory_id, name FROM factories WHERE factory_id IN ('site_1129', 'site_1307', 'site_1458', 'site_1629', 'site_1631')", conn)
            results["db_factories_present"] = f_db.to_dict(orient="records")
        except Exception as e:
            results["db_factories_error"] = str(e)

        conn.close()
    else:
        cto_info["note"] = "forensier.db not found"

    results["cto_info"] = cto_info
    results["inspection_info"] = inspection_info

    # ----------------------------------------------------
    # 5. Check whether 5 site IDs appear in model training data
    # ----------------------------------------------------
    training_data_check = {}
    if os.path.exists(REAL_PARQUET):
        df_real_tr = pd.read_parquet(REAL_PARQUET)
        real_tr_sites = df_real_tr["factory_id"].unique().tolist()
        overlap_sites = [s for s in sites_5 if s in real_tr_sites]
        training_data_check["real_features_parquet_exists"] = True
        training_data_check["total_sites_in_real_features"] = len(real_tr_sites)
        training_data_check["all_real_features_sites"] = sorted(real_tr_sites)
        training_data_check["overlap_with_5_sites"] = overlap_sites
        training_data_check["sites_present_in_training_data"] = (len(overlap_sites) > 0)
    else:
        training_data_check["real_features_parquet_exists"] = False

    results["training_data_check"] = training_data_check

    # ----------------------------------------------------
    # 6. Check whether hybrid_features.parquet matches real_features.parquet
    # ----------------------------------------------------
    feature_schema_check = {}
    hybrid_feat_path = os.path.join(HYBRID_DIR, "hybrid_features.parquet")
    
    if os.path.exists(REAL_PARQUET) and os.path.exists(hybrid_feat_path):
        df_real_schema = pd.read_parquet(REAL_PARQUET)
        df_hyb_schema = pd.read_parquet(hybrid_feat_path)
        
        real_cols = list(df_real_schema.columns)
        hyb_cols = list(df_hyb_schema.columns)
        
        feature_schema_check["real_columns_count"] = len(real_cols)
        feature_schema_check["hybrid_columns_count"] = len(hyb_cols)
        feature_schema_check["real_columns"] = real_cols
        feature_schema_check["hybrid_columns"] = hyb_cols
        feature_schema_check["exact_columns_match"] = (real_cols == hyb_cols)
        feature_schema_check["set_columns_match"] = (set(real_cols) == set(hyb_cols))
        
        # dtypes comparison
        real_dtypes = {c: str(df_real_schema[c].dtype) for c in real_cols}
        hyb_dtypes = {c: str(df_hyb_schema[c].dtype) for c in hyb_cols if c in df_hyb_schema.columns}
        
        dtype_mismatches = {}
        for c in real_cols:
            if c in hyb_dtypes:
                if real_dtypes[c] != hyb_dtypes[c]:
                    dtype_mismatches[c] = {"real": real_dtypes[c], "hybrid": hyb_dtypes[c]}
            else:
                dtype_mismatches[c] = {"real": real_dtypes[c], "hybrid": "MISSING"}
                
        feature_schema_check["dtype_mismatches"] = dtype_mismatches
        feature_schema_check["missing_columns_in_hybrid"] = [c for c in real_cols if c not in hyb_cols]
        feature_schema_check["extra_columns_in_hybrid"] = [c for c in hyb_cols if c not in real_cols]

    results["feature_schema_check"] = feature_schema_check

    # ----------------------------------------------------
    # 7. Distinct events per tamper type in hybrid_tamper_labels.csv
    # ----------------------------------------------------
    labels_path = os.path.join(HYBRID_DIR, "hybrid_tamper_labels.csv")
    labels_audit = {}
    if os.path.exists(labels_path):
        df_lab = pd.read_csv(labels_path)
        labels_audit["total_events"] = len(df_lab)
        labels_audit["events_per_tamper_type"] = df_lab["tamper_type"].value_counts().to_dict()
        labels_audit["events_per_severity"] = df_lab["severity"].value_counts().to_dict()
        labels_audit["events_per_site"] = df_lab["factory_id"].value_counts().to_dict()
        labels_audit["sample_events"] = df_lab.head(5).to_dict(orient="records")

    results["labels_audit"] = labels_audit

    return results

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    res = run_phase_a_audit()
    out_json_path = os.path.join(os.path.dirname(__file__), "audit_results.json")
    with open(out_json_path, "w") as f:
        json.dump(res, f, indent=2, default=str)
    print(f"Successfully saved audit results to {out_json_path}")
