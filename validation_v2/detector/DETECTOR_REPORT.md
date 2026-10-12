# FORENSIAIR ANOMALY DETECTOR REPORT (STEP 2 IMPLEMENTATION)

**Protocol Compliance**: PROTOCOL_v1.md (Sec 4-5) & PROTOCOL_v1.1.md (Sec B, C, G)  
**Execution Scope**: `validation_v2/detector/` (Dev Set Un-injected Telemetry Training)  
**Detector Isolation**: Decoupled per-sensor per-factory Isolation Forest models (81 models trained). Zero label leakage, zero quality code features, zero lookahead.

---

## 1. Detector Architecture & Design

### Model Topology
* **Per-Sensor Per-Factory Decoupled Isolation Forests**: Instead of global models pooled across factories or parameters (which suffer from scale/feature mismatch as discovered in Step 1b audit), a separate `sklearn.ensemble.IsolationForest` is trained for each `(factory_id, parameter_id)` series.
* **Training Input**: Un-injected raw development telemetry (`Data/RawData/monitoring_data(raw).csv`), with `Error` / `Out of Range` quality rows dropped per Protocol v1.1 G.

### Feature Pipeline (`extract_series_features`)
Strictly causal time-series features computed using **values and timestamps ONLY**:
1. `value`: Raw telemetry reading $x_t$.
2. `rolling_mean_4` & `rolling_std_4`: 4-row ($1\text{h}$) backward-looking rolling mean and standard deviation.
3. `rolling_diff_1` & `rolling_diff_4`: 1-row and 4-row backward differences ($x_t - x_{t-1}$, $x_t - x_{t-4}$).
4. `rolling_mean_16` & `rolling_std_16`: 16-row ($4\text{h}$) backward-looking rolling mean and standard deviation.
5. `rolling_min_16` & `rolling_max_16`: 16-row ($4\text{h}$) local minimum and maximum.
6. `hour_sin`, `hour_cos`, `day_sin`, `day_cos`: Diurnal and weekly cyclical temporal features.

### Zero-Leakage & Safety Guarantees
* **Zero Label Usage**: Injected labels (`is_injected`, `event_id`) and ground-truth tamper tags are $0\%$ accessible to the model or feature pipeline.
* **Zero Quality Code Usage**: Quality codes are used *only* in training row filtering, never as input features (per Protocol v1.1 G).
* **Strict Causality**: Rolling windows use `min_periods=1` looking backward. No future data $> T$ affects features at timestamp $T$.
* **Native Missing Data Handling**: Built on `scikit-learn` 1.8.0 native missing value support in `IsolationForest` without global cross-series mean imputation.

---

## 2. Files Created & Artifacts

| File / Artifact Path | Purpose |
| :--- | :--- |
| [`validation_v2/detector/detector.py`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/detector/detector.py) | Main detector class `SensorIsolationForestDetector` & feature extraction engine. |
| [`validation_v2/detector/models/sensor_models.joblib`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/detector/models/sensor_models.joblib) | Serialized dictionary of 81 trained per-sensor per-factory Isolation Forest models. |
| [`validation_v2/detector/test_detector.py`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/detector/test_detector.py) | Pytest test suite covering 7 integrity and safety rules. |
| [`validation_v2/detector/DETECTOR_REPORT.md`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/detector/DETECTOR_REPORT.md) | Technical architecture, run instructions, and verification report. |

---

## 3. Run Instructions

### To Train Models from Scratch
```bash
python validation_v2/detector/detector.py
```

### To Run Test Suite
```bash
python -m pytest validation_v2/detector/test_detector.py
```

---

## 4. Test Suite Results (`test_detector.py`)

```text
============================= test session starts =============================
platform win32 -- Python 3.12.7, pytest-8.4.2, pluggy-1.6.0
collected 7 items

validation_v2\detector\test_detector.py .......                          [100%]

============================== 7 passed in 9.00s ==============================
```

### Verified Criteria
1. **Sensor Separation & Decoupling**: Models across series are distinct object instances.
2. **Zero Data Leakage (Strict Causality)**: Features at timestamp $T$ are identical whether future data $> T$ is present or truncated.
3. **Timestamp Mapping & Order Preservation**: Anomaly score outputs map $1$-to-$1$ to original input row indices even when input data is shuffled.
4. **Missing Data & Invalid Reading Handling**: `NaN` values and missing gaps do not cause exceptions or trigger mean imputation.
5. **Window Boundaries at Start of Series**: Early timestamps (history $< 4$ or $< 16$ rows) yield finite, valid anomaly scores.
6. **Reproducibility**: Deterministic output guaranteed across identical random states.
7. **No Feature Leakage**: $0$ forbidden columns (`is_injected`, `event_id`, `quality_code`, `label`, `tamper`) are present in model feature columns.

---

## 5. Unresolved Decisions & Next Steps

* **No Threshold Tuning Performed**: As instructed, classification decision thresholds have NOT been hardcoded or tuned.
* **No Unseen Data Evaluation**: Evaluation on unseen factories (`Data/Unseen/*.csv`) has NOT been executed and remains isolated for subsequent steps.
* **Next Milestone**: Proceed to Step 4 evaluation on development seeds to analyze detection recall, false alarm rates, and calibration metrics under Protocol v1.1.
