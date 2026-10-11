# ForensiAIR Data Audit Executive Summary: Top 10 Validity Risks

**Protocol:** `PROTOCOL_v1.md` (Frozen)  
**Date:** 2026-10-09  
**Auditor:** Automated Data Verification Engine  

---

### Top 10 Audit Findings Ranked by Risk to Evaluation Validity

1. **Concentrated Data Loss in Quality Code Filter (High Risk)**:
   Filtering `quality_code in ['Error', 'Out of Range']` drops **116,395 rows (9.28%)** overall. Data loss is highly concentrated (e.g. `site_1138` loses **99.9%** of rows), creating severe missingness bias.

2. **Flow Zero-Shutdown Flatline Inflation (High Risk)**:
   `ETP-Flow` exhibits a **44.52% flatline flag rate** due to routine plant shutdowns (0.0 m3/hr). Confounding natural zero-flow pauses with flatline tampering skews detector false-alarm calculations.

3. **100% Dead Parameter Correlation Features (Medium-High Risk)**:
   `corr_ETP-BOD_ETP-TSS`, `corr_ETP-COD_ETP-TSS`, `corr_ETP-Flow_ETP-TSS`, and `corr_ETP-TSS_ETP-pH` are **100% NaN** across the 33 Dev factories because `ETP-TSS` is omitted in the dev telemetry.

4. **SQLite DB Telemetry Truncation (Medium Risk)**:
   `forensier.db` contains only **11,056 telemetry rows** (sampled preview subset) compared to **1,254,459** in `monitoring_data(raw).csv`. DB-driven evaluation scripts produce incomplete scores if run against SQLite.

5. **Widespread Exact-Repeat Runs in Baseline Data (Medium Risk)**:
   Across dev factories, **23.4% of all raw readings** reside within exact-repeat runs >= 2 hours (8+ consecutive identical steps), which triggers flatline detectors on un-injected baseline data.

6. **CTO Consent Limit Breaches in Clean Baseline (Medium Risk)**:
   Clean baseline telemetry contains **1,844+ CTO limit violations** (e.g. pH < 5.5 or > 9.0), proving that limit violations occur naturally in baseline operations.

7. **Schema Disparity in Test Set (Zydus Missing Flow) (Medium Risk)**:
   Test factory `Zydus` provides `ETP-TSS` but completely lacks `ETP-Flow`, whereas all 33 Dev factories provide `ETP-Flow` and lack `ETP-TSS`.

8. **Leading String NA Header Rows in Test Set (Indoco) (Low-Medium Risk)**:
   `Indoco (1).csv` begins with initial rows containing text `"NA"`, requiring string parsing during data ingestion.

9. **Dead Feature missing_rate in Parquet (Low Risk)**:
   The `missing_rate` column in `real_features.parquet` is **100% 0.0 / NaN** because feature extraction evaluated single-series windows without time-gap interpolation.

10. **Per-Reading Tamper Model Retired (Low Risk)**:
    The original per-reading synthetic XGBoost tamper model was retired after over-flagging 45.7% of real readings and replaced by a factory-level logistic regression model.
