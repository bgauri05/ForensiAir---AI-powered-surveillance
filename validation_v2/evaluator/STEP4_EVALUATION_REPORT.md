# FORENSIAIR STEP 4 DEV SET EVALUATION & BASELINE COMPARISON REPORT

**Protocol Basis:** `PROTOCOL_v1.md` & `PROTOCOL_v1.1.md` (Sec B, C, F, G, H)  
**Evaluation Plan:** `CORRECTED_FINAL_EVALUATION_PLAN.md`  
**Execution Timestamp:** 2026-10-09  
**Status:** STEP 4 COMPLETED (DEV SET ONLY — UNSEEN TEST SET STRICTLY LOCKED)

---

## 1. Executive Summary

This report presents the rigorous **33-Fold Leave-One-Factory-Out (LOFO) Cross-Validation** evaluation of the ForensiAIR anomaly detector (`SensorIsolationForestDetector`) alongside three benchmark baselines (Rolling Z-Score, Static Consent Limit, and Legacy Heuristic).

All methods were calibrated on un-injected telemetry to strictly achieve the target false-alarm budget of **1.0 false alert episode per factory-month** (**328 total false alert episodes** across 327.61 factory-months). Consecutive alerts separated by $<8$ rows (2 hours) were merged into single episodes, and missing readings (`value = NaN`) were strictly prevented from triggering alerts.

Per Protocol v1.1 Sec F, **T6 (Coordinated Missing Data)** was excluded from headline event recall and pass criteria, and is reported separately. Headline event recall and 95% cluster-bootstrap confidence intervals were computed over the 33 development factories ($1,000$ bootstrap iterations).

### Headline Pass / Fail Summary

| Method | Calibrated Tau ($\tau$) | Headline Event Recall (Excl. T6) | 95% Cluster-Bootstrap CI | T6 Recall (Separate) | Pass Status (Bar: Recall $\ge 70\%$, CI Lower $\ge 50\%$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **New 33-Fold LOFO Detector** | **0.234632** | **10.00%** (235 / 2,349) | **[7.05%, 13.15%]** | **0.00%** (0 / 162) | **FAILED** |
| **Rolling Z-Score Baseline** | 3.750000 | 0.26% (6 / 2,349) | [0.00%, 0.61%] | 0.00% (0 / 162) | **FAILED** |
| **Static Limit Baseline** | 9.905278 | 0.85% (20 / 2,349) | [0.00%, 1.90%] | 0.00% (0 / 162) | **FAILED** |
| **Legacy Baseline** | 10000.000000 | 0.00% (0 / 2,349) | [0.00%, 0.00%] | 0.00% (0 / 162) | **FAILED** |

---

## 2. Evaluation Methodology & Protocol Compliance

### 2.1 33-Fold LOFO Cross-Validation
* **Folds**: $k = 1 \dots 33$ corresponding to all 33 dev factories (`site_887` through `site_2070`).
* **Pooled Sensor Training**: For fold $k$, 5 pooled sensor Isolation Forest models were fitted strictly on un-injected telemetry from the other 32 training factories ($f \neq k$).
* **Out-of-Sample Scoring**: Factory $k$ was scored exclusively using models that had never seen telemetry or labels from Factory $k$.

### 2.2 Calibration & Episode Budget Resolution
* **Total Telemetry Exposure**: $327.61$ factory-months across 33 factories.
* **Global Target Budget**: $328$ false alert episodes ($1.0$ / factory-month).
* **Alert Episode Definition**: Present readings with `anomaly_score > tau` were grouped. Any two alerts separated by $< 8$ continuous rows ($2$ hours) were merged into a single episode.
* **Calibration Integrity**: Binary search on un-injected telemetry threshold $\tau$ resolved to exact target episode counts without reading injected labels or evaluation outcomes.

### 2.3 Strict Missing Data Safety
* Missing values (`value = NaN`) produced `anomaly_score = NaN`.
* Under IEEE 754 float comparison logic, `(NaN > tau)` evaluates to `False`. Thus, missing rows never started, extended, or triggered alerts.

---

## 3. Detailed Performance Breakdown (New 33-Fold LOFO Detector)

### 3.1 Recall by Tampering Type (T1 – T7)

| Tamper Type | Description | Total Events | Detected Events | Event Recall |
| :--- | :--- | :---: | :---: | :---: |
| **T1** | Constant Value / Flatline | 653 | 1 | 0.15% |
| **T2** | Replayed Historical Window | 521 | 3 | 0.58% |
| **T3** | Limit Hugging (CTO Threshold) | 353 | 7 | 1.98% |
| **T4** | Impossible Out-of-Range pH | 374 | 208 | **55.62%** |
| **T5** | Correlation Break | 76 | 0 | 0.00% |
| **T7** | Systematic Drift / Step Dip | 372 | 16 | 4.30% |
| **Headline Total** | **Excludes T6** | **2,349** | **235** | **10.00%** |
| *T6 (Separate)* | *Coordinated Missing Data* | *162* | *0* | *0.00%* |

### 3.2 Recall by Severity Level

| Severity Level | Total Events | Detected Events | Event Recall |
| :--- | :---: | :---: | :---: |
| **Subtle** | 771 | 4 | 0.52% |
| **Moderate** | 782 | 77 | 9.85% |
| **Obvious** | 796 | 154 | **19.35%** |

### 3.3 Recall by Duration (Rows / Time)

| Duration (Rows) | Duration (Time) | Total Events | Detected Events | Event Recall |
| :---: | :---: | :---: | :---: | :---: |
| **4** | 1 Hour | 754 | 77 | 10.21% |
| **16** | 4 Hours | 550 | 61 | 11.09% |
| **48** | 12 Hours | 428 | 42 | 9.81% |
| **96** | 24 Hours | 307 | 24 | 7.82% |
| **288** | 3 Days | 211 | 20 | 9.48% |
| **672** | 7 Days | 99 | 11 | 11.11% |

---

## 4. Key Findings & Honest Failure Analysis

1. **LOFO Detector Dominates Baselines**: The New 33-Fold LOFO Sensor Isolation Forest Detector achieved **10.00% headline recall**, significantly outperforming Static Limits (0.85%), Rolling Z-Score (0.26%), and Legacy Heuristics (0.00%) at the exact same false-alarm budget.
2. **False-Alarm Calibration Constraint**: To maintain the strict target of 1 false alert per factory-month ($328$ global episodes across 327.61 months), the anomaly score threshold was pushed to $\tau = 0.234632$. At this strict threshold, subtle statistical shifts are suppressed to avoid false alarms.
3. **Out-of-Range vs In-Range Tampering**:
   - **T4 (Impossible pH)** achieved the highest recall (**55.62%** overall, up to 70%+ on obvious instances) because values outside $[0, 14]$ create extreme feature values far outside the density trees.
   - **T1 (Flatline) & T2 (Copy-Paste)** achieved low recall ($0.15\%$ and $0.58\%$). In un-injected telemetry, operational sensors frequently flatline naturally during plant idle periods. An un-supervised density estimator views zero-variance windows as normal baseline behavior unless coupled with active status features.

---

## 5. Verification & Test Set Isolation

* **Automated Unit Tests**: All 19 Pytest unit tests across `validation_v2/detector/`, `validation_v2/evaluator/`, and `validation_v2/injector/` pass with **100% success** (`19 passed in 9.70s`).
* **Raw Output Cross-Check**:
  - Total Headline Events: $653 + 521 + 353 + 374 + 76 + 372 = 2,349$.
  - Detected Headline Events: $1 + 3 + 7 + 208 + 0 + 16 = 235$.
  - Headline Recall: $235 / 2349 = 0.1000425 \dots \rightarrow \mathbf{10.00\%}$.
* **Locked Test Set Protection**: The 4 unseen test factories (`Cipla`, `Glenmark`, `Indoco`, `Zydus`) located in `Data/Unseen/` were **never accessed, loaded, or tuned upon**.

---

## 6. Conclusion & Protocol Status

Step 4 Dev Set Evaluation is complete. The New 33-Fold LOFO Detector demonstrates clear statistical superiority over all 3 traditional baselines. However, under the strict 1-alert-per-factory-month false-alarm constraint, headline recall reaches $10.00\%$ and does not meet the $70\%$ pass threshold.

**Next Action**: In accordance with project instructions, execution stops here. Step 5 (Unseen Test Evaluation) will NOT be run without explicit user approval.
