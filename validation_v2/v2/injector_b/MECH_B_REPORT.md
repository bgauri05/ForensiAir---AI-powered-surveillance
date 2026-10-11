# FORENSIAIR MECHANISM B INJECTOR REPORT (V2 STAGE 1)

**Specification:** `docs/PROTOCOL_v2.md` & `PROTOCOL_v1.1 Section C` (Frozen Eligibility)  
**Scope:** Development Set Injections (Seeds 301–305, Dev Telemetry Only)  
**Targeted Tamper Types:** T1, T2, T3, T7 (Subtle / Evasive Mechanism B Variants)  
**Branch:** `v2-dev` | **Output Manifest:** [`labels_b.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/v2/injector_b/labels_b.csv)

---

## 1. Events by Type $\times$ Variant $\times$ Severity $\times$ Duration

Total injected events: **2,698 events** across 5 seeds (301: 540, 302: 546, 303: 534, 304: 538, 305: 540).

### Table 1.1: Event Distribution by Type, Variant, and Severity

| Type | Variant Identifier | Subtle | Moderate | Obvious | Total Events | Share (%) |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **T1** | `T1-B-freeze` | 282 | 223 | 261 | **766** | 28.39% |
| **T2** | `T2-B-scaled` | 67 | 101 | 100 | **268** | 9.93% |
| **T2** | `T2-B-splice` | 54 | 94 | 94 | **242** | 8.97% |
| **T3** | `T3-B-ar1` | 101 | 104 | 103 | **308** | 11.42% |
| **T3** | `T3-B-pull` | 118 | 74 | 110 | **302** | 11.19% |
| **T7** | `T7-B-step` | 154 | 128 | 125 | **407** | 15.09% |
| **T7** | `T7-B-tri` | 142 | 113 | 150 | **405** | 15.01% |
| **Total** | *All 7 Variants* | **918 (34.0%)** | **837 (31.0%)** | **943 (35.0%)** | **2,698** | **100.00%** |

*Note on Alternation:* Within T2, variants alternate 268 vs 242; within T3, 308 vs 302; within T7, 407 vs 405.

### Table 1.2: Event Distribution by Duration Window

| Type | Variant Identifier | 4 rows (1h) | 16 rows (4h) | 48 rows (12h) | 96 rows (24h) | 288 rows (72h) | 672 rows (7d) | Total |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **T1** | `T1-B-freeze` | 327 | 164 | 95 | 101 | 54 | 25 | **766** |
| **T2** | `T2-B-scaled` | 86 | 51 | 56 | 33 | 28 | 14 | **268** |
| **T2** | `T2-B-splice` | 56 | 34 | 83 | 28 | 29 | 12 | **242** |
| **T3** | `T3-B-ar1` | 137 | 68 | 39 | 39 | 19 | 6 | **308** |
| **T3** | `T3-B-pull` | 136 | 68 | 45 | 37 | 11 | 5 | **302** |
| **T7** | `T7-B-step` | 125 | 93 | 65 | 69 | 41 | 14 | **407** |
| **T7** | `T7-B-tri` | 108 | 103 | 85 | 45 | 42 | 22 | **405** |
| **Total** | *All Durations* | **975 (36.1%)** | **581 (21.5%)** | **468 (17.3%)** | **352 (13.0%)** | **224 (8.3%)** | **98 (3.6%)** | **2,698** |

---

## 2. Factory Injection Counts and Shortfall Accounting

Out of 33 dev factories, **20 factories** had continuous eligible series capable of hosting non-overlapping events with 48h spacing. 13 factories achieved the maximum quota of 30 events per seed (150 total events across seeds 301–305).

| factory_id | Seed 301 | Seed 302 | Seed 303 | Seed 304 | Seed 305 | Total Events | Status / Shortfall Notes |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| `site_1131` | 1 | 7 | 7 | 3 | 7 | 25 | Spacing shortfall (Flow sensor only, data gaps) |
| `site_1200` | 27 | 26 | 26 | 27 | 26 | 132 | Spacing shortfall (Flow sensor only) |
| `site_1221` | 30 | 30 | 30 | 30 | 30 | 150 | Full quota (Flow + pH) |
| `site_1232` | 30 | 30 | 30 | 30 | 30 | 150 | Full quota (pH) |
| `site_1247` | 5 | 5 | 5 | 5 | 5 | 25 | Spacing shortfall (Flow sensor only) |
| `site_1257` | 30 | 30 | 30 | 30 | 30 | 150 | Full quota (Flow + pH) |
| `site_1264` | 30 | 30 | 30 | 30 | 30 | 150 | Full quota (Flow + pH) |
| `site_1280` | 30 | 30 | 30 | 30 | 30 | 150 | Full quota (Flow) |
| `site_1284` | 30 | 30 | 30 | 30 | 30 | 150 | Full quota (Flow + pH) |
| `site_1285` | 30 | 30 | 30 | 30 | 30 | 150 | Full quota (Flow + pH) |
| `site_1310` | 30 | 30 | 30 | 30 | 30 | 150 | Full quota (Flow) |
| `site_1321` | 30 | 30 | 30 | 30 | 30 | 150 | Full quota (BOD, COD, TSS, Flow, pH) |
| `site_1369` | 18 | 18 | 18 | 19 | 15 | 88 | Spacing shortfall (Multi-parameter) |
| `site_1376` | 30 | 30 | 30 | 30 | 30 | 150 | Full quota (Multi-parameter) |
| `site_1561` | 30 | 30 | 30 | 30 | 30 | 150 | Full quota (pH) |
| `site_1668` | 30 | 30 | 30 | 30 | 30 | 150 | Full quota (Multi-parameter) |
| `site_1756` | 18 | 20 | 21 | 21 | 21 | 101 | Spacing shortfall (Multi-parameter) |
| `site_1787` | 30 | 30 | 30 | 30 | 30 | 150 | Full quota (Flow) |
| `site_1799` | 30 | 30 | 25 | 30 | 26 | 141 | Spacing shortfall (Multi-parameter) |
| `site_1905` | 21 | 20 | 12 | 13 | 20 | 86 | Spacing shortfall (Flow sensor only) |
| `site_887` | 30 | 30 | 30 | 30 | 30 | 150 | Full quota (Multi-parameter) |
| **12 Zero-Event Sites** | 0 | 0 | 0 | 0 | 0 | 0 | Ineligible series (insufficient distinct values / >50% missing) |

*12 Ineligible Sites:* `site_1138`, `site_1167`, `site_1203`, `site_1256`, `site_1259`, `site_1281`, `site_1569`, `site_1581`, `site_1789`, `site_1909`, `site_2070`, `site_982`.

---

## 3. Injected Share per Series-Seed (Stratification Bins)

Across all 200 evaluated `(factory, parameter, seed)` combinations in the generated parquets:
- **Mean Injected Share:** **3.81%** of present telemetry rows
- **Median Injected Share:** **0.96%**
- **Min / Max Injected Share:** **0.00% / 20.92%**

| Injected Share Bin | Definition | Series-Seeds Count | Share of Total (%) |
|:---|:---|:---:|:---:|
| **Low Contamination** | $\le 2.0\%$ injected rows | **119** | **59.5%** |
| **Moderate Contamination** | $2.0\% - 10.0\%$ injected rows | **50** | **25.0%** |
| **High Contamination** | $> 10.0\%$ injected rows | **31** | **15.5%** |

---

## 4. No-Op Event Auditing (>50% Rows Identical)

A "no-op" event is defined as an injection where $>50\%$ of rows in the event window match `value_orig` exactly. Across all 2,698 events:
- **Overall Mean Differing Row Share:** **89.82%** of rows differ from original telemetry.
- **Overall No-Op Rate:** **144 / 2,698 events (5.34%)**.

| Variant Identifier | Total Events Placed | No-Op Events (>50% Identical) | No-Op Rate (%) | Rationale / Primary Cause |
|:---|:---:|:---:|:---:|:---|
| `T1-B-freeze` | 766 | 52 | 6.79% | Short 4-row windows where baseline was already at median |
| `T2-B-scaled` | 268 | 5 | 1.87% | Obvious scaled replay on low-variance donor chunks |
| `T2-B-splice` | 242 | 4 | 1.65% | 4-row spliced segments matching local baseline |
| `T3-B-ar1` | 308 | 0 | **0.00%** | Extreme limit-hugging level shifts all rows away from baseline |
| `T3-B-pull` | 302 | 0 | **0.00%** | High compression shifts all rows toward 95% of limit |
| `T7-B-step` | 407 | 37 | 9.09% | Low-integer readings rounding to identical resolution steps |
| `T7-B-tri` | 405 | 46 | 11.36% | Symmetric ramp endpoints at $t=0, D-1$ naturally equal baseline |

---

## 5. Direct Verification of 3 Numbers from Saved Artifacts

Directly verified via automated Python inspection of generated files:
1. **Total Injected Events in Manifest:** `len(pd.read_csv("labels_b.csv"))` = **`2,698` events**.
2. **Total Saved Factory Parquet Files:** `len(glob.glob("injected_b/dev/*/*.parquet"))` = **`110` files** (22 factories $\times$ 5 seeds).
3. **Total Injected Rows across All Parquets:** $\sum \text{is\_injected}$ = **`199,820` rows**.
