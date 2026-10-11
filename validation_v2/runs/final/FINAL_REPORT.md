# FORENSIAIR FINAL TEST EVALUATION REPORT (LOCKED UNSEEN FACTORIES)

**Specification:** `PROTOCOL_v1.md` & `PROTOCOL_v1.1.md` (Frozen)  
**Git Commit (detector-frozen):** `9b493594bb1475aa792123236f3c069308340d2b`  
**Evaluation Type:** Locked Unseen Factories Evaluation (Run Once)  
**Operating Point:** 1.0 False Alert Episode per Factory-Month  
**Total Test Exposure:** 23.91 Factory-Months across 4 Factories  
**Total Injected Events:** 578 Events (Headline: 493, T6: 85)  

## Table 1: Baselines & Detector Comparison (Budget-Matched: 1.0 alert/month)

| Method                                      |   Headline Recall |   95% CI Lower |   95% CI Upper |   T6 Recall |   Median Delay (h) |   Window AUPRC | Pass Bar Status                                                  |
|:--------------------------------------------|------------------:|---------------:|---------------:|------------:|-------------------:|---------------:|:-----------------------------------------------------------------|
| B5: Legacy Composite (Factory risk delta)   |          nan      |       nan      |       nan      |    nan      |             nan    |       nan      | N/A (Paired Risk Delta: Mean=+0.0048, 95% CI [+0.0019, +0.0095]) |
| B0: Random Alerts (Budget rate)             |            0.0304 |         0.0127 |         0.0568 |      0.0471 |               0    |         0.0329 | FAILED                                                           |
| M1: Multi-Check Max Fusion (Pre-declared)   |            0.2921 |         0.2022 |         0.3633 |      0      |               2.88 |         0.2951 | FAILED                                                           |
| F1 (eps=0, exact repeat run-level)          |            0.1014 |         0.0886 |         0.1176 |      0      |               1.75 |       nan      | FAILED                                                           |
| F1 (eps=1, 1-step quasi-flat)               |            0.1521 |         0.1445 |         0.1604 |      0      |               2.75 |       nan      | FAILED                                                           |
| F1 (eps=2, 2-step quasi-flat)               |            0.1846 |         0.1641 |         0.2068 |      0      |               2    |       nan      | FAILED                                                           |
| F2 (Copy-Paste Replay alone)                |            0.1034 |         0.0835 |         0.123  |      0      |              31    |       nan      | FAILED                                                           |
| F3 (Limit Proximity alone)                  |            0.2982 |         0.2695 |         0.3291 |      0      |               1.75 |       nan      | FAILED                                                           |
| F5 (Correlation Break alone)                |            0.2231 |         0.2008 |         0.2447 |      0      |               3    |       nan      | FAILED                                                           |
| F6 (Level Shift Drift alone)                |            0.2637 |         0.2363 |         0.2921 |      0      |               2    |       nan      | FAILED                                                           |
| F6 (Linear Slope Drift alone)               |            0.1947 |         0.1623 |         0.2194 |      0      |               1.75 |       nan      | FAILED                                                           |
| IF (LOFO Sensor Isolation Forest alone)     |            0.2454 |         0.209  |         0.2793 |      0      |               1.5  |       nan      | FAILED                                                           |
| B1: Robust Z-Score (Median/MAD)             |            0.0162 |         0      |         0.0426 |      0.0235 |               1.25 |         0.152  | FAILED                                                           |
| B2: Pooled IF (Legacy style)                |            0.1359 |         0.1016 |         0.1797 |      0      |               0    |         0.0784 | FAILED                                                           |
| B3: Per-Sensor IF alone                     |            0.2454 |         0.209  |         0.2793 |      0      |               1.5  |         0.1881 | FAILED                                                           |
| F4: Validity Hard Alert (pH < 0 or pH > 14) |            0.146  |       nan      |       nan      |      0      |               0    |       nan      | REPORTED SEPARATELY (T4 obvious: 100% recall)                    |
| F7: Gaps Fraction (Missing Data Outages)    |            0      |       nan      |       nan      |      1      |               0    |       nan      | REPORTED SEPARATELY (T6 missing data: 100% recall)               |

### Uncalibrated Baseline (Not Budget-Matched, Outside Pass Table)

| Method                       |   Headline Recall |   95% CI Lower |   95% CI Upper |   T6 Recall |   Median Delay (h) |   Window AUPRC | Pass Bar Status                                                              |
|:-----------------------------|------------------:|---------------:|---------------:|------------:|-------------------:|---------------:|:-----------------------------------------------------------------------------|
| B4: Legacy Fingerprint Rules |            0.5903 |         0.5293 |          0.633 |           0 |                  0 |         0.0684 | NOT BUDGET-MATCHED (Natural alert rate: 28.77 alerts/mo; outside pass table) |

## Table 2: Event Recall by Tampering Type (M1 Multi-Check Max Fusion)

| Tamper Type   |   Total Events |   Detected Events |   Recall (All Severities) |   95% CI Lower |   95% CI Upper |   Recall (Moderate+) |   95% CI Lower (Mod+) | Pass Bar Status                                   |
|:--------------|---------------:|------------------:|--------------------------:|---------------:|---------------:|---------------------:|----------------------:|:--------------------------------------------------|
| T1            |             78 |                19 |                    0.2436 |         0.0526 |         0.425  |               0.2308 |                0.0385 | FAILED                                            |
| T2            |             65 |                23 |                    0.3538 |         0.2188 |         0.5493 |               0.3333 |                0.1111 | FAILED                                            |
| T3            |             89 |                54 |                    0.6067 |         0.4516 |         0.7045 |               0.6271 |                0.4091 | FAILED                                            |
| T4            |             72 |                31 |                    0.4306 |         0.3175 |         0.5238 |               0.5    |                0.3488 | FAILED                                            |
| T5            |             99 |                 1 |                    0.0101 |         0      |         0.0273 |               0      |                0      | FAILED                                            |
| T6            |             85 |                 0 |                    0      |         0      |         0      |               0      |                0      | EXCLUDED FROM PASS CRITERIA (Reported separately) |
| T7            |             90 |                16 |                    0.1778 |         0.0526 |         0.2642 |               0.2034 |                0.0769 | FAILED                                            |

## Table 3: Event Recall by Tampering Type x Severity (M1 Multi-Check Max Fusion)

| Tamper Type   | Severity   |   Total Events |   Detected Events |   Recall |   95% CI Lower |   95% CI Upper |
|:--------------|:-----------|---------------:|------------------:|---------:|---------------:|---------------:|
| T1            | subtle     |             26 |                 7 |   0.2692 |         0.0833 |         0.4286 |
| T1            | moderate   |             29 |                 8 |   0.2759 |         0.0667 |         0.4722 |
| T1            | obvious    |             23 |                 4 |   0.1739 |         0      |         0.5    |
| T2            | subtle     |             20 |                 8 |   0.4    |         0.2941 |         0.4783 |
| T2            | moderate   |             28 |                10 |   0.3571 |         0.1333 |         0.6552 |
| T2            | obvious    |             17 |                 5 |   0.2941 |         0      |         0.5909 |
| T3            | subtle     |             30 |                17 |   0.5667 |         0.5    |         0.7647 |
| T3            | moderate   |             30 |                19 |   0.6333 |         0.3667 |         0.8333 |
| T3            | obvious    |             29 |                18 |   0.6207 |         0.4375 |         0.7692 |
| T4            | subtle     |             22 |                 6 |   0.2727 |         0.1429 |         0.4    |
| T4            | moderate   |             23 |                 4 |   0.1739 |         0.0556 |         0.2593 |
| T4            | obvious    |             27 |                21 |   0.7778 |         0.5    |         0.9286 |
| T5            | subtle     |             43 |                 1 |   0.0233 |         0      |         0.0698 |
| T5            | moderate   |             29 |                 0 |   0      |         0      |         0      |
| T5            | obvious    |             27 |                 0 |   0      |         0      |         0      |
| T6            | subtle     |             39 |                 0 |   0      |         0      |         0      |
| T6            | moderate   |             24 |                 0 |   0      |         0      |         0      |
| T6            | obvious    |             22 |                 0 |   0      |         0      |         0      |
| T7            | subtle     |             31 |                 4 |   0.129  |         0      |         0.25   |
| T7            | moderate   |             32 |                 4 |   0.125  |         0      |         0.2105 |
| T7            | obvious    |             27 |                 8 |   0.2963 |         0.1304 |         0.4286 |

## Table 4: Per-Factory Recall & False Alarms

| factory_id   |   Factory Months |   Headline Events |   Detected Events |   Headline Recall |   T6 Events |   T6 Recall |   Realized FA / Month |
|:-------------|-----------------:|------------------:|------------------:|------------------:|------------:|------------:|----------------------:|
| Cipla        |             5.98 |               128 |                44 |            0.3438 |          22 |           0 |                 6.023 |
| Glenmark     |             5.98 |               128 |                35 |            0.2734 |          22 |           0 |                 3.346 |
| Indoco       |             5.98 |               109 |                16 |            0.1468 |          19 |           0 |                 1.004 |
| Zydus        |             5.98 |               128 |                49 |            0.3828 |          22 |           0 |                 5.856 |

## Table 5: Realized False Alarms per Factory-Month on Clean Test Copies

| factory_id   |   factory_months |   calibrated_tau |   false_alert_episodes |   realized_rate_per_month |
|:-------------|-----------------:|-----------------:|-----------------------:|--------------------------:|
| Cipla        |             5.98 |           3.7955 |                     36 |                     6.023 |
| Glenmark     |             5.98 |           3.7955 |                     20 |                     3.346 |
| Indoco       |             5.98 |           3.7955 |                      6 |                     1.004 |
| Zydus        |             5.98 |           3.7955 |                     35 |                     5.856 |

### False Alarm Summary

|   mean_fa_rate |   std_fa_rate |   median_fa_rate |   min_fa_rate |   max_fa_rate |   total_test_months |   total_false_episodes |
|---------------:|--------------:|-----------------:|--------------:|--------------:|--------------------:|-----------------------:|
|          4.057 |         2.375 |            4.601 |         1.004 |         6.023 |               23.91 |                     97 |

## Table 6: Operating Point Sensitivity (Recall at 1, 2, 4, 10 alerts/month)

|   Target Budget (alerts/fac-mo) |   Realized Mean FA Rate |   Realized Median FA Rate |   Realized Min FA Rate |   Realized Max FA Rate |   Headline Recall |   95% CI Lower |   95% CI Upper |
|--------------------------------:|------------------------:|--------------------------:|-----------------------:|-----------------------:|------------------:|---------------:|---------------:|
|                               1 |                   4.057 |                     4.601 |                  1.004 |                  6.023 |            0.2921 |         0.2022 |         0.3633 |
|                               2 |                   9.243 |                     9.368 |                  6.023 |                 12.213 |            0.3935 |         0.3538 |         0.4141 |
|                               4 |                  14.513 |                    14.387 |                 10.205 |                 19.073 |            0.4686 |         0.4473 |         0.4941 |
|                              10 |                  30.49  |                    33.124 |                 17.064 |                 38.648 |            0.6045 |         0.5363 |         0.6523 |

## Table 7: Detection Tolerance Sensitivity (M1 Fusion at 1.0 alert/month)

| Tolerance Window   | Classification Label   |   Detected Events |   Total Headline Events |   Headline Recall |   95% CI Lower |   95% CI Upper |
|:-------------------|:-----------------------|------------------:|------------------------:|------------------:|---------------:|---------------:|
| 2h                 | Primary (<= 2h)        |               144 |                     493 |            0.2921 |         0.2022 |         0.3633 |
| 24h                | Sensitivity (<= 24h)   |               148 |                     493 |            0.3002 |         0.211  |         0.375  |
| 72h                | Sensitivity (<= 72h)   |               164 |                     493 |            0.3327 |         0.2352 |         0.4121 |

## Table 8: Injected Episode Classification & Alert Multiplicity

| Category                                | Episodes   |   Share (%) |
|:----------------------------------------|:-----------|------------:|
| (a) Overlapping or <= 2h after event    | 188        |       45.41 |
| (b) 2h to 72h after event ends          | 47         |       11.35 |
| (c) Elsewhere (unassociated)            | 179        |       43.24 |
| Total Alert Episodes on Injected Copies | 414        |      100    |
| Mean Episodes per Detected Event        | 1.306      |      nan    |
| Median Episodes per Detected Event      | 1.0        |      nan    |
| Range Episodes per Detected Event       | [1, 4]     |      nan    |

## Table 9: Protocol v1.1 Subgroup Breakdowns

### A. T1 & T2 Natural Run Duration Split

| Tamper Type   | Duration Category                 |   Total Events |   Detected Events |   Recall |   95% CI Lower |   95% CI Upper |
|:--------------|:----------------------------------|---------------:|------------------:|---------:|---------------:|---------------:|
| T1            | Beyond-Natural (>= 99.9th pctile) |             38 |                17 |   0.4474 |         0.1429 |         0.6923 |
| T1            | Within-Natural (< 99.9th pctile)  |             40 |                 2 |   0.05   |         0      |         0.1463 |
| T2            | Beyond-Natural (>= 99.9th pctile) |             31 |                15 |   0.4839 |         0.25   |         0.6667 |
| T2            | Within-Natural (< 99.9th pctile)  |             34 |                 8 |   0.2353 |         0.1    |         0.3333 |

### B. T4 Obvious vs Permit-Breach Split

| T4 Category   |   Total Events |   Detected Events |   Recall |   95% CI Lower |   95% CI Upper |
|:--------------|---------------:|------------------:|---------:|---------------:|---------------:|
| obvious       |             27 |                21 |   0.7778 |         0.5    |         0.9286 |
| permit-breach |             45 |                10 |   0.2222 |         0.2143 |         0.2368 |

### C. T5 Correlation Break Recall per Factory

| factory_id   |   Total Events |   Detected Events |   Recall |
|:-------------|---------------:|------------------:|---------:|
| Cipla        |             28 |                 1 |   0.0357 |
| Glenmark     |             26 |                 0 |   0      |
| Indoco       |             19 |                 0 |   0      |
| Zydus        |             26 |                 0 |   0      |
