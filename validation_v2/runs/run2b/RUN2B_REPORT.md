# FORENSIAIR RUN 2b EVALUATION REPORT (FIX + RERUN)

**Specification:** `PROTOCOL_v1.md` & `PROTOCOL_v1.1.md` (Frozen)  
**Evaluation Type:** Development Set 33-Fold LOFO Cross-Validation (Run 2b)  
**Operating Point:** 1.0 False Alert Episode per Factory-Month  
**Total Dev Exposure:** 327.61 Factory-Months across 33 Factories  
**Total Injected Events:** 2511 Events (Headline: 2349, T6: 152, Excluded T6: 10)  

## 1. Guard & Quality Verification: Per-Method % NaN Across Scored Telemetry

All pre-flight unit tests passed (F3 planted near-limit pH, IF non-NaN, F5 non-NaN on BOD+COD).  
Runtime Guard Status: Zero series with 100% NaN on applicable checks.  

| Method / Check   |   Total Telemetry Readings |   NaN Score Count |   Percent NaN (%) | Guard Status                                 |
|:-----------------|---------------------------:|------------------:|------------------:|:---------------------------------------------|
| M1_fusion        |                    5475353 |                 0 |              0    | PASSED (No series 100% NaN where applicable) |
| F1_eps0          |                    5475353 |                 0 |              0    | PASSED (No series 100% NaN where applicable) |
| F1_eps1          |                    5475353 |                 0 |              0    | PASSED (No series 100% NaN where applicable) |
| F1_eps2          |                    5475353 |                 0 |              0    | PASSED (No series 100% NaN where applicable) |
| F2_copypaste     |                    5475353 |           1914737 |             34.97 | PASSED (No series 100% NaN where applicable) |
| F3_limit         |                    5475353 |           4073564 |             74.4  | PASSED (No series 100% NaN where applicable) |
| F5_corr          |                    5475353 |           5055393 |             92.33 | PASSED (No series 100% NaN where applicable) |
| F6_shift         |                    5475353 |            492110 |              8.99 | PASSED (No series 100% NaN where applicable) |
| F6_slope         |                    5475353 |            433684 |              7.92 | PASSED (No series 100% NaN where applicable) |
| IF_sensor        |                    5475353 |            433684 |              7.92 | PASSED (No series 100% NaN where applicable) |
| B1_zscore        |                    5475353 |                 0 |              0    | PASSED (No series 100% NaN where applicable) |
| B2_pooled_if     |                    5475353 |                 0 |              0    | PASSED (No series 100% NaN where applicable) |
| B3_sensor_if     |                    5475353 |            433684 |              7.92 | PASSED (No series 100% NaN where applicable) |
| B4_legacy_rules  |                    5475353 |                 0 |              0    | PASSED (No series 100% NaN where applicable) |

---

## 2. Baselines & Detector Comparison Table (Budget-Matched: 1.0 alert/month)

| Method                                      |   Headline Recall |   95% CI Lower |   95% CI Upper |   T6 Recall |   Median Delay (h) |   Window AUPRC | Pass Bar Status                                                  |
|:--------------------------------------------|------------------:|---------------:|---------------:|------------:|-------------------:|---------------:|:-----------------------------------------------------------------|
| B5: Legacy Composite (Factory risk delta)   |          nan      |       nan      |       nan      |    nan      |             nan    |       nan      | N/A (Paired Risk Delta: Mean=+0.0169, 95% CI [-0.0184, +0.1290]) |
| B0: Random Alerts (Budget rate)             |            0.0319 |         0.0229 |         0.0406 |      0.0395 |               0    |         0.0436 | FAILED                                                           |
| M1: Multi-Check Max Fusion (Pre-declared)   |            0.1426 |         0.1182 |         0.1667 |      0      |               3.75 |         0.2289 | FAILED                                                           |
| F1 (eps=0, exact repeat run-level)          |            0.0536 |         0.03   |         0.0803 |      0      |               1.75 |       nan      | FAILED                                                           |
| F1 (eps=1, 1-step quasi-flat)               |            0.0745 |         0.0325 |         0.1231 |      0      |               3    |       nan      | FAILED                                                           |
| F1 (eps=2, 2-step quasi-flat)               |            0.1098 |         0.0545 |         0.1753 |      0      |               3    |       nan      | FAILED                                                           |
| F2 (Copy-Paste Replay alone)                |            0.0447 |         0.0291 |         0.0618 |      0      |              23    |       nan      | FAILED                                                           |
| F3 (Limit Proximity alone)                  |            0.1222 |         0.0584 |         0.1862 |      0      |               1.75 |       nan      | FAILED                                                           |
| F5 (Correlation Break alone)                |            0.0243 |         0      |         0.0651 |      0      |               8    |       nan      | FAILED                                                           |
| F6 (Level Shift Drift alone)                |            0.1052 |         0.0774 |         0.1322 |      0      |               2    |       nan      | FAILED                                                           |
| F6 (Linear Slope Drift alone)               |            0.0724 |         0.0575 |         0.0878 |      0      |               1.5  |       nan      | FAILED                                                           |
| IF (LOFO Sensor Isolation Forest alone)     |            0.1145 |         0.0854 |         0.1455 |      0      |               1    |         0.123  | FAILED                                                           |
| B1: Robust Z-Score (Median/MAD)             |            0.0068 |         0      |         0.0209 |      0      |               0.62 |         0.0804 | FAILED                                                           |
| B2: Pooled IF (Legacy style)                |            0.0115 |         0      |         0.0352 |      0.0132 |               0.5  |         0.066  | FAILED                                                           |
| B3: Per-Sensor IF alone                     |            0.1145 |         0.0854 |         0.1455 |      0      |               1    |         0.123  | FAILED                                                           |
| F4: Validity Hard Alert (pH < 0 or pH > 14) |            0.0579 |         0.0394 |         0.0754 |      0      |               0    |         0.0436 | REPORTED SEPARATELY (T4 obvious: 100% recall)                    |
| F7: Gaps Fraction (Missing Data Outages)    |            0      |         0      |         0      |      1      |               0    |         0.0436 | REPORTED SEPARATELY (T6 missing data: 100% recall)               |

### Uncalibrated Baseline (Not Budget-Matched, Outside Pass Table)

| Method                       |   Headline Recall |   95% CI Lower |   95% CI Upper |   T6 Recall |   Median Delay (h) |   Window AUPRC | Pass Bar Status                                                              |
|:-----------------------------|------------------:|---------------:|---------------:|------------:|-------------------:|---------------:|:-----------------------------------------------------------------------------|
| B4: Legacy Fingerprint Rules |                 1 |              1 |              1 |           1 |                  0 |          0.043 | NOT BUDGET-MATCHED (Natural alert rate: 12.09 alerts/mo; outside pass table) |

> **Note on B4:** Legacy fingerprint rules fire at an uncalibrated natural rate of ~12.09 alerts/factory-month (12x over the 1.0 budget). It is reported outside the formal pass table.

---

## 3. Injected Episode Classification & Tolerance Sensitivity (M1 Fusion)

### A. Episode Classification Distribution on Injected Copies

- **(a) Overlapping an Event or within 2h after it ends:** 1453 episodes (12.73% of injected alerts)
- **(b) 2h to 72h after an Event ends:** 1715 episodes (15.03% of injected alerts)
- **(c) Elsewhere (Spurious alerts on clean/unaffected windows):** 8242 episodes (72.23% of injected alerts)
- **Total Alert Episodes on Injected Copies:** 11410 episodes

### B. Episodes per Detected Event

- **Mean episodes per detected event:** 1.58
- **Median episodes per detected event:** 1.0
- **Min / Max episodes per detected event:** [1, 12]

### C. Headline Recall Under Detection Tolerances (Primary vs Sensitivity)

| Tolerance Window   | Classification Label   |   Detected Events |   Total Headline Events |   Headline Recall |   95% CI Lower |   95% CI Upper |
|:-------------------|:-----------------------|------------------:|------------------------:|------------------:|---------------:|---------------:|
| 2h                 | Primary (<= 2h)        |               335 |                    2349 |            0.1426 |         0.1182 |         0.1667 |
| 24h                | Sensitivity (<= 24h)   |               372 |                    2349 |            0.1584 |         0.1331 |         0.1841 |
| 72h                | Sensitivity (<= 72h)   |               427 |                    2349 |            0.1818 |         0.1554 |         0.2083 |

---

## 4. Event Recall by Tampering Type (M1 Multi-Check Max Fusion)

| Tamper Type   |   Total Events |   Detected Events |   Recall (All Severities) |   95% CI Lower |   95% CI Upper |   Recall (Moderate+) |   95% CI Lower (Mod+) | Pass Bar Status                                   |
|:--------------|---------------:|------------------:|--------------------------:|---------------:|---------------:|---------------------:|----------------------:|:--------------------------------------------------|
| T1            |            653 |               106 |                    0.1623 |         0.0984 |         0.2222 |               0.2246 |                0.1335 | FAILED                                            |
| T2            |            521 |                37 |                    0.071  |         0.0401 |         0.1111 |               0.1009 |                0.0573 | FAILED                                            |
| T3            |            353 |                12 |                    0.034  |         0.0134 |         0.0551 |               0.046  |                0.0183 | FAILED                                            |
| T4            |            374 |               142 |                    0.3797 |         0.3087 |         0.4457 |               0.4651 |                0.3923 | FAILED                                            |
| T5            |             76 |                 0 |                    0      |         0      |         0      |               0      |                0      | FAILED                                            |
| T6            |            152 |                 0 |                    0      |         0      |         0      |               0      |                0      | EXCLUDED FROM PASS CRITERIA (Reported separately) |
| T7            |            372 |                38 |                    0.1022 |         0.0536 |         0.1627 |               0.1274 |                0.0722 | FAILED                                            |

---

## 5. Realized False Alarms per Factory-Month Distribution (Held-Out Clean Copies)

| Metric                                  |   Mean |   Std |   Median |   P25 |   P75 |   Min |   Max |   Total Dev Telemetry Months |   Total False Alert Episodes |
|:----------------------------------------|-------:|------:|---------:|------:|------:|------:|------:|-----------------------------:|-----------------------------:|
| Realized False Alarms per Factory-Month |   0.83 | 0.851 |    0.582 |     0 | 1.331 |     0 | 3.161 |                       327.61 |                          327 |

---

## 6. Operating Point Sensitivity (Headline Recall at 1, 2, 4, 10 alerts/month)

|   Target Budget (alerts/fac-mo) |   Realized Mean FA Rate |   Realized Median FA Rate |   Realized Min FA Rate |   Realized Max FA Rate |   Headline Recall |   95% CI Lower |   95% CI Upper |
|--------------------------------:|------------------------:|--------------------------:|-----------------------:|-----------------------:|------------------:|---------------:|---------------:|
|                               1 |                   0.83  |                     0.582 |                      0 |                  3.161 |            0.1426 |         0.1182 |         0.1667 |
|                               2 |                   1.678 |                     1.581 |                      0 |                  5.657 |            0.2009 |         0.1705 |         0.2301 |
|                               4 |                   3.929 |                     3.245 |                      0 |                 18.627 |            0.2754 |         0.2411 |         0.3092 |
|                              10 |                  10.14  |                     8.819 |                      0 |                 31.373 |            0.4483 |         0.4036 |         0.4868 |

---

## 7. Protocol v1.1 Subgroup Breakdowns (M1 Fusion)

### A. T1 & T2 Natural Run Duration Split

| Tamper Type   | Duration Category                 |   Total Events |   Detected Events |   Recall |   95% CI Lower |   95% CI Upper |
|:--------------|:----------------------------------|---------------:|------------------:|---------:|---------------:|---------------:|
| T1            | Beyond-Natural (>= 99.9th pctile) |            189 |                73 |   0.3862 |         0.2817 |         0.4834 |
| T1            | Within-Natural (< 99.9th pctile)  |            464 |                33 |   0.0711 |         0.0336 |         0.1171 |
| T2            | Beyond-Natural (>= 99.9th pctile) |            155 |                26 |   0.1677 |         0.0788 |         0.33   |
| T2            | Within-Natural (< 99.9th pctile)  |            366 |                11 |   0.0301 |         0.0079 |         0.0627 |

### B. T4 Obvious vs Permit-Breach Split

| T4 Category   |   Total Events |   Detected Events |   Recall |   95% CI Lower |   95% CI Upper |
|:--------------|---------------:|------------------:|---------:|---------------:|---------------:|
| obvious       |            136 |                88 |   0.6471 |         0.5538 |         0.7308 |
| permit-breach |            238 |                54 |   0.2269 |         0.1463 |         0.3033 |

### C. T5 Correlation Break Recall per Factory (Exploratory)

| factory_id   |   Total Events |   Detected Events |   Recall |   95% CI Lower |   95% CI Upper |
|:-------------|---------------:|------------------:|---------:|---------------:|---------------:|
| site_1376    |             27 |                 0 |        0 |              0 |              0 |
| site_1799    |             22 |                 0 |        0 |              0 |              0 |
| site_887     |             27 |                 0 |        0 |              0 |              0 |

### D. Recall by Severity

| Severity   |   Total Events |   Detected Events |   Recall |   95% CI Lower |   95% CI Upper |
|:-----------|---------------:|------------------:|---------:|---------------:|---------------:|
| subtle     |            771 |                41 |   0.0532 |         0.0369 |         0.0712 |
| moderate   |            782 |                78 |   0.0997 |         0.0731 |         0.1264 |
| obvious    |            796 |               216 |   0.2714 |         0.2224 |         0.3177 |

### E. Recall by Injected Share Bin

| Injected Share Bin   |   Total Events |   Detected Events |   Recall |   95% CI Lower |   95% CI Upper |
|:---------------------|---------------:|------------------:|---------:|---------------:|---------------:|
| <=2%                 |            564 |                64 |   0.1135 |         0.0776 |         0.1731 |
| 2-10%                |            947 |               142 |   0.1499 |         0.118  |         0.182  |
| >10%                 |            838 |               129 |   0.1539 |         0.1154 |         0.1982 |

### F. Recall by Parameter

| Parameter   |   Total Events |   Detected Events |   Recall |   95% CI Lower |   95% CI Upper |
|:------------|---------------:|------------------:|---------:|---------------:|---------------:|
| ETP-pH      |           1521 |               232 |   0.1525 |         0.1241 |         0.1815 |
| ETP-Flow    |            594 |                80 |   0.1347 |         0.0843 |         0.1957 |
| ETP-BOD     |             70 |                 9 |   0.1286 |         0      |         0.2593 |
| ETP-COD     |            122 |                10 |   0.082  |         0      |         0.1154 |
| ETP-TSS     |             42 |                 4 |   0.0952 |         0      |         0.1154 |

### G. Recall by Injected Duration

|   Duration Rows |   Duration Hours |   Total Events |   Detected Events |   Recall |   95% CI Lower |   95% CI Upper |
|----------------:|-----------------:|---------------:|------------------:|---------:|---------------:|---------------:|
|               4 |                1 |            754 |                10 |   0.0133 |         0.003  |         0.0316 |
|              16 |                4 |            550 |                81 |   0.1473 |         0.1139 |         0.1854 |
|              48 |               12 |            428 |                69 |   0.1612 |         0.1269 |         0.1963 |
|              96 |               24 |            307 |                75 |   0.2443 |         0.1877 |         0.308  |
|             288 |               72 |            211 |                64 |   0.3033 |         0.221  |         0.3898 |
|             672 |              168 |             99 |                36 |   0.3636 |         0.2705 |         0.4933 |
