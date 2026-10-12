import os
import sys
import numpy as np
import pandas as pd
from scipy import stats

REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
RAW_CSV = os.path.join(REPO_ROOT, "Data", "RawData", "monitoring_data(raw).csv")
CTO_CSV = os.path.join(REPO_ROOT, "Original Data", "consent_limits.csv")
NATURAL_RUNS_CSV = os.path.join(REPO_ROOT, "validation_v2", "natural_runs_by_length.csv")
SCORE_CEILING_CSV = os.path.join(REPO_ROOT, "validation_v2", "score_ceiling.csv")

sys.path.insert(0, os.path.join(REPO_ROOT, "validation_v2", "detector"))
from detector import prepare_series, calibrate, score, compute_f5_correlation, score_tail_prob, extract_exact_repeat_runs

def run_part_c_natural_runs():
    print("=" * 80)
    print("RUNNING PART C: NATURAL RUNS BY LENGTH")
    print("=" * 80)

    df_raw = pd.read_csv(RAW_CSV)
    lengths = [8, 16, 48, 96, 288, 672]

    results = []
    for (fac, param), g in df_raw.groupby(["factory_id", "parameter_id"]):
        df_grid = prepare_series(g)
        vals = pd.to_numeric(df_grid["value"], errors="coerce").values
        is_flow = ("flow" in str(param).lower())

        L_row, nat_run_lens = extract_exact_repeat_runs(vals, is_flow=is_flow)
        tot_runs = len(nat_run_lens)

        ts = pd.to_datetime(df_grid["timestamp"]).dropna()
        if len(ts) > 1:
            dur_days = (ts.max() - ts.min()).total_seconds() / 86400.0
            dur_years = max(dur_days / 365.25, 1e-4)
        else:
            dur_days, dur_years = 0.0, 1.0

        runs_per_year = tot_runs / dur_years if dur_years > 0 else tot_runs

        row = {
            "factory_id": fac,
            "parameter_id": param,
            "total_runs": tot_runs,
            "duration_days": round(dur_days, 1),
            "duration_years": round(dur_years, 3),
            "runs_per_year": round(runs_per_year, 1),
        }
        for L in lengths:
            row[f"runs_ge_{L}"] = int((nat_run_lens >= L).sum()) if tot_runs > 0 else 0
            row[f"runs_ge_{L}_per_year"] = round(((nat_run_lens >= L).sum()) / dur_years, 2) if dur_years > 0 else 0.0

        results.append(row)

    df_runs = pd.DataFrame(results)
    df_runs.to_csv(NATURAL_RUNS_CSV, index=False)
    print(f"Saved natural runs table to {NATURAL_RUNS_CSV} (Total series: {len(df_runs)})")

    print("\nSummary of Natural Runs Across All 82 Dev Series:")
    print(f"Total series: {len(df_runs)}")
    print(f"Mean total natural runs per series: {df_runs['total_runs'].mean():.1f}")
    print(f"Mean natural runs per year: {df_runs['runs_per_year'].mean():.1f}")
    for L in lengths:
        col = f"runs_ge_{L}"
        series_with_runs = (df_runs[col] > 0).sum()
        print(f"  Runs >= {L:3d} rows: Total = {df_runs[col].sum():5d} | Series with >= 1 run = {series_with_runs:2d}/82 ({series_with_runs/82*100:.1f}%) | Mean/series = {df_runs[col].mean():.2f}")

    return df_runs

def run_part_d_score_ceiling():
    print("\n" + "=" * 80)
    print("RUNNING PART D: CEILING RE-RUN (ORIGINAL DATA, BLIND CALIBRATION)")
    print("=" * 80)

    df_raw = pd.read_csv(RAW_CSV)
    df_cto = pd.read_csv(CTO_CSV)
    cto_limits = {}
    for _, r in df_cto.iterrows():
        if pd.notna(r["maximum_limit"]) and r["maximum_limit"] > 0:
            cto_limits[(str(r["factory_id"]), str(r["parameter"]))] = float(r["maximum_limit"])

    series_groups = df_raw.groupby(["factory_id", "parameter_id"])
    print(f"Total dev series found: {len(series_groups)}")

    rows = []

    # 1. Single-Series Checks (F1_run, F2, F3, F6, IF, legacy_F1)
    for (fac, param), g in series_groups:
        calib = calibrate(g, mode="blind", cto_limits=cto_limits)
        scored = score(g, calib, cto_limits=cto_limits)

        # Candidate checks to report
        checks_to_eval = [
            ("F1_score_eps0", "F1_run_eps0", None),
            ("F1_score_eps1", "F1_run_eps1", None),
            ("F1_score_eps2", "F1_run_eps2", None),
            ("legacy_F1_range_w16_score", "legacy_F1", 16),
            ("legacy_F1_range_w96_score", "legacy_F1", 96),
            ("legacy_F1_range_w288_score", "legacy_F1", 288),
            ("F2_copypaste_w16_score", "F2_copypaste", 16),
            ("F2_copypaste_w96_score", "F2_copypaste", 96),
            ("F2_copypaste_w288_score", "F2_copypaste", 288),
            ("F3_limit_w16_score", "F3_limit", 16),
            ("F3_limit_w96_score", "F3_limit", 96),
            ("F3_limit_w288_score", "F3_limit", 288),
            ("F6_shift_w16_score", "F6_shift", 16),
            ("F6_shift_w96_score", "F6_shift", 96),
            ("F6_shift_w288_score", "F6_shift", 288),
            ("F6_slope_w16_score", "F6_slope", 16),
            ("F6_slope_w96_score", "F6_slope", 96),
            ("F6_slope_w288_score", "F6_slope", 288),
            ("if_score", "IF", 16),
        ]

        for col, chk_name, w in checks_to_eval:
            if col not in scored.columns:
                continue

            vals = scored[col].dropna().values
            n_valid = len(vals)

            if n_valid == 0:
                rows.append({
                    "factory_id": fac,
                    "parameter_id": param,
                    "check": chk_name,
                    "window": w if w is not None else 0,
                    "n_valid": 0,
                    "max_score": np.nan,
                    "tie_mass_pct": np.nan,
                    "p99_9": np.nan,
                    "p99_97": np.nan
                })
            else:
                max_v = float(np.max(vals))
                tie_mass = float((vals == max_v).mean() * 100.0)
                p999 = float(np.percentile(vals, 99.9))
                p9997 = float(np.percentile(vals, 99.97))

                rows.append({
                    "factory_id": fac,
                    "parameter_id": param,
                    "check": chk_name,
                    "window": w if w is not None else 0,
                    "n_valid": n_valid,
                    "max_score": round(max_v, 4),
                    "tie_mass_pct": round(tie_mass, 2),
                    "p99_9": round(p999, 4),
                    "p99_97": round(p9997, 4)
                })

    # 2. Multi-Parameter Pair Checks (F5 Correlation Break)
    factories = sorted(df_raw["factory_id"].unique())
    bod_cod_tss = ["ETP-BOD", "ETP-COD", "ETP-TSS"]

    for fac in factories:
        sub_fac = df_raw[df_raw["factory_id"] == fac]
        present = [p for p in bod_cod_tss if p in sub_fac["parameter_id"].unique()]
        if len(present) < 2:
            continue

        for w in [96, 288]:
            corr_dict = compute_f5_correlation(sub_fac, w=w)
            for pair_key, r_corr in corr_dict.items():
                # pair_key format: F5_corr_ETP-BOD_ETP-COD_w96
                valid_corr = r_corr.dropna().values
                if len(valid_corr) == 0:
                    continue

                # Calibrate and score self correlation
                sc = score_tail_prob(valid_corr, valid_corr, mode="two_sided")
                vals = sc[~np.isnan(sc)]
                n_valid = len(vals)

                pair_label = pair_key.replace(f"_w{w}", "").replace("F5_corr_", "")
                if n_valid == 0:
                    rows.append({
                        "factory_id": fac,
                        "parameter_id": pair_label,
                        "check": "F5_corr",
                        "window": w,
                        "n_valid": 0,
                        "max_score": np.nan,
                        "tie_mass_pct": np.nan,
                        "p99_9": np.nan,
                        "p99_97": np.nan
                    })
                else:
                    max_v = float(np.max(vals))
                    tie_mass = float((vals == max_v).mean() * 100.0)
                    p999 = float(np.percentile(vals, 99.9))
                    p9997 = float(np.percentile(vals, 99.97))

                    rows.append({
                        "factory_id": fac,
                        "parameter_id": pair_label,
                        "check": "F5_corr",
                        "window": w,
                        "n_valid": n_valid,
                        "max_score": round(max_v, 4),
                        "tie_mass_pct": round(tie_mass, 2),
                        "p99_9": round(p999, 4),
                        "p99_97": round(p9997, 4)
                    })

    df_ceiling = pd.DataFrame(rows)
    df_ceiling.to_csv(SCORE_CEILING_CSV, index=False)
    print(f"Saved updated score ceiling results to {SCORE_CEILING_CSV} (Total rows: {len(df_ceiling)})")

    # Summary analysis: max score >= 3
    print("\n" + "=" * 80)
    print("STEP 2d SCORE CEILING SUMMARY: % SERIES WITH MAX SCORE >= 3")
    print("=" * 80)

    summary_rows = []
    # Distinct checks and windows
    check_window_pairs = df_ceiling[["check", "window"]].drop_duplicates().values

    for chk, w in check_window_pairs:
        sub = df_ceiling[(df_ceiling["check"] == chk) & (df_ceiling["window"] == w)]
        valid_sub = sub[sub["n_valid"] > 0]
        n_eval = len(valid_sub)
        if n_eval == 0:
            continue

        n_ge_3 = int((valid_sub["max_score"] >= 3.0).sum())
        pct_ge_3 = (n_ge_3 / n_eval * 100.0)

        n_lt_3 = int((valid_sub["max_score"] < 3.0).sum())
        pct_lt_3 = (n_lt_3 / n_eval * 100.0)

        med_max = float(valid_sub["max_score"].median())
        med_tie = float(valid_sub["tie_mass_pct"].median())
        med_p999 = float(valid_sub["p99_9"].median())

        summary_rows.append({
            "Check": chk,
            "Window": int(w) if w != 0 else "-",
            "Series Evaluated": n_eval,
            "Max Score >= 3 (Count)": n_ge_3,
            "Max Score >= 3 (%)": round(pct_ge_3, 1),
            "Max Score < 3 (Count)": n_lt_3,
            "Max Score < 3 (%)": round(pct_lt_3, 1),
            "Median Max Score": round(med_max, 4),
            "Median Tie Mass (%)": round(med_tie, 2),
            "Median p99.9 Score": round(med_p999, 4)
        })

    df_sum = pd.DataFrame(summary_rows)
    print(df_sum.to_string(index=False))
    return df_ceiling, df_sum

if __name__ == "__main__":
    run_part_c_natural_runs()
    run_part_d_score_ceiling()
