# FORENSIAIR STAGE 3A — FINAL RESULTS AND PROTOCOL RECONCILIATION REPORT (READ-ONLY)

**Audit Execution Date:** 2026-10-12  
**Audit Scope:** Read-only verification and protocol reconciliation across V1 and V2 development artifacts  
**Git Working Branch:** `v2-dev`  
**Git Integrity Check:** `git diff detector-frozen -- validation_v2/detector validation_v2/injector` is **100% EMPTY**  
**Locked Data Isolation:** `Data/Unseen/` and the 4 locked test factories (`Cipla`, `Glenmark`, `Indoco`, `Zydus`) were **STRICTLY UNTOUCHED AND UNREAD**  
**Execution Constraints:** No models were rerun, no thresholds were retuned, no metrics were altered, and no code or protocol files were modified.

---

## 1. Master Issue & Protocol Reconciliation Table

| Issue / Investigation Item | Primary Evidence Path(s) | Key Audit Finding | Reconciliation Status |
| :--- | :--- | :--- | :---: |
| **1. Event-Count Reconciliation** (2,698 vs 2,694 vs 2,553; 144 vs 141 no-ops) | [`validation_v2/v2/injector_b/MECH_B_REPORT.md`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/injector_b/MECH_B_REPORT.md)<br>[`validation_v2/v2/injector_b/labels_b.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/injector_b/labels_b.csv)<br>[`validation_v2/v2/MECH_B_V1_EVENTS_EVALUATED.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/MECH_B_V1_EVENTS_EVALUATED.csv)<br>[`validation_v2/v2/model/V2_LOG.md`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/model/V2_LOG.md) | The initial Stage 1 injector run produced 2,698 events with 144 no-ops (diff: 2,554). In Stage 1b, per Protocol v2.0 preconditions, the injector was regenerated to cap T2 donor lags to $\le 672$ rows. This shifted donor availability at two sites (-5 at `site_1756`, +1 at `site_1799`), yielding exactly **2,694 total events**. Computing row changes yielded exactly **141 no-op events** (`changed_share < 0.50`). Thus, $2,694 - 141 = \mathbf{2,553}$ primary non-no-op events. Zero data discrepancy exists. | **PASS** |
| **2. Protocol Approval & Freeze Status** (`PROTOCOL_v1.md` and v1.1 Addendum) | [`PROTOCOL_v1.md`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/PROTOCOL_v1.md)<br>[`docs/PROTOCOL_v2.md`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/docs/PROTOCOL_v2.md)<br>Git commit history (`git log --all`) | `PROTOCOL_v1.md` explicitly states `Status: DRAFT` and was never committed to git (remains untracked). While downstream markdown reports cite `PROTOCOL_v1.md` as "Frozen", no formal signed approval document or timestamped owner sign-off exists in the repository. In contrast, `docs/PROTOCOL_v2.md` was committed and frozen under git tag `v2-protocol-frozen` (`8c98d3d`). | **UNVERIFIED** (Protocol v1 / v1.1)<br>**PASS** (Protocol v2.0) |
| **3. Comparison Integrity & Window Consistency** (V1 vs V2, Budget vs Duty Cycle) | [`validation_v2/v2/model/v2_eval_events.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/model/v2_eval_events.csv)<br>[`validation_v2/v2/model/analysis/fair_comparators.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/model/analysis/fair_comparators.csv)<br>[`validation_v2/v2/model/analysis/alert_duty_cycle.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/model/analysis/alert_duty_cycle.csv)<br>[`validation_v2/v2/model/analysis/matched_duty_cycle_sensitivity.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/model/analysis/matched_duty_cycle_sensitivity.csv) | V1 and V2 models are evaluated on the exact same event instances side-by-side using identical detection windows (`[start_dt, end_dt + 2h]`) and gap-merging ($\le 16$ rows). The primary comparison operates under the protocol budget of 1.0 alert episode/factory-month. The matched-duty-cycle sensitivity isolates the temporal persistence penalty by tightening V2 thresholds to match V1 M1's 0.1041% clean duty cycle. | **PASS** |
| **4. Factory Concentration & Exposure Denominators** (33-Factory False Alarm Rates) | [`validation_v2/v2/model/v2_clean_false_alarms.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/model/v2_clean_false_alarms.csv)<br>[`validation_v2/v2/model/analysis/false_alarm_concentration.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/model/analysis/false_alarm_concentration.csv)<br>[`validation_v2/runs/run2b/false_alarms.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/runs/run2b/false_alarms.csv) | All 33 development factories are evaluated with consistent exposure denominators ($m_k$, sum = 327.61 factory-months). Zero factories were removed or excluded. Aggregation mathematically preserves factory exposure. V2 exhibits strong site concentration (top 3 sites generate 74.39% of false alarms in Dir 1), whereas V1 M1 is more dispersed (top 3 sites generate 29.66%). | **PASS** |
| **5. Claim Boundaries & Scientific Generalization** (Real-World Tampering vs Simulation) | [`validation_v2/v2/model/analysis/V2_ANALYSIS_REPORT.md`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/model/analysis/V2_ANALYSIS_REPORT.md)<br>[`docs/mechanism_sources.md`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/docs/mechanism_sources.md) | Findings are rigorously separated into statistically supported conclusions, descriptive measurements, and unresolved claims. Crucially, detection of mathematically simulated synthetic anomalies (Mechanism A step clamps, Mechanism B spline/AR(1) perturbations) is explicitly acknowledged as **NOT proving detection of real-world deliberate tampering in industrial facilities**. | **PASS** |

---

## 2. Issue 1: Event-Count Reconciliation

### 2.1 The Apparent Discrepancy
In earlier documentation:
- `validation_v2/v2/injector_b/MECH_B_REPORT.md` (Stage 1) reported: **2,698 generated events** and **144 no-op events**.
- Subtracting 144 from 2,698 yields **2,554 events**.
- However, V2 Stage 2 evaluation (`v2_eval_events.csv`, `STAGE2_FINAL_REPORT.md`, `V2_ANALYSIS_REPORT.md`) evaluated **2,553 primary non-no-op events**.
- A difference of 1 event ($2,554 - 2,553 = 1$) appeared unresolved.

### 2.2 Root-Cause Identification & Archival Evidence
Tracing git history and log files reveals the exact sequence of events:
1. **Initial Stage 1 Injector Run (Pre-Freeze):**
   - In the preliminary Stage 1 implementation, `injector_b.py` generated 2,698 events across seeds 301–305.
   - However, audit revealed that T2 copy-paste variants (`T2-B-scaled` and `T2-B-splice`) drew donor windows from historical lags up to 2,688 rows (28 days).
   - Furthermore, `labels_b.csv` did not track actual row-level changes (`n_rows_changed`, `changed_share`, `max_abs_change`), and the 144 no-op count was an unverified heuristic estimate.
2. **Stage 1b Regeneration (Mandated Precondition for Freeze):**
   - Per `docs/PROTOCOL_v2.md` Part 0 and `validation_v2/v2/model/V2_LOG.md`:
     > *"If labels_b.csv lacks columns n_rows_changed, changed_share, max_abs_change, no_op (=changed_share<0.5), or any T2-B event has lag >672 rows: regenerate seeds 301-305 with the same code except T2-B-scaled lag 1-7 days (96-672 rows) and T2-B-splice both blocks 1-7 days back."*
   - In Stage 1b, `injector_b.py` was updated to enforce $\text{lag} \le 672$ rows.
   - Restricting candidate donor windows to 1–7 days back altered donor availability and 48-hour event spacing constraints across two factories:
     - **`site_1756`:** event count decreased by 5 (from 101 events to **96 events**).
     - **`site_1799`:** event count increased by 1 (from 141 events to **142 events**).
     - All other 18 event-bearing factories placed identical event counts.
     - Net change: $2,698 - 5 + 1 = \mathbf{2,694\text{ total events}}$.
3. **Exact No-Op Accounting on Regenerated Parquets:**
   - Every injected parquet was re-read against raw telemetry to compute the exact number of modified rows:
     $$\text{changed\_share} = \frac{n\_rows\_changed}{\text{duration\_rows}}$$
   - An event was marked `no_op = True` if $\text{changed\_share} < 0.50$.
   - Exactly **141 events** met this exclusion criterion:
     - **T1 (`T1-B-freeze`):** 46 no-op events out of 760 (6.05%).
     - **T2 (`T2-B-scaled`, `T2-B-splice`):** 13 no-op events out of 523 (2.49%).
     - **T3 (`T3-B-ar1`, `T3-B-pull`):** 0 no-op events out of 611 (0.00%).
     - **T7 (`T7-B-step`, `T7-B-tri`):** 82 no-op events out of 800 (10.25%).
     - **Total:** $46 + 13 + 0 + 82 = \mathbf{141\text{ no-op events}}$.
4. **Primary Evaluation Population:**
   $$\text{Total Generated (2,694)} - \text{No-Op Excluded (141)} = \mathbf{2,553\text{ Primary Events}}$$

### 2.3 Conclusion on Issue 1
The apparent 1-event gap was an artifact of comparing the superseded Stage 1 report ($2,698 - 144 = 2,554$) with the frozen Stage 1b/Stage 2 dataset ($2,694 - 141 = 2,553$). The frozen dataset committed under tag `v2-protocol-frozen` (`8c98d3d`) contains exactly 2,694 rows, exactly 141 no-ops, and exactly 2,553 primary non-no-op events.  
**Audit Finding: RECONCILED (PASS).**

---

## 3. Issue 2: Protocol Approval and Freeze Status

### 3.1 Examination of `PROTOCOL_v1.md` and v1.1 Addendum
- **Repository Location:** `c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance\PROTOCOL_v1.md`.
- **File Content & Header:**
  ```markdown
  # ForensiAIR Validation Protocol v1.1 (Addendum to v1)
  Status: DRAFT. Freezes when the owner approves it, and before any detector code is run or evaluated.
  Date: 2026-10-09
  ```
- **Git Tracking Status:** `git status` reveals `?? PROTOCOL_v1.md` (the file is **untracked** in Git and has never been committed).
- **Git History Search:** `git log --all -- PROTOCOL_v1.md` returns zero commits across all branches and tags.
- **Approval Evidence Search:** No signed approval file, sign-off markdown document, or pull request record exists verifying owner sign-off on `PROTOCOL_v1.md` or its v1.1 addendum prior to running Step 4 or Run 2b evaluations.
- **Downstream References:** While downstream reports (`FINAL_REPORT.md`, `MECH_B_REPORT.md`, `PROTOCOL_v2.md`) retroactively describe Protocol v1 / v1.1 as "Frozen", the source protocol document itself was never updated from `DRAFT` to `APPROVED/FROZEN`.
- **Verdict for Protocol v1 / v1.1:** Because explicit owner sign-off cannot be verified in the git log or file metadata, the formal pre-evaluation approval status is marked **UNVERIFIED**.

### 3.2 Examination of `docs/PROTOCOL_v2.md`
- **Repository Location:** `docs/PROTOCOL_v2.md`.
- **File Content & Header:**
  ```markdown
  # ForensiAIR Validation Protocol v2.0 (Supervised Cross-Mechanism Evaluation)
  Status: FROZEN
  Date: 2026-10-11
  ```
- **Git Commit:** Committed in `8c98d3d2d45f3ab79dfa54327cb56bd94b28188c` on Sunday, October 11, 2026 at 22:41:22 +05:30.
- **Git Tag:** Formally tagged locally as `v2-protocol-frozen`.
- **Precondition Verification:** Preconditions (Stage 1b regenerated labels, T2 lag capping, no-op tracking) were verified prior to model execution.
- **Verdict for Protocol v2.0:** **FORMALLY FROZEN & VERIFIED (PASS).**

---

## 4. Issue 3: Comparison Integrity

### 4.1 Population Consistency
In `validation_v2/v2/model/v2_eval_events.csv`:
- All **4,593 events** (1,899 on Mechanism A; 2,694 on Mechanism B, of which 2,553 are primary non-no-op) contain detection flags for:
  - Supervised V2 models: `is_detected_dir1_pooled`, `is_detected_dir2_pooled`
  - V1 Multi-Check Fusion: `is_detected_V1_M1`
  - V1 Isolation Forest alone: `is_detected_V1_IF`
  - V1 Single checks: `is_detected_V1_F1_eps0`, `_eps1`, `_eps2`, `_F2`, `_F3`, `_F6_shift`, `_F6_slope`
  - Static Consent Limit baseline: `is_detected_B0`
- Both V1 and V2 models were evaluated on the **exact same physical rows and events** in memory, guaranteeing 100% paired population consistency.

### 4.2 Event Matching & Evaluation Windows
The exact matching algorithm in `train_and_evaluate_v2.py` (lines 720–765) was verified:
- **Alert Episode Definition:** Readings with $\text{score} \ge \tau$ are grouped into episodes; gaps $\le 16$ rows (4 hours) are merged; missing readings (`value = NaN`) cannot start, extend, or trigger alerts.
- **Matching Rule:** An episode with start timestamp $T_{\text{start}}$ and end timestamp $T_{\text{end}}$ matches an event with injection window $[t_{\text{start}}, t_{\text{end}}]$ if:
  $$T_{\text{end}} \ge t_{\text{start}} \quad \text{and} \quad T_{\text{start}} \le (t_{\text{end}} + 2\text{ hours})$$
- The identical 2-hour grace window was applied across V1 M1, all V1 single checks, B0, and V2.

### 4.3 Operational Budget vs Matched Clean Duty Cycle Distinction
The distinction between the two evaluation regimes is mathematically and operationally distinct:
1. **Nominal Operating Budget (1.0 Alert Episode / Factory-Month):**
   - The primary protocol constraint governs **alarm frequency**: an operator receives an average of 1 alarm alert per facility per month ($328$ global alert episodes across $327.61$ factory-months).
   - Both V1 M1 ($\tau = 3.7906$) and V2 Pooled ($\tau = 0.97875$ for Train A; $\tau = 0.96469$ for Train B) strictly achieve this 1.0 alert/month rate.
2. **Supplementary Matched-Clean-Duty-Cycle Sensitivity:**
   - Evaluates **alarm persistence**: although both systems sound 1 alarm per month, V1 M1 alerts are brief (mean: 3.6 rows / 54m; median: 1 row / 15m; duty cycle: 0.1041%), whereas V2 alerts persist much longer (mean: 21–23 rows / 5.5h; median: 8–9 rows / 2h; duty cycle: 0.54%–0.67%).
   - The sensitivity analysis tightens V2 thresholds until total clean time in alarm equals V1 M1's 1,185 rows (0.1041% duty cycle). Under this matched temporal footprint:
     - V2 Direction 1 cross-mechanism recall on B drops from $17.31\%$ to **$8.58\%$** (below V1 M1's $15.39\%$).
     - V2 Direction 2 cross-mechanism recall on A drops from $30.60\%$ to **$16.90\%$** (still above V1 M1's $10.16\%$).
- **Verdict:** **INTEGRITY VERIFIED (PASS).**

---

## 5. Issue 4: Factory Concentration & Denominator Audit

### 5.1 Factory Exposure Denominators
In `FACTORY_MONTHS` (`train_and_evaluate_v2.py`, lines 64–74):
- All 33 development factories are assigned canonical telemetry exposure months:
  - 17 factories have full 12.02-month exposure.
  - 16 factories have partial exposure (ranging from 0.11 months for `site_2070` to 11.98 months for `site_1280`).
  - Total exposure denominator: $\sum_{k=1}^{33} m_k = \mathbf{327.61\text{ factory-months}}$.
- Every factory-level rate reported in `v2_clean_false_alarms.csv` and `false_alarm_concentration.csv` uses:
  $$\text{Rate}_k = \frac{\text{Episodes}_k}{m_k}$$
- Zero factories were excluded or dropped.

### 5.2 False-Alarm Concentration Findings
- **V2 Direction 1 (Train A):**
  - Total false alert episodes: 328 across 327.61 months (1.001/mo).
  - Top 3 factories: `site_1280` (122 eps, 10.18/mo), `site_1668` (63 eps, 5.24/mo), `site_1257` (59 eps, 4.91/mo).
  - **Top 3 Share:** $\frac{122 + 63 + 59}{328} = \frac{244}{328} = \mathbf{74.39\%}$.
  - `site_1280` alone accounts for **37.20%** of all false alarms across the entire dev network.
  - 16 of 33 factories produce exactly 0 false alarms.
- **V2 Direction 2 (Train B):**
  - Total false alert episodes: 328.
  - Top 3 factories: `site_1257` (70 eps, 5.82/mo), `site_1668` (38 eps, 3.16/mo), `site_887` (32 eps, 2.66/mo).
  - **Top 3 Share:** $\frac{70 + 38 + 32}{328} = \frac{140}{328} = \mathbf{42.68\%}$.
  - 12 of 33 factories produce 0 false alarms.
- **V1 M1 Fusion Baseline:**
  - Total false alert episodes: 327 across 327.61 months (0.998/mo).
  - Top 3 factories: `site_1376` (38 eps, 3.16/mo), `site_1257` (32 eps, 2.66/mo), `site_1285` (27 eps, 2.25/mo).
  - **Top 3 Share:** $\frac{38 + 32 + 27}{327} = \frac{97}{327} = \mathbf{29.66\%}$.
  - 10 of 33 factories produce 0 false alarms. Max factory rate is 3.16/mo.
- **Verdict:** False alarm aggregation and denominators are mathematically consistent across all 33 facilities. Supervised tree models exhibit severe site-level alarm clustering compared to heuristic baselines.  
**Audit Finding: VERIFIED (PASS).**

---

## 6. Issue 5: Separation of Claims & Scientific Generalization Boundaries

To ensure complete scientific integrity and prevent unwarranted extrapolation, all findings are partitioned into three rigorous categories:

### 6.1 Category A: Statistically Supported Findings
These findings are substantiated by paired hypothesis tests and 10,000-iteration cluster bootstrap confidence intervals grouped by factory:
1. **Direction 2 Superiority on Mechanism A:** V2 trained on Mechanism B achieves $30.60\%$ pooled recall on Mechanism A, statistically significantly outperforming V1 M1 ($10.16\%$, paired diff $+20.43\%$, 95% CI $[+12.99\%, +27.29\%]$), V1 IF alone ($4.69\%$, paired diff $+25.91\%$), and all single checks.
2. **Direction 1 Equivalence to V1 on Mechanism B:** V2 trained on Mechanism A achieves $17.31\%$ pooled recall on Mechanism B vs V1 M1's $15.39\%$ (paired diff $+1.92\%$, 95% CI $[-3.33\%, +6.92\%]$). This difference is **not statistically significant** as the 95% CI spans zero.
3. **Asymmetric Cross-Mechanism Generalization Gap:**
   - Mechanism B models transfer to Mechanism A with no statistically significant loss (pooled gap $+3.32\%$, 95% CI $[-1.13\%, +7.69\%]$).
   - Mechanism A models suffer a statistically significant out-of-mechanism transfer loss on Mechanism B (pooled gap $+10.69\%$, 95% CI $[+6.35\%, +14.98\%]$).
4. **Copy-Paste (T2) Invariance:** Across both mechanisms, T2 copy-paste exhibits essentially zero transfer penalty ($+3.45\%$ on A, $+0.20\%$ on B; both CIs span zero).
5. **Degeneracy at Relaxed Budgets:** At 10.0 alerts/month, Train B collapses into degeneracy ($\tau = 0.01717 < 0.05$; clean duty cycle $57.19\% > 20\%$).

### 6.2 Category B: Descriptive Findings
These findings represent empirical measurements of the development dataset and model outputs:
1. **Duty Cycle Discrepancy:** At the nominal 1.0 alert/month rate, V2 models generate false alert episodes that are 5.2x to 6.4x longer than V1 M1 (duty cycle 0.54%–0.67% vs 0.1041%; median episode length 8–9 rows vs 1 row).
2. **Extreme Site Concentration:** V2 false alarms are concentrated in a few facilities (top 3 sites generate 74.39% in Dir 1), whereas V1 M1 false alarms are substantially more dispersed (top 3 sites generate 29.66%).
3. **Training Data Imbalance:** Positive training rows in Mechanism A are 93.73% dominated by pH and Flow, while BOD, COD, and TSS represent only 1.19%, 2.74%, and 2.35% respectively.
4. **Missing Statutory Limits:** BOD, COD, and TSS series have 41.16% feature missingness due to missing or unparsed consent limits in `consent_limits.csv`.

### 6.3 Category C: Unresolved Claims & Non-Extrapolability Boundaries
These boundaries explicitly define the limits of the experimental evidence:
1. **Simulated Injections $\neq$ Real-World Deliberate Tampering:**  
   > **CRITICAL SCIENTIFIC CAVEAT:** High or moderate recall against mathematically generated synthetic anomalies (e.g. Mechanism A constant freezes, Mechanism B AR(1) limit hugging or spline splices) **MUST NOT be interpreted or claimed as proof of efficacy against real-world deliberate tampering in operational industrial facilities**. Real-world tampering involves complex physical manipulations, logger bypasses, sensor tampering, dilution, and unmodeled factory operating states that are not captured in synthetic mathematical injection engines.
2. **Unseen / Locked Factory Performance Remains Unknown:**  
   Because the 4 locked test factories (`Cipla`, `Glenmark`, `Indoco`, `Zydus`) and directory `Data/Unseen/` remain strictly unread and locked per protocol, the detector's ability to generalize to unseen industrial sites remains **UNVERIFIED**.
3. **Protocol v1 / v1.1 Formal Sign-Off:**  
   The pre-evaluation approval of `PROTOCOL_v1.md` remains **UNVERIFIED** due to untracked git status and draft labeling.

---

## 7. Audit Conclusion & Next Steps

All five reconciliation items have been fully resolved using existing repository evidence. Zero code or protocol changes were made, and no models were rerun.

```
================================================================================
RECONCILIATION SUMMARY:
- Item 1 (Event Count Reconciliation):    PASS (2,694 generated - 141 no-op = 2,553 primary)
- Item 2 (Protocol Status):              UNVERIFIED (Protocol v1 draft status / untracked)
                                         PASS (Protocol v2.0 frozen in git tag 8c98d3d)
- Item 3 (Comparison Integrity):          PASS (Paired events, identical windows & metrics)
- Item 4 (Factory Concentration):         PASS (33 factories, 327.61 fac-mo denominators)
- Item 5 (Conclusions & Claim Limits):   PASS (Rigorous separation of findings & caveats)
================================================================================
```

**STATUS: STAGE 3A RECONCILIATION COMPLETE. STOPPING AND WAITING FOR OWNER APPROVAL BEFORE PROPOSING OR STARTING ANY NEW EXPERIMENT.**
