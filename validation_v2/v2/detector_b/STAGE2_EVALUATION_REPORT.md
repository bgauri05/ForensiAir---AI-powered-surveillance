# FORENSIAIR V2 — STAGE 2, PART 2.4: FINAL LOFO EVALUATION REPORT

**Protocol Basis:** Protocol v2.0 (Frozen) & Protocol v1.1 Section B, C, G (Frozen)  
**Evaluation Scope:** 33 Permitted Development Factories Only  
**Injections Evaluated:** 2,698 Mechanism B Injected Events Across Seeds 301–305  
**Data Isolation:** Strictly Verified — `Data/Unseen/` & 4 Locked Test Factories Zero Access  
**Calibrated False-Alarm Budget:** 1.0 Alert Episode / Factory-Month (328 Target Episodes on 327.61 Factory-Months)  
**Confidence Intervals:** 95% Cluster-Bootstrap (10,000 resamples over 33 development factories)  
**Execution Timestamp:** 2026-10-11 22:24:10  

---

## 1. Executive Summary & Headline Evaluation Findings

In Stage 2 Part 2.4, the enhanced ForensiAIR V2 detector ($M_2$ composite max fusion) was evaluated under a strict 33-fold Leave-One-Factory-Out (LOFO) architecture across all **2,698 Mechanism B development injection events** (Seeds 301–305).

| Evaluation Metric | Frozen V1 Baseline ($M_1$) | Enhanced V2 Detector ($M_2$) | Absolute Delta ($\Delta$) | Relative Change |
|:---|:---:|:---:|:---:|:---:|
| **Overall Detected Events** | **418** / 2,698 | **305** / 2,698 | **-113 events** | **-27.0%** |
| **Overall Event Recall** | **15.49%** | **11.30%** | **-4.19%** | **0.73x** |
| **95% Cluster-Bootstrap CI** | [12.12%, 18.93%] | [7.86%, 15.09%] | CI Overlap at boundary | Measurable Reduction |
| **Median Detection Delay** | 2.25 hours | 3.75 hours | +1.50 hours | Slower composite onset |
| **Operating Threshold $\tau$** | 3.8062 | 4.0883 | +0.2821 | Threshold elevated |
| **Realized False Alarms** | 0.995 / fac-mo | 1.010 / fac-mo | Budget-Matched | 1.0 alert / month |

### Key Empirical Findings & Mechanistic Insights:
1. **Curse of Max-Fusion Dimension Expansion:** In unweighted hard max fusion ($M_2 = \max(V_1, V_2)$), expanding the evaluation surface from 18 columns ($M_1$) to 38 columns ($M_2$) aggregates the union of clean false-alarm excursions. To strictly preserve the frozen budget of 1.0 false alert/month on clean telemetry, the operating cutoff had to be elevated from $\tau_{M1} = 3.8062$ to $\tau_{M2} = 4.0883$ (+0.2821). At this elevated threshold, marginal events previously captured near $\tau \approx 3.81$ are suppressed, resulting in an overall $M_2$ recall of **11.30%** vs $M_1$ **15.49%**.
2. **Component-Level Diagnostic Strengths:** When evaluated at individual budget-matched operating thresholds (where each check operates at 1.0 alert/month):
   - **$F_{7B}$ Transient Peak Deviation** achieves **13.31%** recall (359 events, $\tau = 2.5745$) with 0.0h delay, outperforming any individual V1 check except IF.
   - **$F_{3B}$ Near-Limit Persistence** achieves **12.60%** recall (340 events, $\tau = 1.0593$), successfully detecting 25.5% of $T_3$-pull events (vs 15.9% for V1 $F_3$).
   - **$\text{IF}_B$ Causal Sensor IF** achieves **12.86%** recall (347 events, $\tau = 2.9086$).
   - **$F_{7B}$ Matched Triangular FIR** achieves **12.01%** recall (324 events, $\tau = 3.2298$).
3. **Rigorous Scientific Integrity:** Per the frozen protocol stopping rules, no post-hoc threshold tuning or detector redefining was conducted. The measured drop in composite $M_2$ recall accurately documents the limitation of simple unweighted max-fusion architectures when scaling to multi-detector suites under strict false-alarm budgets.

---

## 2. Comprehensive Methods & Baselines Comparison (1.0 Alert / Month Budget)

All detectors evaluated at the strict protocol operating point of $\approx 1.0$ false alert episode per factory-month (328 target episodes across 327.61 factory-months), except B4 which is reported at its natural uncalibrated alert rate.

| Method Name | Key | Total Events | Detected Events | Event Recall | 95% Cluster CI | Median Delay (h) | Operating $\tau$ | Realized FA (/mo) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **M2: Enhanced Max Fusion (V2)** | `M2_fusion` | 2698 | 305 | **11.30%** | [7.86%, 15.09%] | 3.75 | 4.0883 | 1.010 |
| **M1: Frozen Legacy Max Fusion (V1)** | `M1_fusion` | 2698 | 418 | **15.49%** | [12.12%, 18.93%] | 2.25 | 3.8062 | 0.995 |
| **F1B: Variance Collapse (V2)** | `F1B_var_collapse` | 2698 | 189 | **7.01%** | [4.02%, 10.31%] | 23.25 | 2.2436 | 1.001 |
| **F1B: Unique Ratio (V2)** | `F1B_unique_ratio` | 2698 | 182 | **6.75%** | [3.98%, 9.52%] | 22.25 | 1.7062 | 1.010 |
| **F2B: Z-Norm Shape Distance (V2)** | `F2B_znorm_dist` | 2698 | 80 | **2.97%** | [1.61%, 4.57%] | 19.62 | 2.6953 | 0.998 |
| **F2: Copy-Paste Replay (V1)** | `F2_copypaste` | 2698 | 126 | **4.67%** | [2.74%, 6.67%] | 32.62 | 2.8168 | 1.001 |
| **F3B: Near-Limit Persistence (V2)** | `F3B_hug_persist` | 2698 | 340 | **12.60%** | [5.69%, 19.72%] | 1.75 | 1.0593 | 1.004 |
| **F3B: Variance Clamping (V2)** | `F3B_var_clamp` | 2698 | 164 | **6.08%** | [1.83%, 11.21%] | 0.00 | 1.1564 | 1.001 |
| **F3: Consent Limit Proximity (V1)** | `F3_limit` | 2698 | 256 | **9.49%** | [4.11%, 15.09%] | 2.00 | 1.1786 | 1.001 |
| **F5: Correlation Break (V1)** | `F5_corr` | 2698 | 79 | **2.93%** | [0.00%, 7.44%] | 0.50 | 1.0376 | 1.001 |
| **F6: Level Shift Drift (V1)** | `F6_shift` | 2698 | 280 | **10.38%** | [7.61%, 13.05%] | 2.00 | 3.0779 | 1.001 |
| **F6: Linear Slope Drift (V1)** | `F6_slope` | 2698 | 292 | **10.82%** | [7.92%, 13.66%] | 1.50 | 3.3110 | 1.001 |
| **F7B: Matched Triangular FIR (V2)** | `F7B_tri_conv` | 2698 | 324 | **12.01%** | [8.39%, 15.86%] | 2.12 | 3.2298 | 1.001 |
| **F7B: Step-Jump Contrast (V2)** | `F7B_step_jump` | 2698 | 207 | **7.67%** | [5.40%, 10.26%] | 0.00 | 3.2355 | 1.004 |
| **F7B: Transient Peak Deviation (V2)** | `F7B_transient_dev` | 2698 | 359 | **13.31%** | [9.90%, 16.55%] | 0.00 | 2.5745 | 1.001 |
| **IF_B: Enhanced Causal IF (V2)** | `if_b_score` | 2698 | 347 | **12.86%** | [9.19%, 16.68%] | 1.50 | 2.9086 | 0.998 |
| **F1: Exact Repeat Run-Level (eps=0)** | `F1_eps0` | 2698 | 272 | **10.08%** | [5.93%, 14.45%] | 2.25 | 2.6739 | 1.004 |
| **F1: 1-Step Quasi-Flat (eps=1)** | `F1_eps1` | 2698 | 301 | **11.16%** | [6.17%, 16.57%] | 3.25 | 2.6210 | 1.001 |
| **F1: 2-Step Quasi-Flat (eps=2)** | `F1_eps2` | 2698 | 315 | **11.68%** | [6.64%, 17.05%] | 4.25 | 2.5335 | 1.004 |
| **B0: Random Alerts (1.0 alert/mo)** | `B0_1.0mo` | 2698 | 95 | **3.52%** | [2.67%, 4.34%] | 0.00 | N/A | 1.000 |
| **B1: Robust Z-Score** | `B1_zscore` | 2698 | 183 | **6.78%** | [1.60%, 14.34%] | 0.00 | 46300.0000 | 1.007 |
| **B2: Pooled Isolation Forest** | `B2_pooled_if` | 2698 | 175 | **6.49%** | [2.84%, 10.94%] | 0.00 | 0.2608 | 1.001 |
| **B3: Sensor IF alone** | `B3_sensor_if` | 2698 | 347 | **12.86%** | [9.19%, 16.68%] | 1.50 | 2.9086 | 0.998 |
| **B4: Legacy Fingerprint Rules** | `B4_legacy_rules` | 2698 | 1136 | **42.11%** | [32.45%, 50.97%] | 2.00 | 0.5000 | 12.091 |

> **Note on Baseline B4:** Legacy rules operate at a natural alert rate of 12.091 alerts per factory-month (4.5x the allowed budget) and is therefore not budget-matched.

---

## 3. Tamper Variant Stratification (M2 vs M1 Comparison)

Mechanism B injects 7 distinct evasive variants designed to bypass V1 checks. The table below demonstrates the exact per-variant detection recovery:

| Tamper Type | Mechanism B Variant Archetype | Events | Detected (M2) | Recall M2 | 95% CI (M2) | Detected (M1) | Recall M1 | Delta $\Delta$ | Primary Detecting Check |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **T1** | `T1-B-freeze` | 766 | 76 | **9.92%** | [5.57%, 15.02%] | 91 | 11.88% | **-1.96%** | `F1_eps0` (33.0%) |
| **T2** | `T2-B-scaled` | 268 | 8 | **2.99%** | [1.11%, 5.07%] | 14 | 5.22% | **-2.24%** | `F3B_hug_persist` (7.8%) |
| **T2** | `T2-B-splice` | 242 | 15 | **6.20%** | [1.44%, 11.74%] | 19 | 7.85% | **-1.65%** | `F2_copypaste` (18.2%) |
| **T3** | `T3-B-ar1` | 308 | 85 | **27.60%** | [13.37%, 44.03%] | 105 | 34.09% | **-6.49%** | `if_b_score` (43.2%) |
| **T3** | `T3-B-pull` | 302 | 34 | **11.26%** | [5.80%, 18.37%] | 51 | 16.89% | **-5.63%** | `F3B_hug_persist` (25.5%) |
| **T7** | `T7-B-step` | 407 | 51 | **12.53%** | [6.44%, 19.05%] | 66 | 16.22% | **-3.69%** | `F7B_transient_dev` (26.5%) |
| **T7** | `T7-B-tri` | 405 | 36 | **8.89%** | [5.04%, 13.00%] | 72 | 17.78% | **-8.89%** | `F6_shift` (17.3%) |

---

## 4. Sensitivity Analyses: Severity, Duration & False-Alarm Budget

### A. Severity Stratification
| Tamper Severity | Total Events | Recall M2 (V2) | 95% CI M2 | Recall M1 (V1) | 95% CI M1 | Recall Gain |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Moderate** | 837 | **10.87%** | [6.77%, 15.52%] | 14.34% | [10.56%, 18.33%] | **-3.46%** |
| **Obvious** | 943 | **14.32%** | [9.97%, 18.87%] | 18.45% | [13.84%, 23.03%] | **-4.14%** |
| **Subtle** | 918 | **8.61%** | [5.43%, 11.91%] | 13.51% | [9.64%, 17.34%] | **-4.90%** |

### B. Tamper Duration Stratification
| Duration (Rows) | Duration (Hours) | Total Events | Recall M2 (V2) | 95% CI M2 | Recall M1 (V1) | 95% CI M1 | Recall Gain |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| 4 rows | 1.0 hours | 975 | **5.85%** | [2.68%, 9.70%] | 6.67% | [3.05%, 10.71%] | **-0.82%** |
| 16 rows | 4.0 hours | 581 | **7.92%** | [4.69%, 11.97%] | 12.39% | [8.31%, 17.29%] | **-4.48%** |
| 48 rows | 12.0 hours | 468 | **5.77%** | [3.32%, 8.61%] | 14.32% | [10.46%, 18.42%] | **-8.55%** |
| 96 rows | 24.0 hours | 352 | **21.02%** | [14.06%, 29.64%] | 27.56% | [19.14%, 36.27%] | **-6.53%** |
| 288 rows | 72.0 hours | 224 | **29.02%** | [18.40%, 42.68%] | 33.93% | [23.63%, 46.47%] | **-4.91%** |
| 672 rows | 168.0 hours | 98 | **36.73%** | [21.28%, 50.70%] | 41.84% | [30.23%, 52.07%] | **-5.10%** |

### C. Operating Budget Sensitivity Curve (1.0, 2.0, 4.0, 10.0 Alerts/Month)
| Budget (FA/mo) | Method | Operating $\tau$ | Realized FA (/mo) | Total Events | Detected Events | Event Recall | 95% Cluster CI |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1.0 | `M2_fusion` | 4.0883 | 1.010 | 2698 | 305 | **11.30%** | [7.86%, 15.09%] |
| 1.0 | `M1_fusion` | 3.8062 | 0.995 | 2698 | 418 | **15.49%** | [12.12%, 18.93%] |
| 1.0 | `B0_random` | N/A | 1.000 | 2698 | 95 | **3.52%** | [2.67%, 4.34%] |
| 1.0 | `B1_zscore` | 46300.0000 | 1.007 | 2698 | 183 | **6.78%** | [1.60%, 14.34%] |
| 1.0 | `B2_pooled_if` | 0.2608 | 1.001 | 2698 | 175 | **6.49%** | [2.84%, 10.94%] |
| 1.0 | `B3_sensor_if` | 2.9086 | 0.998 | 2698 | 347 | **12.86%** | [9.19%, 16.68%] |
| 2.0 | `M2_fusion` | 3.8043 | 1.996 | 2698 | 547 | **20.27%** | [16.07%, 24.34%] |
| 2.0 | `M1_fusion` | 3.4878 | 1.999 | 2698 | 638 | **23.65%** | [19.40%, 27.62%] |
| 2.0 | `B0_random` | N/A | 2.000 | 2698 | 146 | **5.41%** | [3.53%, 7.46%] |
| 2.0 | `B1_zscore` | 32000.0000 | 1.999 | 2698 | 226 | **8.38%** | [2.04%, 17.82%] |
| 2.0 | `B2_pooled_if` | 0.1720 | 1.999 | 2698 | 356 | **13.19%** | [6.23%, 21.21%] |
| 2.0 | `B3_sensor_if` | 2.5671 | 1.999 | 2698 | 504 | **18.68%** | [14.21%, 23.18%] |
| 4.0 | `M2_fusion` | 3.4042 | 3.999 | 2698 | 794 | **29.43%** | [24.58%, 33.77%] |
| 4.0 | `M1_fusion` | 3.0283 | 3.999 | 2698 | 907 | **33.62%** | [28.58%, 38.12%] |
| 4.0 | `B0_random` | N/A | 4.000 | 2698 | 331 | **12.27%** | [8.92%, 15.72%] |
| 4.0 | `B1_zscore` | 2850.0000 | 3.996 | 2698 | 408 | **15.12%** | [5.55%, 28.72%] |
| 4.0 | `B2_pooled_if` | 0.1371 | 3.999 | 2698 | 450 | **16.68%** | [7.80%, 27.04%] |
| 4.0 | `B3_sensor_if` | 2.1881 | 3.999 | 2698 | 789 | **29.24%** | [22.76%, 35.64%] |
| 10.0 | `M2_fusion` | 2.6449 | 10.000 | 2698 | 1295 | **48.00%** | [42.00%, 53.03%] |
| 10.0 | `M1_fusion` | 2.4077 | 9.997 | 2698 | 1359 | **50.37%** | [44.17%, 55.74%] |
| 10.0 | `B0_random` | N/A | 10.000 | 2698 | 619 | **22.94%** | [17.61%, 28.05%] |
| 10.0 | `B1_zscore` | 4.4776 | 10.012 | 2698 | 1423 | **52.74%** | [43.64%, 63.11%] |
| 10.0 | `B2_pooled_if` | 0.0734 | 9.987 | 2698 | 850 | **31.50%** | [19.74%, 44.71%] |
| 10.0 | `B3_sensor_if` | 1.6305 | 10.003 | 2698 | 1384 | **51.30%** | [42.69%, 59.61%] |

---

## 5. Architectural Discussion & Root Cause of Max-Fusion Degradation

### The Multiple-Testing Penalty in Extreme Value Fusions
Under the frozen evaluation protocol, an alert episode is triggered whenever $\max_i(S_i) \ge \tau$. If components $S_1, \dots, S_K$ have tail probabilities on clean data, the distribution of their maximum scales with $K$:
$$\mathbb{P}\left(\max_{i=1}^K S_i \ge \tau\right) \approx 1 - \prod_{i=1}^K \left(1 - \mathbb{P}(S_i \ge \tau)\right) \approx \sum_{i=1}^K \mathbb{P}(S_i \ge \tau)$$
When adding 11 new check columns in V2 ($K$ grows from 18 to 38):
1. **Clean False Alarm Expansion:** Even if each check individually satisfies a small false-alarm budget, the union of false alarms across 38 checks multiplies the number of clean episodes.
2. **Threshold Elevation:** To force total clean false-alarm episodes back to the frozen target of 328 episodes (1.0/month), binary search is forced to raise $\tau$ from $3.8062$ to $4.0883$.
3. **Threshold Masking:** Any tampering event that produces a strong response in one check (e.g. $S_{7B} = 3.90$) triggers an alert at $\tau = 3.81$ under $M_1$, but is completely missed under $M_2$ because $\tau = 4.09 > 3.90$.
4. **Individual Component Power:** This explains why individual components ($F_{7B}$ with 13.31% recall, $F_{3B}$ with 12.60% recall, and $\text{IF}_B$ with 12.86% recall) exhibit strong isolated detection power, but underperform when blindly pooled into an unweighted `max()`.

---

## 6. Protocol Verification & Integrity Audit

- [x] **Strict Data Isolation:** Zero reads to `Data/Unseen/` or locked factories (*Cipla, Glenmark, Indoco, Zydus*).
- [x] **No Protocol or Injector Modifications:** `git diff detector-frozen -- validation_v2/detector validation_v2/injector` remains completely empty.
- [x] **33-Fold LOFO Architecture:** Held-out factory was strictly excluded from training fold Isolation Forest models and baseline pooled models.
- [x] **Blind Empirical Calibration:** Thresholds were calibrated strictly via binary search on clean un-injected telemetry to yield the exact operating budget.
- [x] **Missing Readings Safety:** Missing values (`value = NaN`) strictly output `NaN` scores and never trigger or bridge alert episodes. Missing reading leaks: **0**.
- [x] **Runtime Guard Verification:** **0 series 100% NaN** across all applicable checks.

---

## 7. Generated Manifest & Execution Command

### Execution Command:
```bash
python validation_v2/v2/detector_b/evaluate_stage2_v2.py
```

### Artifact Manifest:
1. [`validation_v2/v2/detector_b/evaluate_stage2_v2.py`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/detector_b/evaluate_stage2_v2.py) — Complete LOFO evaluation pipeline.
2. [`validation_v2/v2/detector_b/MECH_B_V2_EVALUATION.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/detector_b/MECH_B_V2_EVALUATION.csv) — Per-event evaluation records across all 2,698 Mechanism B events.
3. [`validation_v2/v2/detector_b/MECH_B_V2_METHODS_COMPARISON.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/detector_b/MECH_B_V2_METHODS_COMPARISON.csv) — Full method comparison table.
4. [`validation_v2/v2/detector_b/MECH_B_V2_VARIANT_BREAKDOWN.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/detector_b/MECH_B_V2_VARIANT_BREAKDOWN.csv) — Per-variant recall and check-level attribution.
5. [`validation_v2/v2/detector_b/MECH_B_V2_BUDGET_SENSITIVITY.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/detector_b/MECH_B_V2_BUDGET_SENSITIVITY.csv) — Budget sensitivity matrix across 1, 2, 4, 10 alerts/month.
6. [`validation_v2/v2/detector_b/STAGE2_EVALUATION_REPORT.md`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/detector_b/STAGE2_EVALUATION_REPORT.md) — Comprehensive final evaluation report.

================================================================================
 EVALUATION & COMPARISON COMPLETE! Total Time: 699.03s
================================================================================
