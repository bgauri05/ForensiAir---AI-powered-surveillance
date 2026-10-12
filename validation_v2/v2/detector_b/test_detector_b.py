"""
Unit Tests for ForensiAIR V2 Detector Components (test_detector_b.py)
Specification: Protocol v2.0 (Frozen) & Protocol v1.1 Section C (Frozen)

Verified Test Requirements:
1. Each component returns valid, documented outputs (bounded >= 0.0).
2. Constant, short, and partially missing series are handled safely without crash.
3. Applicable series do not produce entirely NaN score columns.
4. Past-only features strictly do not use future readings (strict causality).
5. Outputs are deterministic across identical runs.
6. Missing readings cannot independently trigger detections (produce NaN).
7. Components do not import or depend on injector labels or injector modules.
8. Existing V1 files remain completely unchanged.
9. Component-specific sensitivity:
   - F1B flags dithered freeze (p=0.15)
   - F2B flags gain-scaled replay (s=1.08)
   - F3B flags near-limit persistence (95% CTO limit)
   - F7B flags triangular matched-filter ramp
"""

import os
import sys
import subprocess
import pytest
import numpy as np
import pandas as pd

REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
DETECTOR_B_DIR = os.path.join(REPO_ROOT, "validation_v2", "v2", "detector_b")
sys.path.insert(0, DETECTOR_B_DIR)

from detector_b import (
    prepare_series,
    calc_mad,
    get_resolution_step,
    score_tail_prob,
    extract_if_b_features,
    fit_if_b,
    compute_check_statistics_b,
    calibrate_b,
    score_b,
    FEATURE_COLS_B
)

def make_synthetic_df(values, param="ETP-pH", fac="site_test"):
    """Helper to construct synthetic DataFrame on 15m grid."""
    ts = pd.date_range("2024-01-01", periods=len(values), freq="15min")
    return pd.DataFrame({
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "value": values,
        "parameter_id": param,
        "factory_id": fac,
        "quality_code": "Raw"
    })

# -----------------------------------------------------------------------------
# Test 1: Component Outputs and Non-Negative Scores
# -----------------------------------------------------------------------------
def test_1_component_outputs_valid_and_non_negative():
    """Verifies all components produce documented column names and scores >= 0.0."""
    rng = np.random.default_rng(42)
    vals = 7.0 + rng.normal(0, 0.5, 500)
    df_series = make_synthetic_df(vals, param="ETP-pH")
    mock_cto = {("site_test", "ETP-pH"): 9.0}

    calib = calibrate_b(df_series, mode="blind", cto_limits=mock_cto, factory_id="site_test")
    scored = score_b(df_series, calib, cto_limits=mock_cto, factory_id="site_test")

    # Documented columns must exist
    required_cols = [
        "F1B_var_collapse_w16_score", "F1B_var_collapse_w96_score", "F1B_var_collapse_w288_score",
        "F1B_unique_ratio_w96_score", "F1B_unique_ratio_w288_score",
        "F2B_znorm_dist_w16_score", "F2B_znorm_dist_w96_score", "F2B_znorm_dist_w288_score",
        "F3B_hug_persist_w16_score", "F3B_hug_persist_w96_score", "F3B_hug_persist_w288_score",
        "F3B_var_clamp_w96_score", "F3B_var_clamp_w288_score",
        "F7B_tri_conv_w16_score", "F7B_tri_conv_w96_score", "F7B_tri_conv_w288_score",
        "F7B_step_jump_w16_score", "F7B_step_jump_w96_score", "F7B_step_jump_w288_score",
        "F7B_transient_dev_w16_score", "F7B_transient_dev_w96_score",
        "if_b_score", "M1_fusion", "M2_fusion"
    ]
    for c in required_cols:
        assert c in scored.columns, f"Missing expected column: {c}"
        valid_vals = scored[c].dropna()
        if len(valid_vals) > 0:
            assert np.all(valid_vals >= 0.0), f"Scores in {c} must be >= 0.0, found negatives!"

# -----------------------------------------------------------------------------
# Test 2: Edge Cases: Constant, Short, and Missing Series
# -----------------------------------------------------------------------------
def test_2_constant_short_and_missing_series():
    """Verifies edge cases (constant series, short series < 16 rows, missing series) do not crash."""
    # A. Constant series
    const_vals = np.full(200, 7.50)
    df_const = make_synthetic_df(const_vals)
    calib_c = calibrate_b(df_const)
    sc_c = score_b(df_const, calib_c)
    assert not sc_c.empty
    assert "M2_fusion" in sc_c.columns

    # B. Short series (< 16 rows)
    short_vals = np.array([7.1, 7.2, 7.3, 7.2])
    df_short = make_synthetic_df(short_vals)
    calib_s = calibrate_b(df_short)
    sc_s = score_b(df_short, calib_s)
    assert len(sc_s) == len(short_vals)

    # C. Partially missing series
    vals_nan = np.array([7.1, np.nan, 7.3, np.nan, 7.5, 7.6, 7.4, 7.5] * 20)
    df_nan = make_synthetic_df(vals_nan)
    calib_nan = calibrate_b(df_nan)
    sc_nan = score_b(df_nan, calib_nan)
    assert len(sc_nan) == len(vals_nan)

# -----------------------------------------------------------------------------
# Test 3: Applicable Series Do Not Produce Entirely NaN Score Columns
# -----------------------------------------------------------------------------
def test_3_applicable_series_not_100pct_nan():
    """Ensures runtime guard guarantee: applicable series have non-empty valid scores."""
    rng = np.random.default_rng(42)
    n_pts = 1000
    vals = 25.0 + rng.normal(0, 3.0, n_pts)
    df_series = make_synthetic_df(vals, param="ETP-BOD", fac="site_test")
    mock_cto = {("site_test", "ETP-BOD"): 30.0}

    calib = calibrate_b(df_series, mode="blind", cto_limits=mock_cto, factory_id="site_test")
    scored = score_b(df_series, calib, cto_limits=mock_cto, factory_id="site_test")

    # Applicable checks: F1B, F2B, F3B, F7B, IF_B, M2_fusion
    for col in [
        "F1B_var_collapse_w16_score", "F1B_unique_ratio_w96_score",
        "F2B_znorm_dist_w16_score", "F3B_hug_persist_w16_score",
        "F7B_tri_conv_w16_score", "if_b_score", "M2_fusion"
    ]:
        n_valid = int(scored[col].notna().sum())
        assert n_valid > 10, f"Applicable check {col} produced 100% NaN (valid points = {n_valid})"

# -----------------------------------------------------------------------------
# Test 4: Strict Causality (No Future Data Leakage)
# -----------------------------------------------------------------------------
def test_4_strict_causality():
    """Asserts that features and scores at timestamp T are identical whether future data > T exists or is truncated."""
    rng = np.random.default_rng(42)
    n_pts = 600
    vals = 7.0 + rng.normal(0, 0.4, n_pts)
    df_full = make_synthetic_df(vals)
    df_trunc = df_full.iloc[:400].copy()

    # Features at row 350
    feats_full = extract_if_b_features(df_full).iloc[350]
    feats_trunc = extract_if_b_features(df_trunc).iloc[350]

    # Verify all feature values match to machine precision
    for col in FEATURE_COLS_B:
        v_f = feats_full[col]
        v_t = feats_trunc[col]
        if np.isnan(v_f) or np.isnan(v_t):
            assert np.isnan(v_f) and np.isnan(v_t)
        else:
            assert np.isclose(v_f, v_t, atol=1e-7), f"Causality leak detected in feature {col}!"

# -----------------------------------------------------------------------------
# Test 5: Determinism Across Runs
# -----------------------------------------------------------------------------
def test_5_determinism():
    """Asserts that identical inputs produce bitwise identical outputs."""
    rng = np.random.default_rng(101)
    vals = 50.0 + rng.normal(0, 5.0, 500)
    df1 = make_synthetic_df(vals.copy())
    df2 = make_synthetic_df(vals.copy())

    calib1 = calibrate_b(df1)
    calib2 = calibrate_b(df2)
    sc1 = score_b(df1, calib1)
    sc2 = score_b(df2, calib2)

    for c in ["M1_fusion", "M2_fusion", "F1B_var_collapse_w16_score", "F2B_znorm_dist_w16_score"]:
        assert np.allclose(sc1[c].fillna(-999).values, sc2[c].fillna(-999).values), f"Non-deterministic score in {c}"

# -----------------------------------------------------------------------------
# Test 6: Missing Readings Cannot Trigger Alerts (Produce NaN)
# -----------------------------------------------------------------------------
def test_6_missing_readings_produce_nan():
    """Asserts that any row with value=NaN produces NaN for all check scores and M2 fusion."""
    rng = np.random.default_rng(42)
    vals = 7.0 + rng.normal(0, 0.5, 400)
    vals[200:210] = np.nan  # 10 missing rows
    df_series = make_synthetic_df(vals)

    calib = calibrate_b(df_series)
    scored = score_b(df_series, calib)

    nan_rows = scored.iloc[200:210]
    for c in ["M1_fusion", "M2_fusion", "F1B_var_collapse_w16_score", "F2B_znorm_dist_w16_score", "if_b_score"]:
        assert np.all(nan_rows[c].isna()), f"Missing rows produced non-NaN score in {c}!"

# -----------------------------------------------------------------------------
# Test 7: Zero Dependency on Injector Labels or Injector Code
# -----------------------------------------------------------------------------
def test_7_no_injector_labels_dependency():
    """Asserts detector_b.py has zero imports from injector or references to injection label columns."""
    detector_b_py = os.path.join(DETECTOR_B_DIR, "detector_b.py")
    with open(detector_b_py, "r", encoding="utf-8") as f:
        code = f.read()

    forbidden_tokens = ["injector", "labels_b", "is_injected", "event_id", "severity", "t2_source", "p_flicker"]
    for tok in forbidden_tokens:
        assert tok not in code, f"Forbidden label/injector token '{tok}' found in detector_b.py!"

# -----------------------------------------------------------------------------
# Test 8: Frozen V1 Files Remain Completely Unchanged
# -----------------------------------------------------------------------------
def test_8_frozen_v1_files_unchanged():
    """Verifies git diff against detector-frozen tag is strictly empty for V1 files."""
    res = subprocess.run(
        ["git", "diff", "detector-frozen", "--", "validation_v2/detector", "validation_v2/injector"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True
    )
    assert res.returncode == 0, f"git diff failed: {res.stderr}"
    assert res.stdout.strip() == "", f"Frozen V1 files were modified: {res.stdout}"

# -----------------------------------------------------------------------------
# Test 9: Component Sensitivity on Planted Mechanism B Patterns
# -----------------------------------------------------------------------------
def test_9_component_sensitivity():
    """
    Asserts each V2 component flags its intended tampering pattern:
    - F1B flags dithered freeze (p=0.15)
    - F2B flags gain-scaled replay (s=1.08)
    - F3B flags near-limit persistence (95% of CTO limit)
    - F7B flags triangular matched-filter ramp
    """
    rng = np.random.default_rng(42)
    n_pts = 1000

    # A. F1B: Dithered freeze
    vals_f1 = 7.0 + rng.normal(0, 0.8, n_pts)
    med_val = np.median(vals_f1[:500])
    # Plant 64 rows of median freeze with bit flicker (p=0.15)
    flicker = rng.choice([-0.05, 0.0, 0.05], size=64, p=[0.075, 0.85, 0.075])
    vals_f1[500:564] = med_val + flicker
    df_f1 = make_synthetic_df(vals_f1)
    calib_f1 = calibrate_b(df_f1)
    sc_f1 = score_b(df_f1, calib_f1)
    max_planted_f1b = sc_f1["F1B_var_collapse_w16_score"].iloc[500:564].max()
    max_clean_f1b = sc_f1["F1B_var_collapse_w16_score"].iloc[:500].max()
    assert max_planted_f1b > max_clean_f1b, f"F1B did not elevate on dithered freeze ({max_planted_f1b:.2f} vs {max_clean_f1b:.2f})"

    # B. F2B: Gain-scaled replay (s=1.08)
    vals_f2 = 10.0 + rng.normal(0, 2.0, n_pts)
    donor = vals_f2[200:296].copy()
    # Plant scaled replay at lag 288 (rows 488:584)
    vals_f2[488:584] = 1.08 * donor
    df_f2 = make_synthetic_df(vals_f2)
    calib_f2 = calibrate_b(df_f2)
    sc_f2 = score_b(df_f2, calib_f2)
    max_planted_f2b = sc_f2["F2B_znorm_dist_w96_score"].iloc[488:584].max()
    max_clean_f2b = sc_f2["F2B_znorm_dist_w96_score"].iloc[:488].max()
    assert max_planted_f2b > max_clean_f2b, f"F2B did not elevate on scaled replay ({max_planted_f2b:.2f} vs {max_clean_f2b:.2f})"

    # C. F3B: Near-limit persistence (95% CTO limit)
    vals_f3 = 15.0 + rng.normal(0, 2.0, n_pts)
    cto_val = 30.0
    mock_cto3 = {("site_test", "ETP-pH"): cto_val}
    # Plant 64 rows of near-limit hugging at 28.5 (95% of 30)
    vals_f3[600:664] = 28.5 + rng.normal(0, 0.2, 64)
    df_f3 = make_synthetic_df(vals_f3)
    calib_f3 = calibrate_b(df_f3, cto_limits=mock_cto3, factory_id="site_test")
    sc_f3 = score_b(df_f3, calib_f3, cto_limits=mock_cto3, factory_id="site_test")
    max_planted_f3b = sc_f3["F3B_hug_persist_w16_score"].iloc[600:664].max()
    max_clean_f3b = sc_f3["F3B_hug_persist_w16_score"].iloc[:600].max()
    assert max_planted_f3b > max_clean_f3b, f"F3B did not elevate on near-limit persistence ({max_planted_f3b:.2f} vs {max_clean_f3b:.2f})"

    # D. F7B: Triangular bias ramp
    vals_f7 = 20.0 + rng.normal(0, 0.5, n_pts)
    w_ramp = 48
    idx_r = np.arange(w_ramp)
    ramp = 10.0 * (1.0 - np.abs(2.0 * idx_r - (w_ramp - 1)) / (w_ramp - 1))
    vals_f7[700:748] += ramp
    df_f7 = make_synthetic_df(vals_f7)
    calib_f7 = calibrate_b(df_f7)
    sc_f7 = score_b(df_f7, calib_f7)
    max_planted_f7b = sc_f7["F7B_tri_conv_w16_score"].iloc[700:748].max()
    max_clean_f7b = sc_f7["F7B_tri_conv_w16_score"].iloc[:700].max()
    assert max_planted_f7b > max_clean_f7b, f"F7B did not elevate on triangular ramp ({max_planted_f7b:.2f} vs {max_clean_f7b:.2f})"
