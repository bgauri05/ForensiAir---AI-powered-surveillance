# FORENSIAIR DETECTOR SPECIFICATION (STEP 2d REVISION)

**Document Basis:** `PROTOCOL_v1.md` & `PROTOCOL_v1.1.md` (Sec G, H)  
**Location:** `validation_v2/detector/DETECTOR_SPEC.md`  
**Status:** SPECIFICATION REVISED (STEP 2d REVISION: RUN-LEVEL F1 & RESOLUTION-STEP MASKED F2)  

---

## 1. Overview & Framework

The ForensiAIR detector evaluates continuous telemetry per parameter and factory using an empirical **tail-probability score framework**.
* **Inputs**: Timestamps and values only (Protocol v1.1 G). Rows with quality codes `Error` or `Out of Range` are dropped before use.
* **15-Minute Grid**: Every series is reindexed to a continuous 15-minute grid (`freq='15min'`). Missing readings are represented as `NaN`, never imputed or filled.
* **Blind Empirical Calibration**:
  - `calibrate(series_to_score, mode="blind")` (default): Computes check distributions and natural run statistics directly from the series to be evaluated, without ground-truth labels or clean oracle targets.
  - `calibrate(series_to_score, mode="oracle", clean_series=clean_series)`: Sensitivity option where calibration is constructed from clean unaltered historical telemetry.
* **Score Definition & Bounds**:
  $$\text{score} = -\log_{10}(p)$$
  Where tail probability $p$ is strictly bounded in $(0, 1.0]$. All finite scores are strictly **$\ge 0.0$**.

---

## 2. Specification of Checks (F1 – F7 & IF)

| Check | Name | Trailing Windows ($w$) / Scope | Statistic & Formulation | Tail Mode / Scoring | Applicable Parameters / Scope |
| :--- | :--- | :---: | :--- | :---: | :--- |
| **F1** | **Run-Level Flatline & Quasi-Flat Variants** | Row-level ($L \ge 8$), $\epsilon \in \{0, 1, 2\}$ | Contiguous runs with $\max - \min \le \epsilon \times \text{resolution\_step}$. <br/> Evaluated for $\epsilon=0$ (exact repeat), $\epsilon=1$ (1-step quasi-flat), $\epsilon=2$ (2-step quasi-flat). <br/> *Rationale: $\epsilon \in \{0, 1, 2\}$ was chosen to generalize beyond exact repeats on quantized industrial sensors (injector-informed).* <br/> For row $i$, $L = \text{length of run ending at } i$. <br/> If $L \ge 8$: $\text{score} = -\log_{10}\left(\frac{1 + \#\{\text{natural runs } \ge L\}}{1 + \#\text{runs}}\right)$. <br/> Else $0.0$. | Laplace smoothed tail probability | All parameters. **Flow exception**: Flow zero-valued runs are excluded from run statistics and assigned score $0.0$. Missing rows receive `NaN`. Legacy window range columns preserved as `legacy_F1_*`. |
| **F2** | **Copy-Paste Replay** | $w \in \{16, 96, 288\}$ | $\min_{L} \frac{\sum \|x_t - x_{t-L}\| / w}{\text{MAD}_{\text{series}} + 1e-4}$ for $L \in \{96, 192 \dots 672\}$. <br/> **Resolution Mask**: Windows with $\text{range}_w \le 1 \text{ resolution step}$ are set to `NaN` (flat windows belong to F1). | LOW tail (calibrated only on varying windows) | All parameters. Evaluates pattern replay strictly on varying windows. |
| **F3** | Limit Proximity | $w \in \{16, 96, 288\}$ | $\frac{\text{rolling\_median}_w(x)}{L_{\text{CTO}}}$ | HIGH tail | Parameters with a parsed upper consent limit in `consent_limits.csv` (27 dev pairs). Output `NaN` if no parsed limit exists. |
| **F4** | Validity | Instantaneous | Hard boolean flag ($pH < 0$ or $pH > 14$) | Hard Alert ($1.0 / 0.0$) | pH parameter only. Reported separately from F1–F7 score fusion. |
| **F5** | Correlation Break | $w \in \{96, 288\}$ | Rolling Pearson correlation between parameter pairs | Two-sided tail | Multi-parameter factories with $\ge 2$ of BOD/COD/TSS. Evaluated per parameter pair. |
| **F6** | Drift / Dip | $w \in \{16, 96, 288\}$ | Stat 1: $\frac{\text{median}_w - \text{median}_{\text{prior\_672}}}{\text{MAD}_{\text{prior\_672}} + 1e-4}$ <br/> Stat 2: Rolling linear slope (exact fast 1D convolution) | Two-sided tail | All parameters. Empirical distribution learned from series. |
| **F7** | Gaps | $w \in \{16, 96, 288\}$ | Missing fraction: $\frac{\text{count}(\text{NaN})}{w}$ | Direct fraction ($0.0 \dots 1.0$) | All parameters. Output separately; excluded from fusion (v1.1 F). |
| **IF** | Sensor Isolation Forest | Window features ($w=16, 96$) | Windowed features (rolling mean, std, range, diff-std, level-shift z) scored by Isolation Forest (`n_estimators=100..200`). | HIGH tail | All parameters. Fit per parameter on training-fold factories (LOFO) or self-calibrated in blind sensitivity. Missing rows receive `NaN`. |

---

## 3. Tie Handling & Score Guarantees

* **F1 Run-Level Scores ($\epsilon \in \{0, 1, 2\}$)**:
  Uses Laplace (add-1) smoothed survival probability over natural run lengths for each $\epsilon$:
  $$p_\epsilon = \frac{1 + k_\epsilon(L)}{1 + R_\epsilon}$$
  Where $R_\epsilon = \#\text{natural runs with } \max - \min \le \epsilon \times \text{step}$ in the series (excluding Flow 0s), and $k_\epsilon(L) = \#\{\text{natural runs with length} \ge L\}$.
  Because $0 \le k_\epsilon(L) \le R_\epsilon$, $p_\epsilon \in \left[\frac{1}{1 + R_\epsilon}, 1.0\right]$ and $\text{score}_\epsilon \in [0.0, \log_{10}(1 + R_\epsilon)]$.
  Output as `F1_score` (eps0), `F1_score_eps1`, and `F1_score_eps2`.
* **F2 Resolution-Step Masking**:
  By setting flat windows ($\text{range}_w \le \text{step}$) to `NaN`, F2 is protected from zero-difference tie inflation. The calibration distribution only contains genuine varying windows, eliminating artificial tie mass at 0.
* **Clipping**:
  For all empirical rank-based checks (F2, F3, F5, F6, IF), tail probability $p$ is clipped to $[1/N, 1.0]$ and $\text{score} = \max(-\log_{10}(p), 0.0)$. All scores are strictly **$\ge 0.0$**.

---

## 4. Output API Contract

* `calibrate(series, mode="blind", clean_series=None, cto_limits=None) -> calib_dict`
* `score(series, calib_dict, if_model=None, cto_limits=None, f5_corr_dict=None) -> DataFrame`:
  - `timestamp`: 15-min grid string (`%Y-%m-%d %H:%M:%S`).
  - `parameter_id`: Parameter name.
  - `F1_score`: New run-level flatline score ($\epsilon=0$).
  - `F1_score_eps1`: 1-step quasi-flat score ($\epsilon=1$).
  - `F1_score_eps2`: 2-step quasi-flat score ($\epsilon=2$).
  - `legacy_F1_range_w16_score`, `legacy_F1_range_w96_score`, `legacy_F1_range_w288_score`: Legacy window-range F1 scores (retained for comparison).
  - `F2_copypaste_w16_score`, `F2_copypaste_w96_score`, `F2_copypaste_w288_score`: Resolution-step masked copy-paste scores.
  - `F3_limit_w16_score`, `F3_limit_w96_score`, `F3_limit_w288_score`: Consent limit proximity scores (`NaN` if unconstrained).
  - `F6_shift_w16_score`, `F6_shift_w96_score`, `F6_shift_w288_score`: Level shift drift scores.
  - `F6_slope_w16_score`, `F6_slope_w96_score`, `F6_slope_w288_score`: Linear slope drift scores.
  - `F5_corr_w96_score`, `F5_corr_w288_score`: Pair correlation break scores.
  - `if_score`: Isolation Forest anomaly score.
  - `validity`: Hard boolean physical bounds flag ($1.0$ or $0.0$).
  - `gap_frac_w16`, `gap_frac_w96`, `gap_frac_w288`: Missing data fractions.

---

## 5. Score Ceiling Summary (Clean Telemetry, Blind Calibration)

| Check | Window | Series Evaluated | % Series Max $\ge 3$ | Median Max Score | Median Tie Mass (%) | Median p99.9 Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **F1_run_eps0** | - | 81 | 35.8% | 2.21 | 4.80% | 1.15 |
| **F1_run_eps1** | - | 81 | 33.3% | 2.33 | 2.14% | 1.97 |
| **F1_run_eps2** | - | 81 | 29.6% | 2.36 | 1.28% | 1.87 |
| **F2_copypaste** | 16 | 67 | 50.7% | 3.14 | 0.07% | 2.65 |
| **F2_copypaste** | 96 | 66 | 69.7% | 3.47 | 0.03% | 2.79 |
| **F2_copypaste** | 288 | 65 | 63.1% | 3.21 | 0.06% | 2.71 |
| **F3_limit** | 16 | 27 | 44.4% | 2.47 | 0.34% | 2.47 |
| **F3_limit** | 96 | 25 | 20.0% | 2.30 | 0.50% | 2.30 |
| **F3_limit** | 288 | 22 | 13.6% | 2.11 | 0.79% | 2.11 |
| **F6_shift** | 16 | 77 | 76.6% | 3.70 | 0.02% | 2.88 |
| **F6_shift** | 96 | 75 | 68.0% | 3.48 | 0.03% | 2.88 |
| **F6_shift** | 288 | 69 | 52.2% | 3.19 | 0.06% | 2.72 |
| **F6_slope** | 16 | 81 | 79.0% | 3.71 | 0.02% | 2.94 |
| **F6_slope** | 96 | 75 | 77.3% | 3.63 | 0.02% | 2.93 |
| **F6_slope** | 288 | 69 | 65.2% | 3.41 | 0.04% | 2.90 |
| **IF** | 16 | 75 | 84.0% | 3.78 | 0.02% | 2.93 |
| **F5_corr** | 96 | 27 | 48.1% | 2.78 | 0.08% | 2.65 |
| **F5_corr** | 288 | 24 | 41.7% | 2.89 | 0.13% | 2.73 |


