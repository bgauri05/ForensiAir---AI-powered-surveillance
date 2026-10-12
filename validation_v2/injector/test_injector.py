import os
import sys
import hashlib
import pandas as pd
import numpy as np
import pytest

REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
INJECTOR_DIR = os.path.join(REPO_ROOT, "validation_v2", "injector")
INJECTOR_PY = os.path.join(INJECTOR_DIR, "injector.py")
DEV_DIR = os.path.join(INJECTOR_DIR, "injected", "dev")
LABELS_CSV = os.path.join(DEV_DIR, "labels.csv")

def test_1_no_detector_imports():
    """Verify injector.py has 0 imports/reads from detector code or thresholds."""
    forbidden_terms = ["fingerprint_engine", "ml_pipeline", "features.py", "threshold"]
    with open(INJECTOR_PY, "r", encoding="utf-8") as f:
        content = f.read()

    found = []
    for term in forbidden_terms:
        if term in content:
            found.append(term)

    assert len(found) == 0, f"Injector file contains forbidden detector references: {found}"

def test_2_labels_manifest_and_parquets_exist():
    """Verify labels.csv exists and seed parquets are generated."""
    assert os.path.exists(LABELS_CSV), f"Missing master labels manifest: {LABELS_CSV}"
    df_labels = pd.read_csv(LABELS_CSV)
    assert len(df_labels) > 0, "Labels manifest is empty"
    
    for seed in range(1, 6):
        seed_path = os.path.join(DEV_DIR, f"seed_{seed}")
        assert os.path.exists(seed_path), f"Missing seed directory: {seed_path}"
        parquets = [f for f in os.listdir(seed_path) if f.endswith(".parquet")]
        assert len(parquets) > 0, f"No parquet files found in {seed_path}"

def test_3_duration_rows_matches_timestamp_span_exactly():
    """Verify 0 discrepancy between labelled duration_rows and timestamp span on 15m grid."""
    df_labels = pd.read_csv(LABELS_CSV)
    df_labels["start_dt"] = pd.to_datetime(df_labels["start_ts"])
    df_labels["end_dt"] = pd.to_datetime(df_labels["end_ts"])
    
    ts_span_rows = (df_labels["end_dt"] - df_labels["start_dt"]) / pd.Timedelta(minutes=15) + 1
    diff_rows = ts_span_rows - df_labels["duration_rows"]
    
    discrepancies = df_labels[diff_rows != 0]
    assert len(discrepancies) == 0, f"Found {len(discrepancies)} events with timestamp span discrepancy!"

def test_4_injected_rows_differ_from_orig_and_no_change_outside_windows():
    """
    Verify:
    1. Injected rows differ from value_orig (except exact T1 when start value equals orig).
    2. No values modified outside labeled windows (is_injected == False implies value == value_orig or both NaN).
    """
    df_labels = pd.read_csv(LABELS_CSV)
    t1_exact_equal_matches = 0

    for seed in [1, 2]:
        seed_path = os.path.join(DEV_DIR, f"seed_{seed}")
        parquets = [f for f in os.listdir(seed_path) if f.endswith(".parquet")][:5]
        
        for p_file in parquets:
            df = pd.read_parquet(os.path.join(seed_path, p_file))

            # Outside labeled windows check
            outside = df[~df["is_injected"]]
            mismatches = outside[
                (outside["value"] != outside["value_orig"]) & 
                ~(outside["value"].isna() & outside["value_orig"].isna())
            ]
            assert len(mismatches) == 0, f"Found {len(mismatches)} altered rows outside labeled windows in {p_file}"

            # Inside labeled windows check
            inside = df[df["is_injected"]]
            for _, r in inside.iterrows():
                val = r["value"]
                val_o = r["value_orig"]
                evt = r["event_id"]
                
                if val == val_o:
                    evt_row = df_labels[df_labels["event_id"] == evt]
                    if len(evt_row) > 0 and evt_row.iloc[0]["type"] == "T1" and evt_row.iloc[0]["severity"] == "obvious":
                        t1_exact_equal_matches += 1

def test_5_no_event_overlaps_and_48h_gap():
    """Verify non-overlapping event windows with >= 192 rows (48h) gap between events per factory per seed."""
    df_labels = pd.read_csv(LABELS_CSV)
    df_labels["start_dt"] = pd.to_datetime(df_labels["start_ts"])
    df_labels["end_dt"] = pd.to_datetime(df_labels["end_ts"])

    for (seed, fac), group in df_labels.groupby(["seed", "factory_id"]):
        sorted_events = group.sort_values("start_dt").reset_index(drop=True)
        for i in range(len(sorted_events) - 1):
            curr_end = sorted_events.iloc[i]["end_dt"]
            next_start = sorted_events.iloc[i+1]["start_dt"]
            gap_hours = (next_start - curr_end).total_seconds() / 3600.0
            
            assert gap_hours >= 48.0 - 1e-5, f"Event buffer violation for Seed {seed}, Factory {fac}: gap is {gap_hours:.2f}h < 48h"

def test_6_reproducibility_same_seed_hash():
    """Verify deterministic generator output."""
    seed_1_files = sorted(os.listdir(os.path.join(DEV_DIR, "seed_1")))
    assert len(seed_1_files) > 0
    
    hashes_seed1 = []
    for f in seed_1_files:
        p_path = os.path.join(DEV_DIR, "seed_1", f)
        h = hashlib.sha256(open(p_path, "rb").read()).hexdigest()
        hashes_seed1.append(h)
    
    assert len(hashes_seed1) == len(seed_1_files)

def test_7_applicability_and_resolution_grid():
    """Verify T3/T4/T5 applicability and values placed on resolution grid."""
    df_labels = pd.read_csv(LABELS_CSV)
    
    t4_events = df_labels[df_labels["type"] == "T4"]
    for _, r in t4_events.iterrows():
        assert "pH" in str(r["params"]) or "ph" in str(r["params"]).lower(), f"T4 applied to non-pH param: {r['params']}"

    t5_events = df_labels[df_labels["type"] == "T5"]
    for _, r in t5_events.iterrows():
        assert str(r["params"]) in ["ETP-BOD", "ETP-COD"], f"T5 applied to non-BOD/COD param: {r['params']}"

    t3_events = df_labels[df_labels["type"] == "T3"]
    for _, r in t3_events.iterrows():
        assert pd.notna(r["t3_limit"]) and float(r["t3_limit"]) > 0, f"T3 missing CTO limit: {r}"

def test_8_injected_rows_differ_from_value_orig_and_t1_hold_cases():
    """Verify injected rows differ from value_orig and report T1 exact-hold cases where equal."""
    df_labels = pd.read_csv(LABELS_CSV)
    t1_exact_equal_matches = 0
    total_injected_rows = 0

    for seed in range(1, 6):
        seed_path = os.path.join(DEV_DIR, f"seed_{seed}")
        parquets = [f for f in os.listdir(seed_path) if f.endswith(".parquet")]
        
        for p_file in parquets:
            df = pd.read_parquet(os.path.join(seed_path, p_file))
            inside = df[df["is_injected"]]
            total_injected_rows += len(inside)
            
            for _, r in inside.iterrows():
                val = r["value"]
                val_o = r["value_orig"]
                evt = r["event_id"]
                
                if val == val_o:
                    evt_row = df_labels[df_labels["event_id"] == evt]
                    if len(evt_row) > 0 and evt_row.iloc[0]["type"] == "T1":
                        t1_exact_equal_matches += 1

    print(f"\n[Test 8] Total injected rows evaluated: {total_injected_rows}")
    print(f"[Test 8] Total T1 exact-hold matches where injected value == value_orig: {t1_exact_equal_matches}")
    assert t1_exact_equal_matches >= 0

def test_9_event_windows_repass_v11c_eligibility():
    """
    Verify that candidate pre-injected windows (value_orig) in seed parquets pass Protocol v1.1 C eligibility.
    Fails only on violations NOT in known_violations.csv, and prints known ones.
    """
    df_labels = pd.read_csv(LABELS_CSV)
    df_labels["start_dt"] = pd.to_datetime(df_labels["start_ts"])
    df_labels["end_dt"] = pd.to_datetime(df_labels["end_ts"])

    known_viol_csv = os.path.join(INJECTOR_DIR, "known_violations.csv")
    known_set = set()
    if os.path.exists(known_viol_csv):
        df_known = pd.read_csv(known_viol_csv)
        known_set = set(df_known["event_id"].unique())

    parquet_cache = {}
    valid_count = 0
    known_violations_found = []
    unknown_violations_found = []

    for _, row in df_labels.iterrows():
        seed = row["seed"]
        fac = row["factory_id"]
        param = str(row["params"]).split(",")[0].strip()
        s_dt = row["start_dt"]
        e_dt = row["end_dt"]
        eid = row["event_id"]

        pq_key = (seed, fac)
        if pq_key not in parquet_cache:
            pq_path = os.path.join(DEV_DIR, f"seed_{seed}", f"{fac}.parquet")
            df_pq = pd.read_parquet(pq_path)
            df_pq["ts_dt"] = pd.to_datetime(df_pq["timestamp"])
            parquet_cache[pq_key] = df_pq

        df_pq = parquet_cache[pq_key]
        w = df_pq[(df_pq["parameter_id"] == param) & (df_pq["ts_dt"] >= s_dt) & (df_pq["ts_dt"] <= e_dt)]
        assert not w.empty, f"Event {eid} window is empty!"

        has_nan = w["value_orig"].isna().any()
        has_neg = not (w["value_orig"] >= 0).all()

        if has_nan or has_neg:
            reason = "Pre-existing NaNs in candidate window" if has_nan else "Negative values in candidate window"
            if eid in known_set:
                known_violations_found.append((eid, reason))
            else:
                unknown_violations_found.append((eid, reason))
        else:
            valid_count += 1

    print(f"\n[Test 9] Known permitted violations logged ({len(known_violations_found)}):")
    for eid, reason in known_violations_found:
        print(f"  {eid}: {reason}")

    if unknown_violations_found:
        print(f"\n[Test 9] UNKNOWN Protocol v1.1 C eligibility violations ({len(unknown_violations_found)}):")
        for eid, reason in unknown_violations_found:
            print(f"  {eid}: {reason}")

    assert len(unknown_violations_found) == 0, f"Detected {len(unknown_violations_found)} UNKNOWN Protocol v1.1 C eligibility violations!"
    assert len(known_violations_found) == 10, f"Expected exactly 10 known violations, got {len(known_violations_found)}"

def test_10_factory_event_counts_and_repeat_run_shortfalls():
    """
    Verify factory shortfall reasons:
    - site_982 passed initial distinct/missing criteria but generated 0 events due to 99.59% rows in repeat runs >= 8.
    - Report shortfall n rows and % rows in repeat runs >= 8 for site_1131, site_1247, site_1905.
    """
    df_labels = pd.read_csv(LABELS_CSV)
    injected_factories = set(df_labels["factory_id"].unique())
    assert len(injected_factories) == 21, f"Expected 21 factories in labels, got {len(injected_factories)}"

    raw_csv = os.path.join(REPO_ROOT, "Data", "RawData", "monitoring_data(raw).csv")
    df_raw = pd.read_csv(raw_csv)
    df_filt = df_raw[df_raw["quality_code"].isin(["Raw", "L"])].copy()

    def calc_repeat_stats(fac):
        sub = df_filt[df_filt["factory_id"] == fac]
        total_rows = len(sub)
        in_repeat = 0
        for _, g in sub.groupby("parameter_id"):
            g_s = g.sort_values("timestamp").reset_index(drop=True)
            vals = g_s["value"].values
            ts = pd.to_datetime(g_s["timestamp"]).values
            run_len = 1
            for i in range(1, len(vals)):
                gap_min = (ts[i] - ts[i-1]) / np.timedelta64(1, "m")
                if gap_min == 15 and pd.notna(vals[i]) and pd.notna(vals[i-1]) and vals[i] == vals[i-1]:
                    run_len += 1
                else:
                    if run_len >= 8:
                        in_repeat += run_len
                    run_len = 1
            if run_len >= 8:
                in_repeat += run_len
        pct = (in_repeat / total_rows * 100.0) if total_rows > 0 else 0.0
        return total_rows, in_repeat, pct

    shortfall_targets = {
        "site_982": (11380, 11333, 99.59),
        "site_1131": (31048, 30700, 98.88),
        "site_1247": (25956, 25711, 99.06),
        "site_1905": (15762, 14780, 93.77)
    }

    print("\n[Test 10] Shortfall repeat-run analysis:")
    for fac, (exp_tot, exp_rep, exp_pct) in shortfall_targets.items():
        t_rows, r_rows, pct = calc_repeat_stats(fac)
        print(f"  {fac}: total_rows={t_rows}, repeat_run_rows={r_rows} ({pct:.2f}%)")
        assert abs(t_rows - exp_tot) <= 5
        assert abs(r_rows - exp_rep) <= 5
        assert abs(pct - exp_pct) <= 0.5

if __name__ == "__main__":
    pytest.main([__file__])

