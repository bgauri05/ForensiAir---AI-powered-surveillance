import os
import sys
import time
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

# Set paths
REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
MODEL_DIR = os.path.join(REPO_ROOT, "validation_v2", "v2", "model")
ANALYSIS_DIR = os.path.join(MODEL_DIR, "analysis")
os.makedirs(ANALYSIS_DIR, exist_ok=True)

sys.path.insert(0, MODEL_DIR)
from train_and_evaluate_v2 import (
    FACTORY_MONTHS, TOTAL_FACTORY_MONTHS, FOLDS,
    extract_alert_episodes, compute_v1_scores_for_series, V1_CUTOFFS
)

all_dev_factories = list(FACTORY_MONTHS.keys())

print("=" * 80)
print("STARTING V2 ANALYSIS (READ-ONLY DEVELOPMENT EVALUATION, POST-HOC)")
print("=" * 80)

# -----------------------------------------------------------------------------
# 1. Load Precomputed Evaluation Artifacts & Caches
# -----------------------------------------------------------------------------
t0 = time.time()
print("\n[Step 1] Loading precomputed event evaluations and caches...")

df_eval = pd.read_csv(os.path.join(MODEL_DIR, "v2_eval_events.csv"))
print(f"  Loaded v2_eval_events.csv: {len(df_eval)} events")

df_fa = pd.read_csv(os.path.join(MODEL_DIR, "v2_clean_false_alarms.csv"))
print(f"  Loaded v2_clean_false_alarms.csv: {len(df_fa)} rows")

df_budget = pd.read_csv(os.path.join(MODEL_DIR, "v2_budget_sensitivity.csv"))
print(f"  Loaded v2_budget_sensitivity.csv: {len(df_budget)} rows")

df_v1_fa = pd.read_csv(os.path.join(REPO_ROOT, "validation_v2", "runs", "run2b", "false_alarms.csv"))
print(f"  Loaded V1 run2b false_alarms.csv: {len(df_v1_fa)} rows")

with open(os.path.join(MODEL_DIR, "clean_cache.pkl"), "rb") as f:
    clean_grids, clean_features, dev_if_models = pickle.load(f)
print(f"  Loaded clean_cache.pkl: {len(clean_grids)} series in {time.time()-t0:.2f}s")

# Load consent limits
df_cto = pd.read_csv(os.path.join(REPO_ROOT, "Original Data", "consent_limits.csv"))
cto_limits = {}
for _, r in df_cto.iterrows():
    if pd.notna(r["maximum_limit"]) and r["maximum_limit"] > 0:
        cto_limits[(str(r["factory_id"]), str(r["parameter"]))] = float(r["maximum_limit"])

# Fast cluster bootstrap helper
def fast_cluster_bootstrap(df_sub, col_v2, col_comp, n_boot=10000, seed=42):
    g = df_sub.groupby("factory_id")
    counts = g.size().values
    s_v2 = g[col_v2].sum().values
    s_comp = g[col_comp].sum().values
    n_fac = len(counts)
    rng = np.random.RandomState(seed)
    boot_idx = rng.randint(0, n_fac, size=(n_boot, n_fac))
    boot_tot = counts[boot_idx].sum(axis=1)
    boot_v2 = s_v2[boot_idx].sum(axis=1) / boot_tot
    boot_comp = s_comp[boot_idx].sum(axis=1) / boot_tot
    diffs = boot_v2 - boot_comp
    return (
        np.percentile(boot_v2, [2.5, 97.5]),
        np.percentile(boot_comp, [2.5, 97.5]),
        np.percentile(diffs, [2.5, 97.5])
    )

# -----------------------------------------------------------------------------
# 2. ITEM 1: FAIR COMPARATOR EVALUATION
# -----------------------------------------------------------------------------
print("\n" + "=" * 80)
print("ITEM 1: FAIR COMPARATOR EVALUATION (1 ALERT/FACTORY-MONTH)")
print("=" * 80)

comparators = [
    ("is_detected_V1_M1", "V1 M1 Fusion"),
    ("is_detected_V1_IF", "V1 IF alone"),
    ("is_detected_V1_F1_eps0", "V1 F1 (eps=0)"),
    ("is_detected_V1_F1_eps1", "V1 F1 (eps=1)"),
    ("is_detected_V1_F1_eps2", "V1 F1 (eps=2)"),
    ("is_detected_V1_F2", "V1 F2 Copy-Paste"),
    ("is_detected_V1_F3", "V1 F3 Limit Hugging"),
    ("is_detected_V1_F6_shift", "V1 F6 Shift"),
    ("is_detected_V1_F6_slope", "V1 F6 Slope"),
    ("is_detected_B0", "B0 Consent Limit")
]

fair_rows = []

for dir_name, mech, test_label, v2_col in [
    ("Direction 1 (Cross on B)", "B", "Mechanism B (Cross)", "is_detected_dir1_pooled"),
    ("Direction 1 (In-Mech A)", "A", "Mechanism A (In-Mech)", "is_detected_dir1_pooled"),
    ("Direction 2 (Cross on A)", "A", "Mechanism A (Cross)", "is_detected_dir2_pooled"),
    ("Direction 2 (In-Mech B)", "B", "Mechanism B (In-Mech)", "is_detected_dir2_pooled")
]:
    sub_eval = df_eval[(df_eval["mechanism"] == mech) & (~df_eval["no_op"])].copy()
    n_events = len(sub_eval)
    v2_recall = sub_eval[v2_col].mean()

    # Determine per-type post-hoc winners across all comparators + V2
    type_winners = {}
    for t in ["T1", "T2", "T3", "T7", "Pooled"]:
        sub_t = sub_eval if t == "Pooled" else sub_eval[sub_eval["type"] == t]
        scores_t = {c_name: sub_t[c_col].mean() for c_col, c_name in comparators}
        scores_t["V2 Pooled"] = sub_t[v2_col].mean()
        best_name = max(scores_t, key=scores_t.get)
        type_winners[t] = (best_name, scores_t[best_name])

    for c_col, c_name in comparators:
        comp_recall = sub_eval[c_col].mean()
        delta = v2_recall - comp_recall
        ci_v2, ci_comp, ci_diff = fast_cluster_bootstrap(sub_eval, v2_col, c_col, n_boot=10000)

        # Check per-type recall
        t_recs_v2 = {}
        t_recs_c = {}
        for t in ["T1", "T2", "T3", "T7"]:
            sub_t = sub_eval[sub_eval["type"] == t]
            t_recs_v2[t] = sub_t[v2_col].mean()
            t_recs_c[t] = sub_t[c_col].mean()

        fair_rows.append({
            "Evaluation_Setting": dir_name,
            "Test_Mechanism": mech,
            "Events_Count": n_events,
            "Comparator_Method": c_name,
            "V2_Pooled_Recall": round(v2_recall * 100, 2),
            "V2_95_CI": f"[{ci_v2[0]*100:.2f}%, {ci_v2[1]*100:.2f}%]",
            "Comparator_Recall": round(comp_recall * 100, 2),
            "Comparator_95_CI": f"[{ci_comp[0]*100:.2f}%, {ci_comp[1]*100:.2f}%]",
            "Paired_Diff_V2_minus_Comp": round(delta * 100, 2),
            "Paired_95_CI": f"[{ci_diff[0]*100:.2f}%, {ci_diff[1]*100:.2f}%]",
            "Significant_Diff": "YES" if (ci_diff[0] > 0 or ci_diff[1] < 0) else "NO",
            "T1_Comp_Recall": round(t_recs_c["T1"] * 100, 2),
            "T2_Comp_Recall": round(t_recs_c["T2"] * 100, 2),
            "T3_Comp_Recall": round(t_recs_c["T3"] * 100, 2),
            "T7_Comp_Recall": round(t_recs_c["T7"] * 100, 2),
            "Winner_T1_Selected_PostHoc": f"{type_winners['T1'][0]} ({type_winners['T1'][1]*100:.2f}%)",
            "Winner_T2_Selected_PostHoc": f"{type_winners['T2'][0]} ({type_winners['T2'][1]*100:.2f}%)",
            "Winner_T3_Selected_PostHoc": f"{type_winners['T3'][0]} ({type_winners['T3'][1]*100:.2f}%)",
            "Winner_T7_Selected_PostHoc": f"{type_winners['T7'][0]} ({type_winners['T7'][1]*100:.2f}%)",
            "Winner_Pooled_Selected_PostHoc": f"{type_winners['Pooled'][0]} ({type_winners['Pooled'][1]*100:.2f}%)"
        })

df_fair = pd.DataFrame(fair_rows)
out_fair_csv = os.path.join(ANALYSIS_DIR, "fair_comparators.csv")
df_fair.to_csv(out_fair_csv, index=False)
print(f"  Saved Fair Comparators table to {out_fair_csv}")

# Print summary table for Direction 1 Cross and Direction 2 Cross
print("\n[Summary] Fair Comparator Matrix (Direction 1 Cross on B, N=2,553):")
sub_d1 = df_fair[df_fair["Evaluation_Setting"] == "Direction 1 (Cross on B)"]
print(sub_d1[["Comparator_Method", "V2_Pooled_Recall", "Comparator_Recall", "Paired_Diff_V2_minus_Comp", "Paired_95_CI", "Significant_Diff"]].to_string(index=False))

print("\n[Summary] Fair Comparator Matrix (Direction 2 Cross on A, N=1,899):")
sub_d2 = df_fair[df_fair["Evaluation_Setting"] == "Direction 2 (Cross on A)"]
print(sub_d2[["Comparator_Method", "V2_Pooled_Recall", "Comparator_Recall", "Paired_Diff_V2_minus_Comp", "Paired_95_CI", "Significant_Diff"]].to_string(index=False))


# -----------------------------------------------------------------------------
# 3. ITEM 2: SAME-TEST-EVENT GAP EVALUATION
# -----------------------------------------------------------------------------
print("\n" + "=" * 80)
print("ITEM 2: SAME-TEST-EVENT GAP (TRAINED A VS TRAINED B ON SAME TEST EVENTS)")
print("=" * 80)

gap_rows = []

# Mechanism A Events (Tested on A: Trained A [In] vs Trained B [Cross])
sub_a = df_eval[(df_eval["mechanism"] == "A") & (~df_eval["no_op"])].copy()
for t in ["T1", "T2", "T3", "T7", "Pooled"]:
    sub_t = sub_a if t == "Pooled" else sub_a[sub_a["type"] == t]
    r_tr_a = sub_t["is_detected_dir1_pooled"].mean()
    r_tr_b = sub_t["is_detected_dir2_pooled"].mean()
    gap_ab = r_tr_a - r_tr_b
    ci_a, ci_b, ci_gap = fast_cluster_bootstrap(sub_t, "is_detected_dir1_pooled", "is_detected_dir2_pooled", n_boot=10000)

    gap_rows.append({
        "Test_Events_Mechanism": "Mechanism A",
        "Tamper_Type": t,
        "Events_Evaluated": len(sub_t),
        "Recall_Trained_A": round(r_tr_a * 100, 2),
        "CI_95_Trained_A": f"[{ci_a[0]*100:.2f}%, {ci_a[1]*100:.2f}%]",
        "Recall_Trained_B": round(r_tr_b * 100, 2),
        "CI_95_Trained_B": f"[{ci_b[0]*100:.2f}%, {ci_b[1]*100:.2f}%]",
        "Generalization_Gap": round(gap_ab * 100, 2),
        "CI_95_Gap": f"[{ci_gap[0]*100:.2f}%, {ci_gap[1]*100:.2f}%]",
        "Interpretation": "Trained A superior (In-Mech)" if ci_gap[0] > 0 else ("Trained B superior (Cross-Mech)" if ci_gap[1] < 0 else "Indistinguishable (Includes 0)")
    })

# Mechanism B Events (Tested on B: Trained B [In] vs Trained A [Cross])
sub_b = df_eval[(df_eval["mechanism"] == "B") & (~df_eval["no_op"])].copy()
for t in ["T1", "T2", "T3", "T7", "Pooled"]:
    sub_t = sub_b if t == "Pooled" else sub_b[sub_b["type"] == t]
    r_tr_b = sub_t["is_detected_dir2_pooled"].mean()
    r_tr_a = sub_t["is_detected_dir1_pooled"].mean()
    gap_ba = r_tr_b - r_tr_a
    ci_b, ci_a, ci_gap = fast_cluster_bootstrap(sub_t, "is_detected_dir2_pooled", "is_detected_dir1_pooled", n_boot=10000)

    gap_rows.append({
        "Test_Events_Mechanism": "Mechanism B",
        "Tamper_Type": t,
        "Events_Evaluated": len(sub_t),
        "Recall_Trained_A": round(r_tr_a * 100, 2),
        "CI_95_Trained_A": f"[{ci_a[0]*100:.2f}%, {ci_a[1]*100:.2f}%]",
        "Recall_Trained_B": round(r_tr_b * 100, 2),
        "CI_95_Trained_B": f"[{ci_b[0]*100:.2f}%, {ci_b[1]*100:.2f}%]",
        "Generalization_Gap": round(gap_ba * 100, 2),
        "CI_95_Gap": f"[{ci_gap[0]*100:.2f}%, {ci_gap[1]*100:.2f}%]",
        "Interpretation": "Trained B superior (In-Mech)" if ci_gap[0] > 0 else ("Trained A superior (Cross-Mech)" if ci_gap[1] < 0 else "Indistinguishable (Includes 0)")
    })

df_gap = pd.DataFrame(gap_rows)
out_gap_csv = os.path.join(ANALYSIS_DIR, "same_test_event_gap.csv")
df_gap.to_csv(out_gap_csv, index=False)
print(f"  Saved Same-Test-Event Gap table to {out_gap_csv}")
print(df_gap.to_string(index=False))


# -----------------------------------------------------------------------------
# 4. ITEM 3: ALERT DUTY CYCLE & MATCHED SENSITIVITY
# -----------------------------------------------------------------------------
print("\n" + "=" * 80)
print("ITEM 3: ALERT DUTY CYCLE & MATCHED SENSITIVITY ON CLEAN DEV DATA")
print("=" * 80)

# Compute V1 clean scores across all 81 clean series
print("  Computing V1 clean scores across 81 clean series...")
v1_clean_scores = {}
for (fac, param), grid in clean_grids.items():
    v1_clean_scores[(fac, param)] = compute_v1_scores_for_series(
        grid, fac, cto_limits, if_model=dev_if_models.get(param)
    )

tot_valid_readings = sum((~np.isnan(grid["value"].values)).sum() for grid in clean_grids.values())
tot_grid_rows = sum(len(grid) for grid in clean_grids.values())
print(f"  Total valid clean telemetry readings: {tot_valid_readings:,} (Total grid rows: {tot_grid_rows:,})")

duty_rows = []

# V1 methods
v1_method_list = [
    ("M1", "V1 M1 Fusion", V1_CUTOFFS["M1"]),
    ("IF", "V1 IF alone", V1_CUTOFFS["IF"]),
    ("F1_eps0", "V1 F1 (eps=0)", V1_CUTOFFS["F1_eps0"]),
    ("F1_eps1", "V1 F1 (eps=1)", V1_CUTOFFS["F1_eps1"]),
    ("F1_eps2", "V1 F1 (eps=2)", V1_CUTOFFS["F1_eps2"]),
    ("F2", "V1 F2 Copy-Paste", V1_CUTOFFS["F2"]),
    ("F3", "V1 F3 Limit Hugging", V1_CUTOFFS["F3"]),
    ("F6_shift", "V1 F6 Shift", V1_CUTOFFS["F6_shift"]),
    ("F6_slope", "V1 F6 Slope", V1_CUTOFFS["F6_slope"])
]

for m_key, m_name, tau in v1_method_list:
    all_lengths = []
    tot_alert_rows = 0
    tot_episodes = 0
    for (fac, param), sc_dict in v1_clean_scores.items():
        grid = clean_grids[(fac, param)]
        vals = grid["value"].values
        ts_arr = grid["ts_dt"].values
        sc = sc_dict[m_key]
        eps = extract_alert_episodes(sc, vals, tau, ts_arr)
        tot_episodes += len(eps)
        for ep in eps:
            length_rows = ep["end_idx"] - ep["start_idx"] + 1
            all_lengths.append(length_rows)
            sub_vals = vals[ep["start_idx"]:ep["end_idx"]+1]
            tot_alert_rows += int(np.sum(~np.isnan(sub_vals)))

    pct_rows = (tot_alert_rows / tot_valid_readings) * 100
    mean_len = np.mean(all_lengths) if all_lengths else 0.0
    med_len = np.median(all_lengths) if all_lengths else 0.0
    eps_mo = tot_episodes / TOTAL_FACTORY_MONTHS

    duty_rows.append({
        "Method": m_name,
        "Family": "V1",
        "Operating_Cutoff_Tau": tau,
        "Clean_Alert_Episodes": tot_episodes,
        "Episodes_per_Month": round(eps_mo, 3),
        "Total_Alert_Rows": tot_alert_rows,
        "Pct_Valid_Rows_in_Alerts": round(pct_rows, 4),
        "Mean_Alert_Length_Rows": round(mean_len, 2),
        "Median_Alert_Length_Rows": round(med_len, 1)
    })

# B0 Consent Limit on Clean Data
b0_lengths = []
b0_alert_rows = 0
b0_episodes = 0
for (fac, param), grid in clean_grids.items():
    c_lim = cto_limits.get((fac, param), np.nan)
    vals = grid["value"].values
    ts_arr = grid["ts_dt"].values
    if not np.isnan(c_lim):
        sc_b0 = (vals > c_lim).astype(float)
        sc_b0[np.isnan(vals)] = np.nan
        eps = extract_alert_episodes(sc_b0, vals, 0.5, ts_arr)
        b0_episodes += len(eps)
        for ep in eps:
            length_rows = ep["end_idx"] - ep["start_idx"] + 1
            b0_lengths.append(length_rows)
            sub_vals = vals[ep["start_idx"]:ep["end_idx"]+1]
            b0_alert_rows += int(np.sum(~np.isnan(sub_vals)))

pct_b0 = (b0_alert_rows / tot_valid_readings) * 100
mean_len_b0 = np.mean(b0_lengths) if b0_lengths else 0.0
med_len_b0 = np.median(b0_lengths) if b0_lengths else 0.0
eps_mo_b0 = b0_episodes / TOTAL_FACTORY_MONTHS

duty_rows.append({
    "Method": "B0 Consent Limit",
    "Family": "Baseline",
    "Operating_Cutoff_Tau": "Consent Limit",
    "Clean_Alert_Episodes": b0_episodes,
    "Episodes_per_Month": round(eps_mo_b0, 3),
    "Total_Alert_Rows": b0_alert_rows,
    "Pct_Valid_Rows_in_Alerts": round(pct_b0, 4),
    "Mean_Alert_Length_Rows": round(mean_len_b0, 2),
    "Median_Alert_Length_Rows": round(med_len_b0, 1)
})

# Now compute V2 Out-Of-Fold Clean Scores for Direction 1 and Direction 2
print("  Fitting 5 folds of HistGradientBoosting to compute clean duty cycle for V2...")
t_v2_start = time.time()
with open(os.path.join(MODEL_DIR, "inj_cache.pkl"), "rb") as f:
    inj_cache = pickle.load(f)

df_labels_a = pd.read_csv(os.path.join(REPO_ROOT, "validation_v2", "injector", "injected", "dev", "labels.csv"))
df_labels_a = df_labels_a[df_labels_a["type"].isin(["T1", "T2", "T3", "T7"])].copy()
if "parameter" not in df_labels_a.columns and "params" in df_labels_a.columns:
    df_labels_a["parameter"] = df_labels_a["params"]
df_labels_a["no_op"] = False
df_labels_a["start_dt"] = pd.to_datetime(df_labels_a["start_ts"])
df_labels_a["end_dt"] = pd.to_datetime(df_labels_a["end_ts"])

df_labels_b = pd.read_csv(os.path.join(REPO_ROOT, "validation_v2", "v2", "injector_b", "labels_b.csv"))
df_labels_b = df_labels_b[df_labels_b["type"].isin(["T1", "T2", "T3", "T7"])].copy()
df_labels_b["start_dt"] = pd.to_datetime(df_labels_b["start_ts"])
df_labels_b["end_dt"] = pd.to_datetime(df_labels_b["end_ts"])

oof_v2_clean = {"dir1": {}, "dir2": {}}
test_inj_scores_v2 = {"dir1": {}, "dir2": {}}

for fold_idx in range(5):
    test_facs = FOLDS[fold_idx]["all"]
    train_facs = [f for f in all_dev_factories if f not in test_facs]

    # Train A pooled
    train_ev_a = df_labels_a[df_labels_a["factory_id"].isin(train_facs) & (~df_labels_a["no_op"])].copy()
    pos_dfs_a = []
    for _, ev in train_ev_a.iterrows():
        k_inj = ("A", ev["seed"], ev["factory_id"], ev["parameter"])
        if k_inj in inj_cache:
            _, feats, _, ts_arr, _ = inj_cache[k_inj]
            m_pos = (ts_arr >= ev["start_dt"]) & (ts_arr <= ev["end_dt"])
            if np.any(m_pos):
                pos_dfs_a.append(feats[m_pos])

    neg_rows_by_fac = {}
    for fac in train_facs:
        fac_dfs = [clean_features[(f, p)].iloc[::16] for (f, p) in clean_features if f == fac]
        if fac_dfs:
            neg_rows_by_fac[fac] = pd.concat(fac_dfs, ignore_index=True)

    X_pos_a = pd.concat(pos_dfs_a, ignore_index=True)
    target_neg_a = max(1, (len(X_pos_a) * 20) // len(train_facs))
    X_neg_a = pd.concat([df_n.sample(min(len(df_n), target_neg_a), random_state=42) for df_n in neg_rows_by_fac.values()], ignore_index=True)

    X_tr_a = pd.concat([X_pos_a, X_neg_a], ignore_index=True)
    y_tr_a = np.concatenate([np.ones(len(X_pos_a)), np.zeros(len(X_neg_a))])

    clf_a = HistGradientBoostingClassifier(
        max_depth=6, learning_rate=0.1, max_iter=200, l2_regularization=1.0,
        class_weight="balanced", random_state=42, categorical_features=[0]
    )
    clf_a.fit(X_tr_a, y_tr_a)

    # Train B pooled
    train_ev_b = df_labels_b[df_labels_b["factory_id"].isin(train_facs) & (~df_labels_b["no_op"])].copy()
    pos_dfs_b = []
    for _, ev in train_ev_b.iterrows():
        k_inj = ("B", ev["seed"], ev["factory_id"], ev["parameter"])
        if k_inj in inj_cache:
            _, feats, _, ts_arr, _ = inj_cache[k_inj]
            m_pos = (ts_arr >= ev["start_dt"]) & (ts_arr <= ev["end_dt"])
            if np.any(m_pos):
                pos_dfs_b.append(feats[m_pos])

    X_pos_b = pd.concat(pos_dfs_b, ignore_index=True)
    target_neg_b = max(1, (len(X_pos_b) * 20) // len(train_facs))
    X_neg_b = pd.concat([df_n.sample(min(len(df_n), target_neg_b), random_state=42) for df_n in neg_rows_by_fac.values()], ignore_index=True)

    X_tr_b = pd.concat([X_pos_b, X_neg_b], ignore_index=True)
    y_tr_b = np.concatenate([np.ones(len(X_pos_b)), np.zeros(len(X_neg_b))])

    clf_b = HistGradientBoostingClassifier(
        max_depth=6, learning_rate=0.1, max_iter=200, l2_regularization=1.0,
        class_weight="balanced", random_state=42, categorical_features=[0]
    )
    clf_b.fit(X_tr_b, y_tr_b)

    # Score clean test factories
    for fac in test_facs:
        for (f, p), grid in clean_grids.items():
            if f == fac:
                feats = clean_features[(f, p)]
                vals = grid["value"].values
                sc_a = clf_a.predict_proba(feats)[:, 1]
                sc_a[np.isnan(vals)] = np.nan
                oof_v2_clean["dir1"][(fac, p)] = (vals, sc_a)

                sc_b = clf_b.predict_proba(feats)[:, 1]
                sc_b[np.isnan(vals)] = np.nan
                oof_v2_clean["dir2"][(fac, p)] = (vals, sc_b)

    # Score test injected series for matched duty cycle sensitivity
    for fac in test_facs:
        for mech_t in ["A", "B"]:
            seeds_t = [1, 2, 3, 4, 5] if mech_t == "A" else [301, 302, 303, 304, 305]
            for s in seeds_t:
                for p in ["ETP-pH", "ETP-Flow", "ETP-COD", "ETP-TSS", "ETP-BOD"]:
                    k_inj = (mech_t, s, fac, p)
                    if k_inj in inj_cache:
                        _, feats_inj, vals_inj, _, _ = inj_cache[k_inj]
                        sc_inj_a = clf_a.predict_proba(feats_inj)[:, 1]
                        sc_inj_a[np.isnan(vals_inj)] = np.nan
                        test_inj_scores_v2["dir1"][(mech_t, s, fac, p)] = sc_inj_a

                        sc_inj_b = clf_b.predict_proba(feats_inj)[:, 1]
                        sc_inj_b[np.isnan(vals_inj)] = np.nan
                        test_inj_scores_v2["dir2"][(mech_t, s, fac, p)] = sc_inj_b

print(f"  V2 clean & test injected scoring finished in {time.time()-t_v2_start:.2f}s!")

# Add V2 Dir 1 and Dir 2 duty cycle at 1.0 alert/month operating points
tau_v2_d1 = 0.97875
tau_v2_d2 = 0.96469

for d_tag, d_name, tau in [
    ("dir1", "V2 Pooled (Train A)", tau_v2_d1),
    ("dir2", "V2 Pooled (Train B)", tau_v2_d2)
]:
    all_lengths = []
    tot_alert_rows = 0
    tot_episodes = 0
    for (fac, param), (vals, sc) in oof_v2_clean[d_tag].items():
        grid = clean_grids[(fac, param)]
        ts_arr = grid["ts_dt"].values
        eps = extract_alert_episodes(sc, vals, tau, ts_arr)
        tot_episodes += len(eps)
        for ep in eps:
            length_rows = ep["end_idx"] - ep["start_idx"] + 1
            all_lengths.append(length_rows)
            sub_vals = vals[ep["start_idx"]:ep["end_idx"]+1]
            tot_alert_rows += int(np.sum(~np.isnan(sub_vals)))

    pct_rows = (tot_alert_rows / tot_valid_readings) * 100
    mean_len = np.mean(all_lengths) if all_lengths else 0.0
    med_len = np.median(all_lengths) if all_lengths else 0.0
    eps_mo = tot_episodes / TOTAL_FACTORY_MONTHS

    duty_rows.append({
        "Method": d_name,
        "Family": "V2 (Supervised)",
        "Operating_Cutoff_Tau": tau,
        "Clean_Alert_Episodes": tot_episodes,
        "Episodes_per_Month": round(eps_mo, 3),
        "Total_Alert_Rows": tot_alert_rows,
        "Pct_Valid_Rows_in_Alerts": round(pct_rows, 4),
        "Mean_Alert_Length_Rows": round(mean_len, 2),
        "Median_Alert_Length_Rows": round(med_len, 1)
    })

df_duty = pd.DataFrame(duty_rows)
out_duty_csv = os.path.join(ANALYSIS_DIR, "alert_duty_cycle.csv")
df_duty.to_csv(out_duty_csv, index=False)
print(f"  Saved Alert Duty Cycle table to {out_duty_csv}")
print(df_duty.to_string(index=False))

# Sensitivity: Matched Duty Cycle Recall
# M1's clean rows inside alerts = 1,185 rows (0.1041% of valid rows)
target_alert_rows_m1 = 1185
print(f"\n[Sensitivity] Calculating matched duty cycle cutoff for V2 to match M1's {target_alert_rows_m1} alert rows (0.1041%)...")

def find_tau_for_target_rows(scores_dict, target_rows):
    # Binary search over tau
    all_scores = []
    for (fac, param), (vals, scs) in scores_dict.items():
        v = scs[~np.isnan(vals) & ~np.isnan(scs)]
        if len(v) > 0:
            step = max(1, len(v) // 10000)
            all_scores.extend(v[::step])
    all_scores = np.sort(np.array(all_scores))
    low_idx = 0
    high_idx = len(all_scores) - 1
    best_tau = float(all_scores[-1])
    best_diff = 999999

    for _ in range(40):
        mid_idx = (low_idx + high_idx) // 2
        tau = float(all_scores[mid_idx])
        # Count total alert rows inside episodes
        tot_rows = 0
        for (fac, param), (vals, scs) in scores_dict.items():
            eps = extract_alert_episodes(scs, vals, tau, np.arange(len(vals)))
            for ep in eps:
                sub_vals = vals[ep["start_idx"]:ep["end_idx"]+1]
                tot_rows += int(np.sum(~np.isnan(sub_vals)))

        diff = abs(tot_rows - target_rows)
        if diff < best_diff:
            best_diff = diff
            best_tau = tau

        if tot_rows > target_rows:
            low_idx = mid_idx + 1
        else:
            high_idx = mid_idx - 1

        if low_idx >= high_idx:
            break

    return best_tau

tau_duty_d1 = find_tau_for_target_rows(oof_v2_clean["dir1"], target_alert_rows_m1)
tau_duty_d2 = find_tau_for_target_rows(oof_v2_clean["dir2"], target_alert_rows_m1)

print(f"  V2 Dir 1 (Train A) Matched Cutoff: tau = {tau_duty_d1:.5f}")
print(f"  V2 Dir 2 (Train B) Matched Cutoff: tau = {tau_duty_d2:.5f}")

# Evaluate Recall at Matched Duty Cycle Cutoffs
sens_matched_rows = []

for d_tag, d_label, tau_m in [
    ("dir1", "Train A", tau_duty_d1),
    ("dir2", "Train B", tau_duty_d2)
]:
    # Check realized clean duty cycle at tau_m
    tot_alert_rows = 0
    tot_eps = 0
    for (fac, param), (vals, scs) in oof_v2_clean[d_tag].items():
        eps = extract_alert_episodes(scs, vals, tau_m, np.arange(len(vals)))
        tot_eps += len(eps)
        for ep in eps:
            sub_vals = vals[ep["start_idx"]:ep["end_idx"]+1]
            tot_alert_rows += int(np.sum(~np.isnan(sub_vals)))

    real_duty = (tot_alert_rows / tot_valid_readings) * 100
    real_fa = tot_eps / TOTAL_FACTORY_MONTHS

    for mech_eval in ["A", "B"]:
        sub_ev = df_eval[(df_eval["mechanism"] == mech_eval) & (~df_eval["no_op"])].copy()
        n_det = 0
        for _, r in sub_ev.iterrows():
            k_inj = (mech_eval, r["seed"], r["factory_id"], r["parameter"])
            sc_inj = test_inj_scores_v2[d_tag].get(k_inj)
            if sc_inj is not None:
                grid, _, vals, ts_arr, _ = inj_cache[k_inj]
                eps = extract_alert_episodes(sc_inj, vals, tau_m, ts_arr)
                s_dt = pd.to_datetime(r["start_dt"])
                e_dt = pd.to_datetime(r["end_dt"])
                e_dt_2h = e_dt + pd.Timedelta(hours=2)
                det = any(
                    (pd.to_datetime(ep["end_ts"]) >= s_dt) and
                    (pd.to_datetime(ep["start_ts"]) <= e_dt_2h)
                    for ep in eps
                )
                if det:
                    n_det += 1

        rec = n_det / len(sub_ev)
        sens_matched_rows.append({
            "Direction": d_label,
            "Matched_Duty_Cutoff_Tau": tau_m,
            "Clean_Alert_Rows": tot_alert_rows,
            "Realized_Clean_Duty_Pct": round(real_duty, 4),
            "Realized_Clean_FA_mo": round(real_fa, 3),
            "Test_Mechanism": mech_eval,
            "Setting": "In-Mechanism" if (d_tag == "dir1" and mech_eval == "A") or (d_tag == "dir2" and mech_eval == "B") else "Cross-Mechanism",
            "Evaluated_Events": len(sub_ev),
            "Detected_Events": n_det,
            "Recall_Matched_Duty": round(rec * 100, 2)
        })

df_matched_sens = pd.DataFrame(sens_matched_rows)
out_matched_csv = os.path.join(ANALYSIS_DIR, "matched_duty_cycle_sensitivity.csv")
df_matched_sens.to_csv(out_matched_csv, index=False)
print(f"  Saved Matched Duty Cycle Sensitivity table to {out_matched_csv}")
print(df_matched_sens.to_string(index=False))


# -----------------------------------------------------------------------------
# 5. ITEM 4: FALSE-ALARM CONCENTRATION ANALYSIS
# -----------------------------------------------------------------------------
print("\n" + "=" * 80)
print("ITEM 4: FALSE-ALARM CONCENTRATION ANALYSIS (33 DEVELOPMENT FACTORIES)")
print("=" * 80)

# Merge false alarm counts across V2 Dir 1, V2 Dir 2, and V1 M1
v2_d1_fa = df_fa[(df_fa["Direction"] == "dir1") & (df_fa["Model"] == "pooled")].set_index("Factory_ID")
v2_d2_fa = df_fa[(df_fa["Direction"] == "dir2") & (df_fa["Model"] == "pooled")].set_index("Factory_ID")
v1_m1_fa = df_v1_fa.set_index("factory_id")

conc_rows = []
for fac in all_dev_factories:
    m_k = FACTORY_MONTHS[fac]
    eps_d1 = int(v2_d1_fa.loc[fac, "Alert_Episodes"]) if fac in v2_d1_fa.index else 0
    rate_d1 = round(eps_d1 / m_k, 3)
    eps_d2 = int(v2_d2_fa.loc[fac, "Alert_Episodes"]) if fac in v2_d2_fa.index else 0
    rate_d2 = round(eps_d2 / m_k, 3)
    eps_v1 = int(v1_m1_fa.loc[fac, "false_alert_episodes"]) if fac in v1_m1_fa.index else 0
    rate_v1 = round(eps_v1 / m_k, 3)

    conc_rows.append({
        "Factory_ID": fac,
        "Exposure_Months": m_k,
        "V2_Dir1_Episodes": eps_d1,
        "V2_Dir1_FA_Rate_mo": rate_d1,
        "V2_Dir2_Episodes": eps_d2,
        "V2_Dir2_FA_Rate_mo": rate_d2,
        "V1_M1_Episodes": eps_v1,
        "V1_M1_FA_Rate_mo": rate_v1
    })

df_conc = pd.DataFrame(conc_rows)
out_conc_csv = os.path.join(ANALYSIS_DIR, "false_alarm_concentration.csv")
df_conc.to_csv(out_conc_csv, index=False)
print(f"  Saved False Alarm Concentration table to {out_conc_csv}")

# Top 3 factory share calculations
top3_d1 = df_conc.sort_values("V2_Dir1_Episodes", ascending=False).head(3)
tot_eps_d1 = df_conc["V2_Dir1_Episodes"].sum()
share_top3_d1 = top3_d1["V2_Dir1_Episodes"].sum() / tot_eps_d1

top3_d2 = df_conc.sort_values("V2_Dir2_Episodes", ascending=False).head(3)
tot_eps_d2 = df_conc["V2_Dir2_Episodes"].sum()
share_top3_d2 = top3_d2["V2_Dir2_Episodes"].sum() / tot_eps_d2

top3_v1 = df_conc.sort_values("V1_M1_Episodes", ascending=False).head(3)
tot_eps_v1 = df_conc["V1_M1_Episodes"].sum()
share_top3_v1 = top3_v1["V1_M1_Episodes"].sum() / tot_eps_v1

print(f"\n[Summary] V2 Dir 1 Pooled Top 3 Factories (Total Episodes = {tot_eps_d1}):")
for _, r in top3_d1.iterrows():
    print(f"  {r['Factory_ID']}: {r['V2_Dir1_Episodes']} eps ({r['V2_Dir1_FA_Rate_mo']}/mo)")
print(f"  -> Top 3 Share: {share_top3_d1*100:.2f}% | Factories with 0 FAs: {(df_conc['V2_Dir1_Episodes']==0).sum()}/33")

print(f"\n[Summary] V2 Dir 2 Pooled Top 3 Factories (Total Episodes = {tot_eps_d2}):")
for _, r in top3_d2.iterrows():
    print(f"  {r['Factory_ID']}: {r['V2_Dir2_Episodes']} eps ({r['V2_Dir2_FA_Rate_mo']}/mo)")
print(f"  -> Top 3 Share: {share_top3_d2*100:.2f}% | Factories with 0 FAs: {(df_conc['V2_Dir2_Episodes']==0).sum()}/33")

print(f"\n[Summary] V1 M1 Fusion Top 3 Factories (Total Episodes = {tot_eps_v1}):")
for _, r in top3_v1.iterrows():
    print(f"  {r['Factory_ID']}: {r['V1_M1_Episodes']} eps ({r['V1_M1_FA_Rate_mo']}/mo)")
print(f"  -> Top 3 Share: {share_top3_v1*100:.2f}% | Factories with 0 FAs: {(df_conc['V1_M1_Episodes']==0).sum()}/33")


# -----------------------------------------------------------------------------
# 6. ITEM 5: PARAMETER CHECK & ZERO-RECALL DIAGNOSTIC
# -----------------------------------------------------------------------------
print("\n" + "=" * 80)
print("ITEM 5: PARAMETER CHECK & ZERO-RECALL DIAGNOSTIC (BOD/COD/TSS)")
print("=" * 80)

# Training positive counts per parameter in Mechanism A and Mechanism B
param_check_rows = []
params_list = ["ETP-pH", "ETP-Flow", "ETP-COD", "ETP-TSS", "ETP-BOD"]

# Positives in A
pos_a_events = df_labels_a.groupby("parameter").size()
pos_a_rows = df_labels_a.groupby("parameter")["duration_rows"].sum()
tot_pos_a_rows = pos_a_rows.sum()

# Positives in B
pos_b_events = df_labels_b[~df_labels_b["no_op"]].groupby("parameter").size()
pos_b_rows = df_labels_b[~df_labels_b["no_op"]].groupby("parameter")["duration_rows"].sum()
tot_pos_b_rows = pos_b_rows.sum()

# Feature NaN percentages per parameter on clean dev series
nan_pct_by_param = {p: [] for p in params_list}
for (fac, p), feats in clean_features.items():
    if p in nan_pct_by_param:
        nan_pct_by_param[p].append(feats.isna().mean().values)

mean_nan_pct_by_param = {}
for p in params_list:
    if nan_pct_by_param[p]:
        mean_nan_pct_by_param[p] = np.mean(nan_pct_by_param[p], axis=0) * 100
    else:
        mean_nan_pct_by_param[p] = np.zeros(45)

feature_cols = list(clean_features[list(clean_features.keys())[0]].columns)

# Recall by parameter in both directions
# On Mechanism B (Test B)
sub_b_eval = df_eval[(df_eval["mechanism"] == "B") & (~df_eval["no_op"])]
rec_b_d1 = sub_b_eval.groupby("parameter")["is_detected_dir1_pooled"].mean() * 100
rec_b_d2 = sub_b_eval.groupby("parameter")["is_detected_dir2_pooled"].mean() * 100
rec_b_m1 = sub_b_eval.groupby("parameter")["is_detected_V1_M1"].mean() * 100

# On Mechanism A (Test A)
sub_a_eval = df_eval[(df_eval["mechanism"] == "A") & (~df_eval["no_op"])]
rec_a_d1 = sub_a_eval.groupby("parameter")["is_detected_dir1_pooled"].mean() * 100
rec_a_d2 = sub_a_eval.groupby("parameter")["is_detected_dir2_pooled"].mean() * 100
rec_a_m1 = sub_a_eval.groupby("parameter")["is_detected_V1_M1"].mean() * 100

for p in params_list:
    ev_a = int(pos_a_events.get(p, 0))
    r_a = int(pos_a_rows.get(p, 0))
    share_a = (r_a / tot_pos_a_rows) * 100

    ev_b = int(pos_b_events.get(p, 0))
    r_b = int(pos_b_rows.get(p, 0))
    share_b = (r_b / tot_pos_b_rows) * 100

    mean_nan_all_feats = float(np.mean(mean_nan_pct_by_param[p]))

    param_check_rows.append({
        "Parameter": p,
        "Mech_A_Pos_Events": ev_a,
        "Mech_A_Pos_Rows": r_a,
        "Mech_A_Pos_Row_Share_Pct": round(share_a, 2),
        "Mech_B_Pos_Events": ev_b,
        "Mech_B_Pos_Rows": r_b,
        "Mech_B_Pos_Row_Share_Pct": round(share_b, 2),
        "Mean_Feature_NaN_Pct": round(mean_nan_all_feats, 2),
        "V2_Recall_Dir1_Cross_on_B": round(float(rec_b_d1.get(p, 0.0)), 2),
        "V2_Recall_Dir2_InMech_on_B": round(float(rec_b_d2.get(p, 0.0)), 2),
        "V1_M1_Recall_on_B": round(float(rec_b_m1.get(p, 0.0)), 2),
        "V2_Recall_Dir2_Cross_on_A": round(float(rec_a_d2.get(p, 0.0)), 2),
        "V2_Recall_Dir1_InMech_on_A": round(float(rec_a_d1.get(p, 0.0)), 2),
        "V1_M1_Recall_on_A": round(float(rec_a_m1.get(p, 0.0)), 2)
    })

df_param = pd.DataFrame(param_check_rows)
out_param_csv = os.path.join(ANALYSIS_DIR, "parameter_check.csv")
df_param.to_csv(out_param_csv, index=False)
print(f"  Saved Parameter Check table to {out_param_csv}")
print(df_param.to_string(index=False))

# Also save full 45-feature NaN breakdown per parameter
df_nan_feats = pd.DataFrame({
    "Feature": feature_cols,
    "ETP-pH_NaN_Pct": [round(mean_nan_pct_by_param["ETP-pH"][i], 2) for i in range(45)],
    "ETP-Flow_NaN_Pct": [round(mean_nan_pct_by_param["ETP-Flow"][i], 2) for i in range(45)],
    "ETP-COD_NaN_Pct": [round(mean_nan_pct_by_param["ETP-COD"][i], 2) for i in range(45)],
    "ETP-TSS_NaN_Pct": [round(mean_nan_pct_by_param["ETP-TSS"][i], 2) for i in range(45)],
    "ETP-BOD_NaN_Pct": [round(mean_nan_pct_by_param["ETP-BOD"][i], 2) for i in range(45)]
})
out_nan_csv = os.path.join(ANALYSIS_DIR, "feature_nan_breakdown_by_param.csv")
df_nan_feats.to_csv(out_nan_csv, index=False)
print(f"  Saved Feature NaN breakdown to {out_nan_csv}")


# -----------------------------------------------------------------------------
# 7. ITEM 6: BUDGET TABLE & DEGENERACY AUDIT
# -----------------------------------------------------------------------------
print("\n" + "=" * 80)
print("ITEM 6: BUDGET SENSITIVITY TABLE & DEGENERACY AUDIT")
print("=" * 80)

# Check duty cycle and degeneracy for each row in v2_budget_sensitivity.csv
# Mark degenerate if tau < 0.05 or alert duty cycle > 20%
budget_audit_rows = []

for _, r in df_budget.iterrows():
    b_target = float(r["Budget_Target_mo"])
    tau = float(r["Operating_Cutoff_Tau"])
    d_dir = r["Direction"]
    d_tag = "dir1" if d_dir == "Train A" else "dir2"

    # Compute clean alert duty cycle at this exact tau
    all_lengths = []
    tot_alert_rows = 0
    tot_episodes = 0
    for (fac, param), (vals, sc) in oof_v2_clean[d_tag].items():
        grid = clean_grids[(fac, param)]
        ts_arr = grid["ts_dt"].values
        eps = extract_alert_episodes(sc, vals, tau, ts_arr)
        tot_episodes += len(eps)
        for ep in eps:
            length_rows = ep["end_idx"] - ep["start_idx"] + 1
            all_lengths.append(length_rows)
            sub_vals = vals[ep["start_idx"]:ep["end_idx"]+1]
            tot_alert_rows += int(np.sum(~np.isnan(sub_vals)))

    duty_pct = (tot_alert_rows / tot_valid_readings) * 100
    is_deg_tau = (tau < 0.05)
    is_deg_duty = (duty_pct > 20.0)
    is_deg = is_deg_tau or is_deg_duty

    deg_reason = []
    if is_deg_tau:
        deg_reason.append(f"tau={tau:.5f} < 0.05")
    if is_deg_duty:
        deg_reason.append(f"duty_cycle={duty_pct:.2f}% > 20.0%")
    deg_str = "DEGENERATE (" + ", ".join(deg_reason) + ")" if is_deg else "VALID"

    row_dict = r.to_dict()
    row_dict["Clean_Duty_Cycle_Pct"] = round(duty_pct, 4)
    row_dict["Is_Degenerate"] = is_deg
    row_dict["Degeneracy_Status"] = deg_str
    budget_audit_rows.append(row_dict)

df_budget_audit = pd.DataFrame(budget_audit_rows)
out_budget_csv = os.path.join(ANALYSIS_DIR, "budget_sensitivity_degenerate.csv")
df_budget_audit.to_csv(out_budget_csv, index=False)
print(f"  Saved Budget Sensitivity Audit table to {out_budget_csv}")
print(df_budget_audit[["Budget_Target_mo", "Operating_Cutoff_Tau", "Direction", "Test_Mechanism", "Test_Type", "Recall_Pct", "Clean_Duty_Cycle_Pct", "Degeneracy_Status"]].to_string(index=False))

print("\n" + "=" * 80)
print("ALL 6 ANALYSIS DELIVERABLES COMPUTED AND SAVED SUCCESSFULLY!")
print("=" * 80)
