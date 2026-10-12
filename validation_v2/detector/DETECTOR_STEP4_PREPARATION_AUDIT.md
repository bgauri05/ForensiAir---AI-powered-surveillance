# FORENSIAIR STEP 4 PREPARATION & AUDIT REPORT

**Protocol Basis:** `PROTOCOL_v1.md` & `PROTOCOL_v1.1.md` (Sec B, C, F, G, H)  
**Status:** Audit & Pre-Step 4 Protocol Resolution  
**Scope:** Resolution of 5 key protocol and evaluation design questions before commencing Step 4 dev set evaluation.

---

## 1. LOFO Evaluation Plan vs Chronological 50/50 Split

### Comparison
* **Protocol v1.1 LOFO (Leave-One-Factory-Out) Plan**:
  - **Status**: **REQUIRED Primary Evaluation Method**.
  - **Mechanism**: To evaluate Factory $A$, detector models are trained strictly on the other 21 factories (excluding Factory $A$).
  - **Data Leakage Guarantee**: Factory $A$'s telemetry (both un-injected and injected) is $100\%$ excluded from training. $0\%$ overlap exists between training time slots and testing time slots.
  - **Test Sample Coverage**: Evaluates **100% of injected events** ($2,511$ events across Seeds 1–5), preserving full statistical power and cluster bootstrap coverage.
* **Proposed Chronological 50/50 Split (Self-Baseline)**:
  - **Status**: **SECONDARY Ablation Experiment**.
  - **Mechanism**: Train on first 50% of timeline, evaluate on second 50%.
  - **Limitation**: Discards $1,188$ injected events ($47.3\%$) that fall in the first half of the timeline, reducing test sample size to $1,323$ events.

### Recommended Resolution
* **Primary Headline Evaluation**: **LOFO Cross-Validation** under Protocol v1.1.
* **Secondary Report Section**: Chronological 50/50 Split reported as an ablation study comparing factory self-calibration against LOFO cross-factory generalization.

---

## 2. Injected Event Timestamp & Sample Size Audit

Empirical timestamp audit of all $2,511$ injected events across Seeds 1–5 in `validation_v2/injector/injected/dev/labels.csv`:

| Evaluation Scheme | Events Evaluated | Discarded Events | Training Overlap | Statistical Power |
| :--- | :---: | :---: | :---: | :---: |
| **LOFO Cross-Validation (Primary)** | **2,511 (100.0%)** | **0 (0.0%)** | **0.0% (Zero)** | **Maximum (Full Seeds 1–5)** |
| **50/50 Chronological Split (Secondary)** | **1,323 (52.7%)** | **1,188 (47.3%)** | **0.0% (Zero)** | Reduced |

### 50/50 Chronological Split Event Breakdown (1,323 Evaluation Events)
| Tamper Type | Seed 1 | Seed 2 | Seed 3 | Seed 4 | Seed 5 | Total Events |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **T1 (Flatline)** | 70 | 80 | 65 | 71 | 69 | **355** |
| **T2 (Copy-Paste)** | 59 | 52 | 60 | 63 | 59 | **293** |
| **T3 (Limit Hugging)** | 41 | 32 | 40 | 35 | 41 | **189** |
| **T4 (Impossible pH)** | 38 | 42 | 36 | 36 | 35 | **187** |
| **T5 (Corr Break)** | 8 | 5 | 5 | 6 | 8 | **32** |
| **T6 (Coordinated Missing)** | 13 | 13 | 25 | 14 | 13 | **78** |
| **T7 (Drift / Dip)** | 40 | 36 | 33 | 35 | 45 | **189** |
| **Total** | **270** | **260** | **264** | **260** | **269** | **1,323** |

---

## 3. Score Direction, Threshold Convention & Missing Data Protocol

### Score Direction
* `anomaly_score = -decision_function(X)`
* **Convention**: Higher positive scores indicate greater anomaly severity. Thresholding rule: `alert = (anomaly_score > threshold)`.

### Missing Data (`NaN`) Handling Protocol
* Protocol v1.1 B & F mandate that missing telemetry readings (`value = NaN`) must NEVER trigger false alarms or count as tamper detections.
* **Demonstrably Safe Implementation**:
  ```python
  # Assign NaN to missing telemetry readings to prevent alerting on data outages
  scores[df_eval["value"].isna()] = np.nan
  ```
* In numpy/pandas, `(np.nan > threshold)` evaluates strictly to `False`, guaranteeing zero false alerts on missing telemetry rows.

---

## 4. Alert Grouping & False-Alarm Budget Calibration

### Factory-Month Budget Calculation
* Total dev telemetry duration across all 33 dev factories = **327.68 factory-months**.
* Total False-Alarm Budget ($1.0$ per factory-month) = **328 false alert episodes**.

### Alert Grouping & Clustering Algorithm
1. **Reading-Level Thresholding**: Identify all present telemetry rows where `anomaly_score > threshold` ($\tau$).
2. **Episode Clustering**: Group consecutive alert readings into a single **False Alert Episode**.
   - An episode starts at the first reading exceeding $\tau$.
   - An episode ends when readings remain below $\tau$ for $\ge 8$ consecutive 15-minute rows ($2\text{ hours}$).
3. **Threshold Calibration via Binary Search**:
   - For each method (New Decoupled Detector, Rolling Z-Score Baseline, Static Limit Baseline, Legacy XGBoost), binary search calibrates threshold $\tau$ on un-injected telemetry until total false alert episodes equal **328**.

---

## 5. Unseen Test Set Execution Protocol (4 Factories)

1. **Frozen Code & Hyperparameters**:
   - Model feature definitions (`FEATURE_COLS`), `random_state=42`, `contamination=0.05`, `n_estimators=100`, and threshold calibration rules are $100\%$ frozen on the dev set.
2. **Schema Normalization**:
   - Load `Data/Unseen/*.csv` files (Cipla, Glenmark, Indoco, Zydus) and map columns to standard schema (`timestamp`, `factory_id`, `parameter_id`, `value`). Keep missing readings as `NaN`.
3. **Zero-Tuning Scoring**:
   - Run frozen detector pipeline without accessing labels, setting custom thresholds per factory, or performing iterative parameter tuning.
4. **Strict Isolation**:
   - Locked test set evaluation will be executed in a separate step after Step 4 dev set results are finalized and reported.
