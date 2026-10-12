# FORENSIAIR V2 — STAGE 2, PART 2.2: DETECTOR COMPONENT ENGINEERING REPORT

**Specification:** Protocol v2.0 (Frozen) & Protocol v1.1 Section C (Frozen)  
**Location:** [`validation_v2/v2/detector_b/`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/detector_b/)  
**Status:** Part 2.2 Completed — All 9 Targeted Unit Tests Passed (100% Success)  

---

## 1. Components Implemented & Component Interfaces

The V2 detector component suite is implemented in [`validation_v2/v2/detector_b/detector_b.py`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/detector_b/detector_b.py). It maintains strict compatibility with the existing 15-minute regular time grid and missing-data semantics, outputting tail-probability anomaly scores bounded in $[0.0, \infty)$ via $-\log_{10}(p)$.

### Summary of Component Architecture

| Component | Target Fault / Mechanism | Window Sizes ($w$) | Raw Statistic & Mathematical Formulation | Tail Scoring Mode | Applicable Parameters |
|:---|:---|:---:|:---|:---:|:---|
| **F1B: Local Variance Collapse** | `T1-B-freeze` (Dither flicker $p \in \{0.15, 0.05, 0.0\}$) | $16, 96, 288$ | $\frac{\text{std}_w(x)}{\text{std}_{\text{prior\_672}}(x) + 1e-4}$ <br/> (Drops toward 0 during frozen telemetry) | LOW tail (`mode="low"`) | All parameters. Flow zero-valued windows masked to `NaN`. |
| **F1B: Unique Value Fraction** | `T1-B-freeze` (Quantization dither) | $96, 288$ | $\frac{\text{nunique}_w(x)}{w}$ <br/> ($\le 3/w$ during bit flicker vs normal variation) | LOW tail (`mode="low"`) | All parameters. Flow zero-valued windows masked to `NaN`. |
| **F2B: Z-Normalized Shape Replay** | `T2-B-scaled` (Gain scaling $s \in [0.90, 1.10]$) & `T2-B-splice` | $16, 96, 288$ | $\min_{L} \sqrt{\max(2(1 - r_L), 0.0)}$ for $L \in \{96 \dots 672\}$, where $r_L = \text{corr}_w(x_t, x_{t-L})$. <br/> *Resolution Mask:* Windows with $\text{range}_w \le \text{step}$ set to `NaN`. | LOW tail (`mode="low"`) | All parameters. Evaluates pattern replay invariant to scaling. |
| **F3B: Near-Limit Persistence** | `T3-B-ar1` (AR(1) near-limit hugging) & `T3-B-pull` | $16, 96, 288$ | $\text{hug\_frac}_w \times \frac{\text{median}_w(x)}{L_{\text{CTO}}}$, where $\text{hug\_frac}_w = \text{mean}_w(x \ge 0.85 \cdot L_{\text{CTO}})$. | HIGH tail (`mode="high"`) | Parameters with parsed CTO limits in `consent_limits.csv`. `NaN` otherwise. |
| **F3B: Variance Clamping** | `T3-B-pull` (Variance compression near ceiling) | $96, 288$ | When $\text{median}_w \ge 0.80 \cdot L_{\text{CTO}}$: $\frac{\text{median}_w / L_{\text{CTO}}}{\text{std}_w / (\text{MAD} + 1e-4) + 0.1}$, else $0.0$. | HIGH tail (`mode="high"`) | Parameters with parsed CTO limits in `consent_limits.csv`. `NaN` otherwise. |
| **F7B: Matched Triangular Filter** | `T7-B-tri` (Symmetric triangular bias ramps) | $16, 96, 288$ | $|\text{conv}_{\text{tri}}(x)_w| / (\text{MAD} + 1e-4)$, using zero-mean normalized symmetric triangular kernel $K_{\text{tri}}$. | HIGH tail (`mode="high"`) | All parameters. Convolved via fast causal 1D FIR filter. |
| **F7B: Step-Jump Contrast** | `T7-B-step` (Abrupt step jumps with exponential decay) | $16, 96, 288$ | $\frac{\|\text{mean}(x_{t-w/2:t}) - \text{mean}(x_{t-w:t-w/2})\|}{\text{std}_{\text{prior\_672}} + 1e-4}$. | HIGH tail (`mode="high"`) | All parameters. Detects mid-window change points. |
| **F7B: Transient Peak Deviation** | `T7-B-step`, `T7-B-tri` (Transient departure from ambient trend) | $16, 96$ | $\frac{\max(x_{\max} - x_{\text{med}}, x_{\text{med}} - x_{\min})}{\text{MAD} + 1e-4}$. | HIGH tail (`mode="high"`) | All parameters. Captures acute departures from median. |
| **IF_B: Enhanced Sensor Isolation Forest** | All multi-variate and subtle evasive shifts | $16$ rows ($4\text{h}$) | 9 causal window features scored by decoupled per-sensor Isolation Forest (`n_estimators=100`). | HIGH tail (`mode="high"`) | All parameters. Scored via negative decision function tail probability. |
| **M1 Fusion (Legacy)** | Baseline benchmark comparison | All | $\max(F_1, F_2, F_3, F_5, F_6, \text{IF})$ | Row-wise Max | Backward compatibility with V1. |
| **M2 Fusion (Composite)** | Full V2 Tamper Surveillance | All | $\max(F_1, F_{1B}, F_2, F_{2B}, F_3, F_{3B}, F_5, F_6, F_{7B}, \text{IF}_B)$ | Row-wise Max | Primary V2 detector decision surface. |

---

## 2. Feature & Scoring Methods

1. **Strictly Causal Windows:** All rolling statistics use trailing backward-looking windows ($[t-w+1 : t]$). No future points $> t$ are used.
2. **Tail Probability Scoring:**
   - Raw statistics are calibrated against reference empirical distributions learned via blind calibration on the series being scored (`calibrate_b(mode="blind")`).
   - Tail probabilities are computed using binary search via `np.searchsorted`, clipped to $[1/N, 1.0]$.
   - Anomaly scores are computed as $-\log_{10}(p)$, guaranteeing that all scores are finite and strictly $\ge 0.0$.
3. **Shape Invariance in F2B:**
   - By leveraging the mathematical equivalence $\text{RMSD}_{\text{znorm}} = \sqrt{2(1 - r_L)}$, F2B evaluates Pearson correlation against historical lags.
   - For an affine-scaled replay $x'_t = s \cdot x_{t-L} + c$, correlation $r_L \equiv 1.0$, resulting in $\text{RMSD}_{\text{znorm}} \equiv 0.0$. This completely nullifies gain-scaling evasion.
4. **Matched Filtering in F7B:**
   - The triangular kernel $K_{\text{tri}}(i) = 1 - \frac{|2i - (w-1)|}{w-1}$ matches the exact symmetrical geometry of $T7\text{-B-tri}$ injections, concentrating signal energy into an acute filter response.

---

## 3. Missing-Data Handling & Runtime Guards

1. **IEEE 754 Safety:** If $x_t$ is missing (`value = NaN`), all individual check scores, IF_B scores, and both $M_1$ and $M_2$ fusions evaluate strictly to `NaN`. Under float comparisons `(NaN >= tau)` evaluates to `False`, guaranteeing that missing readings never start or continue alerts.
2. **Zero 100% NaN Guard:** Pre-flight unit tests confirm that applicable series always produce valid, finite scores for applicable checks.
3. **Flow Shutdown Masking:** Zero-valued flow windows are masked (`NaN` or $0.0$) in F1B and F2B, preventing natural plant idle periods from generating false freeze alarms.
4. **Consent Limit Protection:** F3B checks are strictly constrained to series with verified upper statutory CTO limits in `consent_limits.csv`. Series without audited limits safely produce `NaN` and are excluded from limit fusion.

---

## 4. IF_B: Enhanced Isolation Forest Feature Construction

The enhanced Isolation Forest (`extract_if_b_features`) uses 9 strictly causal features computed exclusively from past telemetry without whole-series lookahead:
1. `rolling_mean_16`: 16-row rolling mean
2. `rolling_std_16`: 16-row rolling standard deviation
3. `rolling_range_16`: 16-row local range ($\max - \min$)
4. `diff_std_16`: 16-row standard deviation of first differences
5. `diff_mean_16`: 16-row mean absolute difference (captures high-frequency jitter)
6. `z_level_16`: local level deviation standardized against prior 96 rows
7. `var_ratio_16_96`: ratio of short-term variance to medium-term variance ($\text{std}_{16} / (\text{std}_{96} + 1e-4)$)
8. `tri_conv_16`: 16-row normalized triangular FIR filter response
9. `unique_ratio_16`: distinct value fraction in 16 rows (dither/quantization proxy)

All training of IF_B (`fit_if_b`) is designed strictly for clean, un-injected development telemetry (pooled across training fold factories under LOFO). Zero injection labels or injected parquets are used.

---

## 5. Unit Test Execution & Verification (`test_detector_b.py`)

A comprehensive 9-test test suite was implemented in [`validation_v2/v2/detector_b/test_detector_b.py`](file:///c:/Users/gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance\validation_v2\v2\detector_b\test_detector_b.py).

### Execution Command:
```bash
python -m pytest validation_v2/v2/detector_b/test_detector_b.py -v
```

### Test Session Output:
```text
============================= test session starts =============================
platform win32 -- Python 3.12.7, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance
plugins: anyio-4.13.0, langsmith-0.11.0, asyncio-0.26.0
collected 9 items

validation_v2/v2/detector_b/test_detector_b.py::test_1_component_outputs_valid_and_non_negative PASSED [ 11%]
validation_v2/v2/detector_b/test_detector_b.py::test_2_constant_short_and_missing_series PASSED        [ 22%]
validation_v2/v2/detector_b/test_detector_b.py::test_3_applicable_series_not_100pct_nan PASSED        [ 33%]
validation_v2/v2/detector_b/test_detector_b.py::test_4_strict_causality PASSED                        [ 44%]
validation_v2/v2/detector_b/test_detector_b.py::test_5_determinism PASSED                             [ 55%]
validation_v2/v2/detector_b/test_detector_b.py::test_6_missing_readings_produce_nan PASSED            [ 66%]
validation_v2/v2/detector_b/test_detector_b.py::test_7_no_injector_labels_dependency PASSED          [ 77%]
validation_v2/v2/detector_b/test_detector_b.py::test_8_frozen_v1_files_unchanged PASSED               [ 88%]
validation_v2/v2/detector_b/test_detector_b.py::test_9_component_sensitivity PASSED                  [100%]

============================== 9 passed in 4.71s ==============================
```

### Verified Criteria:
1. **Valid Documented Outputs:** All components return expected column names with finite scores $\ge 0.0$.
2. **Edge Cases:** Constant series, short series ($< 16$ rows), and missing blocks execute safely without errors.
3. **Runtime Guards:** Applicable series never produce 100% NaN score columns.
4. **Strict Causality:** Feature vectors at timestamp $T$ are bitwise identical whether future data $> T$ exists or is truncated.
5. **Determinism:** Identical input series produce identical scores.
6. **Missing Safety:** Missing values (`value = NaN`) strictly yield `score = NaN`.
7. **Zero Label Leakage:** Source code contains zero imports from injector modules or references to injected label columns.
8. **Frozen V1 Code Integrity:** `git diff detector-frozen -- validation_v2/detector validation_v2/injector` confirmed strictly 0 modifications.
9. **Targeted Sensitivity:**
   - Planted dithered freeze ($p=0.15$) significantly elevates F1B score over baseline.
   - Planted gain-scaled replay ($s=1.08$) significantly elevates F2B score over baseline.
   - Planted near-limit persistence (95% of CTO limit) significantly elevates F3B score over baseline.
   - Planted triangular bias ramp significantly elevates F7B matched-filter score over baseline.

---

## 6. Files Created or Modified

- **Created:**
  1. [`validation_v2/v2/detector_b/detector_b.py`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/detector_b/detector_b.py) — V2 detector components and M2 composite fusion.
  2. [`validation_v2/v2/detector_b/test_detector_b.py`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/detector_b/test_detector_b.py) — 9-test unit test suite.
  3. [`validation_v2/v2/detector_b/PART_2_2_REPORT.md`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/detector_b/PART_2_2_REPORT.md) — Technical report.
- **Modified:** Zero existing files modified. Frozen V1 files remain completely untouched.

---

## 7. Status Summary

Part 2.2 has **PASSED all targeted unit tests (9/9 passed)**. The detector components are verified, fully documented, mathematically sound, strictly causal, and ready for clean-telemetry calibration in Part 2.3.
