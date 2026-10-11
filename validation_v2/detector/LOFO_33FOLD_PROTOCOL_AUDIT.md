# FORENSIAIR 33-FOLD LOFO CROSS-VALIDATION AUDIT & SPECIFICATION

**Protocol Basis:** `PROTOCOL_v1.md` & `PROTOCOL_v1.1.md` (Sec B, C, F, G, H)  
**Status:** FINAL 33-FOLD LOFO PROTOCOL SPECIFICATION  
**Scope:** Clarification of the 33 development factory LOFO folds, distinction between injection-eligible and un-injected-only factories, and false-alarm budget allocation.

---

## 1. LOFO Fold & Training Structure (33 Folds)

* **Total Development Factories**: **33 Factories** (`site_887` through `site_2070`).
* **LOFO Fold Count**: **33 Folds** ($k = 1 \dots 33$).
* **Training Set per Fold**: In fold $k$, the **32 remaining development factories** are pooled to fit the sensor-type Isolation Forest models:
  - `IsolationForest_pH`
  - `IsolationForest_Flow`
  - `IsolationForest_BOD`
  - `IsolationForest_COD`
  - `IsolationForest_TSS`
* **Held-Out Test Set per Fold**: The single $k$-th development factory $F_k$ is held out. Zero rows of $F_k$ are used in training fold $k$.

---

## 2. Distinction Between Factory Populations

| Population | Factory Count | Protocol Rule | Role in LOFO Evaluation |
| :--- | :---: | :--- | :--- |
| **All Development Factories** | **33** | Protocol v1.1 B | Evaluated for **False Alarms** on un-injected telemetry ($327.61$ total factory-months). |
| **Injection-Eligible Factories** | **21** | Protocol v1.1 C ($>10$ distinct values, $\le 50\%$ missing) | Evaluated for **Tamper Event Recall** across $2,511$ injected events (Seeds 1–5). |
| **Un-injected Only Factories** | **12** | Ineligible for injection ($>50\%$ missing or $\le 10$ distinct values) | Evaluated for **False Alarms only** ($0$ injected events, $0$ contribution to Recall denominator). |

---

## 3. Handling Un-injected Only Factories (12 Factories)

1. **False Alarm Calibration**:
   - Each un-injected-only factory $F_k$ (e.g. `site_1138`, `site_1167`, `site_1256`, `site_1581`) is scored using fold $k$'s 32-factory LOFO models.
   - Threshold $\tau_k$ is set to yield $1.0 \times M_k$ false alert episodes on its un-injected telemetry.
2. **Recall Computation**:
   - Contributes $0$ events to the overall event recall numerator and denominator.
   - Prevents divide-by-zero while rigorously verifying that sparse/noisy real telemetry does not trigger excessive false alerts.

---

## 4. Empirical 33-Fold LOFO Factory Audit Table

| Fold $k$ | Factory ID | Param Count | Factory-Months ($M_k$) | False Alarm Budget | Injected Events | Has Injections? |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| 1 | `site_1131` | 1 | 12.02 | 12 | 5 | Yes |
| 2 | `site_1138` | 1 | 11.77 | 12 | 0 | No |
| 3 | `site_1167` | 1 | 10.01 | 10 | 0 | No |
| 4 | `site_1200` | 1 | 11.88 | 12 | 55 | Yes |
| 5 | `site_1203` | 1 | 12.02 | 12 | 0 | No |
| 6 | `site_1221` | 2 | 11.95 | 12 | 150 | Yes |
| 7 | `site_1232` | 2 | 11.43 | 11 | 150 | Yes |
| 8 | `site_1247` | 1 | 12.02 | 12 | 10 | Yes |
| 9 | `site_1256` | 2 | 0.75 | 1 | 0 | No |
| 10 | `site_1257` | 2 | 12.02 | 12 | 150 | Yes |
| 11 | `site_1259` | 2 | 4.76 | 5 | 0 | No |
| 12 | `site_1264` | 2 | 12.02 | 12 | 150 | Yes |
| 13 | `site_1280` | 1 | 11.98 | 12 | 150 | Yes |
| 14 | `site_1281` | 2 | 12.02 | 12 | 0 | No |
| 15 | `site_1284` | 2 | 11.51 | 12 | 150 | Yes |
| 16 | `site_1285` | 2 | 12.02 | 12 | 150 | Yes |
| 17 | `site_1310` | 1 | 12.02 | 12 | 150 | Yes |
| 18 | `site_1321` | 5 | 12.02 | 12 | 150 | Yes |
| 19 | `site_1369` | 5 | 12.02 | 12 | 88 | Yes |
| 20 | `site_1376` | 5 | 12.02 | 12 | 150 | Yes |
| 21 | `site_1561` | 1 | 12.02 | 12 | 150 | Yes |
| 22 | `site_1569` | 1 | 1.91 | 2 | 0 | No |
| 23 | `site_1581` | 2 | 11.24 | 11 | 0 | No |
| 24 | `site_1668` | 5 | 12.02 | 12 | 150 | Yes |
| 25 | `site_1756` | 5 | 12.02 | 12 | 79 | Yes |
| 26 | `site_1787` | 1 | 12.02 | 12 | 150 | Yes |
| 27 | `site_1789` | 4 | 12.02 | 12 | 0 | No |
| 28 | `site_1799` | 5 | 12.02 | 12 | 150 | Yes |
| 29 | `site_1905` | 1 | 8.13 | 8 | 24 | Yes |
| 30 | `site_1909` | 2 | 2.80 | 3 | 0 | No |
| 31 | `site_2070` | 5 | 0.11 | 0 | 0 | No |
| 32 | `site_887` | 5 | 12.02 | 12 | 150 | Yes |
| 33 | `site_982` | 4 | 1.02 | 1 | 0 | No |
| **Total** | **33 Folds** | **67** | **327.61** | **328** | **2,511** | **21 Yes / 12 No** |

---

## 5. Pass Criteria & Baseline Methods (Step 4)

* **Target Budget**: $328$ false alert episodes across 33 development factories ($1.0$ per factory-month).
* **Methods to Compare**:
  1. New 33-Fold LOFO Sensor Isolation Forest Detector.
  2. Rolling Z-Score Baseline ($|x_t - \mu_t| / \sigma_t$).
  3. Static Limit Baseline (distance to 3-sigma / consent limit).
  4. Legacy Pooled XGBoost / Global Isolation Forest.
* **Pass Bar**: Overall Event Recall $\ge 0.70$ with 95% cluster bootstrap confidence interval lower bound $\ge 0.50$.
