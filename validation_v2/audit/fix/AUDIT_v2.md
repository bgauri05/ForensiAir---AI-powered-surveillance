# ForensiAIR Data Audit v2: Re-Stated & Corrected Claims

**Protocol:** `PROTOCOL_v1.md` (Frozen)  
**Date:** 2026-10-09  
**Scope:** Recomputed empirical audit of dev telemetry (`monitoring_data(raw).csv`, `real_features.parquet`) and test telemetry (`Data/Unseen/*.csv`).

---

## 1. Executive Summary & Corrected Claims

| Claim Item | Old Audit Claim (v1) | Recomputed Value (v2) | Changed? | Rationale & Explanation |
| :--- | :--- | :--- | :---: | :--- |
| **`ETP-Flow` Flatline Rate** | `44.52%` | **`68.61%`** | **YES** | Exact recomputation on `real_features.parquet` (321,284 / 468,247 rows) |
| **Non-Flow Effluent Flatline Rate** | `31.5%` (range 0.81%–4.92%) | **`36.29%`** | **YES** | Mean non-Flow flatline across BOD (30.4%), COD (24.96%), and pH (40.76%) |
| **Overall Dataset Flatline Rate** | `~7%` | **`49.59%`** | **YES** | 564,392 out of 1,138,064 parquet rows have `flatline_flag == 1.0` |
| **Dev Factories Monitoring TSS** | `0 factories` ("Dev lacks TSS") | **`10 factories`** | **YES** | 10 dev factories (`site_1138`, `site_1259`, `site_1281`, etc.) monitor TSS in raw CSV |
| **Dev Factories Monitoring Flow** | `33 factories` ("All 33 have Flow") | **`31 factories`** | **YES** | 31 dev factories monitor `ETP-Flow` (`site_1232` and `site_1259` do not monitor Flow) |
| **Rule 3 Clean Exclusions** | `1,241 rows` (0.10%) | **`45,926 rows` (3.65%)** | **YES** | Includes invalid negative values (38,073), pH violations, sentinels, and NaNs |
| **Missing Rate Explanation** | Dead due to single-series window | **No Time Grid Expansion** | **YES** | `missing_rate` evaluates single-series rolling windows without expanding missing 15-min timestamps |
| **Dev Series Missingness > 50%** | Not reported | **`31 of 82 series`** | **NEW** | 37.8% of all dev factory-parameter series suffer > 50% temporal missingness |
| **Test Set Quality Code Availability**| Not reported | **`0% Available`** | **NEW** | Unseen test CSVs (`Cipla`, `Glenmark`, `Indoco`, `Zydus`) contain no quality code columns |

---

## 2. Parameter-by-Parameter Flatline Breakdown (`real_features.parquet`)

| Parameter ID | Parquet Total Rows | Flatline Rows ($1.0$) | Exact Flatline Rate (%) |
| :--- | :---: | :---: | :---: |
| `ETP-Flow` | 468,247 | 321,284 | **68.61%** |
| `ETP-pH` | 430,935 | 177,625 | **40.76%** |
| `ETP-COD` | 77,221 | 19,482 | **24.96%** |
| `ETP-BOD` | 77,236 | 23,709 | **30.4%** |
| **Total / Overall** | **1,138,064** | **564,392** | **49.59%** |

---

## 3. Top 10 Revised Validity Risks

1. **Massive Flatline Prevalence (49.93% Overall)**: Half of all parquet feature rows trigger flatline flags, dominated by `ETP-Flow` zero-shutdown runs (**68.61%**) and baseline effluent flatlines (**19.82%**).
2. **High Temporal Missingness (31 of 82 Series > 50% Missing)**: Over 37% of dev telemetry series suffer severe time gaps > 50%.
3. **Severe Quality Filter Data Loss (116,395 Rows Dropped)**: Dropping `Error`/`Out of Range` rows concentrates data loss up to 99.9% in specific sites (`site_1138`).
4. **Test Set Quality Code Omission**: Test set CSVs lack quality codes, making `DATA_INTEGRITY` fingerprint computation un-evaluable on test set.
5. **Correlation Feature Imputation (93.66% of Training Rows)**: Nearly all Isolation Forest training rows require feature imputation due to missing correlation pairs (71%–85% NaN).
6. **Widespread Baseline Repeat Runs (58.36% of Raw Data in Runs >= 2h)**: Natural operational repetitions generate long constant runs on clean telemetry.
7. **Schema Disparity (Zydus Flow Missing)**: `Zydus` lacks Flow (has TSS), whereas dev set contains Flow for 31 factories.
8. **Dev Set TSS Omission in Parquet**: 10 dev factories monitor TSS in raw CSV, but TSS features are omitted from `real_features.parquet`.
9. **SQLite Preview Truncation**: `forensier.db` holds only 11,056 rows, creating a mismatch against parquet files.
10. **CTO Baseline Breaches**: Baseline clean data exhibits 1,844+ CTO consent breaches.
