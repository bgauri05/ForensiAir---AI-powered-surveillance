import os
import sys
import random
import pandas as pd
import numpy as np

# Fixed seed for complete determinism and reproducibility
SEED = 42
np.random.seed(SEED)
random.seed(SEED)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXTRACT_DIR = r"C:\Users\gauri\.gemini\antigravity-ide\brain\cce24d3d-74f1-4565-b5c1-6c1e9d618d6d\scratch\output_rar"
HYBRID_V2_DIR = os.path.join(REPO_ROOT, "experiments", "hybrid_v2")
os.makedirs(HYBRID_V2_DIR, exist_ok=True)

CTO_LIMITS = {
    "ETP-COD": 250.0,
    "ETP-BOD": 30.0,
    "ETP-TSS": 100.0,
    "ETP-pH": (5.5, 9.0),
    "ETP-Flow": 500.0
}

def parse_cell(cell_str):
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

def load_and_clean_base_telemetry():
    file1 = os.path.join(EXTRACT_DIR, "mpcb_etp_data.csv")
    file2 = os.path.join(EXTRACT_DIR, "mpcb_etp_dataII.csv")

    rows = []
    for fp in [file1, file2]:
        df_raw = pd.read_csv(fp)
        param_cols = [c for c in df_raw.columns if c.startswith("ETP-") and "_" in c]
        for _, r in df_raw.iterrows():
            ts_str = r["Time"]
            site_id = r["site_id"]
            for col in param_cols:
                val, code = parse_cell(r[col])
                if val is not None:
                    rows.append({
                        "factory_id": site_id,
                        "parameter_id": col.split("_")[0],
                        "timestamp": ts_str,
                        "value": val,
                        "quality_code": code or "Raw"
                    })

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.drop_duplicates(subset=["factory_id", "parameter_id", "timestamp"]).sort_values(["factory_id", "parameter_id", "timestamp"]).reset_index(drop=True)
    
    # Exclude site_1458 due to extreme data sparsity (only 2 readings total)
    df = df[df["factory_id"] != "site_1458"].reset_index(drop=True)
    return df

def generate_hybrid_v2_dataset():
    print("=== STEP 1: LOADING & SAVING UNTOUCHED CONTROL TELEMETRY ===")
    df_control = load_and_clean_base_telemetry()
    
    control_parquet = os.path.join(HYBRID_V2_DIR, "control_telemetry.parquet")
    control_csv = os.path.join(HYBRID_V2_DIR, "control_telemetry.csv")
    df_control.to_parquet(control_parquet, index=False)
    df_control.to_csv(control_csv, index=False)
    print(f"Control telemetry saved ({len(df_control):,} rows):\n  - {control_parquet}\n  - {control_csv}\n")

    print("=== STEP 2: AUDITING EXCLUDED BASELINE WINDOWS & DATA GAPS ===")
    excluded_ranges = {}
    for (fac, param), grp in df_control.groupby(["factory_id", "parameter_id"]):
        grp = grp.sort_values("timestamp").reset_index(drop=True)
        grp["diff"] = grp["timestamp"].diff()
        
        # Identify gaps > 1 hour
        gap_indices = grp[grp["diff"] > pd.Timedelta(hours=1)].index.tolist()
        
        ex_list = []
        for idx in gap_indices:
            prev_ts = grp.loc[idx - 1, "timestamp"]
            curr_ts = grp.loc[idx, "timestamp"]
            ex_list.append((prev_ts, curr_ts))
            
        # Identify existing flatlines > 6h (24 steps)
        grp["var_24"] = grp["value"].rolling(window=24, min_periods=24).var()
        flat_indices = grp[grp["var_24"] < 1e-5].index.tolist()
        for idx in flat_indices:
            start_ts = grp.loc[max(0, idx - 23), "timestamp"]
            end_ts = grp.loc[idx, "timestamp"]
            ex_list.append((start_ts, end_ts))
            
        excluded_ranges[(fac, param)] = ex_list

    print(f"Identified exclusion windows across {len(excluded_ranges)} series.")

    print("=== STEP 3: GENERATING HYBRID V2 TAMPERING EVENTS (320 EVENTS TARGET) ===")
    
    # 8 Tamper types: 7 with detectors, 1 without detector ("BDL GAMING")
    tamper_specs = [
        ("IMPOSSIBLE PH RANGE", "rule_range", 40),
        ("FLATLINE", "rule_flatline", 40),
        ("LIMIT HUGGING", "rule_limit_hugging", 40),
        ("INSPECTION DIP", "rule_inspection_dip", 40),
        ("CORRELATION BREAK", "rule_correlation_break", 40),
        ("COPY-PASTE", "rule_copy_paste", 40), # Multi-day copy-paste
        ("COORDINATED MISSING DATA", "rule_missing", 40),
        ("BDL GAMING", "none", 40) # No detector
    ]

    df_neutral = df_control.copy()
    df_visible = df_control.copy()

    manifest_entries = []
    occupied_intervals = {} # (fac, param) -> list of (start_ts, end_ts)

    def is_window_valid(fac, param, start_ts, end_ts, series_min_ts, series_max_ts):
        # Must be at least 24h away from edges
        if start_ts < series_min_ts + pd.Timedelta(hours=24):
            return False
        if end_ts > series_max_ts - pd.Timedelta(hours=24):
            return False
            
        # Check collision with previous events
        if (fac, param) in occupied_intervals:
            for s, e in occupied_intervals[(fac, param)]:
                if max(start_ts, s) <= min(end_ts, e):
                    return False
                    
        # Check collision with baseline excluded windows
        if (fac, param) in excluded_ranges:
            for s, e in excluded_ranges[(fac, param)]:
                if max(start_ts, s) <= min(end_ts, e):
                    return False

        return True

    event_id_counter = 1
    valid_sites = ["site_1129", "site_1307", "site_1629", "site_1631"]

    for tamper_type, detector_type, target_count in tamper_specs:
        events_created = 0
        attempts = 0
        
        while events_created < target_count and attempts < 1000:
            attempts += 1
            fac = random.choice(valid_sites)
            fac_df = df_control[df_control["factory_id"] == fac]
            params = fac_df["parameter_id"].unique().tolist()
            
            if tamper_type == "COPY-PASTE":
                # Multi-day copy-paste: select series with at least 5 days of data
                param = random.choice(params)
            else:
                param = random.choice(params)

            sub = fac_df[fac_df["parameter_id"] == param].sort_values("timestamp").reset_index(drop=True)
            if len(sub) < 300:
                continue

            series_min = sub["timestamp"].min()
            series_max = sub["timestamp"].max()

            # Event duration
            if tamper_type == "COPY-PASTE":
                # Multi-day duration: 2 to 4 days = 192 to 384 reading steps
                duration_steps = random.randint(192, 384)
            elif tamper_type in ["FLATLINE", "LIMIT HUGGING", "INSPECTION DIP", "IMPOSSIBLE PH RANGE", "BDL GAMING", "COORDINATED MISSING DATA", "CORRELATION BREAK"]:
                severity_choice = random.choice(["easy", "medium", "subtle"])
                if tamper_type == "FLATLINE" and severity_choice == "subtle":
                    duration_steps = random.randint(12, 24) # 3h to 6h for subtle flatline
                else:
                    duration_steps = random.randint(16, 48) # 4h to 12h
            else:
                duration_steps = random.randint(16, 48)

            start_idx = random.randint(96, len(sub) - duration_steps - 96)
            start_ts = sub.loc[start_idx, "timestamp"]
            end_ts = sub.loc[start_idx + duration_steps - 1, "timestamp"]

            if not is_window_valid(fac, param, start_ts, end_ts, series_min, series_max):
                continue

            # Pick severity
            severity = random.choice(["easy", "medium", "subtle"])

            # Create mask for telemetry selection
            mask_n = (
                (df_neutral["factory_id"] == fac) &
                (df_neutral["parameter_id"] == param) &
                (df_neutral["timestamp"] >= start_ts) &
                (df_neutral["timestamp"] <= end_ts)
            )
            mask_v = (
                (df_visible["factory_id"] == fac) &
                (df_visible["parameter_id"] == param) &
                (df_visible["timestamp"] >= start_ts) &
                (df_visible["timestamp"] <= end_ts)
            )

            orig_vals = df_neutral.loc[mask_n, "value"].values.copy()
            if len(orig_vals) == 0:
                continue

            # Execute Tamper Modification based on Severity & Rules
            injected_vals = orig_vals.copy()
            visible_code = "Raw"

            if tamper_type == "IMPOSSIBLE PH RANGE":
                if param == "ETP-pH":
                    if severity == "easy":
                        injected_vals[:] = random.choice([1.0, 1.5, 13.0, 13.8])
                    elif severity == "medium":
                        injected_vals[:] = random.choice([1.8, 12.2])
                    else: # subtle: just outside 5.5-9.0 range (e.g. 5.1 or 9.3)
                        injected_vals[:] = random.choice([5.1, 5.3, 9.2, 9.4])
                else:
                    med = np.nanmedian(orig_vals) or 50.0
                    mult = 8.0 if severity == "easy" else (5.0 if severity == "medium" else 2.5)
                    injected_vals[:] = med * mult
                visible_code = "O" # Out of range

            elif tamper_type == "FLATLINE":
                base_v = float(orig_vals[0])
                if severity == "subtle":
                    # Flatline with small jitter (sigma = 0.02)
                    injected_vals[:] = base_v + np.random.normal(0, 0.02, size=len(orig_vals))
                else:
                    injected_vals[:] = base_v
                visible_code = "E"

            elif tamper_type == "LIMIT HUGGING":
                limit_v = CTO_LIMITS.get(param, 100.0)
                if isinstance(limit_v, tuple):
                    limit_val = limit_v[1]
                else:
                    limit_val = limit_v

                if severity == "easy":
                    injected_vals[:] = limit_val * random.uniform(0.97, 0.99)
                elif severity == "medium":
                    injected_vals[:] = limit_val * random.uniform(0.95, 0.96)
                else: # subtle: 85% - 94% of limit + noise (sigma = 1.5)
                    base_hug = limit_val * random.uniform(0.85, 0.94)
                    injected_vals[:] = base_hug + np.random.normal(0, 1.5, size=len(orig_vals))
                visible_code = "input"

            elif tamper_type == "INSPECTION DIP":
                if severity == "easy":
                    drop_pct = random.uniform(0.50, 0.65) # 50-65% drop
                elif severity == "medium":
                    drop_pct = random.uniform(0.35, 0.49) # 35-49% drop
                else: # subtle: 15-30% drop
                    drop_pct = random.uniform(0.15, 0.30)
                injected_vals[:] = orig_vals * (1.0 - drop_pct)
                visible_code = "C" # Calibration / manual adjustment

            elif tamper_type == "CORRELATION BREAK":
                if severity == "subtle":
                    injected_vals[:] = orig_vals * random.uniform(0.70, 0.85)
                else:
                    injected_vals[:] = orig_vals * random.uniform(0.10, 0.30)
                visible_code = "E"

            elif tamper_type == "COPY-PASTE":
                # Multi-day copy-paste
                src_start = max(0, start_idx - duration_steps)
                src_vals = sub.iloc[src_start : src_start + duration_steps]["value"].values
                if len(src_vals) == len(orig_vals):
                    if severity == "subtle":
                        # Lag variation and small noise (sigma = 0.5)
                        injected_vals[:] = src_vals + np.random.normal(0, 0.5, size=len(orig_vals))
                    else:
                        injected_vals[:] = src_vals
                else:
                    injected_vals[:] = orig_vals[0]
                visible_code = "input"

            elif tamper_type == "COORDINATED MISSING DATA":
                injected_vals[:] = np.nan
                visible_code = "E"

            elif tamper_type == "BDL GAMING":
                # No detector
                if severity == "subtle":
                    injected_vals[:] = np.random.uniform(0.04, 0.08, size=len(orig_vals))
                else:
                    injected_vals[:] = np.random.uniform(0.01, 0.04, size=len(orig_vals))
                visible_code = "L"

            # Apply modifications to Datasets
            # Variant 1: Code Neutral (Keep original quality codes)
            df_neutral.loc[mask_n, "value"] = injected_vals

            # Variant 2: Code Visible (Update quality codes)
            df_visible.loc[mask_v, "value"] = injected_vals
            if visible_code != "Raw":
                df_visible.loc[mask_v, "quality_code"] = visible_code

            # Record in manifest
            event_id = f"EVT_{event_id_counter:04d}"
            event_id_counter += 1

            manifest_entries.append({
                "event_id": event_id,
                "site": fac,
                "parameter": param,
                "tamper_type": tamper_type,
                "detector_type": detector_type,
                "severity": severity,
                "start": str(start_ts),
                "end": str(end_ts),
                "rows_affected": len(orig_vals),
                "seed": SEED,
                "original_value_mean": round(float(np.nanmean(orig_vals)), 4),
                "injected_value_mean": round(float(np.nanmean(injected_vals)), 4),
                "variant": "dual (code-neutral & code-visible)"
            })

            # Mark interval as occupied
            if (fac, param) not in occupied_intervals:
                occupied_intervals[(fac, param)] = []
            occupied_intervals[(fac, param)].append((start_ts, end_ts))

            events_created += 1

        print(f"  [{tamper_type}] Created {events_created} events (Target: {target_count}).")

    df_manifest = pd.DataFrame(manifest_entries)
    print(f"\nSuccessfully generated {len(df_manifest)} total tampering events in manifest.")

    # Save Datasets
    neut_parquet = os.path.join(HYBRID_V2_DIR, "hybrid_v2_code_neutral_telemetry.parquet")
    neut_csv = os.path.join(HYBRID_V2_DIR, "hybrid_v2_code_neutral_telemetry.csv")
    vis_parquet = os.path.join(HYBRID_V2_DIR, "hybrid_v2_code_visible_telemetry.parquet")
    vis_csv = os.path.join(HYBRID_V2_DIR, "hybrid_v2_code_visible_telemetry.csv")
    manifest_csv = os.path.join(HYBRID_V2_DIR, "tamper_manifest.csv")

    df_neutral.to_parquet(neut_parquet, index=False)
    df_neutral.to_csv(neut_csv, index=False)
    df_visible.to_parquet(vis_parquet, index=False)
    df_visible.to_csv(vis_csv, index=False)
    df_manifest.to_csv(manifest_csv, index=False)

    print(f"\nSaved Phase B hybrid_v2 datasets:")
    print(f"  - Code-Neutral Variant: {neut_parquet}")
    print(f"  - Code-Visible Variant: {vis_parquet}")
    print(f"  - Tamper Manifest:     {manifest_csv}")

if __name__ == "__main__":
    generate_hybrid_v2_dataset()
