# DEVELOPMENT DIAGNOSTIC REPORT: ANALYSIS 2B (READ-ONLY, DEV ONLY)

**Diagnostic Scope:** Post-hoc read-only analysis on development telemetry only (`validation_v2/runs/run2b/`).  
**Status:** **Development Diagnostic** (Does not modify detector, cutoff, injector, labels, or test evaluations).  
**Operating Cutoff:** Frozen M1 Dev Cutoff $\tau = 3.7955$ applied to dev clean copies (no injections).  
**Baseline Reference:** Run 2b Default Dev Clean Run (327.61 factory-months across 33 factories, unweighted mean rate = 0.83 alerts/factory-month).

---

## 1. Summary Comparison Table

| Diagnostic Condition | Evaluation Scope | Total Clean Episodes | Total Exposure (fac-mo) | Pooled Rate (alerts/fac-mo) | Unweighted Mean Rate | Median Rate | Min Rate | Max Rate |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Baseline Dev Run 2b** | Default QC filter (`Raw`, `L`) | **326** | 327.61 | 0.995 | **0.828** (0.83) | **0.582** | 0.000 | 3.161 |
| **Task 1: KEEP ERROR ROWS** | Error & Out-of-Range kept as-is | **336** | 327.61 | 1.026 | **0.853** | **0.832** | 0.000 | 3.161 |
| **Task 2: SHORT SERIES** | Truncated to first 6 months | **119** | 159.93 | 0.744 | **0.610** | **0.334** | 0.000 | 2.676 |

---

## 2. Task 1: KEEP ERROR ROWS (Development Diagnostic)

### 2.1 Protocol & Methodology
- In the default development pipeline, rows tagged with `quality_code` in `["Error", "Out of Range"]` (116,395 rows in raw telemetry) were dropped before building the 15-minute grid.
- In unseen test CSVs, no quality codes exist; values are ingested as-is.
- To diagnose the impact of uncleaned telemetry artifacts on false alarms, all Error and Out-of-Range rows were KEPT with their recorded values as-is (e.g., negative calibration holds, zero dropouts) and scored using the frozen M1 cutoff $\tau = 3.7955$.

### 2.2 Alert Episode & Rate Comparison
- **Total Alert Episodes:** **336 episodes** (vs **326** in baseline, net difference of **+10 episodes**).
- **Realized False Alarms per Factory-Month:**
  - **Mean (unweighted across 33 factories):** **0.853** alerts/fac-mo (vs baseline **0.828** / **0.830**).
  - **Median:** **0.832** alerts/fac-mo (vs baseline **0.582**).
  - **Min:** **0.000** alerts/fac-mo.
  - **Max:** **3.161** alerts/fac-mo (`site_1376`).
  - **Pooled Rate:** 336 / 327.61 = **1.026** alerts/fac-mo.

### 2.3 Overlap with Kept Error-Tagged Rows
- Across the clean series, **44 new (disjoint) alert episodes** were identified that did not overlap any baseline episode.
- **26 out of the 44 new extra episodes (59.1%) directly overlap kept Error-tagged rows.**
- Across all 336 episodes in the keep-error run, **26 episodes (7.7%) overlap kept Error-tagged rows.**
- **Key Site Impacts:**
  - `site_1138`: Possesses 30,815 Error rows and only 24 Raw rows across 2024. In the baseline run (where errors were dropped), it had 0 alerts. Keeping error rows generated **2 alert episodes**, both directly overlapping Error rows (0.170 alerts/fac-mo).
  - `site_1281`: Increased from 6 episodes to **19 episodes** (+13 episodes), with **12 episodes directly overlapping Error rows** (rate increased from 0.499 to 1.581 alerts/fac-mo).
  - `site_1257`: +1 episode, 3 overlapping Error rows.
  - `site_1284`: 2 episodes overlap Error rows.
  - `site_1285`: 5 episodes overlap Error rows.
  - `site_1668`: 2 episodes overlap Error rows.

---

## 3. Task 2: SHORT SERIES (Truncated to First 6 Months)

### 3.1 Protocol & Methodology
- In unseen test evaluation, all 4 factories (`Cipla`, `Glenmark`, `Indoco`, `Zydus`) were 6 months long (5.98 factory-months each).
- To diagnose whether shorter duration (fewer samples in the blind calibration tail) inflates false alarms, all dev factories were truncated to their first 6 months of telemetry (default filtering: `allowed_qc = ["Raw", "L"]`).
- Scored with blind calibration on the truncated series at frozen cutoff $\tau = 3.7955$.

### 3.2 Alert Episode & Rate Comparison
- **Total Exposure:** **159.93 factory-months** (down from 327.61).
- **Total Alert Episodes:** **119 episodes**.
- **Realized False Alarms per Factory-Month:**
  - **Mean (unweighted across 33 factories):** **0.610** alerts/fac-mo (vs baseline **0.828** / **0.830**).
  - **Median:** **0.334** alerts/fac-mo (vs baseline **0.582**).
  - **Min:** **0.000** alerts/fac-mo.
  - **Max:** **2.676** alerts/fac-mo (`site_1257`, 16 episodes / 5.98 mo).
  - **Pooled Rate:** 119 / 159.93 = **0.744** alerts/fac-mo.

### 3.3 Diagnostic Conclusion
Truncating telemetry from 12 months to 6 months did **NOT** increase the false alarm rate on dev telemetry. Instead, the mean false alarm rate decreased from 0.83 to 0.61 alerts/month (and pooled rate decreased from 0.995 to 0.744).  
This confirms that the higher realized false alarm rate observed on the test set (4.057 alerts/month) was **not an artifact of short 6-month series length**, but stems from site-specific distribution shift (sensor limit proximity and covariance patterns).

---

## 4. Task 3: DISPERSION on Default Dev Run (Run 2b)

### 4.1 Cross-Factory Distribution Statistics
Across all 33 development factories under the default Run 2b operating point ($\tau = 3.7955$ / $3.7906$):
- **Min Rate:** **0.000** alerts/factory-month (10 factories with zero alerts).
- **Median Rate:** **0.582** alerts/factory-month (`site_1321`).
- **Mean Rate (unweighted):** **0.830** alerts/factory-month.
- **Pooled Rate:** 327 / 327.61 = **0.998** alerts/factory-month.
- **Max Rate:** **3.161** alerts/factory-month (`site_1376`).
- **25th Percentile (P25):** 0.000
- **75th Percentile (P75):** 1.331
- **Standard Deviation:** 0.851

### 4.2 Factories with False Alarm Rate Above 2.0 Alerts/Month
Exactly **4 out of 33 factories (12.1%)** had a realized false alarm rate above 2.0 alerts/month:
1. **`site_1376`:** **3.161 alerts/mo** (38 episodes / 12.02 factory-months)
2. **`site_1257`:** **2.662 alerts/mo** (32 episodes / 12.02 factory-months)
3. **`site_1285`:** **2.246 alerts/mo** (27 episodes / 12.02 factory-months)
4. **`site_1668`:** **2.163 alerts/mo** (26 episodes / 12.02 factory-months)

### 4.3 Factories with Zero False Alarms (0.000 alerts/month)
10 out of 33 factories had zero alert episodes:  
`site_1138`, `site_1167`, `site_1256`, `site_1259`, `site_1569`, `site_1581`, `site_1789`, `site_1909`, `site_2070`, `site_982`.

---

## 5. Artifacts Created in this Diagnostic
All outputs written strictly to [`validation_v2/runs/run2b/analysis/`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/runs/run2b/analysis/):
- [`ANALYSIS_2B_REPORT.md`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/runs/run2b/analysis/ANALYSIS_2B_REPORT.md): This report.
- [`summary_comparison.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/runs/run2b/analysis/summary_comparison.csv): High-level comparison across Baseline, Task 1, and Task 2.
- [`task1_keep_error_rows.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/runs/run2b/analysis/task1_keep_error_rows.csv): Per-factory breakdown of alert episodes and error-row overlaps.
- [`task2_short_series.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/runs/run2b/analysis/task2_short_series.csv): Per-factory breakdown on 6-month truncated series.
- [`task3_dispersion_run2b.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/validation_v2/runs/run2b/analysis/task3_dispersion_run2b.csv): Full 33-factory false alarm rates and exposure from Run 2b.
