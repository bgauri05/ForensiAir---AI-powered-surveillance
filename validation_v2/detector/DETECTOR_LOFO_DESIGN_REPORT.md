# FORENSIAIR FINAL STEP 4 LOFO EVALUATION DESIGN REPORT

**Protocol Basis:** `PROTOCOL_v1.md` & `PROTOCOL_v1.1.md` (Sec B, C, F, G, H)  
**Status:** FINAL DESIGN RESOLUTION & AUDIT BEFORE STEP 4 EVALUATION  
**Scope:** Resolution of LOFO scoring mechanics, pooled sensor models, threshold calibration, missing data safety, and test-set locking.

---

## 1. LOFO Scoring Mechanics for Held-Out Factories

### Problem Addressed
Training 81 factory-specific models means a held-out factory has no factory-specific model trained on other factories. Under strict **Leave-One-Factory-Out (LOFO)** cross-validation, an evaluated factory must be scored using models trained **without any data from that factory**.

### Final LOFO Scoring Design
For each LOFO fold $k \in \{1 \dots 22\}$:
1. **Held-Out Factory**: $F_k$ (e.g. `site_1200`).
2. **Training Factories**: The remaining 21 dev factories $\{F_j \mid j \neq k\}$.
3. **Model Construction**:
   - For each parameter $p \in \{\text{ETP-pH}, \text{ETP-Flow}, \text{ETP-BOD}, \text{ETP-COD}, \text{ETP-TSS}\}$:
     - Pool the un-injected feature matrices extracted from all training factories $\{F_j \mid j \neq k\}$ into $X_{\text{pooled}, p}^{(k)}$.
     - Fit a single **Sensor-Type Pooled Isolation Forest model** $M_{p}^{(k)}$ on $X_{\text{pooled}, p}^{(k)}$.
4. **Scoring Held-Out Factory $F_k$**:
   - For each parameter $p$ in $F_k$, extract feature matrix $X_{F_k, p}$ using `extract_series_features`.
   - Score using the pooled model: `raw_scores = -M_p^{(k)}.decision_function(X_{F_k, p})`.
   - **Zero Leakage**: Factory $F_k$'s telemetry is $100\%$ excluded from $M_{p}^{(k)}$ training.

---

## 2. Sensor-Type Pooled Isolation Forest Models

### Architectural Impact
* **Complementary Support in `detector.py`**:
  - `detector.py` will support two operational modes:
    1. `mode="factory"`: 81 factory-specific models trained on un-injected self-telemetry (used for self-baseline analysis).
    2. `mode="lofo_pooled"`: 5 sensor-type pooled models per fold trained across $N-1$ factories for strict LOFO evaluation.
* **Feature Extraction Engine Unchanged**:
  - The feature pipeline `extract_series_features` remains $100\%$ identical! The exact same 13 causal backward-looking features (`value`, `rolling_mean_4`, `rolling_std_4`, `rolling_diff_1`, `rolling_diff_4`, `rolling_mean_16`, `rolling_std_16`, `rolling_min_16`, `rolling_max_16`, `hour_sin`, `hour_cos`, `day_sin`, `day_cos`) are used for both modes.

---

## 3. Threshold Calibration Protocol (Zero Performance Tuning Leakage)

### Calibration Mechanics
1. **Un-Injected Telemetry Only**:
   - Threshold $\tau$ is calibrated ONLY on un-injected real telemetry.
   - **Zero tamper injection labels or detection outcomes are ever accessed during threshold setting.**
2. **Factory-Month Budget Protocol**:
   - For each held-out factory $F_k$ with $M_k$ factory-months of telemetry:
     - On $F_k$'s un-injected telemetry, score with the LOFO models $M_{p}^{(k)}$.
     - Binary search finds the exact score threshold $\tau_k$ that yields exactly $M_k$ false alert episodes ($1.0$ false alert per factory-month).
3. **Application to Injected Events**:
   - Apply the un-injected calibrated threshold $\tau_k$ directly to Factory $F_k$'s injected parquets (Seeds 1–5).
   - This guarantees that every method (New Detector, Rolling Z-Score Baseline, Static Limit Baseline, Legacy XGBoost) is evaluated at the exact same false-alarm rate budget without any performance tuning or label leakage.

---

## 4. LOFO Isolation & Missing Data Safety Guarantees

| Requirement | Safety Mechanism | Compliance Status |
| :--- | :--- | :---: |
| **LOFO Isolation** | Factory $F_k$ telemetry is $100\%$ excluded from fold $k$ model training. | **CONFIRMED** |
| **No Missing Data Alerts** | Readings with `value = NaN` are assigned `anomaly_score = np.nan`. | **CONFIRMED** |
| **Numpy Evaluation Safety** | In Python/numpy, `(np.nan > threshold)` evaluates to `False`. Missing rows can NEVER trigger false alarms or tamper detections. | **CONFIRMED** |

---

## 5. Locked Test Set Confirmation

* The 4 unseen test factories (`Data/Unseen/*.csv`: Cipla, Glenmark, Indoco, Zydus) remain **$100\%$ locked and untouched**.
* Zero code, models, or threshold calibration will touch or execute on `Data/Unseen/*.csv` during Step 4.

---

## Summary of Final Evaluation Design for Step 4

1. **Primary Method**: LOFO Cross-Validation using Sensor-Type Pooled Isolation Forest models across 22 dev factories ($2,511$ events evaluated across Seeds 1–5).
2. **Baselines to Compare at 1.0 False Alert / Month**:
   - **Method 1**: New LOFO Sensor-Type Isolation Forest Detector.
   - **Method 2**: Rolling Z-Score Baseline ($|x_t - \mu_t| / \sigma_t$).
   - **Method 3**: Static Limit Baseline (distance to 3-sigma / consent limit).
   - **Method 4**: Legacy Pooled XGBoost / Global Isolation Forest.
3. **Primary Pass Criteria**: Overall Recall $\ge 0.70$ with 95% cluster bootstrap confidence interval lower bound $\ge 0.50$.
