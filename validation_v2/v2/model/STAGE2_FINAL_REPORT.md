# FORENSIAIR V2 — STAGE 2 FINAL EVALUATION REPORT

**Execution Timestamp:** 2026-10-11 23:40:44  
**Git Tag v2-protocol-frozen Hash:** `8c98d3d2d45f3ab79dfa54327cb56bd94b28188c`  
**Operating Budget:** 1.0 False Alert Episode / Factory-Month (328 Target Episodes on 327.61 Factory-Months)  
**Evaluation Architecture:** 5-Fold Factory-Grouped Cross-Validation, Bidirectional Cross-Mechanism  

---

## Table 1: Cross-Mechanism Generalization Gap (development result, post-hoc)

| Direction | Tamper Type | In-Mechanism Test | In Events | In Recall | In 95% CI | Cross-Mechanism Test | Cross Events | Cross Recall | Cross 95% CI | Generalization Gap |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Direction 1 (Train A) | **T1** | Mechanism A | 653 | 27.72% | [14.77%, 37.58%] | Mechanism B | 714 | **7.98%** | [3.86%, 12.54%] | **+19.74%** |
| Direction 1 (Train A) | **T2** | Mechanism A | 521 | 37.81% | [19.31%, 49.80%] | Mechanism B | 510 | **32.94%** | [21.56%, 42.93%] | **+4.87%** |
| Direction 1 (Train A) | **T3** | Mechanism A | 353 | 28.05% | [19.48%, 36.44%] | Mechanism B | 611 | **4.42%** | [1.61%, 7.50%] | **+23.63%** |
| Direction 1 (Train A) | **T7** | Mechanism A | 372 | 44.89% | [33.62%, 54.61%] | Mechanism B | 718 | **26.46%** | [15.88%, 37.21%] | **+18.43%** |
| Direction 1 (Train A) | **Pooled** | Mechanism A | 1899 | 33.91% | [24.62%, 42.13%] | Mechanism B | 2553 | **17.31%** | [11.81%, 22.92%] | **+16.60%** |
| Direction 2 (Train B) | **T1** | Mechanism B | 714 | 21.57% | [10.20%, 34.86%] | Mechanism A | 653 | **18.07%** | [8.92%, 26.15%] | **+3.50%** |
| Direction 2 (Train B) | **T2** | Mechanism B | 510 | 33.14% | [22.16%, 43.25%] | Mechanism A | 521 | **34.36%** | [18.31%, 45.97%] | **-1.22%** |
| Direction 2 (Train B) | **T3** | Mechanism B | 611 | 20.13% | [12.27%, 30.30%] | Mechanism A | 353 | **37.39%** | [25.42%, 48.65%] | **-17.26%** |
| Direction 2 (Train B) | **T7** | Mechanism B | 718 | 37.47% | [23.73%, 50.28%] | Mechanism A | 372 | **40.86%** | [27.51%, 52.42%] | **-3.40%** |
| Direction 2 (Train B) | **Pooled** | Mechanism B | 2553 | 28.01% | [19.96%, 36.08%] | Mechanism A | 1899 | **30.60%** | [22.97%, 37.45%] | **-2.59%** |

---

## Table 2: Paired Difference V2 vs Best V1 Comparator (Cross-Mechanism) (development result, post-hoc)

| Evaluation Direction | Tamper Type | Events | Recall V2 | 95% CI V2 | Recall V1 M1 | Recall V1 IF | Recall V1 Best | Paired Diff (V2 - M1) | Paired Diff (V2 - Best V1) | Paired 95% CI | Passes Reading Rule |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Direction 1 (Train A -> Test B Cross) | **T1** | 714 | **7.98%** | [3.86%, 12.54%] | 12.75% | 1.26% | 39.50% | -4.76% | **-31.51%** | [-42.97%, -21.02%] | **NO (FAIL)** |
| Direction 1 (Train A -> Test B Cross) | **T2** | 510 | **32.94%** | [21.56%, 42.93%] | 8.43% | 3.53% | 23.53% | +24.51% | **+9.41%** | [-3.93%, 21.57%] | **NO (FAIL)** |
| Direction 1 (Train A -> Test B Cross) | **T3** | 611 | **4.42%** | [1.61%, 7.50%] | 19.80% | 31.26% | 55.16% | -15.38% | **-50.74%** | [-61.82%, -39.34%] | **NO (FAIL)** |
| Direction 1 (Train A -> Test B Cross) | **T7** | 718 | **26.46%** | [15.88%, 37.21%] | 19.22% | 22.84% | 43.04% | +7.24% | **-16.57%** | [-25.50%, -7.73%] | **NO (FAIL)** |
| Direction 1 (Train A -> Test B Cross) | **Pooled** | 2553 | **17.31%** | [11.81%, 22.92%] | 15.39% | 14.96% | 41.05% | +1.92% | **-23.74%** | [-29.04%, -18.42%] | **NO (FAIL)** |
| Direction 2 (Train B -> Test A Cross) | **T1** | 653 | **18.07%** | [8.92%, 26.15%] | 16.23% | 4.59% | 43.95% | +1.84% | **-25.88%** | [-31.04%, -19.86%] | **NO (FAIL)** |
| Direction 2 (Train B -> Test A Cross) | **T2** | 521 | **34.36%** | [18.31%, 45.97%] | 7.10% | 1.73% | 18.23% | +27.26% | **+16.12%** | [-3.05%, 30.18%] | **NO (FAIL)** |
| Direction 2 (Train B -> Test A Cross) | **T3** | 353 | **37.39%** | [25.42%, 48.65%] | 3.40% | 3.97% | 36.26% | +33.99% | **+1.13%** | [-13.98%, 15.94%] | **NO (FAIL)** |
| Direction 2 (Train B -> Test A Cross) | **T7** | 372 | **40.86%** | [27.51%, 52.42%] | 10.22% | 9.68% | 21.24% | +30.65% | **+19.62%** | [1.99%, 34.45%] | **YES (PASS)** |
| Direction 2 (Train B -> Test A Cross) | **Pooled** | 1899 | **30.60%** | [22.97%, 37.45%] | 10.16% | 4.69% | 31.02% | +20.43% | **-0.42%** | [-8.06%, 6.59%] | **NO (FAIL)** |

---

## Table 3: Realized Clean False Alarms per Factory-Month (development result, post-hoc)

| Direction | Model Architecture | Mean FA / Month | Median FA / Month | Max FA / Month | Operating Cutoff $\tau$ | Target Budget |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| dir1 | `T1_T2` | **0.840** | 0.000 | 16.110 | 0.97424 | 1.000 / mo |
| dir1 | `T3` | **0.856** | 0.083 | 7.571 | 0.98123 | 1.000 / mo |
| dir1 | `T7` | **0.871** | 0.083 | 6.905 | 0.96699 | 1.000 / mo |
| dir1 | `pooled` | **0.845** | 0.083 | 10.184 | 0.97875 | 1.000 / mo |
| dir2 | `T1_T2` | **0.934** | 0.333 | 5.907 | 0.94895 | 1.000 / mo |
| dir2 | `T3` | **0.858** | 0.416 | 5.158 | 0.95911 | 1.000 / mo |
| dir2 | `T7` | **0.862** | 0.083 | 7.238 | 0.96257 | 1.000 / mo |
| dir2 | `pooled` | **0.930** | 0.250 | 5.824 | 0.96469 | 1.000 / mo |

---

## Table 4: Stratification by Severity, Duration and Parameter (development result, post-hoc)

| Dimension | Subgroup Category | Events | Recall V2 (Dir 1 Cross) | 95% CI V2 | Recall V1 M1 | 95% CI V1 | Delta |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Severity** | `moderate` | 807 | **19.33%** | [12.17%, 27.42%] | 14.13% | [9.90%, 18.62%] | **+5.20%** |
| **Severity** | `obvious` | 897 | **22.74%** | [14.96%, 31.14%] | 19.96% | [14.58%, 25.81%] | **+2.78%** |
| **Severity** | `subtle` | 849 | **9.66%** | [5.15%, 14.67%] | 11.78% | [7.81%, 15.91%] | **-2.12%** |
| **Duration** | `<=16 rows (<=4h)` | 1428 | **5.60%** | [2.86%, 8.92%] | 7.21% | [5.17%, 9.56%] | **-1.61%** |
| **Duration** | `48-96 rows (12h-24h)` | 810 | **27.04%** | [21.07%, 32.07%] | 19.88% | [15.85%, 23.76%] | **+7.16%** |
| **Duration** | `>=288 rows (>=72h)` | 315 | **45.40%** | [27.75%, 61.18%] | 40.95% | [30.33%, 52.60%] | **+4.45%** |
| **Parameter** | `ETP-BOD` | 119 | **0.00%** | [0.00%, 0.00%] | 16.81% | [4.88%, 32.50%] | **-16.81%** |
| **Parameter** | `ETP-COD` | 93 | **0.00%** | [0.00%, 0.00%] | 12.90% | [3.85%, 20.00%] | **-12.90%** |
| **Parameter** | `ETP-Flow` | 794 | **14.99%** | [3.44%, 24.84%] | 17.76% | [10.31%, 26.56%] | **-2.77%** |
| **Parameter** | `ETP-TSS` | 114 | **0.00%** | [0.00%, 0.00%] | 14.04% | [0.00%, 19.64%] | **-14.04%** |
| **Parameter** | `ETP-pH` | 1433 | **22.54%** | [16.25%, 29.07%] | 14.24% | [10.17%, 18.06%] | **+8.30%** |

---

## Table 5: Operating Budget Sensitivity Curve (development result, post-hoc)

| Target Budget | Direction | Test Mechanism | Cutoff $\tau$ | Realized FA (/mo) | Evaluated Events | Detected Events | Event Recall |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1.0 / mo | Train A | A (In-Mechanism) | 0.97875 | 1.001 | 1899 | 644 | **33.91%** |
| 1.0 / mo | Train A | B (Cross-Mechanism) | 0.97875 | 1.001 | 2553 | 442 | **17.31%** |
| 1.0 / mo | Train B | B (In-Mechanism) | 0.96469 | 1.001 | 2553 | 715 | **28.01%** |
| 1.0 / mo | Train B | A (Cross-Mechanism) | 0.96469 | 1.001 | 1899 | 581 | **30.60%** |
| 2.0 / mo | Train A | A (In-Mechanism) | 0.95384 | 1.999 | 1899 | 860 | **45.29%** |
| 2.0 / mo | Train A | B (Cross-Mechanism) | 0.95384 | 1.999 | 2553 | 729 | **28.55%** |
| 2.0 / mo | Train B | B (In-Mechanism) | 0.94119 | 1.999 | 2553 | 925 | **36.23%** |
| 2.0 / mo | Train B | A (Cross-Mechanism) | 0.94119 | 1.999 | 1899 | 742 | **39.07%** |
| 4.0 / mo | Train A | A (In-Mechanism) | 0.90995 | 3.999 | 1899 | 1075 | **56.61%** |
| 4.0 / mo | Train A | B (Cross-Mechanism) | 0.90995 | 3.999 | 2553 | 1004 | **39.33%** |
| 4.0 / mo | Train B | B (In-Mechanism) | 0.89653 | 3.999 | 2553 | 1249 | **48.92%** |
| 4.0 / mo | Train B | A (Cross-Mechanism) | 0.89653 | 3.999 | 1899 | 946 | **49.82%** |
| 10.0 / mo | Train A | A (In-Mechanism) | 0.50024 | 10.000 | 1899 | 1522 | **80.15%** |
| 10.0 / mo | Train A | B (Cross-Mechanism) | 0.50024 | 10.000 | 2553 | 1778 | **69.64%** |
| 10.0 / mo | Train B | B (In-Mechanism) | 0.01717 | 9.322 | 2553 | 2487 | **97.41%** |
| 10.0 / mo | Train B | A (Cross-Mechanism) | 0.01717 | 9.322 | 1899 | 1846 | **97.21%** |

---

## Table 6: No-Op Event Impact Analysis on Mechanism B (development result, post-hoc)

| Tamper Type | Total Events (Incl No-Op) | No-Op Count | No-Op Share | Primary Events (Excl No-Op) | Recall (No-Op Excluded) | 95% CI (Excluded) | Recall (No-Op Included) | 95% CI (Included) | Impact Delta |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **T1** | 760 | 46 | 6.05% | 714 | **7.98%** | [3.86%, 12.54%] | **7.50%** | [3.61%, 11.81%] | **+0.48%** |
| **T2** | 523 | 13 | 2.49% | 510 | **32.94%** | [21.56%, 42.93%] | **32.31%** | [21.18%, 42.21%] | **+0.63%** |
| **T3** | 611 | 0 | 0.00% | 611 | **4.42%** | [1.61%, 7.50%] | **4.42%** | [1.61%, 7.50%] | **+0.00%** |
| **T7** | 800 | 82 | 10.25% | 718 | **26.46%** | [15.88%, 37.21%] | **26.12%** | [16.11%, 36.10%] | **+0.34%** |
| **Pooled** | 2694 | 141 | 5.23% | 2553 | **17.31%** | [11.81%, 22.92%] | **17.15%** | [11.55%, 22.76%] | **+0.16%** |

---

## Table 7: Type-Specialist Diagnostic Models (development result, post-hoc)

| Specialist Model | Target Tamper Types | Operating Cutoff $\tau$ | Realized FA (/mo) | Evaluated Events | Specialist Recall | 95% CI Specialist | Pooled Model Recall | 95% CI Pooled | Architectural Status |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **T1_T2 Specialist** | `T1+T2` | 0.97424 | 1.001 | 1224 | **21.90%** | [10.41%, 34.06%] | **18.38%** | [10.66%, 25.89%] | *Not additive (individual 1.0/mo budget)* |
| **T3 Specialist** | `T3` | 0.98123 | 0.998 | 611 | **24.88%** | [9.33%, 41.77%] | **4.42%** | [1.61%, 7.50%] | *Not additive (individual 1.0/mo budget)* |
| **T7 Specialist** | `T7` | 0.96699 | 1.001 | 718 | **32.73%** | [22.27%, 42.36%] | **26.46%** | [15.88%, 37.21%] | *Not additive (individual 1.0/mo budget)* |

---

## Table 8: Window AUPRC and Detection Delay Summary (development result, post-hoc)

| Evaluation Setting | Method | Window AUPRC | Median Detection Delay (h) | Operating Budget |
|:---|:---|:---:|:---:|:---:|
| Direction 1 Cross (Train A -> Test B) | **V2 Pooled Supervised Model** | **0.2464** | 3.75 h | 1.0 false alert / month |
| Direction 1 Cross (Train A -> Test B) | **V1 M1 Multi-Check Fusion** | **0.2568** | 3.75 h | 1.0 false alert / month |
| Direction 1 Cross (Train A -> Test B) | **B0 Random Alerts** | **0.0334** | 0.00 h | 1.0 false alert / month |
