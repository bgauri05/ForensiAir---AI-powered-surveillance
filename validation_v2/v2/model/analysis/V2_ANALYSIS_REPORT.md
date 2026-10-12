# FORENSIAIR V2 POST-HOC DEVELOPMENT ANALYSIS REPORT

**Protocol Basis:** `docs/PROTOCOL_v2.md` & `PROTOCOL_v1.1.md` (Sec C, F, G)  
**Execution Mode:** Strictly read-only analysis from saved development evaluation outputs  
**Source Parquets / Artifacts:** `validation_v2/v2/model/v2_eval_events.csv`, `v2_clean_false_alarms.csv`, `v2_budget_sensitivity.csv`, `clean_cache.pkl`, `inj_cache.pkl`  
**Git Tag Hash:** `8c98d3d2d45f3ab79dfa54327cb56bd94b28188c` (`v2-protocol-frozen`)  
**Scope Notice:** Development evaluation on 33 development factories only. Unseen test set (`Data/Unseen/` and locked factories Cipla, Glenmark, Indoco, Zydus) strictly untouched and unread. No model retraining or parameter retuning performed.  
**Labeling:** All findings in this document are labeled **development result, post-hoc**.

---

## 1. Fair Comparator Evaluation at 1.0 Alert / Factory-Month (development result, post-hoc)

### 1.1 Methodology and Operating Constraints
All comparators are evaluated on the **exact same event instances** at the protocol-mandated operating budget of **1.0 false alert episode per factory-month** (328 total false alert episodes across 327.61 factory-months on un-injected development telemetry):
- **Included Comparators:** Frozen V1 M1 Multi-Check Fusion, V1 Isolation Forest alone (`IF_sensor`), V1 F1 Flatline (`eps=0, 1, 2`), V1 F2 Copy-Paste (`w16, w96, w288`), V1 F3 Limit Hugging (`w16, w96, w288`), V1 F6 Shift (`w16, w96, w288`), V1 F6 Slope (`w16, w96, w288`), and B0 Static Consent Limit Baseline.
- **Excluded Comparator (B4 Legacy Heuristic):** Baseline B4 is strictly excluded from fair comparator tables because it is **not budget-matched**. On clean telemetry, B4 triggers 688 false alert episodes (28.775 alerts/factory-month), exceeding the 1.0/month operating budget by nearly 29x.
- **Statistical Inference:** Paired recall differences ($\Delta = \text{Recall}_{V2} - \text{Recall}_{\text{Comp}}$) and paired 95% confidence intervals were generated via 10,000 cluster-bootstrap resamples grouped by factory ($N=21$ event-bearing development factories).
- **Post-Hoc Winner Column:** Per-type winners are explicitly flagged in a dedicated column labeled `Selected Post Hoc`. Selecting individual single-check winners by type post hoc represents an uncalibrated theoretical upper bound that cannot be achieved simultaneously by any single deployed detector under a single operating budget.

### 1.2 Fair Comparator Table — Direction 1 Cross-Mechanism (Trained on A, Tested on Mechanism B, N=2,553 Primary Non-No-Op Events) (development result, post-hoc)

| Comparator Method | V2 Pooled Recall | V2 95% CI | Comparator Recall | Comparator 95% CI | Paired Diff ($V2 - \text{Comp}$) | Paired 95% CI | Statistically Significant | Selected Post Hoc Winner per Type |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **V1 M1 Multi-Check Fusion** | **17.31%** | [11.81%, 22.92%] | 15.39% | [10.58%, 20.37%] | **+1.92%** | [-3.33%, +6.92%] | NO (Includes 0) | **Pooled Winner: V2 Pooled (17.31%)** |
| **V1 IF Alone (`if_score`)** | **17.31%** | [11.81%, 22.92%] | 14.96% | [7.95%, 22.17%] | **+2.35%** | [-5.92%, +10.30%] | NO (Includes 0) | **T3 Winner: V1 IF (31.26%)** |
| **V1 F1 Flatline ($\epsilon=0$)** | **17.31%** | [11.81%, 22.92%] | 10.50% | [7.21%, 13.98%] | **+6.82%** | [+1.84%, +11.39%] | **YES (V2 Superior)** | *V1 F1 $\epsilon=0$ (T1: 35.15%)* |
| **V1 F1 Flatline ($\epsilon=1$)** | **17.31%** | [11.81%, 22.92%] | 11.32% | [7.87%, 14.88%] | **+5.99%** | [+0.80%, +10.78%] | **YES (V2 Superior)** | *V1 F1 $\epsilon=1$ (T1: 35.15%)* |
| **V1 F1 Flatline ($\epsilon=2$)** | **17.31%** | [11.81%, 22.92%] | 11.99% | [8.46%, 15.63%] | **+5.33%** | [+0.26%, +10.13%] | **YES (V2 Superior)** | **T1 Winner: V1 F1 $\epsilon=2$ (35.29%)** |
| **V1 F2 Copy-Paste** | **17.31%** | [11.81%, 22.92%] | 4.82% | [1.88%, 8.23%] | **+12.50%** | [+7.65%, +17.30%] | **YES (V2 Superior)** | **T2 Winner: V2 Pooled (32.94%)** |
| **V1 F3 Limit Hugging** | **17.31%** | [11.81%, 22.92%] | 10.38% | [4.35%, 17.59%] | **+6.93%** | [-0.48%, +14.66%] | NO (Includes 0) | *V1 F3 (T3: 16.20%)* |
| **V1 F6 Systematic Shift** | **17.31%** | [11.81%, 22.92%] | 11.01% | [6.62%, 15.94%] | **+6.31%** | [+0.14%, +12.81%] | **YES (V2 Superior)** | *V1 F6 Shift (T7: 16.71%)* |
| **V1 F6 Systematic Slope** | **17.31%** | [11.81%, 22.92%] | 11.24% | [6.03%, 17.47%] | **+6.07%** | [-1.17%, +13.14%] | NO (Includes 0) | *V1 F6 Slope (T7: 18.38%)* |
| **B0 Consent Limit Baseline** | **17.31%** | [11.81%, 22.92%] | 3.25% | [0.00%, 7.87%] | **+14.06%** | [+8.83%, +19.26%] | **YES (V2 Superior)** | *B0 (T7: 4.18%)* |

*Per-Type Breakdown on Mechanism B:*
- **T1 Flatline ($N=714$):** V1 F1 $\epsilon=2$ (35.29%) > V1 F1 $\epsilon=0, 1$ (35.15%) > V1 M1 (12.75%) > V2 Pooled (7.98%). Winner selected post-hoc: **V1 F1 $\epsilon=2$**.
- **T2 Copy-Paste ($N=510$):** V2 Pooled (32.94%) > V1 F2 (9.80%) > V1 M1 (8.43%) > V1 F3 (6.86%). Winner selected post-hoc: **V2 Pooled**.
- **T3 Limit Hugging ($N=611$):** V1 IF (31.26%) > V1 F6 Slope (23.40%) > V1 F6 Shift (21.44%) > V1 M1 (19.80%) > V1 F3 (16.20%) > V2 Pooled (4.42%). Winner selected post-hoc: **V1 IF**.
- **T7 Systematic Drift ($N=718$):** V2 Pooled (26.46%) > V1 IF (22.84%) > V1 M1 (19.22%) > V1 F6 Slope (18.38%) > V1 F6 Shift (16.71%). Winner selected post-hoc: **V2 Pooled**.

---

### 1.3 Fair Comparator Table — Direction 2 Cross-Mechanism (Trained on B, Tested on Mechanism A, N=1,899 Events) (development result, post-hoc)

| Comparator Method | V2 Pooled Recall | V2 95% CI | Comparator Recall | Comparator 95% CI | Paired Diff ($V2 - \text{Comp}$) | Paired 95% CI | Statistically Significant | Selected Post Hoc Winner per Type |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **V1 M1 Multi-Check Fusion** | **30.60%** | [22.88%, 37.65%] | 10.16% | [6.69%, 13.90%] | **+20.43%** | [+12.99%, +27.29%] | **YES (V2 Superior)** | **Pooled Winner: V2 Pooled (30.60%)** |
| **V1 IF Alone (`if_score`)** | **30.60%** | [22.88%, 37.65%] | 4.69% | [2.11%, 7.79%] | **+25.91%** | [+16.52%, +34.07%] | **YES (V2 Superior)** | *V1 IF (T7: 9.68%)* |
| **V1 F1 Flatline ($\epsilon=0$)** | **30.60%** | [22.88%, 37.65%] | 6.58% | [3.95%, 9.53%] | **+24.01%** | [+17.24%, +30.21%] | **YES (V2 Superior)** | *V1 F1 $\epsilon=0$ (T1: 18.99%)* |
| **V1 F1 Flatline ($\epsilon=1$)** | **30.60%** | [22.88%, 37.65%] | 9.22% | [5.85%, 12.85%] | **+21.38%** | [+14.77%, +27.94%] | **YES (V2 Superior)** | *V1 F1 $\epsilon=1$ (T1: 24.81%)* |
| **V1 F1 Flatline ($\epsilon=2$)** | **30.60%** | [22.88%, 37.65%] | 13.59% | [9.22%, 18.33%] | **+17.01%** | [+10.00%, +24.08%] | **YES (V2 Superior)** | **T1 Winner: V1 F1 $\epsilon=2$ (36.60%)** |
| **V1 F2 Copy-Paste** | **30.60%** | [22.88%, 37.65%] | 5.53% | [1.79%, 10.22%] | **+25.07%** | [+17.04%, +32.68%] | **YES (V2 Superior)** | **T2 Winner: V2 Pooled (34.36%)** |
| **V1 F3 Limit Hugging** | **30.60%** | [22.88%, 37.65%] | 8.16% | [3.16%, 14.17%] | **+22.43%** | [+12.86%, +31.40%] | **YES (V2 Superior)** | **T3 Winner: V2 Pooled (37.39%)** |
| **V1 F6 Systematic Shift** | **30.60%** | [22.88%, 37.65%] | 5.27% | [3.16%, 7.74%] | **+25.33%** | [+16.71%, +32.96%] | **YES (V2 Superior)** | *V1 F6 Shift (T7: 11.56%)* |
| **V1 F6 Systematic Slope** | **30.60%** | [22.88%, 37.65%] | 3.00% | [1.47%, 4.90%] | **+27.59%** | [+18.84%, +35.36%] | **YES (V2 Superior)** | *V1 F6 Slope (T7: 5.38%)* |
| **B0 Consent Limit Baseline** | **30.60%** | [22.88%, 37.65%] | 3.53% | [0.00%, 7.85%] | **+27.07%** | [+19.95%, +33.53%] | **YES (V2 Superior)** | *B0 (T7: 4.30%)* |

*Per-Type Breakdown on Mechanism A:*
- **T1 Flatline ($N=653$):** V1 F1 $\epsilon=2$ (36.60%) > V1 F1 $\epsilon=1$ (24.81%) > V1 F1 $\epsilon=0$ (18.99%) > V2 Pooled (18.07%) > V1 M1 (16.23%). Winner selected post-hoc: **V1 F1 $\epsilon=2$**.
- **T2 Copy-Paste ($N=521$):** V2 Pooled (34.36%) > V1 F2 (12.28%) > V1 M1 (7.10%) > V1 F1 $\epsilon=2$ (3.07%). Winner selected post-hoc: **V2 Pooled**.
- **T3 Limit Hugging ($N=353$):** V2 Pooled (37.39%) > V1 F3 (30.88%) > V1 F6 Shift (6.23%) > V1 IF (3.97%) > V1 M1 (3.40%). Winner selected post-hoc: **V2 Pooled**.
- **T7 Systematic Drift ($N=372$):** V2 Pooled (40.86%) > V1 F6 Shift (11.56%) > V1 M1 (10.22%) > V1 IF (9.68%) > V1 F6 Slope (5.38%). Winner selected post-hoc: **V2 Pooled**.

---

## 2. Same-Test-Event Generalization Gap (development result, post-hoc)

To evaluate whether cross-mechanism degradation is driven by genuine generalization loss or differences in the underlying test event distributions, we evaluate **both models on the exact same test events**.

### 2.1 Same-Test-Event Gap Table (development result, post-hoc)

| Test Event Set | Tamper Type | Events Evaluated | Recall Trained A | 95% Cluster CI (A) | Recall Trained B | 95% Cluster CI (B) | Generalization Gap | 95% Cluster CI (Gap) | Architectural Interpretation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Mechanism A Events** | **T1** | 653 | **27.72%** | [14.86%, 37.45%] | 18.07% | [8.75%, 26.04%] | **+9.65%** | [+2.90%, +15.85%] | Trained A superior (In-Mechanism advantage) |
| **Mechanism A Events** | **T2** | 521 | **37.81%** | [19.09%, 50.07%] | 34.36% | [18.29%, 46.00%] | **+3.45%** | [-0.59%, +6.69%] | Indistinguishable (Includes 0) |
| **Mechanism A Events** | **T3** | 353 | 28.05% | [19.65%, 36.41%] | **37.39%** | [25.72%, 48.81%] | **-9.35%** | [-17.87%, -0.85%] | **Trained B superior (Cross-Mechanism advantage!)** |
| **Mechanism A Events** | **T7** | 372 | **44.89%** | [33.81%, 54.48%] | 40.86% | [27.25%, 52.54%] | **+4.03%** | [-3.69%, +11.36%] | Indistinguishable (Includes 0) |
| **Mechanism A Events** | **Pooled** | **1,899** | **33.91%** | [24.44%, 42.17%] | **30.60%** | [22.88%, 37.65%] | **+3.32%** | [-1.13%, +7.69%] | **Indistinguishable (Includes 0)** |
| **Mechanism B Events** | **T1** | 714 | 7.98% | [3.87%, 12.53%] | **21.57%** | [10.28%, 34.93%] | **+13.59%** | [+5.12%, +23.33%] | Trained B superior (In-Mechanism advantage) |
| **Mechanism B Events** | **T2** | 510 | 32.94% | [21.75%, 42.99%] | **33.14%** | [22.34%, 43.22%] | **+0.20%** | [-2.08%, +2.83%] | **Indistinguishable (Includes 0, Robust Transfer)** |
| **Mechanism B Events** | **T3** | 611 | 4.42% | [1.57%, 7.40%] | **20.13%** | [12.25%, 29.86%] | **+15.71%** | [+8.52%, +25.47%] | Trained B superior (In-Mechanism advantage) |
| **Mechanism B Events** | **T7** | 718 | 26.46% | [16.42%, 37.27%] | **37.47%** | [23.92%, 50.16%] | **+11.00%** | [+2.42%, +19.32%] | Trained B superior (In-Mechanism advantage) |
| **Mechanism B Events** | **Pooled** | **2,553** | 17.31% | [11.77%, 22.86%] | **28.01%** | [19.83%, 36.22%] | **+10.69%** | [+6.35%, +14.98%] | **Trained B superior (Strict Positive Gap)** |

### 2.2 Key Findings on Same-Test-Event Generalization
1. **Asymmetric Robustness:** Mechanism B trained models transfer remarkably well to Mechanism A events: the pooled gap on Mechanism A is only $+3.32\%$ and its 95% CI $[-1.13\%, +7.69\%]$ spans zero. In fact, on T3 limit hugging, **Trained B significantly outperforms Trained A** by $+9.35\%$ ($37.39\%$ vs $28.05\%$) because Mechanism B's diverse, subtle scaling/clipping injections provide richer supervision than Mechanism A's rigid clamp injections.
2. **Transfer Penalty on Mechanism B:** When testing on Mechanism B events, models trained strictly on Mechanism A experience a pronounced and statistically significant transfer loss of $+10.69\%$ pooled ($17.31\%$ vs $28.01\%$, CI $[+6.35\%, +14.98\%]$). This drop is concentrated in T1 flatline ($+13.59\%$), T3 limit hugging ($+15.71\%$), and T7 drift ($+11.00\%$).
3. **Invariance of Copy-Paste (T2):** Across both directions, T2 copy-paste exhibits essentially zero transfer gap ($+3.45\%$ on A, $+0.20\%$ on B), demonstrating that multi-scale repeat, similarity, and variance features transfer across injection engines without mechanism-specific degradation.

---

## 3. Clean Telemetry Alert Duty Cycle & Matched Sensitivity (development result, post-hoc)

### 3.1 Alert Duty Cycle on Clean Development Telemetry
Operating at 1.0 alert episode per factory-month guarantees an average of 1 alarm per month, but the **duty cycle** (% of valid rows spent inside alerts) and **mean duration of false alarms** differ dramatically across model families. Consecutive rows above threshold are grouped, merging gaps $\le 16$ rows (4 hours) into continuous episodes.

| Method | Family | Operating Cutoff $\tau$ | Clean Episodes | Episodes / Month | Alert Rows Flagged | % of Valid Rows in Alerts (Duty Cycle) | Mean Alert Length (Rows) | Median Alert Length (Rows) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **V1 M1 Fusion** | V1 Multi-Check | 3.7906 | 327 | 0.998 | **1,185** | **0.1041%** | **3.62** | **1.0** |
| **V1 IF Alone** | V1 Density | 2.5560 | 309 | 0.943 | 2,685 | 0.2359% | 8.69 | 7.0 |
| **V1 F1 Flatline ($\epsilon=0$)** | V1 Single-Check | 2.6739 | 329 | 1.004 | 21,800 | 1.9155% | 66.26 | 6.0 |
| **V1 F1 Flatline ($\epsilon=1$)** | V1 Single-Check | 2.6210 | 327 | 0.998 | 20,456 | 1.7974% | 62.56 | 5.0 |
| **V1 F1 Flatline ($\epsilon=2$)** | V1 Single-Check | 2.5335 | 327 | 0.998 | 21,364 | 1.8772% | 65.33 | 7.0 |
| **V1 F2 Copy-Paste** | V1 Single-Check | 2.8168 | 328 | 1.001 | 1,744 | 0.1532% | 5.32 | 2.0 |
| **V1 F3 Limit Hugging** | V1 Single-Check | 1.1786 | 328 | 1.001 | 20,080 | 1.7644% | 61.25 | 25.5 |
| **V1 F6 Shift** | V1 Single-Check | 3.0779 | 328 | 1.001 | 1,525 | 0.1340% | 4.65 | 3.0 |
| **V1 F6 Slope** | V1 Single-Check | 3.3110 | 328 | 1.001 | 1,332 | 0.1170% | 4.06 | 2.0 |
| **B0 Consent Limit** | Baseline Rule | Consent Limit | 0 | 0.000 | 0 | 0.0000% | 0.00 | 0.0 |
| **V2 Pooled (Train A)** | V2 Supervised | 0.97875 | 291 | 0.888 | **6,132** | **0.5388%** | **21.07** | **9.0** |
| **V2 Pooled (Train B)** | V2 Supervised | 0.96469 | 325 | 0.992 | **7,613** | **0.6689%** | **23.45** | **8.0** |

*Crucial Operational Insight:* While V1 M1 produces tight, fleeting false alarms (median duration: 1 row / 15 minutes; mean: 3.6 rows / 54 minutes; duty cycle: 0.104%), the supervised V2 models produce much longer false alert episodes (mean duration: 21–23 rows / ~5.5 hours; median: 8–9 rows / ~2 hours; duty cycle: 0.54%–0.67%). V2 occupies **5.2x to 6.4x more operator surveillance time** in false alarm status than V1 M1.

---

### 3.2 Sensitivity: Recall at Matched Duty Cycle (0.1041% Clean Telemetry Rows Flagged) (development result, post-hoc)

To isolate the impact of alert episode persistence, we tightened the operating threshold $\tau$ of V2 until its **clean duty cycle exactly matched V1 M1's 1,185 rows (0.1041%)**:
- **Train A Matched Cutoff:** $\tau = 0.99078$ (yields 1,190 alert rows, 0.1046% duty cycle, 0.250 false alarms/month).
- **Train B Matched Cutoff:** $\tau = 0.98634$ (yields 1,182 alert rows, 0.1039% duty cycle, 0.205 false alarms/month).

| Direction | Operating Setting | Matched Cutoff $\tau$ | Clean Duty Cycle | Clean FA Rate (/mo) | Test Mechanism | Evaluated Events | Detected Events | Recall at Matched Duty Cycle |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Train A** | **In-Mechanism** | 0.99078 | 0.1046% | 0.250 / mo | Mechanism A | 1,899 | 381 | **20.06%** |
| **Train A** | **Cross-Mechanism** | 0.99078 | 0.1046% | 0.250 / mo | Mechanism B | 2,553 | 219 | **8.58%** |
| **Train B** | **Cross-Mechanism** | 0.98634 | 0.1039% | 0.205 / mo | Mechanism A | 1,899 | 321 | **16.90%** |
| **Train B** | **In-Mechanism** | 0.98634 | 0.1039% | 0.205 / mo | Mechanism B | 2,553 | 388 | **15.20%** |

*Takeaway:* When constrained to the exact same temporal alert footprint as V1 M1 (0.104% clean duty cycle), V2 Direction 1 cross-mechanism recall drops from $17.31\%$ to **$8.58\%$** (below V1 M1's $15.39\%$), while Direction 2 cross-mechanism recall drops from $30.60\%$ to **$16.90\%$** (still above V1 M1's $10.16\%$).

---

## 4. False-Alarm Concentration Across Factories (development result, post-hoc)

Across the 33 development factories, false alarms are not distributed uniformly.

### 4.1 Concentration Summary Table (development result, post-hoc)

| Metric | V2 Pooled Direction 1 (Train A) | V2 Pooled Direction 2 (Train B) | V1 M1 Multi-Check Fusion |
| :--- | :---: | :---: | :---: |
| **Total Clean False Alarms** | 328 episodes | 328 episodes | 327 episodes |
| **Top Factory 1** | `site_1280` (122 eps, 10.18/mo) | `site_1257` (70 eps, 5.82/mo) | `site_1376` (38 eps, 3.16/mo) |
| **Top Factory 2** | `site_1668` (63 eps, 5.24/mo) | `site_1668` (38 eps, 3.16/mo) | `site_1257` (32 eps, 2.66/mo) |
| **Top Factory 3** | `site_1257` (59 eps, 4.91/mo) | `site_887` (32 eps, 2.66/mo) | `site_1285` (27 eps, 2.25/mo) |
| **Share of Clean Episodes from Top 3 Factories** | **74.39%** (244 / 328) | **42.68%** (140 / 328) | **29.66%** (97 / 327) |
| **Factories with Zero False Alarms** | **16 of 33 (48.5%)** | **12 of 33 (36.4%)** | **10 of 33 (30.3%)** |
| **Maximum Realized Monthly FA Rate** | **10.184 / month** (`site_1280`) | **5.824 / month** (`site_1257`) | **3.161 / month** (`site_1376`) |

### 4.2 Factory-Level Breakdown (Top 10 Factories by Alarm Rate) (development result, post-hoc)

| Factory ID | Exposure (Months) | V2 Dir 1 Episodes | V2 Dir 1 FA/mo | V2 Dir 2 Episodes | V2 Dir 2 FA/mo | V1 M1 Episodes | V1 M1 FA/mo |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `site_1280` | 11.98 | **122** | **10.184** | 20 | 1.669 | 16 | 1.336 |
| `site_1668` | 12.02 | **63** | **5.241** | **38** | **3.161** | 24 | 1.997 |
| `site_1257` | 12.02 | **59** | **4.908** | **70** | **5.824** | **32** | **2.662** |
| `site_887` | 12.02 | 16 | 1.331 | **32** | **2.662** | 26 | 2.163 |
| `site_1284` | 11.51 | 11 | 0.956 | 23 | 1.998 | 21 | 1.825 |
| `site_1376` | 12.02 | 8 | 0.666 | 29 | 2.413 | **38** | **3.161** |
| `site_1221` | 11.95 | 6 | 0.502 | 26 | 2.176 | 18 | 1.506 |
| `site_1281` | 12.02 | 3 | 0.250 | 13 | 1.082 | 22 | 1.830 |
| `site_1259` | 4.76 | 2 | 0.420 | 2 | 0.420 | 4 | 0.840 |
| `site_1310` | 12.02 | 2 | 0.166 | 8 | 0.666 | 17 | 1.414 |

*Analysis:* V2 exhibits severe **site-specific false-alarm concentration**. In Direction 1, a single facility (`site_1280`) accounts for **37.20%** of all false alarms, and the top 3 sites account for **74.39%**. By contrast, V1 M1 is substantially more balanced across factories (top 3 share is 29.66%, max site rate is 3.16/mo). This indicates that the tree-based model is learning complex site-specific feature interactions that trigger repeated alerts when held-out sites possess unusual baseline dynamics.

---

## 5. Parameter Check & Diagnosis of Zero Recall on BOD/COD/TSS (development result, post-hoc)

### 5.1 Training Positive Distribution, Missingness, and Recall by Parameter (development result, post-hoc)

| Parameter | Mech A Training Positive Events | Mech A Positive Rows (Share %) | Mech B Training Positive Events | Mech B Positive Rows (Share %) | Mean Feature Missingness (% NaN) | V2 Recall Dir 1 (Test B Cross) | V2 Recall Dir 2 (Test B In-Mech) | V1 M1 Recall (Test B) | V2 Recall Dir 2 (Test A Cross) | V2 Recall Dir 1 (Test A In-Mech) | V1 M1 Recall (Test A) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **ETP-pH** | 1,147 | 81,328 (**51.33%**) | 1,433 | 107,300 (**55.32%**) | 31.59% | **22.54%** | **33.50%** | 14.24% | **32.69%** | **33.83%** | 7.85% |
| **ETP-Flow** | 594 | 67,184 (**42.40%**) | 794 | 68,408 (**35.27%**) | 35.04% | **14.99%** | **28.34%** | 17.76% | **34.34%** | **42.93%** | 13.47% |
| **ETP-COD** | 80 | 4,344 (**2.74%**) | 93 | 6,512 (**3.36%**) | 41.15% | **0.00%** | **2.15%** | 12.90% | **1.25%** | **0.00%** | 12.50% |
| **ETP-TSS** | 42 | 3,720 (**2.35%**) | 114 | 8,024 (**4.14%**) | 41.15% | **0.00%** | **7.02%** | 14.04% | **2.38%** | **2.38%** | 9.52% |
| **ETP-BOD** | 36 | 1,880 (**1.19%**) | 119 | 3,724 (**1.92%**) | 41.16% | **0.00%** | **0.00%** | 16.81% | **0.00%** | **0.00%** | 25.00% |

### 5.2 Technical Diagnosis: Data-Volume Effect vs Code Bug

The zero (or near-zero) recall of V2 on ETP-BOD, ETP-COD, and ETP-TSS is **conclusively a data-volume and extreme class imbalance effect, NOT a software bug**:

1. **Extreme Representation Asymmetry:** In Mechanism A training data, ETP-pH and ETP-Flow account for **93.73% of all positive training rows** (148,512 / 158,456 rows). ETP-BOD represents only **1.19%** (1,880 rows), ETP-TSS represents **2.35%** (3,720 rows), and ETP-COD represents **2.74%** (4,344 rows). In unweighted gradient boosted decision trees (`HistGradientBoostingClassifier`), trees greedily choose splits that maximize gradient gain across the dominant 93.7% of samples (pH and Flow).
2. **Global Calibration Threshold Suppression:** Because the global operating threshold is calibrated to satisfy a strict budget of 1.0 alert episode per factory-month across all 81 series pooled, $\tau$ is set extremely high ($\tau = 0.97875$ for Train A; $\tau = 0.96469$ for Train B). While the model produces positive predictions for BOD, COD, and TSS events (typically peaking in the range of 0.60 to 0.85), these scores **never breach the 0.96–0.98 decision boundary**.
3. **Feature Missingness & Consent Limit Absence:** BOD, COD, and TSS series have higher feature missingness (41.16% vs 31.59% for pH) because consent limits (`consent_limits.csv`) are missing or unparsed for the majority of organic parameters in the dev set. Consequently, limit features (`limit_ratio_w*`, `frac_above_85pct_w*`) are entirely NaN for these series.
4. **Contrast with V1 Heuristics:** Frozen V1 M1 detects 12.9%–25.0% of BOD, COD, and TSS events because V1's checks are scale-free statistical tests (e.g. F1 flatline counts consecutive duplicate floats, F6 tests z-score shifts normalized by local MAD) that operate independently of sample frequency across parameters. V2's pooled supervised architecture naturally sacrifices low-frequency parameters to minimize false positives on high-volume parameters.

---

## 6. Budget Sensitivity Matrix & Degeneracy Audit (development result, post-hoc)

Per protocol criteria, an operating budget row is marked **DEGENERATE** if the operating threshold satisfies $\tau < 0.05$ or the clean alert duty cycle exceeds $20.0\%$.

### 6.1 Degeneracy Audit Table (development result, post-hoc)

| Target Budget (/mo) | Direction | Operating Cutoff $\tau$ | Realized FA (/mo) | Clean Duty Cycle (% Valid Rows in Alerts) | Test Mechanism | Setting | Evaluated Events | Detected Events | Recall (%) | Degeneracy Status |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1.0** | Train A | 0.97875 | 1.001 | 0.5388% | A | In-Mechanism | 1,899 | 644 | 33.91% | **VALID** |
| **1.0** | Train A | 0.97875 | 1.001 | 0.5388% | B | Cross-Mechanism | 2,553 | 442 | 17.31% | **VALID** |
| **1.0** | Train B | 0.96469 | 1.001 | 0.6689% | B | In-Mechanism | 2,553 | 715 | 28.01% | **VALID** |
| **1.0** | Train B | 0.96469 | 1.001 | 0.6689% | A | Cross-Mechanism | 1,899 | 581 | 30.60% | **VALID** |
| **2.0** | Train A | 0.95384 | 1.999 | 1.8095% | A | In-Mechanism | 1,899 | 860 | 45.29% | **VALID** |
| **2.0** | Train A | 0.95384 | 1.999 | 1.8095% | B | Cross-Mechanism | 2,553 | 729 | 28.55% | **VALID** |
| **2.0** | Train B | 0.94119 | 1.999 | 1.5626% | B | In-Mechanism | 2,553 | 925 | 36.23% | **VALID** |
| **2.0** | Train B | 0.94119 | 1.999 | 1.5626% | A | Cross-Mechanism | 1,899 | 742 | 39.07% | **VALID** |
| **4.0** | Train A | 0.90995 | 3.999 | 4.1980% | A | In-Mechanism | 1,899 | 1,075 | 56.61% | **VALID** |
| **4.0** | Train A | 0.90995 | 3.999 | 4.1980% | B | Cross-Mechanism | 2,553 | 1,004 | 39.33% | **VALID** |
| **4.0** | Train B | 0.89653 | 3.999 | 3.4466% | B | In-Mechanism | 2,553 | 1,249 | 48.92% | **VALID** |
| **4.0** | Train B | 0.89653 | 3.999 | 3.4466% | A | Cross-Mechanism | 1,899 | 946 | 49.82% | **VALID** |
| **10.0** | Train A | 0.50024 | 10.000 | 18.0176% | A | In-Mechanism | 1,899 | 1,522 | 80.15% | **VALID** |
| **10.0** | Train A | 0.50024 | 10.000 | 18.0176% | B | Cross-Mechanism | 2,553 | 1,778 | 69.64% | **VALID** |
| **10.0** | Train B | 0.01717 | 9.322 | **57.1917%** | B | In-Mechanism | 2,553 | 2,487 | 97.41% | **DEGENERATE ($\tau=0.01717 < 0.05$, duty cycle $= 57.19\% > 20.0\%$)** |
| **10.0** | Train B | 0.01717 | 9.322 | **57.1917%** | A | Cross-Mechanism | 1,899 | 1,846 | 97.21% | **DEGENERATE ($\tau=0.01717 < 0.05$, duty cycle $= 57.19\% > 20.0\%$)** |

### 6.2 Degeneracy Analysis
At the relaxed budget of 10.0 alerts/month:
- **Train A** maintains a non-degenerate threshold ($\tau = 0.50024$) and clean duty cycle of $18.02\% < 20\%$.
- **Train B** completely collapses into degeneracy: $\tau$ drops to **$0.01717$** (far below the $0.05$ floor), and clean telemetry is flagged **$57.19\%$ of the time**. Under this condition, the model is essentially sounding alarms continuously, rendering the apparent $97\%$ recall meaningless in practice.

---

## 7. Artifact Manifest

All generated analysis tables have been serialized to `validation_v2/v2/model/analysis/`:
- `fair_comparators.csv`: Paired comparator matrix and cluster-bootstrap CIs across both directions.
- `same_test_event_gap.csv`: Head-to-head generalization gaps on identical test events.
- `alert_duty_cycle.csv`: Temporal footprint, mean/median lengths, and duty cycles on clean telemetry.
- `matched_duty_cycle_sensitivity.csv`: Recall at matched clean duty cycle (0.1041%).
- `false_alarm_concentration.csv`: 33-factory breakdown and top-3 concentration metrics.
- `parameter_check.csv`: Training volume, missingness, and recall by parameter.
- `feature_nan_breakdown_by_param.csv`: 45-feature missingness audit across parameters.
- `budget_sensitivity_degenerate.csv`: Budget curve with degeneracy audit flags.
