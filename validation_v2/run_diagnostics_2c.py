import os
import sys
import numpy as np
import pandas as pd
from scipy import stats

REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
RAW_CSV = os.path.join(REPO_ROOT, "Data", "RawData", "monitoring_data(raw).csv")
CTO_CSV = os.path.join(REPO_ROOT, "Original Data", "consent_limits.csv")
SCORE_CEILING_CSV = os.path.join(REPO_ROOT, "validation_v2", "score_ceiling.csv")

sys.path.insert(0, os.path.join(REPO_ROOT, "validation_v2", "detector"))
from detector import prepare_series, calibrate, score

def run_part_c():
    print("=" * 80)
    print("RUNNING PART C: SCORE CEILING ANALYSIS (LABEL-FREE, BLIND CALIBRATION)")
    print("=" * 80)

    df_raw = pd.read_csv(RAW_CSV)
    df_cto = pd.read_csv(CTO_CSV)
    cto_limits = {}
    for _, r in df_cto.iterrows():
        if pd.notna(r["maximum_limit"]) and r["maximum_limit"] > 0:
            cto_limits[(str(r["factory_id"]), str(r["parameter"]))] = float(r["maximum_limit"])

    # Dev series: all (factory_id, parameter_id)
    series_groups = df_raw.groupby(["factory_id", "parameter_id"])
    print(f"Total dev series found: {len(series_groups)}")

    checks = ["F1_range", "F2_copypaste", "F3_limit", "F6_shift", "F6_slope"]
    windows = [16, 96, 288]

    rows = []

    for (fac, param), g in series_groups:
        # Blind calibration on original unaltered series
        calib = calibrate(g, mode="blind", cto_limits=cto_limits)
        scored = score(g, calib, cto_limits=cto_limits)

        for chk in checks:
            for w in windows:
                col = f"{chk}_w{w}_score"
                if col not in scored.columns:
                    continue

                vals = scored[col].dropna().values
                n_valid = len(vals)

                if n_valid == 0:
                    rows.append({
                        "factory_id": fac,
                        "parameter_id": param,
                        "check": chk,
                        "window": w,
                        "n_valid": 0,
                        "max_score": np.nan,
                        "tie_mass_pct": np.nan,
                        "p99_9": np.nan,
                        "p99_97": np.nan
                    })
                else:
                    max_v = float(np.max(vals))
                    # tie mass: % of valid windows tied at the max
                    tie_mass = float((vals == max_v).mean() * 100.0)
                    p999 = float(np.percentile(vals, 99.9))
                    p9997 = float(np.percentile(vals, 99.97))

                    rows.append({
                        "factory_id": fac,
                        "parameter_id": param,
                        "check": chk,
                        "window": w,
                        "n_valid": n_valid,
                        "max_score": round(max_v, 4),
                        "tie_mass_pct": round(tie_mass, 2),
                        "p99_9": round(p999, 4),
                        "p99_97": round(p9997, 4)
                    })

    df_ceiling = pd.DataFrame(rows)
    df_ceiling.to_csv(SCORE_CEILING_CSV, index=False)
    print(f"Saved score ceiling results to {SCORE_CEILING_CSV} (Total rows: {len(df_ceiling)})")

    # Summary analysis: for each check, in how many series is max score < 3?
    print("\n" + "=" * 80)
    print("PART C SUMMARY: IN HOW MANY SERIES IS MAX SCORE < 3?")
    print("=" * 80)

    summary_rows = []
    total_series = df_ceiling[["factory_id", "parameter_id"]].drop_duplicates().shape[0]

    for chk in checks:
        for w in windows:
            sub = df_ceiling[(df_ceiling["check"] == chk) & (df_ceiling["window"] == w)]
            # Valid scored series
            valid_sub = sub[sub["n_valid"] > 0]
            n_evaluated = len(valid_sub)
            n_lt_3 = int((valid_sub["max_score"] < 3.0).sum())
            pct_lt_3 = (n_lt_3 / n_evaluated * 100.0) if n_evaluated > 0 else 0.0
            
            # Reasons: N_valid < 1000 vs Tie Mass > 0.1%
            n_small_N = int((valid_sub["n_valid"] < 1000).sum())
            n_tie_mass = int(((valid_sub["max_score"] < 3.0) & (valid_sub["tie_mass_pct"] >= 0.10)).sum())
            
            med_max = float(valid_sub["max_score"].median()) if n_evaluated > 0 else np.nan
            med_tie = float(valid_sub["tie_mass_pct"].median()) if n_evaluated > 0 else np.nan

            summary_rows.append({
                "Check": chk,
                "Window": w,
                "Series With Data": n_evaluated,
                "Max Score < 3 (Count)": n_lt_3,
                "Max Score < 3 (%)": round(pct_lt_3, 1),
                "Median Max Score": round(med_max, 4),
                "Median Tie Mass (%)": round(med_tie, 2),
                "Small N (<1k)": n_small_N,
                "High Tie Mass (>=0.1%)": n_tie_mass
            })

    df_sum = pd.DataFrame(summary_rows)
    print(df_sum.to_string(index=False))
    return df_ceiling, df_sum

def run_part_d():
    print("\n" + "=" * 80)
    print("RUNNING PART D: F5 SANITY ANALYSIS (BOD / COD / TSS PAIRS)")
    print("=" * 80)

    df_raw = pd.read_csv(RAW_CSV)
    params = ["ETP-BOD", "ETP-COD", "ETP-TSS"]

    # Factories with >= 2 of BOD/COD/TSS
    fac_counts = df_raw[~df_raw["quality_code"].isin(["Error", "Out of Range"])].groupby("factory_id")["parameter_id"].apply(lambda s: set(s).intersection(params))
    eligible_facs = sorted(fac_counts[fac_counts.apply(len) >= 2].index.tolist())
    print(f"Eligible factories with >= 2 parameters ({len(eligible_facs)} factories): {eligible_facs}")

    pair_combos = [("ETP-BOD", "ETP-COD"), ("ETP-BOD", "ETP-TSS"), ("ETP-COD", "ETP-TSS")]

    f5_rows = []

    for fac in eligible_facs:
        sub = df_raw[df_raw["factory_id"] == fac]
        grids = {}
        for p in params:
            p_sub = sub[sub["parameter_id"] == p]
            if not p_sub.empty:
                g = prepare_series(p_sub)
                if not g.empty:
                    grids[p] = g.set_index("ts_dt")["value"]

        df_fac = pd.DataFrame(grids)

        for p1, p2 in pair_combos:
            if p1 not in df_fac.columns or p2 not in df_fac.columns:
                continue

            valid = df_fac[[p1, p2]].dropna()
            n_valid = len(valid)

            if n_valid < 10:
                f5_rows.append({
                    "factory_id": fac,
                    "param_a": p1,
                    "param_b": p2,
                    "n_valid_rows": n_valid,
                    "median_rolling_corr_w96": np.nan,
                    "linear_fit_R2": np.nan,
                    "linear_slope": np.nan,
                    "median_ratio": np.nan,
                    "pct_rows_ratio_const_1pct": np.nan,
                    "flagged_R2_gt_095": False
                })
                continue

            v1 = valid[p1].values
            v2 = valid[p2].values

            # 1. Rolling correlation (w=96)
            r_corr = valid[p1].rolling(96, min_periods=96).corr(valid[p2])
            med_corr = float(r_corr.median()) if r_corr.notna().any() else np.nan

            # 2. Linear fit R^2
            if np.std(v1) > 1e-6 and np.std(v2) > 1e-6:
                slope, intercept, r_value, p_value, std_err = stats.linregress(v2, v1)
                r2 = float(r_value ** 2)
            else:
                slope, intercept, r2 = 0.0, 0.0, 0.0

            # 3. % rows where ratio value_a / value_b is constant (within 1%)
            # We evaluate ratio a / b where b != 0
            nz_mask = (v2 != 0) & (~np.isnan(v1)) & (~np.isnan(v2))
            if np.any(nz_mask):
                ratios = v1[nz_mask] / v2[nz_mask]
                med_ratio = float(np.median(ratios))
                if abs(med_ratio) > 1e-6:
                    # within 1% of median ratio
                    is_const = np.abs(ratios - med_ratio) <= (0.01 * np.abs(med_ratio))
                    pct_const = float(np.mean(is_const) * 100.0)
                else:
                    pct_const = 0.0
            else:
                med_ratio = np.nan
                pct_const = 0.0

            flag = bool(r2 > 0.95)

            f5_rows.append({
                "factory_id": fac,
                "param_a": p1,
                "param_b": p2,
                "n_valid_rows": n_valid,
                "median_rolling_corr_w96": round(med_corr, 4) if pd.notna(med_corr) else np.nan,
                "linear_fit_R2": round(r2, 4),
                "linear_slope": round(slope, 4),
                "median_ratio": round(med_ratio, 4) if pd.notna(med_ratio) else np.nan,
                "pct_rows_ratio_const_1pct": round(pct_const, 2),
                "flagged_R2_gt_095": flag
            })

    df_f5 = pd.DataFrame(f5_rows)
    f5_csv = os.path.join(REPO_ROOT, "validation_v2", "f5_sanity.csv")
    df_f5.to_csv(f5_csv, index=False)
    print(f"\nSaved F5 Sanity results to {f5_csv}")
    print("\n" + "=" * 80)
    print("F5 SANITY RESULTS TABLE:")
    print("=" * 80)
    print(df_f5.to_string(index=False))

    flagged = df_f5[df_f5["flagged_R2_gt_095"]]
    print(f"\nTOTAL FLAGGED PAIRS (R^2 > 0.95): {len(flagged)} / {len(df_f5)}")
    return df_f5

if __name__ == "__main__":
    run_part_c()
    run_part_d()
