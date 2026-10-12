# 🔍 Phase A: Data Readiness & Audit Report (`hybrid_v2`)

**Location**: `experiments/hybrid_v2/data_readiness_report.md`  
**Target Raw Telemetry Source**: `output.rar` (`mpcb_etp_data.csv` and `mpcb_etp_dataII.csv`)  
**Audit Executed**: 2026-10-04  

---

## 1. Actual Schema & Grain of `cleaned_output_rar_telemetry`

### 1.1 Schema & Data Types
The cleaned telemetry dataset derived from `output.rar` is stored in `Data/OutputRar_Hybrid/cleaned_output_rar_telemetry.parquet` (and `.csv`).

| Column Name | Data Type | Description |
|---|---|---|
| `factory_id` | `object` / `string` | Site identifier (e.g. `site_1129`, `site_1307`, `site_1458`, `site_1629`, `site_1631`) |
| `parameter_id` | `object` / `string` | ETP parameter name (`ETP-Flow`, `ETP-pH`, `ETP-COD`, `ETP-BOD`, `ETP-TSS`) |
| `timestamp` | `datetime64[ns]` | Telemetry measurement timestamp (15-minute intervals) |
| `value` | `float64` | Numeric telemetry measurement value |
| `quality_code` | `object` / `string` | MPCB data quality flag (`U` = Raw, `L` = Below Detection Limit, `E` = Error) |

### 1.2 Dataset Grain & Uniqueness
- **Grain**: Exactly **one row per `(factory_id, timestamp, parameter_id)`**.
- **Uniqueness Check**: `is_unique_grain = True` (Maximum row count per `(factory_id, timestamp, parameter_id)` composite key is 1).
- **Total Cleaned Records**: **114,513** unique time-series entries.

---

### 1.3 Breakdown of Row Counts

#### A. Row Counts per Site:
- `site_1307` (*Mangalam Organics Limited*): **34,867 rows**
- `site_1129` (*Clean Science & Technology D-28*): **30,556 rows**
- `site_1629` (*M/s. Kamsons Polymers Pvt Ltd*): **25,276 rows**
- `site_1631` (*Dorfketal Chemicals India Pvt Ltd*): **23,810 rows**
- `site_1458` (*Stratechem (India) Pvt Ltd*): **4 rows** (Sparse data artifact)

#### B. Row Counts per Parameter:
- `ETP-pH`: **52,269 rows**
- `ETP-Flow`: **47,958 rows**
- `ETP-BOD`: **4,762 rows**
- `ETP-COD`: **4,762 rows**
- `ETP-TSS`: **4,762 rows**

#### C. Row Counts per Site and Parameter:

| Site ID | Parameter | Total Clean Rows | Start Date | End Date |
|---|---|---|---|---|
| `site_1129` | `ETP-Flow` | **30,556** | 2024-01-01 00:00 | 2024-12-31 23:45 |
| `site_1307` | `ETP-pH` | **34,867** | 2024-01-01 00:00 | 2024-12-31 23:45 |
| `site_1458` | `ETP-Flow` | **2** | 2024-07-01 00:00 | 2024-07-01 00:15 |
| `site_1458` | `ETP-pH` | **2** | 2024-07-01 00:00 | 2024-07-01 00:15 |
| `site_1629` | `ETP-Flow` | **12,638** | 2024-01-01 00:00 | 2024-07-31 23:45 |
| `site_1629` | `ETP-pH` | **12,638** | 2024-01-01 00:00 | 2024-07-31 23:45 |
| `site_1631` | `ETP-BOD` | **4,762** | 2024-06-01 00:00 | 2024-08-31 23:45 |
| `site_1631` | `ETP-COD` | **4,762** | 2024-06-01 00:00 | 2024-08-31 23:45 |
| `site_1631` | `ETP-Flow` | **4,762** | 2024-06-01 00:00 | 2024-08-31 23:45 |
| `site_1631` | `ETP-TSS` | **4,762** | 2024-06-01 00:00 | 2024-08-31 23:45 |
| `site_1631` | `ETP-pH` | **4,762** | 2024-06-01 00:00 | 2024-08-31 23:45 |

#### D. Row Counts per Site and Month (2024 Calendar Year):

| Site ID | Month | Clean Row Count |
|---|---|---|
| `site_1129` | 2024-01 | 2,968 |
| `site_1129` | 2024-02 | 2,533 |
| `site_1129` | 2024-03 | 2,811 |
| `site_1129` | 2024-04 | 2,815 |
| `site_1129` | 2024-05 | 2,598 |
| `site_1129` | 2024-06 | 2,596 |
| `site_1129` | 2024-07 | 2,227 |
| `site_1129` | 2024-08 | 2,309 |
| `site_1129` | 2024-09 | 2,269 |
| `site_1129` | 2024-10 | 2,534 |
| `site_1129` | 2024-11 | 2,182 |
| `site_1129` | 2024-12 | 2,714 |
| `site_1307` | 2024-01 | 2,975 |
| `site_1307` | 2024-02 | 2,772 |
| `site_1307` | 2024-03 | 2,970 |
| `site_1307` | 2024-04 | 2,872 |
| `site_1307` | 2024-05 | 2,780 |
| `site_1307` | 2024-06 | 2,853 |
| `site_1307` | 2024-07 | 2,976 |
| `site_1307` | 2024-08 | 2,976 |
| `site_1307` | 2024-09 | 2,867 |
| `site_1307` | 2024-10 | 2,971 |
| `site_1307` | 2024-11 | 2,879 |
| `site_1307` | 2024-12 | 2,976 |
| `site_1458` | 2024-07 | 4 |
| `site_1629` | 2024-01 | 5,934 |
| `site_1629` | 2024-02 | 3,400 |
| `site_1629` | 2024-03 | 14 |
| `site_1629` | 2024-04 | 4,262 |
| `site_1629` | 2024-05 | 4,772 |
| `site_1629` | 2024-06 | 2,632 |
| `site_1629` | 2024-07 | 4,262 |
| `site_1631` | 2024-06 | 12,585 |
| `site_1631` | 2024-08 | 11,225 |

---

## 2. Dedupe Audit

Audit of raw file parsing, cell unpivoting, file overlap, and record deduplication:

```
+-------------------------------------------------------------------------------+
|                             DEDUPE AUDIT SUMMARY                              |
+----------------------------------------------------+--------------------------+
| Metric Description                                 | Count / Value            |
+----------------------------------------------------+--------------------------+
| Raw CSV rows in file 1 (`mpcb_etp_data.csv`)       | 120,096                  |
| Raw CSV rows in file 2 (`mpcb_etp_dataII.csv`)     | 20,544                   |
| Total Raw CSV timeline rows                        | 140,640                  |
+----------------------------------------------------+--------------------------+
| Extracted valid parameter records (File 1)         | 151,137                  |
| Extracted valid parameter records (File 2)         | 82,940                   |
| Total Extracted valid records                      | 234,077                  |
+----------------------------------------------------+--------------------------+
| Null / NA cells filtered during unpivoting         | 8,204,323                |
| Exact overlapping records of File 2 present in File 1| 82,940 (100% of File 2)  |
| Duplicate timestamp entries dropped                | 119,564                  |
+----------------------------------------------------+--------------------------+
| FINAL CLEAN UNIQUE TELEMETRY RECORDS               | 114,513                  |
+----------------------------------------------------+--------------------------+
```

### Explanations of Dropped Rows:
1. **Empty / Null Cell Filtering (`8,204,323` cells)**: The 65-column CSV contains wide columns for 12 quality codes per parameter. Empty cells or cells containing `['NA', 'E']` (no value recorded) were filtered out during unpivoting.
2. **File 2 Overlap (`82,940` records)**: `mpcb_etp_dataII.csv` contains telemetry for `site_1631` from June to August 2024. All 82,940 valid parameter records in File 2 are 100% identical duplicate entries already captured in `mpcb_etp_data.csv`.
3. **Duplicate Timestamps (`119,564` records)**: Multiple quality code channels for the same parameter and timestamp (e.g. `ETP-COD_U` and `ETP-COD_V`) or duplicate rows across files were deduplicated to retain a single canonical reading per `(factory_id, parameter_id, timestamp)`.

---

## 3. Baseline Quality per Site & Parameter

Summary of baseline anomalies, missing data percentages, existing flatlines, impossible pH spikes, and gaps $> 1\text{h}$ across all site/parameter series:

```
+-----------------------------------------------------------------------------------------------------------------------+
|                                              BASELINE QUALITY AUDIT                                                   |
+---------------+-----------+--------+----------+---------+------------+---------------------+----------+--------+----+
| Site ID       | Parameter | Actual | Expected | Missing | Missing %  | Quality Code Dist.  | Flatlines| Imp pH |Gaps|
+---------------+-----------+--------+----------+---------+------------+---------------------+----------+--------+----+
| site_1129     | ETP-Flow  | 30,556 | 35,136   | 4,580   | 13.04%     | U: 30556            | 6,395    | N/A    | 42 |
| site_1307     | ETP-pH    | 34,867 | 35,136   | 269     | 0.77%      | U: 34268, L: 599    | 0        | 1      | 11 |
| site_1458     | ETP-Flow  | 2      | 2        | 0       | 0.00%      | E: 2                | 0        | N/A    | 0  |
| site_1458     | ETP-pH    | 2      | 2        | 0       | 0.00%      | U: 2                | 0        | 2      | 0  |
| site_1629     | ETP-Flow  | 12,638 | 20,448   | 7,810   | 38.20%     | U: 12630, E: 8      | 9,014    | N/A    | 66 |
| site_1629     | ETP-pH    | 12,638 | 20,448   | 7,810   | 38.20%     | U: 12638            | 30       | 4      | 66 |
| site_1631     | ETP-BOD   | 4,762  | 8,101    | 3,339   | 41.22%     | U: 4152, L: 610     | 302      | N/A    | 2  |
| site_1631     | ETP-COD   | 4,762  | 8,101    | 3,339   | 41.22%     | U: 4152, L: 610     | 299      | N/A    | 2  |
| site_1631     | ETP-Flow  | 4,762  | 8,101    | 3,339   | 41.22%     | U: 4152, L: 610     | 3,867    | N/A    | 2  |
| site_1631     | ETP-TSS   | 4,762  | 8,101    | 3,339   | 41.22%     | U: 4152, L: 610     | 3,902    | N/A    | 2  |
| site_1631     | ETP-pH    | 4,762  | 8,101    | 3,339   | 41.22%     | U: 4152, L: 610     | 639      | 0      | 2  |
+---------------+-----------+--------+----------+---------+------------+---------------------+----------+--------+----+
```

### Windows Excluded from Injection:
1. **`site_1458` Entire Series**: Contains only 2 readings total (99.99% overall temporal gap). Must be excluded completely from tamper pattern generation.
2. **Data Gaps $> 1\text{h}$ (189 Total Gap Windows)**: No synthetic tampering events will be placed spanning data gaps.
3. **Existing Baseline Flatline Windows**: Existing zero-variance runs $> 6\text{h}$ (such as `site_1629` ETP-Flow flatline blocks) must be excluded to prevent overlapping synthetic injections over corrupted baseline sensors.
4. **Time Series Edge Buffer**: Injections will maintain a minimum 24-hour buffer (96 periods) from series start and end boundaries to ensure clean rolling feature calculations.

---

## 4. CTO Discharge Limits & Inspection Dates Audit

### 4.1 Consent to Operate (CTO) Limits
- **Site-Specific CTO Documents**: Per-factory custom consent limit documents do not exist in the database for these 5 facilities (`site_1129`, `site_1307`, `site_1458`, `site_1629`, `site_1631`).
- **Global Regulatory Standards**: Standard CPCB environmental discharge limits are applied consistently across parameters:
  - `ETP-COD`: Max limit **250.0 mg/L**
  - `ETP-BOD`: Max limit **30.0 mg/L**
  - `ETP-TSS`: Max limit **100.0 mg/L**
  - `ETP-pH`: Legal range **5.5 to 9.0**
  - `ETP-Flow`: Max limit **500.0 $m^3/\text{day}$**

### 4.2 Regulatory Inspection Dates
- **Database Inspection Records**: `0` inspection events exist in `forensier.db` for these 5 sites (historical inspection records in `forensier.db` cover other core facilities such as `site_1569`, `site_1369`, `site_1200`, `site_1284`, `site_1376`).
- **Phase B Requirement**: Synthetic inspection target dates must be established per facility to evaluate pre-inspection dip detection.

---

## 5. Model Training Data Overlap Check

- **Question**: Do these 5 site IDs appear in the training data of the current production models?
- **Audit Result**: **NO. None of the 5 site IDs (`site_1129`, `site_1307`, `site_1458`, `site_1629`, `site_1631`) appear in `Data/RawData/real_features.parquet` or the current model training database.**
- **Details**:
  - `Data/RawData/real_features.parquet` contains 33 core facilities (`site_1131`, `site_1138`, ..., `site_982`).
  - The 5 facilities in `output.rar` are completely **out-of-sample unseen facilities**.
  - **Implication**: This dataset provides a zero-leakage benchmark for evaluating model generalization.

---

## 6. Feature Matrix Schema Comparison

Comparison between production feature schema (`Data/RawData/real_features.parquet`) and previous `hybrid_features.parquet` in `Data/OutputRar_Hybrid/`:

```
+---------------------------------------------------------------------------------------------------+
|                                  FEATURE SCHEMA COMPARISON MATRIX                                 |
+------------------------------------+--------------------------------+-----------------------------+
| Feature Metric                     | real_features.parquet (Target) | Previous hybrid_features    |
+------------------------------------+--------------------------------+-----------------------------+
| Total Column Count                 | 28 Columns                     | 16 Columns                  |
| Exact Column Order Match           | Target Standard                | Non-matching                |
+------------------------------------+--------------------------------+-----------------------------+
```

### Missing Columns in Previous Hybrid Dataset (Must be Added in Phase B):
1. `corr_ETP-Flow_ETP-pH`
2. `corr_ETP-BOD_ETP-COD`
3. `corr_ETP-BOD_ETP-Flow`
4. `corr_ETP-BOD_ETP-TSS`
5. `corr_ETP-BOD_ETP-pH`
6. `corr_ETP-COD_ETP-Flow`
7. `corr_ETP-COD_ETP-TSS`
8. `corr_ETP-COD_ETP-pH`
9. `corr_ETP-Flow_ETP-TSS`
10. `corr_ETP-TSS_ETP-pH`
11. `bdl_rate`
12. `duplicate_run_length`
13. `cov_severity`
14. `bod_cod_ratio`
15. `bod_cod_ratio_volatility`
16. `quality_error_rate`

### Phase B Implementation Directive:
The feature generator for `hybrid_v2` must import directly from the production feature pipeline to ensure **all 28 columns, order, and data types match `real_features.parquet` exactly**.

---

## 7. Distinct Event Audit in `hybrid_tamper_labels.csv`

Audit of event objects in `Data/OutputRar_Hybrid/hybrid_tamper_labels.csv`:

- **Total Distinct Events**: **100 events**

### A. Events per Tamper Type:
- `INSPECTION DIP`: **15 events**
- `LIMIT HUGGING`: **14 events**
- `COORDINATED MISSING DATA`: **14 events**
- `CORRELATION BREAK`: **13 events**
- `BDL GAMING`: **12 events**
- `FLATLINE`: **12 events**
- `IMPOSSIBLE PH RANGE`: **11 events**
- `COPY-PASTE`: **9 events**

### B. Events per Severity Tier:
- `low`: **43 events**
- `high`: **33 events**
- `medium`: **24 events**

### C. Events per Facility:
- `site_1307`: **28 events**
- `site_1129`: **25 events**
- `site_1629`: **24 events**
- `site_1631`: **23 events**

---

## 8. Summary of Hard Rules & Readiness Status

1. **Read-Only Compliance**: No existing codebase files, models, or databases were modified.
2. **Phase B Readiness**:
   - `site_1458` will be excluded from injection (insufficient data).
   - Target event count will scale to $\ge 300$ distinct events ($\ge 30$ per detector type, $\ge 30$ multi-day copy-paste events).
   - Severity calibration (easy, medium, subtle) will strictly observe non-overlapping thresholds and baseline exclusion rules.
   - Dual variants (code-neutral and code-visible) will be output alongside SHA256 integrity checksum manifests.
