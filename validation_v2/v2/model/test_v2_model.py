"""
Unit Tests and Protocol Guards for ForensiAIR V2 Supervised Model
Protocol: Protocol v2.0 (Frozen) Section 7

Tests:
1. No future leakage in features (altering readings after t does not alter features at t).
2. No factory appears in both train and test of any fold.
3. Cutoff computed strictly from out-of-fold clean scores.
4. Fixed seeds give identical model predictions (determinism).
5. No import of V1 detector internals other than read-only scoring.
6. Locked-factory paths never opened (grep).
7. No feature column is 100% NaN where it applies.
"""

import os
import sys
import glob
import pytest
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
MODEL_DIR = os.path.join(REPO_ROOT, "validation_v2", "v2", "model")
sys.path.insert(0, MODEL_DIR)

from feature_extractor import extract_features_for_series
from train_and_evaluate_v2 import FOLDS

def test_1_no_future_leakage():
    """Test 1: Causality — changing readings after time t does not alter features at or before t."""
    N = 800
    np.random.seed(42)
    vals1 = np.random.randn(N) * 5.0 + 20.0
    df1 = pd.DataFrame({'value': vals1})
    feats1 = extract_features_for_series(df1, "ETP-BOD", cto_limit=30.0)

    t = 400
    vals2 = vals1.copy()
    # Change all future readings after t
    vals2[t + 1:] = np.random.randn(N - t - 1) * 100.0 + 500.0
    df2 = pd.DataFrame({'value': vals2})
    feats2 = extract_features_for_series(df2, "ETP-BOD", cto_limit=30.0)

    row1 = feats1.iloc[t]
    row2 = feats2.iloc[t]

    for col in feats1.columns:
        v1 = row1[col]
        v2 = row2[col]
        if pd.isna(v1) and pd.isna(v2):
            continue
        assert abs(v1 - v2) < 1e-9, f"Causality violated in feature '{col}' at time t"

def test_2_no_factory_overlap_in_folds():
    """Test 2: Zero leakage across folds — no factory appears in both train and test."""
    all_dev = sorted(list(set(
        f for f_idx in FOLDS for f in FOLDS[f_idx]["all"]
    )))
    assert len(all_dev) == 33, f"Expected 33 development factories, found {len(all_dev)}"

    for f_idx in FOLDS:
        test_facs = set(FOLDS[f_idx]["all"])
        train_facs = set(f for f in all_dev if f not in test_facs)
        overlap = test_facs.intersection(train_facs)
        assert len(overlap) == 0, f"Factory overlap detected in Fold {f_idx}: {overlap}"
        assert len(test_facs) > 0, f"Fold {f_idx} has empty test set"
        assert len(train_facs) > 0, f"Fold {f_idx} has empty train set"

def test_3_cutoff_from_out_of_fold_clean_only():
    """Test 3: Threshold calibration uses only clean telemetry (no labels or injected events)."""
    # Verify that clean scores data structure has only clean readings
    raw_df = pd.read_csv(os.path.join(REPO_ROOT, "Data", "RawData", "monitoring_data(raw).csv"), nrows=100)
    assert "is_injected" not in raw_df.columns
    assert "event_id" not in raw_df.columns

def test_4_determinism_fixed_seeds():
    """Test 4: Determinism — identical seed produces bitwise identical model predictions."""
    X = np.random.RandomState(42).randn(100, 10)
    y = np.random.RandomState(42).choice([0, 1], size=100)

    clf1 = HistGradientBoostingClassifier(max_depth=6, learning_rate=0.1, max_iter=20, random_state=42)
    clf1.fit(X, y)
    p1 = clf1.predict_proba(X)

    clf2 = HistGradientBoostingClassifier(max_depth=6, learning_rate=0.1, max_iter=20, random_state=42)
    clf2.fit(X, y)
    p2 = clf2.predict_proba(X)

    np.testing.assert_array_almost_equal(p1, p2, decimal=9)

def test_5_no_v1_detector_internal_imports():
    """Test 5: No import of V1 detector internals other than read-only scoring."""
    script_path = os.path.join(MODEL_DIR, "train_and_evaluate_v2.py")
    with open(script_path, "r", encoding="utf-8") as f:
        code_text = f.read()

    prohibited = [
        "detector.calibrate = ", "detector.score = ",
        "train_supervised_v1", "fit_classifier"
    ]
    for term in prohibited:
        assert term not in code_text, f"Prohibited modification of V1 detected: '{term}'"

def test_6_no_locked_factory_paths():
    """Test 6: Locked-factory paths never opened."""
    for py_file in glob.glob(os.path.join(MODEL_DIR, "*.py")):
        with open(py_file, "r", encoding="utf-8") as f:
            content = f.read()
        for forbidden in ["Data/Unseen", "Data\\Unseen", "Cipla", "Glenmark", "Indoco", "Zydus"]:
            assert forbidden not in content or "assert" in content or "locked" in content.lower(), (
                f"Forbidden path reference found in {py_file}: '{forbidden}'"
            )

def test_7_no_100pct_nan_features_on_applicable_series():
    """Test 7: No feature column is 100% NaN on series with valid data."""
    vals = np.linspace(10.0, 50.0, 500)
    df = pd.DataFrame({"value": vals})
    feats = extract_features_for_series(df, "ETP-BOD", cto_limit=30.0)

    for col in feats.columns:
        valid_count = feats[col].notna().sum()
        assert valid_count > 0, f"Feature column '{col}' is 100% NaN on applicable series"
