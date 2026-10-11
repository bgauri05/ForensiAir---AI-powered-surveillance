# FORENSIAIR STEP 4 CORRECTED FINAL EVALUATION PLAN

**Protocol Basis:** `PROTOCOL_v1.md` & `PROTOCOL_v1.1.md` (Sec B, C, F, G, H)  
**Status:** CORRECTED & AUDITED FINAL EVALUATION PLAN (AWAITING APPROVAL)  
**Scope:** Final resolution of factory counts, headline event definitions (T6 exclusion), short-duration factory budget rules, and standardized baseline comparison.

---

## 1. Factory Reconciliation (22 Eligible vs 21 Injected vs 33 LOFO Folds)

* **Total Development Factories**: **33 Factories** (`site_887` through `site_2070`).
* **LOFO Cross-Validation Folds**: **33 Folds** ($k = 1 \dots 33$).
* **Series Eligibility Audit (Protocol v1.1 C)**:
  - **22 Factories** contain $\ge 1$ series meeting initial criteria ($>10$ distinct values & $\le 50\%$ missingness).
  - **21 Factories** actually had eligible candidate windows that passed all Protocol v1.1 C rules (including Rule 4 isolation from repeat runs $\ge 8$ rows).
  - **1 Factory (`site_982`)**: Met initial distinct/missing criteria, but **99.7% of its telemetry sat in natural exact-repeat runs $\ge 8$ rows**, so 0 candidate windows passed Rule 4.
  - **12 Factories** (the 11 ineligible + `site_982`) carry **0 injected events**.

---

## 2. Event Population & Headline Recall Definition (Excluding T6)

Per Protocol v1.1 F (*"Coordinated missing data T6 is excluded from the headline results and from the pass criteria"*):

### Injected Event Population Breakdown
* **Total Master Injected Events**: **2,511 Events** (Seeds 1–5).
* **Headline Tamper Events (T1, T2, T3, T4, T5, T7)**: **2,349 Events** ($469.8$ per seed average).
  - **T1 (Flatline)**: 653 events
  - **T2 (Copy-Paste)**: 521 events
  - **T3 (Limit Hugging)**: 353 events
  - **T4 (Impossible pH)**: 374 events
  - **T5 (Correlation Break)**: 76 events
  - **T7 (Drift / Dip)**: 372 events
* **T6 (Coordinated Missing Data)**: **162 Events** (Reported separately, excluded from headline recall).

### Official Formula Definitions
$$\text{Headline Event Recall} = \frac{\text{Detected Headline Events (T1, T2, T3, T4, T5, T7)}}{\mathbf{2,349} \text{ Total Headline Events}}$$

$$\text{T6 Missing Data Recall (Reported Separately)} = \frac{\text{Detected T6 Events}}{\mathbf{162} \text{ Total T6 Events}}$$

---

## 3. False-Alarm Calibration & Short-Duration Factory Protocol

### Total Target False-Alarm Budget
* Total dev telemetry duration across all 33 dev factories = **327.61 factory-months**.
* Total Target False-Alarm Budget ($1.0$ per factory-month) = **328 false alert episodes**.
* **Short-Duration Factories**:
  - `site_1256`: $22.96$ days ($0.754$ months) $\rightarrow$ $0.754$ target budget.
  - `site_2070`: $3.38$ days ($0.111$ months) $\rightarrow$ $0.111$ target budget.
  - Both contribute proportionally to the global 328 false alert episode budget.

### Standardized Alert-Episode Clustering Rule (All 4 Methods)
For every evaluated method (New 33-Fold LOFO Detector, Rolling Z-Score Baseline, Static Limit Baseline, Legacy XGBoost):
1. **Binary Thresholding**: Identify present readings where `score > threshold` ($\tau$).
2. **Missing Reading Safety**: Readings with `value = NaN` are assigned `score = np.nan`. In numpy, `(np.nan > threshold)` is ALWAYS `False`. Missing rows CANNOT start, continue, or trigger alerts.
3. **Episode Clustering**: Consecutive alert readings separated by $< 8$ rows ($2\text{ hours}$) are merged into a **single False Alert Episode**.
4. **Binary Search Calibration**: Calibrate threshold $\tau$ on un-injected telemetry such that total false alert episodes across all 33 factories equals **328**.

---

## 4. Final Methods to Compare & Pass Bars (Step 4)

| Method | Description | Threshold Calibration | Evaluation Scope |
| :--- | :--- | :--- | :--- |
| **Method 1: New LOFO Detector** | 33-fold LOFO Sensor Isolation Forest (`SensorIsolationForestDetector`) | Calibrated to 328 false alert episodes on un-injected telemetry | 2,349 headline events across Seeds 1–5 |
| **Method 2: Rolling Z-Score** | Backward rolling Z-score $|x_t - \mu_{t, 16}| / \sigma_{t, 16}$ | Calibrated to 328 false alert episodes on un-injected telemetry | 2,349 headline events across Seeds 1–5 |
| **Method 3: Static Limit** | Absolute distance to 3-sigma / CTO consent limit | Calibrated to 328 false alert episodes on un-injected telemetry | 2,349 headline events across Seeds 1–5 |
| **Method 4: Legacy Model** | Legacy pooled XGBoost / global Isolation Forest | Calibrated to 328 false alert episodes on un-injected telemetry | 2,349 headline events across Seeds 1–5 |

### Pass Bar (Protocol v1.1)
* **Overall Headline Event Recall $\ge 0.70$**
* **95% Cluster Bootstrap Confidence Interval Lower Bound $\ge 0.50$** (bootstrapped over the 33 factories).
