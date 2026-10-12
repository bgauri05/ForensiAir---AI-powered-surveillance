import os
import sys
import numpy as np
import pandas as pd
import pytest

REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
EVAL_DIR = os.path.join(REPO_ROOT, "validation_v2", "evaluator")

sys.path.insert(0, EVAL_DIR)
from evaluator import count_false_alarm_episodes, compute_cluster_bootstrap_ci

def test_episode_clustering_gaps():
    """Verify that alerts separated by < 8 rows are merged, and >= 8 rows form distinct episodes."""
    scores = np.array([0.1, 0.5, 0.6, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.6, 0.1])
    values = np.ones(len(scores)) * 7.0
    tau = 0.4

    # Indices of > 0.4 are: [1, 2] (gap 1 -> same episode) and [9] (gap 9-2 = 7? wait, 9-2=7 is < 8!)
    # Let's test explicit gaps:
    scores_2 = np.zeros(30)
    scores_2[0] = 0.5
    scores_2[1] = 0.5
    # Gap of 10 rows: index 1 to 11
    scores_2[11] = 0.5
    values_2 = np.ones(30) * 7.0

    episodes = count_false_alarm_episodes(scores_2, values_2, threshold=0.4)
    assert episodes == 2, f"Expected 2 episodes for gap >= 8, got {episodes}"

def test_missing_data_zero_alerts():
    """Verify missing readings (NaN values or NaN scores) produce 0 alert episodes."""
    scores = np.array([0.9, 0.9, 0.9])
    values = np.array([np.nan, np.nan, np.nan])

    episodes = count_false_alarm_episodes(scores, values, threshold=0.5)
    assert episodes == 0, f"Expected 0 episodes for NaN values, got {episodes}"

def test_t6_excluded_from_headline():
    """Verify compute_cluster_bootstrap_ci excludes T6 events from headline recall."""
    df_dummy = pd.DataFrame([
        {"factory_id": "fac1", "type": "T1", "is_detected": True},
        {"factory_id": "fac1", "type": "T6", "is_detected": False},
        {"factory_id": "fac2", "type": "T4", "is_detected": True},
        {"factory_id": "fac2", "type": "T6", "is_detected": False},
    ])
    mean_rec, ci_l, ci_u = compute_cluster_bootstrap_ci(df_dummy, n_bootstraps=50, seed=42)
    assert mean_rec == 1.0, f"Expected headline recall 1.0 (excluding T6), got {mean_rec}"

def test_evaluation_artifacts_exist():
    """Verify all Step 4 evaluation output CSVs are present and non-empty."""
    summary_csv = os.path.join(EVAL_DIR, "evaluation_summary.csv")
    type_csv = os.path.join(EVAL_DIR, "lofo_recall_by_type.csv")
    sev_csv = os.path.join(EVAL_DIR, "lofo_recall_by_severity.csv")
    dur_csv = os.path.join(EVAL_DIR, "lofo_recall_by_duration.csv")

    assert os.path.exists(summary_csv) and os.path.getsize(summary_csv) > 0
    assert os.path.exists(type_csv) and os.path.getsize(type_csv) > 0
    assert os.path.exists(sev_csv) and os.path.getsize(sev_csv) > 0
    assert os.path.exists(dur_csv) and os.path.getsize(dur_csv) > 0

def test_lofo_beats_baselines():
    """Verify New 33-Fold LOFO Detector achieves higher headline recall than baselines."""
    summary_csv = os.path.join(EVAL_DIR, "evaluation_summary.csv")
    df_sum = pd.read_csv(summary_csv)
    
    lofo_rec = df_sum[df_sum["Method"] == "New 33-Fold LOFO Detector"]["Headline Recall"].values[0]
    zscore_rec = df_sum[df_sum["Method"] == "Rolling Z-Score Baseline"]["Headline Recall"].values[0]
    static_rec = df_sum[df_sum["Method"] == "Static Limit Baseline"]["Headline Recall"].values[0]
    legacy_rec = df_sum[df_sum["Method"] == "Legacy Baseline"]["Headline Recall"].values[0]

    assert lofo_rec > zscore_rec
    assert lofo_rec > static_rec
    assert lofo_rec > legacy_rec
