# FORENSIAIR RUN 2 DIAGNOSTICS REPORT

**Evaluation Specification:** `PROTOCOL_v1.md` + `PROTOCOL_v1.1.md` (Frozen)  
**Evaluation Scope:** 33 Development Factories (327.61 Factory-Months, Seeds 1–5, 2,501 Valid Injected Events)  
**Primary Operating Point:** Target 1.0 Alert Episode / Factory-Month on Training Clean Telemetry (328 Target Episodes)  

---

## 1. Per-Method Operating Point & Calibration Diagnostics

The table below reports for each evaluated method: the calibrated cutoff $\tau$, alert episodes and flagged rows on clean telemetry vs. injected copies, count of series with zero alerts, realized clean false alarm rate per factory-month, and the root cause of zero recall or saturation.

| Method | Cutoff $\tau$ | Clean Episodes | Clean Rows | Injected Episodes | Injected Rows | Clean Zero-Alert Series | Injected Zero-Alert Series | Realized FA / Month | Diagnosis & Root Cause |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **M1: Multi-Check Max Fusion** | 3.7709 | 328 | 867 | 1,323 | 19,940 | 39 / 81 (48.1%) | 32 / 200 (16.0%) | **1.001** | N/A (Active detector, 14.39% recall) |
| **F1 (eps=0 exact repeat)** | 2.6739 | 329 | 21,559 | 1,387 | 88,797 | 47 / 81 (58.0%) | 74 / 200 (37.0%) | **1.004** | N/A (Active detector, 5.36% recall) |
| **F1 (eps=1 1-step quasi-flat)** | 2.621 | 328 | 20,324 | 1,436 | 87,163 | 47 / 81 (58.0%) | 77 / 200 (38.5%) | **1.001** | N/A (Active detector, 7.45% recall) |
| **F1 (eps=2 2-step quasi-flat)** | 2.5335 | 329 | 21,260 | 1,557 | 102,463 | 43 / 81 (53.1%) | 67 / 200 (33.5%) | **1.004** | N/A (Active detector, 10.98% recall) |
| **F2 (Copy-Paste replay)** | 2.8168 | 328 | 1,453 | 918 | 4,250 | 26 / 81 (32.1%) | 29 / 200 (14.5%) | **1.001** | N/A (Active detector, 4.47% recall) |
| **F3 (Limit Proximity)** | 1.1786 | 328 | 19,587 | 0 | 0 | 58 / 81 (71.6%) | 200 / 200 (100.0%) | **1.001** | NO ALERTS ON EVENTS: Only 27/81 series have CTO limits; on those series tau=1.4556 required extreme proximity, missing T3 events; 0 alert episodes on injected series. |
| **F5 (Correlation Break)** | 1.0 | 0 | 0 | 0 | 0 | 81 / 81 (100.0%) | 200 / 200 (100.0%) | **0.000** | CODE BUG: Correlation stats not added to calib_dict in calibrate(); score_tail_prob received empty calibration distribution, outputting 100% NaN scores. |
| **F6 (Level Shift Drift)** | 3.0779 | 328 | 1,345 | 1,183 | 5,682 | 22 / 81 (27.2%) | 10 / 200 (5.0%) | **1.001** | N/A (Active detector, 10.52% recall) |
| **F6 (Linear Slope Drift)** | 3.311 | 328 | 914 | 1,117 | 3,772 | 24 / 81 (29.6%) | 20 / 200 (10.0%) | **1.001** | N/A (Active detector, 7.24% recall) |
| **IF (LOFO Sensor Isolation Forest)** | 1.0 | 0 | 0 | 0 | 0 | 81 / 81 (100.0%) | 200 / 200 (100.0%) | **0.000** | CODE BUG: evaluate_run2 called calibrate(skip_if=True) which omitted if_raw_score from calib_dict; score_tail_prob received empty calibration array, outputting 100% NaN. |
| **B0: Random Alerts** | N/A (Budget) | 328 | 5,248 | 1,235 | 26,240 | 0 / 81 (0.0%) | 0 / 200 (0.0%) | **1.001** | N/A (Active baseline, 3.19% recall) |
| **B1: Robust Z-Score** | 46300.0 | 330 | 3,444 | 936 | 1,831 | 69 / 81 (85.2%) | 170 / 200 (85.0%) | **1.007** | N/A (Active baseline, 0.68% recall) |
| **B2: Pooled IF** | 0.2608 | 328 | 1,537 | 1,162 | 4,915 | 67 / 81 (82.7%) | 170 / 200 (85.0%) | **1.001** | N/A (Active baseline, 1.15% recall) |
| **B3: Per-Sensor IF alone** | 1.0 | 0 | 0 | 0 | 0 | 81 / 81 (100.0%) | 200 / 200 (100.0%) | **0.000** | CODE BUG: Identical to IF_sensor; inherited 100% NaN scores due to skip_if=True omitting if_raw_score calibration distribution. |
| **B4: Legacy Fingerprint Rules** | 0.5 | 3,961 | 349,264 | 17,443 | 1,491,347 | 17 / 81 (21.0%) | 15 / 200 (7.5%) | **12.091** | UNCONSTRAINED BINARY RULES: Uncalibrated binary flags fired 3,961 times on clean series (12.09 alerts/fac-mo, 12x over budget); achieved 100% recall by saturating telemetry. |

### Detailed Explanation of the Exact Zeros for IF, B3, F3, F5
1. **IF (LOFO Sensor Isolation Forest) & B3 (Per-Sensor IF alone) — CODE BUG**:
   - In `detector.py` lines 492–503, `if_score` is computed as:
     `calib_if = calib_dict.get('if_raw_score', np.array([]))`  
     `out_df['if_score'] = score_tail_prob(calib_if, if_raw_sc, mode='high')`
   - In `evaluate_run2.py` lines 468 and 627, calibration was called with:
     `calib = calibrate(grid, mode='blind', cto_limits=cto_limits, skip_if=True)`
   - The flag `skip_if=True` was added in Step 2b to avoid self-training an internal IF model, but it simultaneously skipped computing `calib_dict['if_raw_score']`. Consequently, `calib_if` was an empty array ($N = 0$).
   - Line 31 of `score_tail_prob` states: `if N == 0: return np.full(len(current_stat), np.nan)`.
   - Therefore, `if_score` and `B3_sensor_if` were **100% NaN** across all rows in both clean and injected telemetry. Because all scores were NaN, zero alert episodes were ever formed.

2. **F5 (Correlation Break) — CODE BUG**:
   - In `detector.py`, `compute_f5_correlation` is computed factory-wide across parameter pairs (BOD, COD, TSS).
   - However, `calibrate()` accepts a single `df_series`, not a factory dataframe, and does not accept `f5_corr_dict`. Thus, `calib_dict` **never contained** keys `F5_corr_w96` or `F5_corr_w288`.
   - In `score()` lines 486–487:
     `calib_corr = calib_dict.get(f'F5_corr_w{w}', np.array([]))`  
     `out_df[col_name] = score_tail_prob(calib_corr, curr_corr, mode='two_sided')`
   - Because `calib_corr` was permanently empty, `score_tail_prob` returned **100% NaN** for all F5 scores. Zero alert episodes were ever generated.

3. **F3 (Limit Proximity) — NO ALERTS ON INJECTED EVENTS (Design / Coverage Limitation)**:
   - F3 requires a consent-to-operate maximum limit from `consent_limits.csv`.
   - In the dev dataset, only **27 out of 81 series (33.3%)** have an identifiable consent limit. For the remaining 54 series, F3 is 100% NaN.
   - On the 27 clean series with limits, F3 produced valid scores. Binary search calibrated a global cutoff $\tau = 1.1786$ ($p \approx 0.066$).
   - On injected copies, T3 tampering brings readings close to the limit (e.g. 90–98%), but in blind calibration, the injected readings are included in the calibration series, raising the threshold. Crucially, at $\tau = 1.1786$, zero episodes were formed that overlapped the injected T3 windows, resulting in **0 alert episodes** on injected telemetry and 0% recall.

4. **B4 Realized Alerts per Factory-Month — 12.091 ALERTS/MONTH (Saturation)**:
   - B4 consists of fixed, uncalibrated binary threshold rules (`rolling_std < 1e-6`, `autocorr > 0.95`, etc.).
   - On clean industrial telemetry, normal operating regimes regularly trigger these rules (autocorrelation in continuous sensors is almost always $> 0.95$, and quantised industrial sensors naturally exhibit flat segments).
   - B4 generated **3,961 alert episodes** and **349,264 flagged rows** on clean telemetry across 327.61 months, yielding a realized false alarm rate of **12.091 alerts per factory-month** (12x higher than the permitted budget of 1.0).
   - B4's reported 100% recall was achieved entirely because its alerts saturate the telemetry, violating the false-alarm constraint.

---

## 2. Perfect-Ranker Recall Cap (Structural Constraint Analysis)

### Mathematical Proof of the 1-Alert-per-Event Bound
In `labels.csv`, every injected event $i$ has a start timestamp $s_i$ and end timestamp $e_i$. Protocol v1.1 Section 5 specifies that an event is detected if an alert episode overlaps $[s_i, e_i + 2\text{h}]$. Alert episodes merge contiguous flagged rows with gaps $\le 16$ rows (4 hours).
An analysis of all 2,349 headline injected events reveals that **zero events have overlapping or adjacent detection windows**:
$$\min_{i \ne j} |s_j - e_i| > 4\text{h}$$
Consequently, **a single alert episode can detect at most ONE event**.

### Perfect-Ranker Recall Cap Formula
For a factory $f$ with duration $M_f$ months and $E_{f,s}$ injected events in seed $s$:
- At budget $B \in \{1, 2, 4, 10\}$ alerts/factory-month, the maximum allowed alert episodes is $N_B = \text{round}(B \times M_f)$.
- The maximum number of events ANY detector (even an all-knowing oracle / perfect ranker) can detect is:
$$\text{Cap}_{\text{events}} = \min(E_{f,s}, N_B)$$
- The theoretical maximum recall cap is:
$$\text{Cap}_{\text{recall}} = \frac{\min(E_{f,s}, N_B)}{E_{f,s}}$$

### Dev Set Summary: Perfect-Ranker Recall Cap vs. Realized M1 Recall
Across the 21 injection factories (105 series-seeds):
- Total Headline Events: **2,349** (Mean = 22.4 events / factory-seed)
- Mean Injected Event Frequency: **1.88 events per factory-month** (Min = 0.08, Max = 2.62 events/month)

| Target Budget | Allowed Alerts (Dev Total) | Perfect-Ranker Event Cap | Perfect-Ranker Recall Cap | Realized M1 Recall | M1 % of Perfect Ranker |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **1 alert / factory-month** | 1,235 | 1,109 / 2,349 | **47.21%** | **14.39%** | **30.5%** |
| **2 alerts / factory-month** | 2,470 | 2,044 / 2,349 | **87.02%** | **20.43%** | **23.5%** |
| **4 alerts / factory-month** | 4,945 | 2,349 / 2,349 | **100.00%** | **26.99%** | **27.0%** |
| **10 alerts / factory-month** | 12,345 | 2,349 / 2,349 | **100.00%** | **45.08%** | **45.1%** |

> **Key Theoretical Finding**: The target bar of $\ge 70\%$ recall at 1.0 alert/factory-month is **MATHEMATICALLY IMPOSSIBLE** under this injection distribution. Because factories experience an average of 1.88 injected events per month, a budget of 1.0 alert/month caps the maximum possible recall of an all-knowing oracle at **47.21%**. M1's realized recall of 14.39% represents nearly a third (30.5%) of the theoretical ceiling.

### How Alerts Are Counted: Per Factory vs. Per Series
- In Protocol v1.1, alerts are strictly budgeted **per factory-month**, NOT per series-month.
- Total budget across all 33 dev factories is $1.0 \times 327.61 = 328$ alert episodes.
- In a factory with 5 monitored parameters (pH, Flow, BOD, COD, TSS), all alerts across all 5 parameters aggregate into the factory's single monthly budget.
- If alerts had been budgeted **per series-month**, the total allowed budget would be $81 \times 12.02 \approx 970$ alert episodes (a $3\times$ higher budget), raising the 1-alert cap from 47.21% to over 85%.

*(Full per factory-seed breakdown across all 105 seeds is saved in `perfect_ranker_cap.csv`)*.

---

## 3. M1 Recall by Type $\times$ Severity $\times$ Duration (Summary Table)

Below is an aggregated summary of the 124-cell matrix saved to `m1_recall_type_severity_duration.csv`.

| Tamper Type | Severity | Duration 4 rows (1h) | Duration 16 rows (4h) | Duration 48 rows (12h) | Duration 96 rows (24h) | Duration 288 rows (72h) | Duration 672 rows (168h) | Overall Type Recall |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **T1 (Flatline)** | subtle | 4.3% (3/70) | 4.1% (2/49) | 0.0% (0/39) | 8.3% (3/36) | 7.7% (2/26) | 30.0% (3/10) | **17.5% (114/653)** |
| | moderate | 4.2% (3/71) | 2.0% (1/49) | 7.9% (3/38) | 18.5% (5/27) | 50.0% (9/18) | 22.2% (2/9) | |
| | obvious | 8.2% (5/61) | 21.7% (10/46) | 29.3% (12/41) | 61.3% (19/31) | 100.0% (18/18) | 100.0% (14/14) | |
| **T2 (Copy-Paste)** | subtle | 0.0% (0/59) | 0.0% (0/38) | 0.0% (0/25) | 0.0% (0/23) | 5.3% (1/19) | 10.0% (1/10) | **7.9% (41/521)** |
| | moderate | 2.0% (1/51) | 2.7% (1/37) | 3.4% (1/29) | 16.7% (4/24) | 5.9% (1/17) | 11.1% (1/9) | |
| | obvious | 0.0% (0/54) | 18.6% (8/43) | 0.0% (0/30) | 38.5% (10/26) | 52.9% (9/17) | 30.0% (3/10) | |
| **T3 (Limit Proximity)** | subtle | 0.0% (0/37) | 0.0% (0/23) | 0.0% (0/24) | 0.0% (0/18) | 0.0% (0/10) | 0.0% (0/6) | **3.4% (12/353)** |
| | moderate | 0.0% (0/40) | 0.0% (0/27) | 0.0% (0/26) | 0.0% (0/18) | 0.0% (0/12) | 0.0% (0/7) | |
| | obvious | 0.0% (0/38) | 11.1% (3/27) | 10.0% (2/20) | 25.0% (5/20) | 18.2% (2/11) | 0.0% (0/7) | |
| **T4 (Impossible pH)** | subtle | 0.0% (0/37) | 0.0% (0/26) | 5.3% (1/19) | 13.3% (2/15) | 9.1% (1/11) | 0.0% (0/6) | **35.3% (132/374)** |
| | moderate | 2.6% (1/39) | 14.8% (4/27) | 36.8% (7/19) | 52.9% (9/17) | 70.0% (7/10) | 85.7% (6/7) | |
| | obvious | 3.1% (1/32) | 88.0% (22/25) | 100.0% (24/24) | 85.0% (17/20) | 84.6% (11/13) | 80.0% (8/10) | |
| **T5 (Corr Break)** | subtle | 0.0% (0/8) | 0.0% (0/6) | 0.0% (0/5) | 0.0% (0/4) | 0.0% (0/2) | 0.0% (0/1) | **0.0% (0/76)** |
| | moderate | 0.0% (0/9) | 0.0% (0/5) | 0.0% (0/4) | 0.0% (0/4) | 0.0% (0/3) | 0.0% (0/1) | |
| | obvious | 0.0% (0/8) | 0.0% (0/6) | 0.0% (0/4) | 0.0% (0/4) | 0.0% (0/2) | 0.0% (0/1) | |
| **T6 (Dropout)** | all severities | 0.0% (0/40) | 0.0% (0/33) | 0.0% (0/31) | 0.0% (0/22) | 0.0% (0/16) | 0.0% (0/10) | **0.0% (0/152)** *(100% by F7)* |
| **T7 (Drift / Dip)** | subtle | 0.0% (0/41) | 0.0% (0/25) | 0.0% (0/24) | 0.0% (0/15) | 0.0% (0/9) | 0.0% (0/4) | **10.5% (39/372)** |
| | moderate | 0.0% (0/41) | 4.3% (1/23) | 4.3% (1/23) | 12.5% (2/16) | 0.0% (0/12) | 0.0% (0/5) | |
| | obvious | 4.9% (2/41) | 13.0% (3/23) | 33.3% (7/21) | 68.8% (11/16) | 81.8% (9/11) | 50.0% (3/6) | |

---

## 4. Detector Scoring Mechanics & Rank Percentile Properties

### Does Score Equal Percentile Within the Scored Series for Every Check?
**NO.** The scoring functions across checks differ fundamentally from simple row percentiles:

1. **F1 (Quasi-Flat Run-Level Score)**:
   - Uses Laplace-smoothed run-length tail probability:
     $$p = \frac{1 + \sum [\text{natural run lengths} \ge L]}{1 + R_\epsilon}, \quad \text{score} = -\log_{10}(p)$$
   - This is defined over the distribution of *completed natural run lengths* in the series, NOT rows.
   - Every row with quasi-flat run length $L < 8$ receives score = **0.0**.
   - If a series has fewer completed runs (small $R_\epsilon$), its theoretical maximum score is limited to $\log_{10}(1 + R_\epsilon)$, which varies by series length.

2. **F2 (Copy-Paste Replay)**:
   - Evaluates trailing window minimum absolute difference vs. lags $96, \dots, 672$.
   - Windows whose range $\le 1\text{ resolution step}$ are explicitly **masked to NaN** (to prevent flatlines from triggering F2).
   - The number of valid windows $N$ varies between series; NaN rows receive no score.

3. **F3 (Limit Proximity)**:
   - Defined as trailing median divided by consent limit: $r_{\text{med}} / \text{CTO}_{\max}$.
   - For series without consent limits, 100% of rows are **NaN**.

4. **F6 (Shift & Slope)**:
   - Evaluates two-sided empirical tail probabilities: $p = 2 \min(p_{\text{left}}, p_{\text{right}})$.
   - Due to two-sided folding and windowing, the distribution has point mass boundaries.

5. **M1 Max Fusion**:
   - M1 takes the element-wise maximum across 17 check columns:
     $$\text{M1} = \max(F1_0, F1_1, F1_2, F2_{16,96,288}, F3_{16,96,288}, F5_{96,288}, F6\text{shift}_{16,96,288}, F6\text{slope}_{16,96,288}, \text{IF})$$
   - The maximum of multiple tail probabilities completely destroys any single-variable percentile rank property.

### Is the Number of Flagged Rows per Series Fixed by $\tau$?
**NO. The number of flagged rows varies dramatically across series**, for three mathematical reasons:

1. **Episode-Budget Calibration vs. Row Budget**:
   - $\tau$ is calibrated to achieve a target number of **alert EPISODES** (after merging gaps $\le 16$ rows), NOT a target count of rows.
   - A single contiguous anomaly spanning 200 rows forms **1 episode**.
   - 10 isolated spikes spaced 20 rows apart form **10 episodes**.
   - Therefore, the number of flagged rows required to produce 1 episode varies by more than an order of magnitude depending on temporal clustering.

2. **Series Duration Heterogeneity**:
   - Factory series lengths range from 0.11 months (320 rows) to 12.02 months (35,000 rows).
   - Even under a uniform score distribution, a 12-month series has $100\times$ more rows than a 0.11-month series.

3. **Tie Mass and Zero Scores**:
   - In F1, all rows with run length $< 8$ have score 0.0. In series where no run exceeds length 8, **zero rows** have score $> 0$.
   - At $\tau = 3.7709$, 39 out of 81 clean series (48.1%) had **exactly 0 flagged rows and 0 alerts**, while `site_1376` had 38 episodes and `site_1257` had 31 episodes.

---

## 5. Summary of Diagnostic Artifacts Written

The following diagnostic files have been generated strictly inside `validation_v2/runs/run2/diag/`:
1. `method_diagnostics.csv`: Per-method operating points, episode counts, row counts, zero-alert series, and root cause diagnosis.
2. `perfect_ranker_cap.csv`: Per factory-seed event counts, duration, and perfect-ranker recall ceiling across budgets 1, 2, 4, and 10 alerts/month.
3. `m1_recall_type_severity_duration.csv`: Full 3-way interaction table of M1 recall by tampering type $\times$ severity $\times$ duration rows.
4. `RUN2_DIAGNOSTICS_REPORT.md`: This comprehensive diagnostic report.
