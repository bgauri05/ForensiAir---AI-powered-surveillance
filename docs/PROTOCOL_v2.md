# ForensiAIR Validation Protocol v2.0 (Supervised Cross-Mechanism Evaluation)

**Status:** FROZEN  
**Date:** 2026-10-11  
**Scope:** Development Set Only (33 Permitted Development Factories, strictly zero access to Data/Unseen/ or the 4 locked factories Cipla, Glenmark, Indoco, Zydus).  
**Basis:** Protocol v1.1 Section C eligibility, V1 Dev Injections (Mechanism A), and Mechanism B Evasive Injections.

---

## 1. Overview & Evaluation Objectives
Protocol v2.0 governs the Stage 2 evaluation of a supervised machine-learning detector trained on causal time-series features to assess cross-mechanism generalization:
1. **Mechanism A (V1 Injections):** Canonical, sharp tampering patterns (types T1, T2, T3, T7) across seeds 1–5.
2. **Mechanism B (V2 Injections):** Physically motivated evasive tampering patterns (types T1, T2, T3, T7) across seeds 301–305.
3. **Core Hypothesis:** Can a supervised detector trained on one tampering mechanism reliably detect the other mechanism (generalize out-of-mechanism) under the strict operating constraint of $\le 1.0$ false-alert episode per factory-month?

---

## 2. Data Scope & Populations
- **Permitted Factories:** The 33 development factories. Locked test factories (`Cipla`, `Glenmark`, `Indoco`, `Zydus`) and directory `Data/Unseen/` must NEVER be accessed.
- **Permitted Tamper Types:** T1, T2, T3, and T7 only.
- **Mechanism A Data:** V1 injected development data (`validation_v2/injector/injected/dev/labels.csv`, seeds 1–5).
- **Mechanism B Data:** Mechanism B development data (`validation_v2/v2/injector_b/labels_b.csv`, seeds 301–305).
- **No-Op Events:** Events with `changed_share < 0.50` (`no_op = True`) are excluded from training positives and from primary recall denominators, and counted separately; recall with them included is also reported.
- **Negative Data:** Clean un-injected telemetry from the 33 development factories (`Data/RawData/monitoring_data(raw).csv`, filtering for allowed quality codes `Raw` and `L`, 15-minute regular grid, missing readings preserved as NaN).

---

## 3. Five-Fold Factory-Grouped Cross-Validation
- All 33 development factories are assigned to 5 factory-grouped folds such that event-bearing factories are spread evenly.
- **Zero Leakage:** No factory may appear in both training and test sets of any fold.
- **Two Evaluation Directions:**
  - **Direction 1 (Train A $\rightarrow$ Test A & B):** Model trained on Mechanism A events of the training folds; evaluated on held-out factories for Mechanism A (in-mechanism) and Mechanism B (cross-mechanism).
  - **Direction 2 (Train B $\rightarrow$ Test B & A):** Model trained on Mechanism B events of the training folds; evaluated on held-out factories for Mechanism B (in-mechanism) and Mechanism A (cross-mechanism).

---

## 4. Feature Extraction Architecture (Protocol Section 4)
Features are computed per parameter using strictly backward-looking past telemetry (zero future leakage, zero quality codes, zero V1 detector scores):
1. **Multi-Scale Windows:** For $w \in \{16, 48, 96, 288\}$ rows (4 hours, 12 hours, 24 hours, 72 hours):
   - `range`: $\max(x_{t-w+1:t}) - \min(x_{t-w+1:t})$
   - `std`: Sample standard deviation over window $w$.
   - `exact_repeat_run_length`: Contiguous run length where consecutive readings are identical.
   - `unique_value_count`: Number of distinct finite readings in window $w$.
   - `fraction_unchanged`: Fraction of consecutive step differences equal to zero ($|x_i - x_{i-1}| < 10^{-6}$).
   - `level_shift`: Absolute difference between window mean and prior 7-day mean ($| \text{mean}_{w} - \text{mean}_{t-672:t} |$).
   - `slope`: Linear slope over window $w$ relative to prior 7 days.
   - `min_lagged_similarity`: Minimum distance across candidate historical lags $\text{lag} \in \{96, 192, 288, 384, 480, 576, 672\}$ (step 96, 1–7 days), scaled by MAD.
   - `missing_fraction`: Fraction of missing (NaN) readings in window $w$.
2. **Statutory Permit Limits:**
   - `limit_ratio`: $\text{median}_{w} / L_{\text{CTO}}$ (NaN if series has no parsed upper limit in `consent_limits.csv`).
   - `fraction_above_85pct`: Fraction of readings in window $w \ge 0.85 \times L_{\text{CTO}}$ (NaN if no parsed limit).
3. **Adaptive Scale Normalization:**
   - Scale-dependent features are divided by expanding past MAD (floor = 1 empirical resolution step).
   - Parameter identity is encoded as a categorical feature.
   - Structurally undefined features remain NaN (native missing-value support in tree learner).
4. **Causality Constraint:** Modifying readings after time $t$ must strictly produce zero difference in features at or before time $t$.

---

## 5. Model Architecture & Training Protocol
- **Classifier:** `HistGradientBoostingClassifier(max_depth=6, learning_rate=0.1, max_iter=200, l2_regularization=1.0, class_weight='balanced', random_state=42)` with no hyperparameter tuning.
- **Model Suite:**
  - **Primary Model:** ONE pooled model trained on all four tamper types ($T_1, T_2, T_3, T_7$).
  - **Secondary Diagnostic Models:** Type-specialist models ($T_1+T_2$, $T_3$, $T_7$), evaluated at their own budget of 1 alert/month and labeled "not additive".
- **Positive Samples:** Rows strictly inside event windows (dropping transition rows within 2 hours after event end).
- **Negative Samples:** Clean un-injected telemetry sampled at $\le 20$ negative rows per positive row, stratified by factory.
- **Preprocessing:** All scaling and category encoders fitted strictly on training factories of each fold.

---

## 6. Operating Cutoff & Calibration Protocol
- **Out-of-Fold Clean Telemetry Scoring:** Every development factory's clean telemetry is scored by the model trained on the fold where that factory was held out.
- **Global Threshold Calibration:** Out-of-fold clean scores across all 33 factories are pooled. A single global cutoff $\tau$ is chosen via binary search to yield exactly **1.0 false alert episode per factory-month** (328 target episodes across 327.61 total factory-months).
- **Episode Merging:** Alert points ($\text{score} \ge \tau$, $\text{value} \ne \text{NaN}$) separated by gaps $\le 16$ rows (4 hours) are merged into a single episode.
- **Event Matching:** An injection event $[t_{\text{start}}, t_{\text{end}}]$ is detected if an alert episode overlaps the event or starts within 2 hours after event end ($t_{\text{ep\_end}} \ge t_{\text{start}}$ and $t_{\text{ep\_start}} \le t_{\text{end}} + 2\text{h}$).
- **Comparators:** The identical clean-data calibration and event matching rules are applied to frozen V1 comparators: M1 composite fusion, per-sensor Isolation Forest alone, F1 (eps0, eps1, eps2), F2, F3, F6 shift and slope, and B0 random alerts.

---

## 7. Reading Rule & Acceptance Bar (Protocol Section 7)
- **Generalization Gap:** Defined as $\text{Recall}_{\text{in-mechanism}} - \text{Recall}_{\text{cross-mechanism}}$.
- **Formal Reading Rule:** V2 counts as genuinely better for a tamper type if and only if:
  1. The 95% cluster-bootstrap confidence interval of the paired difference ($V_2 - \text{Best } V_1$) strictly excludes 0 (lower bound $> 0$).
  2. The realized clean false-alarm rate of V2 is not higher than that of the comparator ($\le 1.0$ alert episode per factory-month).
- **Cluster Bootstrap:** 10,000 multinomial resamples at the factory level.
- **Budget Sensitivity:** Performance is also evaluated at 2.0, 4.0, and 10.0 false alert episodes per factory-month.
