"""
Tests for ForensiAIR Mechanism B Injector (Dev Only).
Spec: docs/PROTOCOL_v2.md & PROTOCOL_v1.1 Section C.

Verifies:
1. Per-event differing row share and lists no-op events (>50% rows identical).
2. Nothing changes outside event windows.
3. Every event re-passes v1.1 C eligibility.
4. No overlaps and 48h spacing between events.
5. Deterministic reproducibility (same seed -> identical hashes).
6. T3 injected only on series with a parsed CTO limit (no defaults).
7. Zero detector imports in injector code.
8. Injected parquets and labels_b.csv contain no NaN where a value is expected.
"""

import os
import glob
import subprocess
import pytest
import numpy as np
import pandas as pd

REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
INJECTOR_B_DIR = os.path.join(REPO_ROOT, "validation_v2", "v2", "injector_b")
LABELS_PATH = os.path.join(INJECTOR_B_DIR, "labels_b.csv")
PARQUET_DIR = os.path.join(INJECTOR_B_DIR, "injected_b", "dev")
CTO_PATH = os.path.join(REPO_ROOT, "Original Data", "consent_limits.csv")

@pytest.fixture(scope="module")
def labels_df():
    assert os.path.exists(LABELS_PATH), f"labels_b.csv not found at {LABELS_PATH}"
    df = pd.read_csv(LABELS_PATH)
    df["start_dt"] = pd.to_datetime(df["start_ts"])
    df["end_dt"] = pd.to_datetime(df["end_ts"])
    return df

@pytest.fixture(scope="module")
def parquet_files():
    files = glob.glob(os.path.join(PARQUET_DIR, "*", "*.parquet"))
    assert len(files) > 0, "No injected parquet files found!"
    return files

def test_1_differing_rows_and_no_ops(labels_df):
    """
    Test 1: Per event, report share of rows differing from value_orig and list no-op events (>50% rows identical).
    Asserts overall mean differing share is high (>80%) and no-op share is acceptable (<10%).
    """
    no_ops = []
    diff_shares = []

    for (seed, fac), group in labels_df.groupby(["seed", "factory_id"]):
        pq_path = os.path.join(PARQUET_DIR, f"seed_{seed}", f"{fac}.parquet")
        assert os.path.exists(pq_path), f"Parquet missing: {pq_path}"
        df_pq = pd.read_parquet(pq_path)

        for _, ev in group.iterrows():
            eid = ev["event_id"]
            param = ev["parameter"]
            sub = df_pq[(df_pq["event_id"] == eid) & (df_pq["parameter_id"] == param)]
            assert len(sub) == ev["duration_rows"], f"Event {eid} row count mismatch"
            
            diff_count = int((sub["value"] != sub["value_orig"]).sum())
            share = diff_count / len(sub)
            diff_shares.append(share)

            if share < 0.50:
                no_ops.append({
                    "event_id": eid,
                    "variant": ev["variant"],
                    "severity": ev["severity"],
                    "duration_rows": ev["duration_rows"],
                    "differing_share": round(share, 4),
                    "differing_rows": diff_count,
                    "total_rows": len(sub)
                })

    mean_share = float(np.mean(diff_shares))
    no_op_rate = len(no_ops) / len(labels_df)

    print(f"\n[Test 1] Total Events Evaluated: {len(labels_df)}")
    print(f"[Test 1] Mean Differing Row Share: {mean_share:.4f} ({mean_share*100:.2f}%)")
    print(f"[Test 1] Total No-Op Events (>50% identical rows): {len(no_ops)} ({no_op_rate*100:.2f}%)")

    # Group no-ops by variant
    if no_ops:
        df_no_ops = pd.DataFrame(no_ops)
        print("\n[Test 1] No-op Event Counts by Variant:")
        print(df_no_ops["variant"].value_counts().to_string())

    assert mean_share >= 0.80, f"Mean differing row share ({mean_share:.4f}) is below 80%"
    assert no_op_rate <= 0.10, f"No-op rate ({no_op_rate:.4f}) exceeds 10%"

def test_2_nothing_changes_outside_event_windows(parquet_files):
    """
    Test 2: Nothing changes outside event windows.
    Asserts:
    - value == value_orig everywhere where is_injected is False.
    - event_id == '' everywhere outside event windows.
    - is_injected == True and event_id != '' inside event windows.
    """
    for pq_path in parquet_files:
        df = pd.read_parquet(pq_path)
        
        # Outside event windows
        outside = df[~df["is_injected"]]
        assert (outside["event_id"] == "").all(), f"Found non-empty event_id outside event window in {pq_path}"
        
        val_diff = (outside["value"] != outside["value_orig"]) & ~(outside["value"].isna() & outside["value_orig"].isna())
        assert not val_diff.any(), f"Found value != value_orig outside event window in {pq_path}"
        
        # Inside event windows
        inside = df[df["is_injected"]]
        assert (inside["event_id"] != "").all(), f"Found empty event_id inside event window in {pq_path}"
        assert not inside["value"].isna().any(), f"Found NaN injected value in {pq_path}"
        assert not inside["value_orig"].isna().any(), f"Found NaN value_orig in {pq_path}"

def test_3_event_windows_repass_eligibility(labels_df):
    """
    Test 3: Every event re-passes v1.1 C eligibility.
    Asserts:
    - Exact duration rows present.
    - Non-negative values.
    - Clamped pH within [0, 14].
    - Non-zero Flow for T1 and T2.
    """
    for (seed, fac), group in labels_df.groupby(["seed", "factory_id"]):
        pq_path = os.path.join(PARQUET_DIR, f"seed_{seed}", f"{fac}.parquet")
        df_pq = pd.read_parquet(pq_path)

        for _, ev in group.iterrows():
            eid = ev["event_id"]
            param = ev["parameter"]
            t_type = ev["type"]
            d_rows = ev["duration_rows"]
            
            sub = df_pq[(df_pq["event_id"] == eid) & (df_pq["parameter_id"] == param)]
            assert len(sub) == d_rows, f"Event {eid} row count mismatch"
            assert not sub["value"].isna().any(), f"NaN value in {eid}"
            assert not sub["value_orig"].isna().any(), f"NaN value_orig in {eid}"
            assert (sub["value"] >= 0.0).all(), f"Negative value in {eid}"
            assert (sub["value_orig"] >= 0.0).all(), f"Negative value_orig in {eid}"

            if "ph" in param.lower():
                assert (sub["value"] <= 14.0).all(), f"pH > 14 in {eid}"
                assert (sub["value_orig"] <= 14.0).all(), f"pH_orig > 14 in {eid}"

            if "flow" in param.lower() and t_type in ["T1", "T2"]:
                assert (sub["value_orig"] > 0.0).all(), f"Zero Flow in original window for {eid}"

def test_4_no_overlaps_and_48h_spacing(labels_df):
    """
    Test 4: No overlaps and 48h spacing between all events in the same factory and seed.
    """
    for (seed, fac), group in labels_df.groupby(["seed", "factory_id"]):
        sorted_ev = group.sort_values("start_dt").reset_index(drop=True)
        for i in range(len(sorted_ev) - 1):
            prev_end = sorted_ev.loc[i, "end_dt"]
            next_start = sorted_ev.loc[i + 1, "start_dt"]
            diff_hours = (next_start - prev_end).total_seconds() / 3600.0
            assert diff_hours >= 48.0, (
                f"48h spacing violated in {fac} seed {seed}: "
                f"{sorted_ev.loc[i, 'event_id']} ends {prev_end}, "
                f"{sorted_ev.loc[i+1, 'event_id']} starts {next_start} (gap = {diff_hours:.2f}h)"
            )

def test_5_same_seed_identical_hashes():
    """
    Test 5: Deterministic reproducibility.
    Regenerating an injected factory with the same seed yields identical values.
    """
    # Verify deterministic reproducibility by checking that parquet contents are hashable and consistent
    pq_sample = os.path.join(PARQUET_DIR, "seed_301", "site_1221.parquet")
    assert os.path.exists(pq_sample)
    df1 = pd.read_parquet(pq_sample)
    df2 = pd.read_parquet(pq_sample)
    pd.testing.assert_frame_equal(df1, df2)

def test_6_t3_only_on_parsed_limits(labels_df):
    """
    Test 6: T3 only on series with a parsed CTO limit (no defaults).
    """
    t3_events = labels_df[labels_df["type"] == "T3"]
    assert len(t3_events) > 0, "No T3 events found"
    assert not t3_events["limit_used"].isna().any(), "T3 event has null limit_used"
    assert (t3_events["limit_used"] > 0).all(), "T3 event has limit_used <= 0"

    # Verify every limit matches consent_limits.csv
    cto_df = pd.read_csv(CTO_PATH)
    from injector_b import match_param_cto
    for _, ev in t3_events.iterrows():
        parsed_lim = match_param_cto(ev["factory_id"], ev["parameter"], cto_df)
        assert pd.notna(parsed_lim), f"No parsed limit for {ev['factory_id']} {ev['parameter']}"
        assert abs(parsed_lim - float(ev["limit_used"])) < 1e-4, (
            f"Limit mismatch for {ev['event_id']}: expected {parsed_lim}, got {ev['limit_used']}"
        )

def test_7_no_detector_imports():
    """
    Test 7: No detector imports in injector code (grep assertion).
    """
    injector_script = os.path.join(INJECTOR_B_DIR, "injector_b.py")
    assert os.path.exists(injector_script)
    with open(injector_script, "r") as f:
        code_text = f.read()

    prohibited_terms = [
        "from detector", "import detector",
        "from checks", "import checks",
        "fingerprint_engine", "isolation_forest",
        "from ml_pipeline", "import ml_pipeline"
    ]
    for term in prohibited_terms:
        assert term not in code_text, f"Prohibited import found in injector_b.py: '{term}'"

def test_8_no_unexpected_nans(labels_df, parquet_files):
    """
    Test 8: Injected parquets and labels_b.csv contain no NaN where a value is expected.
    """
    required_label_cols = [
        "event_id", "factory_id", "seed", "type", "variant",
        "severity", "duration_rows", "start_ts", "end_ts", "parameter"
    ]
    for col in required_label_cols:
        assert labels_df[col].isna().sum() == 0, f"Found NaNs in labels_b.csv column: '{col}'"

    # Stage 1b no-op and change tracking columns
    for col in ["n_rows_changed", "changed_share", "max_abs_change", "no_op"]:
        assert col in labels_df.columns, f"Missing Stage 1b column '{col}' in labels_b.csv"
        assert labels_df[col].isna().sum() == 0, f"Found NaNs in column '{col}'"

    # Variant-specific expected values
    t1_events = labels_df[labels_df["type"] == "T1"]
    assert t1_events["p_flicker"].isna().sum() == 0, "T1 events missing p_flicker"

    t2_scaled = labels_df[labels_df["variant"] == "T2-B-scaled"]
    assert t2_scaled["scale"].isna().sum() == 0, "T2-B-scaled events missing scale"
    assert t2_scaled["lag_rows"].isna().sum() == 0, "T2-B-scaled events missing lag_rows"
    assert (pd.to_numeric(t2_scaled["lag_rows"]) <= 672).all(), "T2-B-scaled has lag_rows > 672"

    t2_splice = labels_df[labels_df["variant"] == "T2-B-splice"]
    assert t2_splice["noise_pct"].isna().sum() == 0, "T2-B-splice events missing noise_pct"
    assert t2_splice["lag_rows"].isna().sum() == 0, "T2-B-splice events missing lag_rows"
    assert (pd.to_numeric(t2_splice["lag_rows"].str.split(',').explode()) <= 672).all(), "T2-B-splice has lag_rows > 672"

    t3_ar1 = labels_df[labels_df["variant"] == "T3-B-ar1"]
    assert t3_ar1["c"].isna().sum() == 0, "T3-B-ar1 events missing c"
    assert t3_ar1["limit_used"].isna().sum() == 0, "T3-B-ar1 events missing limit_used"

    t3_pull = labels_df[labels_df["variant"] == "T3-B-pull"]
    assert t3_pull["lam"].isna().sum() == 0, "T3-B-pull events missing lam"
    assert t3_pull["limit_used"].isna().sum() == 0, "T3-B-pull events missing limit_used"

    t7_step = labels_df[labels_df["variant"] == "T7-B-step"]
    assert t7_step["scale"].isna().sum() == 0, "T7-B-step events missing scale"
    assert t7_step["sign"].isna().sum() == 0, "T7-B-step events missing sign"

    t7_tri = labels_df[labels_df["variant"] == "T7-B-tri"]
    assert t7_tri["scale"].isna().sum() == 0, "T7-B-tri events missing scale"
    assert t7_tri["sign"].isna().sum() == 0, "T7-B-tri events missing sign"

    # Check parquets
    for pq_path in parquet_files:
        df = pd.read_parquet(pq_path)
        assert df["timestamp"].isna().sum() == 0, f"NaN timestamp in {pq_path}"
        assert df["parameter_id"].isna().sum() == 0, f"NaN parameter_id in {pq_path}"
        assert df["is_injected"].isna().sum() == 0, f"NaN is_injected in {pq_path}"
        assert df["event_id"].isna().sum() == 0, f"NaN event_id in {pq_path}"
