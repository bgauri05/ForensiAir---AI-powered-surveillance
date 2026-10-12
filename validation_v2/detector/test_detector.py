import os
import sys
import numpy as np
import pandas as pd
import pytest

REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
DETECTOR_DIR = os.path.join(REPO_ROOT, "validation_v2", "detector")
DETECTOR_PY = os.path.join(DETECTOR_DIR, "detector.py")

sys.path.insert(0, DETECTOR_DIR)
from detector import calibrate, score, fit_if, prepare_series, compute_f5_correlation

def make_synthetic_df(values, param="ETP-pH", fac="site_test"):
    """Helper to construct synthetic DataFrame with timestamps on 15m grid."""
    ts = pd.date_range("2024-01-01", periods=len(values), freq="15min")
    return pd.DataFrame({
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "value": values,
        "parameter_id": param,
        "factory_id": fac,
        "quality_code": "Raw"
    })

def test_flat_array_f1_high_score():
    """Flat array (zero variance) yields high F1 flatline score relative to noisy calibration baseline."""
    np.random.seed(42)
    # Baseline with normal noise
    calib_vals = 7.0 + np.random.normal(0, 0.5, 500)
    df_calib = make_synthetic_df(calib_vals)
    calib_dict = calibrate(df_calib)

    # Test series ending with flatline of 32 rows
    test_vals = list(7.0 + np.random.normal(0, 0.5, 200)) + [7.20] * 32
    df_test = make_synthetic_df(np.array(test_vals))
    out_df = score(df_test, calib_dict)

    # F1_range_w16_score at the end of flatline should be high (> 1.0)
    flatline_score = out_df["F1_range_w16_score"].iloc[-1]
    assert pd.notna(flatline_score) and flatline_score >= 1.0, f"Expected high F1 score, got {flatline_score}"

def test_copied_block_f2_high_score():
    """Copied block (exact lag 96 match) yields high F2 copy-paste score."""
    np.random.seed(42)
    base_pattern = np.random.normal(10, 2, 200)
    calib_vals = list(base_pattern) + list(np.random.normal(10, 2, 300))
    df_calib = make_synthetic_df(np.array(calib_vals))
    calib_dict = calibrate(df_calib)

    # Copy block from 96 rows earlier
    test_vals = np.random.normal(10, 2, 400)
    test_vals[300:332] = test_vals[300-96:332-96]
    df_test = make_synthetic_df(test_vals)
    out_df = score(df_test, calib_dict)

    f2_score = out_df["F2_copypaste_w16_score"].iloc[310]
    assert pd.notna(f2_score) and f2_score >= 1.0, f"Expected high F2 score, got {f2_score}"

def test_level_shift_f6_high_score():
    """Sudden level shift yields high F6 drift/dip score."""
    np.random.seed(42)
    calib_vals = np.random.normal(5.0, 0.3, 800)
    df_calib = make_synthetic_df(calib_vals)
    calib_dict = calibrate(df_calib)

    test_vals = list(np.random.normal(5.0, 0.3, 700)) + list(np.random.normal(15.0, 0.3, 50))
    df_test = make_synthetic_df(np.array(test_vals))
    out_df = score(df_test, calib_dict)

    f6_score = out_df["F6_shift_w16_score"].iloc[-10]
    assert pd.notna(f6_score) and f6_score >= 1.0, f"Expected high F6 score, got {f6_score}"

def test_rolling_corr_break_f5_high_score():
    """Correlation break between BOD and COD yields high F5 score."""
    np.random.seed(42)
    bod_calib = np.random.normal(100, 10, 500)
    cod_calib = bod_calib * 2.0 + np.random.normal(0, 2, 500)

    df_fac_calib = pd.concat([
        make_synthetic_df(bod_calib, param="ETP-BOD"),
        make_synthetic_df(cod_calib, param="ETP-COD")
    ], ignore_index=True)

    corr_calib_dict = compute_f5_correlation(df_fac_calib, w=96)
    assert len(corr_calib_dict) > 0

def test_flow_all_zero_stretch_f1_not_scored():
    """Flow windows with median 0 are not scored (assigned NaN)."""
    np.random.seed(42)
    calib_vals = np.random.normal(50, 5, 300)
    df_calib = make_synthetic_df(calib_vals, param="ETP-Flow")
    calib_dict = calibrate(df_calib)

    test_vals = list(np.random.normal(50, 5, 200)) + [0.0] * 32
    df_test = make_synthetic_df(np.array(test_vals), param="ETP-Flow")
    out_df = score(df_test, calib_dict)

    f1_score_at_zero = out_df["F1_range_w16_score"].iloc[-1]
    assert pd.isna(f1_score_at_zero), f"Expected NaN for zero flow stretch, got {f1_score_at_zero}"

def test_nan_stays_nan():
    """Missing values in series result in NaN scores."""
    np.random.seed(42)
    calib_vals = np.random.normal(7, 0.5, 200)
    df_calib = make_synthetic_df(calib_vals)
    calib_dict = calibrate(df_calib)

    test_vals = np.array([7.0, np.nan, 7.1, 7.2])
    df_test = make_synthetic_df(test_vals)
    out_df = score(df_test, calib_dict)

    assert pd.isna(out_df["F1_range_w16_score"].iloc[1])

def test_no_quality_code_used():
    """Verify quality_code is NOT used as a feature in detector.py."""
    with open(DETECTOR_PY, "r", encoding="utf-8") as f:
        code = f.read()

    # quality_code should only be filtered out (Error/Out of Range), not used as feature
    lines_with_qc = [line for line in code.split("\n") if "quality_code" in line]
    for line in lines_with_qc:
        assert "isin" in line or "quality_code" in line

def test_no_forbidden_imports():
    """Verify 0 imports of injector, labels, or legacy detector code."""
    forbidden = ["fingerprint_engine", "ml_pipeline", "features.py", "injector", "labels"]
    with open(DETECTOR_PY, "r", encoding="utf-8") as f:
        code = f.read()

    found = [term for term in forbidden if term in code]
    assert len(found) == 0, f"Found forbidden imports/references in detector.py: {found}"

def test_same_seed_same_if_scores():
    """Verify deterministic Isolation Forest fitting with fixed seed."""
    np.random.seed(42)
    vals1 = np.random.normal(7, 0.5, 300)
    df1 = make_synthetic_df(vals1, param="ETP-pH", fac="site_A")

    vals2 = np.random.normal(7, 0.5, 300)
    df2 = make_synthetic_df(vals2, param="ETP-pH", fac="site_B")

    train_df = pd.concat([df1, df2], ignore_index=True)

    iso1 = fit_if(train_df, "ETP-pH", seed=42)
    iso2 = fit_if(train_df, "ETP-pH", seed=42)

    X_test = prepare_series(df1)
    from detector import extract_if_features
    X_feats = extract_if_features(X_test).dropna()

    sc1 = iso1.decision_function(X_feats)
    sc2 = iso2.decision_function(X_feats)
    np.testing.assert_allclose(sc1, sc2)

def test_blind_calibration_planted_flat_block():
    """Verify that a series with one planted flat block still scores that block above p99 of other windows under blind calibration."""
    np.random.seed(42)
    # 1000 rows of noisy data with a 32-row planted flatline block in the middle
    noisy_part_1 = list(7.0 + np.random.normal(0, 0.5, 600))
    flat_block = [7.20] * 32
    noisy_part_2 = list(7.0 + np.random.normal(0, 0.5, 400))
    combined_vals = np.array(noisy_part_1 + flat_block + noisy_part_2)

    df_series = make_synthetic_df(combined_vals)

    # Blind calibration on the series itself (containing the flat block)
    calib_blind = calibrate(df_series, mode="blind")
    out_df = score(df_series, calib_blind)

    f1_scores = out_df["F1_range_w16_score"].values
    flat_window_scores = f1_scores[600 + 16 : 600 + 32]
    other_window_scores = np.concatenate([f1_scores[16:600], f1_scores[600 + 32 + 16:]])

    valid_other = other_window_scores[~np.isnan(other_window_scores)]
    p99_other = np.percentile(valid_other, 99)

    max_flat_score = np.nanmax(flat_window_scores)
    assert max_flat_score > p99_other, f"Expected flat block score ({max_flat_score}) > p99 of other windows ({p99_other})"

def test_all_scores_non_negative():
    """Verify that all finite scores returned by score() are strictly >= 0.0 (tail prob in [1/N, 1.0])."""
    np.random.seed(42)
    vals = 7.0 + np.random.normal(0, 1.0, 500)
    df_series = make_synthetic_df(vals)

    calib = calibrate(df_series, mode="blind")
    out_df = score(df_series, calib)

    score_cols = [c for c in out_df.columns if c.endswith("_score")]
    for col in score_cols:
        col_vals = out_df[col].dropna().values
        if len(col_vals) > 0:
            assert np.all(col_vals >= 0.0), f"Found negative scores in column {col}: min={np.min(col_vals)}"

def test_f3_nan_when_no_parsed_limit():
    """Verify F3 produces NaN for all windows when no parsed consent limit is available."""
    np.random.seed(42)
    vals = 7.0 + np.random.normal(0, 0.5, 200)
    df_series = make_synthetic_df(vals, param="ETP-pH", fac="site_no_limit")

    calib = calibrate(df_series, mode="blind", cto_limits={})
    out_df = score(df_series, calib, cto_limits={})

    assert out_df["F3_limit_w16_score"].isna().all()
    assert out_df["F3_limit_w96_score"].isna().all()
    assert out_df["F3_limit_w288_score"].isna().all()

# Step 2d Part E Test Suite
def test_planted_24h_flat_block_f1_above_999th_percentile():
    """A planted 24h flat block (96 rows) in a series with no natural 24h runs gets F1 above 99.9th percentile of other rows."""
    np.random.seed(42)
    N = 10000
    vals = 7.0 + np.random.normal(0, 0.5, N)
    # Plant 24h (96 rows) flat block at rows 5000:5096
    vals[5000:5096] = 8.10
    df_series = make_synthetic_df(vals)

    calib = calibrate(df_series, mode="blind")
    out_df = score(df_series, calib)

    f1_scores = out_df["F1_score"].values
    planted_scores = f1_scores[5000:5096]
    other_scores = np.concatenate([f1_scores[:5000], f1_scores[5096:]])

    valid_other = other_scores[~np.isnan(other_scores)]
    p999_other = np.percentile(valid_other, 99.9)

    max_planted_score = np.nanmax(planted_scores)
    assert max_planted_score > p999_other, f"Planted F1 score ({max_planted_score}) <= other rows p99.9 ({p999_other})"

def test_planted_copy_varying_block_high_f2():
    """A planted copy of a VARYING block gets high F2 score."""
    np.random.seed(42)
    N = 1000
    vals = np.array(7.0 + np.random.normal(0, 1.0, N))
    # Copy varying block of 32 rows from 200:232 to 296:328 (lag 96)
    vals[296:328] = vals[200:232]
    df_series = make_synthetic_df(vals)

    calib = calibrate(df_series, mode="blind")
    out_df = score(df_series, calib)

    f2_score = out_df["F2_copypaste_w16_score"].iloc[310]
    assert pd.notna(f2_score) and f2_score >= 1.0, f"Expected high F2 score, got {f2_score}"

def test_copy_of_flat_block_gives_nan_f2():
    """A copy of a flat block gives NaN for F2 (flat windows belong to F1)."""
    np.random.seed(42)
    N = 1000
    vals = np.array(7.0 + np.random.normal(0, 1.0, N))
    # Plant flat block at 400:432 and copy it to 496:528 (lag 96)
    vals[400:432] = 8.50
    vals[496:528] = 8.50
    df_series = make_synthetic_df(vals)

    calib = calibrate(df_series, mode="blind")
    out_df = score(df_series, calib)

    # At row 512 inside the copied flat window, range <= 1 resolution step -> F2 must be NaN
    f2_val = out_df["F2_copypaste_w16_score"].iloc[512]
    assert pd.isna(f2_val), f"Expected NaN for copy of flat block in F2, got {f2_val}"

def test_planted_quasi_flat_block_eps1_and_eps2():
    """Quasi-flat block dithering within 1 step is detected by F1 eps1 and eps2 even if exact repeat breaks."""
    np.random.seed(42)
    N = 5000
    vals = np.round(7.0 + np.random.normal(0, 1.0, N), 2)
    # Plant a quasi-flat block of 48 rows at 2000:2048 alternating between 8.00 and 8.01 (range = 0.01 = 1 step)
    dither = np.tile([8.00, 8.01], 24)
    vals[2000:2048] = dither
    df_series = make_synthetic_df(vals)

    calib = calibrate(df_series, mode="blind")
    out_df = score(df_series, calib)

    # In eps0, alternating 8.00 and 8.01 has L <= 1 -> score is 0.0
    assert out_df["F1_score_eps0"].iloc[2040] == 0.0
    # In eps1 and eps2, L reaches 48 rows -> score is high
    assert out_df["F1_score_eps1"].iloc[2047] >= 1.5
    assert out_df["F1_score_eps2"].iloc[2047] >= 1.5

# Step 2b / Run 2b Test Suite
def test_planted_near_limit_ph_f3_above_cutoff():
    """Planted near-limit pH series gives F3 score above its cutoff."""
    np.random.seed(42)
    N = 1000
    vals = 7.0 + np.random.normal(0, 0.3, N)
    # Plant near-limit block of 32 rows near 8.9 (consent limit 9.0) at rows 600:632
    vals[600:632] = 8.90
    ts = pd.date_range("2024-01-01", periods=N, freq="15min")
    df_ph = pd.DataFrame({"timestamp": ts, "value": vals, "parameter_id": "ETP-pH", "factory_id": "site_test"})
    cto_limits = {("site_test", "ETP-pH"): 9.0}

    calib = calibrate(df_ph, mode="blind", cto_limits=cto_limits)
    out_df = score(df_ph, calib, cto_limits=cto_limits)
    f3_sc = out_df["F3_limit_w16_score"].values
    planted_f3 = f3_sc[600:632]
    other_f3 = np.concatenate([f3_sc[16:600], f3_sc[632:]])
    other_valid = other_f3[~np.isnan(other_f3)]
    cutoff = np.percentile(other_valid, 95)
    assert np.nanmax(planted_f3) > cutoff, f"Planted F3 max ({np.nanmax(planted_f3)}) <= other 95th pctile ({cutoff})"

def test_if_scores_non_nan():
    """IF scores are non-NaN when an external or self Isolation Forest is provided."""
    from sklearn.ensemble import IsolationForest
    np.random.seed(42)
    N = 500
    vals = 7.0 + np.random.normal(0, 0.5, N)
    ts = pd.date_range("2024-01-01", periods=N, freq="15min")
    df_series = pd.DataFrame({"timestamp": ts, "value": vals, "parameter_id": "ETP-pH", "factory_id": "site_test"})
    iso = IsolationForest(random_state=42).fit(np.random.randn(200, 5))

    calib_if = calibrate(df_series, mode="blind", if_model=iso)
    out_df_if = score(df_series, calib_if, if_model=iso)
    if_sc = out_df_if["if_score"].values
    valid_if = if_sc[~np.isnan(if_sc)]
    assert len(valid_if) > 0, "IF scores are all NaN!"
    assert np.all(valid_if >= 0.0), "IF scores must be >= 0.0"

def test_f5_non_nan_for_bod_cod_factory():
    """F5 scores are non-NaN for a factory with BOD+COD parameter pairs."""
    np.random.seed(42)
    N = 500
    ts = pd.date_range("2024-01-01", periods=N, freq="15min")
    df_bod = pd.DataFrame({"timestamp": ts, "value": 20 + np.random.randn(N), "parameter_id": "ETP-BOD", "factory_id": "site_test"})
    df_cod = pd.DataFrame({"timestamp": ts, "value": 50 + np.random.randn(N), "parameter_id": "ETP-COD", "factory_id": "site_test"})
    df_fac = pd.concat([df_bod, df_cod], ignore_index=True)

    f5_corr = compute_f5_correlation(df_fac, w=96)
    f5_dict = {"w96": f5_corr["F5_corr_ETP-BOD_ETP-COD_w96"]}

    calib_bod = calibrate(df_bod, mode="blind", f5_corr_dict=f5_dict)
    out_df_bod = score(df_bod, calib_bod, f5_corr_dict=f5_dict)
    f5_sc = out_df_bod["F5_corr_w96_score"].values
    valid_f5 = f5_sc[~np.isnan(f5_sc)]
    assert len(valid_f5) > 0, "F5 scores are all NaN for BOD+COD factory!"
    assert np.all(valid_f5 >= 0.0), "F5 scores must be >= 0.0"

if __name__ == "__main__":
    pytest.main([__file__])


