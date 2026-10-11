# FORENSIAIR DETECTOR PROTOCOL AUDIT & EVALUATION DESIGN REPORT

**Status:** AUDIT & RECOMMENDATIONS BEFORE STEP 4 EVALUATION  
**Protocol Basis:** `PROTOCOL_v1.md` (Sec 2-5) & `PROTOCOL_v1.1.md` (Sec B, C, G, H)  
**Scope:** Audit of `SensorIsolationForestDetector` against LOFO rules, train/test temporal separation, unseen factory protocol, scikit-learn NaN mechanics, and Step 4 baseline comparison requirements.

---

## Executive Audit Summary

| Audit Item | Current Detector State | Identified Conflict / Risk | Recommended Protocol-Compliant Fix |
| :--- | :--- | :--- | :--- |
| **1. LOFO vs Factory Models** | 81 factory-specific models trained on own telemetry. | Supervised LOFO cannot apply directly because a factory left out has no model trained on other factories. | **Dual Evaluation**: (A) Self-Baseline Transductive (Train 50% / Test 50% split) and (B) Sensor-Type Pooled LOFO (Train on 21 factories, test on 22nd). |
| **2. Injected Windows Baseline** | Trained on entire un-injected timeline ($100\%$). | Evaluates on the exact same time slots used during training (temporal overlap/leakage). | **Chronological Temporal Split**: Train detector on first 50% of timeline; evaluate injections and false alarms strictly on second 50%. |
| **3. Unseen Factories (Locked Test)** | Unseen factories (Cipla, Glenmark, Indoco, Zydus) not yet touched. | Hyperparameter tuning or threshold setting on unseen factories violates locked-test rules. | **Zero-Tuning Transductive Fit**: On unseen test factories, fit unsupervised model using frozen hyperparameters (`contamination=0.05`, `n_estimators=100`, `FEATURE_COLS`) without touching labels or tuning. |
| **4. NaN Score Handling** | scikit-learn 1.8.0 handles NaNs natively during fit/predict. | Rows with `value = NaN` receive non-zero anomaly scores, potentially triggering false alerts on missing data. | **Explicit Missing Value Masking**: Force `anomaly_score = NaN` or `0.0` whenever input sensor reading `value` is `NaN`. |
| **5. Step 4 Evaluation Plan** | Detector outputs raw continuous `anomaly_score = -decision_function`. | Thresholds must not be arbitrary; methods must be compared at equal false-alarm rates. | **Equal False-Alarm Rate Calibration**: Calibrate threshold $\tau$ for each model on un-injected telemetry to exactly 1.0 alert / factory-month, then measure event Recall across Seeds 1–5. |

---

## Detailed Findings & Protocol-Compliant Recommendations

### 1. Leave-One-Factory-Out (LOFO) vs Decoupled Per-Factory Models

#### Finding
The `SensorIsolationForestDetector` trains 81 separate models, one for each `(factory_id, parameter_id)` pair. If a strict LOFO cross-validation scheme is executed where Factory $A$ is excluded from training, Factory $A$ will have no factory-specific model available for evaluation.

#### Recommendation
We recommend a **two-tier evaluation design** for Step 4:
1. **Primary Method (Factory Self-Baseline / Transductive Anomaly Detection)**:
   - Split each factory's timeline into a **Training Baseline Period** (first 50% of un-injected telemetry) and an **Evaluation Period** (second 50% of telemetry containing injected tamper windows and un-injected false alarm evaluation windows).
   - This matches real-world OCEMS surveillance where each factory's sensor baseline is established during an initial compliance period.
2. **Secondary Method (Sensor-Type Pooled LOFO Model)**:
   - Train 4 global sensor models (`IsolationForest_pH`, `IsolationForest_Flow`, `IsolationForest_BOD`, `IsolationForest_COD`) pooled across 21 factories, and evaluate on the 22nd left-out factory.
   - Compare performance between Factory Self-Baseline and Sensor-Type Pooled LOFO to measure cross-factory generalization loss.

---

### 2. Prevention of Temporal Overlap / Data Leakage

#### Finding
`detector.py` currently trains on 100% of `monitoring_data(raw).csv`. Injected events were synthesized at candidate time slots within this same timeline. Training on the exact time slots used for evaluation introduces temporal overlap between training and testing data.

#### Recommendation
* **Chronological Block Partitioning**:
  - **Train Set (0% – 50% Timeline)**: Un-injected telemetry from the first half of the dataset used exclusively for `fit()`.
  - **Test Set (50% – 100% Timeline)**: Un-injected false alarm windows AND injected tamper parquets (Seeds 1–5) in the second half of the dataset used exclusively for `predict_anomaly_score()`.
* **Zero Window Overlap Guarantee**: Ensures 0 training time slots are evaluated during testing.

---

### 3. Protocol for 4 Unseen Test Factories (Cipla, Glenmark, Indoco, Zydus)

#### Finding
The 4 unseen test factories have missing quality codes (Protocol v1.1 G) and whole-logger outages. Accessing them for hyperparameter tuning or feature selection violates the frozen protocol.

#### Recommendation
* **Frozen Execution**:
  1. All hyperparameters (`n_estimators=100`, `contamination=0.05`, `FEATURE_COLS`, scaling rules) are frozen on the dev set.
  2. On unseen factories, fit the unsupervised `SensorIsolationForestDetector` using raw telemetry without modifying any code or hyperparameter.
  3. No evaluation or threshold adjustment will be performed on unseen factories until Step 4 dev set evaluation is complete and approved.

---

### 4. Empirical Verification of scikit-learn NaN Handling

#### Finding
Empirical testing on `scikit-learn` 1.8.0 confirmed that `IsolationForest.fit()` and `decision_function()` execute without error on feature matrices containing `NaN`s. However, when a row contains `value = NaN` (missing telemetry reading), `decision_function()` assigns it a non-zero anomaly score.

#### Conflict with Protocol v1.1 F
Protocol v1.1 F states: *"No claim is made that gaps indicate tampering. Coordinated missing data (T6) is reported separately."*

#### Fix Specification
In `predict_anomaly_score()`, add explicit masking:
```python
# Mask missing readings so data outages are not flagged as sensor tampering
missing_mask = df_eval["value"].isna()
scores[missing_mask] = 0.0  # or np.nan
```

---

### 5. Step 4 Equal False-Alarm Rate Evaluation Design

#### Requirement (Protocol v1.1 Sec B & H)
Step 4 requires comparing detector methods at the **exact same false-alarm budget**: **1 false alert per factory-month** on un-injected telemetry.

#### Standardized Threshold Calibration Procedure
For every evaluated method (New Decoupled Detector, Moving Z-Score Baseline, Static Limit Baseline, Legacy XGBoost):
1. **Step 4.1 (Threshold Calibration)**: Run model on un-injected test-period telemetry. Find threshold $\tau$ such that total false alerts equal $1.0 \times \text{Factory Months}$.
2. **Step 4.2 (Event Detection Scoring)**: Apply calibrated threshold $\tau$ to injected test parquets (Seeds 1–5).
3. **Step 4.3 (Event Recall Calculation)**: An injected event (T1–T7, excluding T6) is **detected** if $\ge 1$ reading inside $[T_{\text{start}}, T_{\text{end}}]$ exceeds $\tau$.
4. **Step 4.4 (Pass Criteria)**: Calculate overall Recall $\ge 0.70$ with 95% cluster bootstrap confidence interval lower bound $\ge 0.50$.

---

## Recommended Next Action

Do not edit code or run evaluation yet. Present this audit report to the owner/user for review and approval of the recommended **50/50 Chronological Train/Test Split** and **Equal False-Alarm Calibration Procedure**.
