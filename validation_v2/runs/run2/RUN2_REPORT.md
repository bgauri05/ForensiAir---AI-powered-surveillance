# FORENSIAIR RUN 2 EVALUATION REPORT

**Specification:** `PROTOCOL_v1.md` & `PROTOCOL_v1.1.md` (Frozen)  
**Evaluation Type:** Development Set 33-Fold LOFO Cross-Validation (Run 2)  
**Operating Point:** 1.0 False Alert Episode per Factory-Month  
**Total Dev Exposure:** 327.61 Factory-Months across 33 Factories  
**Total Injected Events:** 2511 Events (Headline: 2349, T6: 152, Excluded T6: 10)  

## 1. Baselines & Detector Comparison (Operating Point = 1.0 alert/month)

| Method                                      |   Headline Recall |   95% CI Lower |   95% CI Upper |   T6 Recall |   Median Delay (h) |   Window AUPRC | Pass Bar Status                                                  |
|:--------------------------------------------|------------------:|---------------:|---------------:|------------:|-------------------:|---------------:|:-----------------------------------------------------------------|
| B5: Legacy Composite (Factory risk delta)   |          nan      |       nan      |       nan      |    nan      |             nan    |       nan      | N/A (Paired Risk Delta: Mean=+0.0169, 95% CI [-0.0184, +0.1290]) |
| B0: Random Alerts (Budget rate)             |            0.0319 |         0.0229 |         0.0406 |      0.0395 |               0    |         0.0436 | FAILED                                                           |
| M1: Multi-Check Max Fusion (Pre-declared)   |            0.1439 |         0.1178 |         0.1704 |      0      |               3.75 |         0.222  | FAILED                                                           |
| F1 (eps=0, exact repeat run-level)          |            0.0536 |         0.03   |         0.0803 |      0      |               1.75 |       nan      | FAILED                                                           |
| F1 (eps=1, 1-step quasi-flat)               |            0.0745 |         0.0325 |         0.1231 |      0      |               3    |       nan      | FAILED                                                           |
| F1 (eps=2, 2-step quasi-flat)               |            0.1098 |         0.0545 |         0.1753 |      0      |               3    |       nan      | FAILED                                                           |
| F2 (Copy-Paste Replay alone)                |            0.0447 |         0.0291 |         0.0618 |      0      |              23    |       nan      | FAILED                                                           |
| F3 (Limit Proximity alone)                  |            0      |         0      |         0      |      0      |             nan    |       nan      | FAILED                                                           |
| F5 (Correlation Break alone)                |            0      |         0      |         0      |      0      |             nan    |       nan      | FAILED                                                           |
| F6 (Level Shift Drift alone)                |            0.1052 |         0.0774 |         0.1322 |      0      |               2    |       nan      | FAILED                                                           |
| F6 (Linear Slope Drift alone)               |            0.0724 |         0.0575 |         0.0878 |      0      |               1.5  |       nan      | FAILED                                                           |
| IF (LOFO Sensor Isolation Forest alone)     |            0      |         0      |         0      |      0      |             nan    |         0      | FAILED                                                           |
| B1: Robust Z-Score (Median/MAD)             |            0.0068 |         0      |         0.0209 |      0      |               0.62 |         0.0804 | FAILED                                                           |
| B2: Pooled IF (Legacy style)                |            0.0115 |         0      |         0.0352 |      0.0132 |               0.5  |         0.066  | FAILED                                                           |
| B3: Per-Sensor IF alone                     |            0      |         0      |         0      |      0      |             nan    |         0      | FAILED                                                           |
| B4: Legacy Fingerprint Rules                |            1      |         1      |         1      |      1      |               0    |         0.043  | PASSED                                                           |
| F4: Validity Hard Alert (pH < 0 or pH > 14) |            0.0579 |         0.0394 |         0.0754 |      0      |               0    |         0.0436 | REPORTED SEPARATELY (T4 obvious: 100% recall)                    |
| F7: Gaps Fraction (Missing Data Outages)    |            0      |         0      |         0      |      1      |               0    |         0.0436 | REPORTED SEPARATELY (T6 missing data: 100% recall)               |

---

## 2. Event Recall by Tampering Type (M1 Multi-Check Max Fusion)

| Tamper Type   |   Total Events |   Detected Events |   Recall (All Severities) |   95% CI Lower |   95% CI Upper |   Recall (Moderate+) |   95% CI Lower (Mod+) | Pass Bar Status                                   |
|:--------------|---------------:|------------------:|--------------------------:|---------------:|---------------:|---------------------:|----------------------:|:--------------------------------------------------|
| T1            |            653 |               114 |                    0.1746 |         0.1107 |         0.2398 |               0.2388 |                0.1456 | FAILED                                            |
| T2            |            521 |                41 |                    0.0787 |         0.0441 |         0.1236 |               0.1124 |                0.0631 | FAILED                                            |
| T3            |            353 |                12 |                    0.034  |         0.0134 |         0.0551 |               0.046  |                0.0183 | FAILED                                            |
| T4            |            374 |               132 |                    0.3529 |         0.2864 |         0.4189 |               0.4264 |                0.3547 | FAILED                                            |
| T5            |             76 |                 0 |                    0      |         0      |         0      |               0      |                0      | FAILED                                            |
| T6            |            152 |                 0 |                    0      |         0      |         0      |               0      |                0      | EXCLUDED FROM PASS CRITERIA (Reported separately) |
| T7            |            372 |                39 |                    0.1048 |         0.0559 |         0.1645 |               0.1313 |                0.0754 | FAILED                                            |

---

## 3. Realized False Alarms per Factory-Month Distribution (Held-Out Clean Copies)

| Metric                                  |   Mean |   Std |   Median |   P25 |   P75 |   Min |   Max |   Total Dev Telemetry Months |   Total False Alert Episodes |
|:----------------------------------------|-------:|------:|---------:|------:|------:|------:|------:|-----------------------------:|-----------------------------:|
| Realized False Alarms per Factory-Month |  0.834 | 0.835 |    0.749 |     0 | 1.248 |     0 | 3.161 |                       327.61 |                          328 |

---

## 4. Operating Point Sensitivity (Headline Recall at 1, 2, 4, 10 alerts/month)

|   Target Budget (alerts/fac-mo) |   Realized Mean FA Rate |   Realized Median FA Rate |   Realized Min FA Rate |   Realized Max FA Rate |   Headline Recall |   95% CI Lower |   95% CI Upper |
|--------------------------------:|------------------------:|--------------------------:|-----------------------:|-----------------------:|------------------:|---------------:|---------------:|
|                               1 |                   0.834 |                     0.749 |                      0 |                  3.161 |            0.1439 |         0.1178 |         0.1704 |
|                               2 |                   1.664 |                     1.431 |                      0 |                  5.408 |            0.2043 |         0.1715 |         0.2382 |
|                               4 |                   3.951 |                     3.161 |                      0 |                 18.627 |            0.2699 |         0.2357 |         0.3037 |
|                              10 |                  10.129 |                     9.068 |                      0 |                 31.373 |            0.4508 |         0.4043 |         0.4913 |

---

## 5. Protocol v1.1 Subgroup Breakdowns (M1 Fusion)

### A. T1 & T2 Natural Run Duration Split

| Tamper Type   | Duration Category                 |   Total Events |   Detected Events |   Recall |   95% CI Lower |   95% CI Upper |
|:--------------|:----------------------------------|---------------:|------------------:|---------:|---------------:|---------------:|
| T1            | Beyond-Natural (>= 99.9th pctile) |            189 |                75 |   0.3968 |         0.2936 |         0.5035 |
| T1            | Within-Natural (< 99.9th pctile)  |            464 |                39 |   0.0841 |         0.0401 |         0.1386 |
| T2            | Beyond-Natural (>= 99.9th pctile) |            155 |                30 |   0.1935 |         0.0887 |         0.3906 |
| T2            | Within-Natural (< 99.9th pctile)  |            366 |                11 |   0.0301 |         0.0079 |         0.0627 |

### B. T4 Obvious vs Permit-Breach Split

| T4 Category   |   Total Events |   Detected Events |   Recall |   95% CI Lower |   95% CI Upper |
|:--------------|---------------:|------------------:|---------:|---------------:|---------------:|
| obvious       |            136 |                86 |   0.6324 |         0.5401 |         0.7174 |
| permit-breach |            238 |                46 |   0.1933 |         0.1245 |         0.2629 |

### C. T5 Correlation Break Recall per Factory (Exploratory)

| factory_id   |   Total Events |   Detected Events |   Recall |   95% CI Lower |   95% CI Upper |
|:-------------|---------------:|------------------:|---------:|---------------:|---------------:|
| site_1376    |             27 |                 0 |        0 |              0 |              0 |
| site_1799    |             22 |                 0 |        0 |              0 |              0 |
| site_887     |             27 |                 0 |        0 |              0 |              0 |

### D. Recall by Severity

| Severity   |   Total Events |   Detected Events |   Recall |   95% CI Lower |   95% CI Upper |
|:-----------|---------------:|------------------:|---------:|---------------:|---------------:|
| subtle     |            771 |                43 |   0.0558 |         0.0392 |         0.075  |
| moderate   |            782 |                73 |   0.0934 |         0.0646 |         0.1232 |
| obvious    |            796 |               222 |   0.2789 |         0.2286 |         0.3272 |

### E. Recall by Injected Share Bin

| Injected Share Bin   |   Total Events |   Detected Events |   Recall |   95% CI Lower |   95% CI Upper |
|:---------------------|---------------:|------------------:|---------:|---------------:|---------------:|
| <=2%                 |            564 |                68 |   0.1206 |         0.0821 |         0.189  |
| 2-10%                |            947 |               141 |   0.1489 |         0.1119 |         0.1844 |
| >10%                 |            838 |               129 |   0.1539 |         0.1122 |         0.2006 |

### F. Recall by Parameter

| Parameter   |   Total Events |   Detected Events |   Recall |   95% CI Lower |   95% CI Upper |
|:------------|---------------:|------------------:|---------:|---------------:|---------------:|
| ETP-pH      |           1521 |               228 |   0.1499 |         0.1195 |         0.1809 |
| ETP-Flow    |            594 |                85 |   0.1431 |         0.0886 |         0.2192 |
| ETP-BOD     |             70 |                 8 |   0.1143 |         0      |         0.2593 |
| ETP-COD     |            122 |                11 |   0.0902 |         0      |         0.1346 |
| ETP-TSS     |             42 |                 6 |   0.1429 |         0      |         0.2222 |

### G. Recall by Injected Duration

|   Duration Rows |   Duration Hours |   Total Events |   Detected Events |   Recall |   95% CI Lower |   95% CI Upper |
|----------------:|-----------------:|---------------:|------------------:|---------:|---------------:|---------------:|
|               4 |                1 |            754 |                15 |   0.0199 |         0.0047 |         0.0455 |
|              16 |                4 |            550 |                79 |   0.1436 |         0.1103 |         0.1866 |
|              48 |               12 |            428 |                66 |   0.1542 |         0.1191 |         0.1914 |
|              96 |               24 |            307 |                78 |   0.2541 |         0.191  |         0.3214 |
|             288 |               72 |            211 |                65 |   0.3081 |         0.2299 |         0.3869 |
|             672 |              168 |             99 |                35 |   0.3535 |         0.2667 |         0.4915 |
