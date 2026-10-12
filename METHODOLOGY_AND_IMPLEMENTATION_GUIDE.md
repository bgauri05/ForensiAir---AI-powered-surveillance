# 🛡️ Forensier: AI-Powered Industrial Environmental Surveillance & Tampering Detection
## 📘 Comprehensive Methodology & Implementation Guide

---

## 📑 Table of Contents
1. [Executive Summary & System Scope](#1-executive-summary--system-scope)
2. [Data Scraper & Ingestion Pipeline Infrastructure](#2-data-scraper--ingestion-pipeline-infrastructure)
   - [2.1 MPCB OCEMS Telemetry REST API Scraper](#21-mpcb-ocems-telemetry-rest-api-scraper)
   - [2.2 ETP-pH Concurrent Scraper Engine](#22-etp-ph-concurrent-scraper-engine)
   - [2.3 Consent to Operate (CTO) Intelligence Collector](#23-consent-to-operate-cto-intelligence-collector)
   - [2.4 Inspection Schedule Collector](#24-inspection-schedule-collector)
   - [2.5 CDP Network Interception & Selenium Prototypes](#25-cdp-network-interception--selenium-prototypes)
3. [Feature Engineering & Characterization Engine](#3-feature-engineering--characterization-engine)
   - [3.1 Raw Telemetry Feature Extraction](#31-raw-telemetry-feature-extraction)
   - [3.2 5-Module Dataset Characterization Engine](#32-5-module-dataset-characterization-engine)
4. [Machine Learning Pipeline, Risk Engine & Fingerprints](#4-machine-learning-pipeline-risk-engine--fingerprints)
   - [4.1 8 Industrial Tampering Fingerprints](#41-8-industrial-tampering-fingerprints)
   - [4.2 Unsupervised Anomaly Detection (Isolation Forest)](#42-unsupervised-anomaly-detection-isolation-forest)
   - [4.3 Weak-Supervised Factory-Level Tamper Model](#43-weak-supervised-factory-level-tamper-model)
   - [4.4 Composite Risk Score Mathematical Formulation](#44-composite-risk-score-mathematical-formulation)
   - [4.5 Risk Categorization & Recommended Action Triggers](#45-risk-categorization--recommended-action-triggers)
5. [Explainable AI (XAI) & SHAP Attributions](#5-explainable-ai-xai--shap-attributions)
   - [5.1 Dual-Model SHAP Explainer Pipeline](#51-dual-model-shap-explainer-pipeline)
   - [5.2 KernelExplainer & LinearExplainer Methodology](#52-kernelexplainer--linearexplainer-methodology)
6. [Backend API & Database Infrastructure Code Trace](#6-backend-api--database-infrastructure-code-trace)
   - [6.1 Relational Database Schema & Seeding Logic](#61-relational-database-schema--seeding-logic)
   - [6.2 FastAPI Endpoint Mapping](#62-fastapi-endpoint-mapping)
7. [Frontend Architecture & Visualization Layer](#7-frontend-architecture--visualization-layer)
8. [Data Integrity Audit: Hardcoded vs Precomputed vs Real Dynamic Data](#8-data-integrity-audit-hardcoded-vs-precomputed-vs-real-dynamic-data)

---

## 1. Executive Summary & System Scope

**Forensier** (formerly *ForensiAir*) is an AI-assisted environmental surveillance and forensic analytics application designed to monitor Continuous Emission & Effluent Monitoring Systems (OCEMS) operated by industrial facilities in Maharashtra (specifically focusing on the Taloja and Mahad industrial belts).

### System Scope & Technical Implementation:
- **Facility Scope**:
  - **97 Target Regional Facilities**: Initial candidate list of industrial plants in the Taloja & Mahad MIDC industrial belts stored in [`scraper/all_factories.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/scraper/all_factories.csv).
  - **33 Core Monitored Facilities**: Active chemical, pharmaceutical, and metallurgical plants (`site_1131` through `site_982`) that had complete, high-frequency continuous OCEMS telemetry available. All feature engineering, 8 fingerprint detectors, ML models, SHAP explanations, and dashboard UI views operate on these 33 core facilities.
- **Telemetry Ingestion**: Ingests **1,138,064 continuous time-series telemetry readings** across key Effluent Treatment Plant (ETP) parameters: `COD`, `BOD`, `TSS`, `pH`, `Flow`, and `Totalizer`.
- **Hybrid Risk Scoring**: Combines **8 rule-based domain fingerprints**, **Unsupervised Isolation Forest anomaly scoring**, and an **L2-Regularized Logistic Regression model** trained on proxy labels (validated via Leave-One-Out Cross Validation, LOOCV).
- **Model Explainability**: Integrates **SHAP (SHapley Additive exPlanations)** attributions to provide feature-level diagnostic breakdowns for each facility.

```
       +-----------------------------------------------------------------+
       |                  MPCB Portal / Sensor Hardware                   |
       +-----------------------------------------------------------------+
                                        |
      Base64 JSON Protocol              | Playwright / pdfplumber + ddddocr
                                        v
       +-----------------------------------------------------------------+
       |                   Scraper & Ingestion Layer                     |
       |  - mpcb_scraper_final.py      - collector/consent/ (CTO PDFs)  |
       |  - scrape_ph_concurrent.py    - collector/inspection/ (CIA)    |
       +-----------------------------------------------------------------+
                                        |
                                        v
       +-----------------------------------------------------------------+
       |            Feature Engineering & Characterization               |
       |  - Rolling Stats, Correlations, Autocorrelations, Gap Analysis  |
       |  - 5-Module Characterization Engine (factory_profiles.parquet)  |
       +-----------------------------------------------------------------+
                                        |
       +--------------------------------+--------------------------------+
       |                                                                 |
       v                                                                 v
+-----------------------------+                           +-----------------------------+
|    8 Industrial Tamper      |                           |     Machine Learning Models |
|        Fingerprints         |                           |  - Isolation Forest         |
| (pH, Dips, Flatlines, etc.) |                           |  - Weak-Supervision LR      |
+-----------------------------+                           +-----------------------------+
       |                                                                 |
       +--------------------------------+--------------------------------+
                                        |
                                        v
       +-----------------------------------------------------------------+
       |                  Composite Risk Engine (0 - 100)                |
       |  Risk = 0.10(XGB/LR) + 0.225(ISO_norm) + 0.675(Fingerprint_ratio)|
       +-----------------------------------------------------------------+
                                        |
                                        v
       +-----------------------------------------------------------------+
       |             FastAPI Backend & SQLite Database Layer             |
       |  - main.py, seed_db.py, forensier.db, SHAP JSON Engine          |
       +-----------------------------------------------------------------+
                                        |
                                        v
       +-----------------------------------------------------------------+
       |            React + Vite + Tailwind Frontend Dashboard           |
       +-----------------------------------------------------------------+
```

---

## 2. Data Scraper & Ingestion Pipeline Infrastructure

The data extraction layer comprises network protocol inspection, automated CAPTCHA processing, PDF tabular parsing, and concurrent HTTP requests.

### 2.1 MPCB OCEMS Telemetry REST API Scraper
- **File**: [`scraper/mpcb_scraper_final.py`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/scraper/mpcb_scraper_final.py)
- **Target Endpoint**: `https://onlinecems.ecmpcb.in/glens/publicPortal/api/v2.0/{endpoint}`
- **Target Scale**: 97 candidate target factories listed in [`scraper/all_factories.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/scraper/all_factories.csv) (from which 33 core facilities yielded full continuous telemetry).
- **Base64 Payload Protocol**:
  The MPCB GLENS public portal transmits all JSON payloads as **Base64 encoded strings** sent with `Content-Type: text/plain`. Responses are returned as Base64 encoded strings.
  ```python
  def call_api(endpoint: str, payload: dict, timeout=15) -> dict:
      url = BASE_API_URL + endpoint
      payload_json = json.dumps(payload)
      payload_b64 = base64.b64encode(payload_json.encode("utf-8")).decode("ascii")
      headers = {"Content-Type": "text/plain", "Accept": "application/json, text/plain, */*"}
      resp = requests.post(url, headers=headers, data=payload_b64, timeout=timeout)
      if resp.status_code == 200:
          return json.loads(base64.b64decode(resp.text).decode("utf-8"))
  ```
- **Ingested Parameters**: `ETP-COD`, `ETP-BOD`, `ETP-TSS`, `ETP-pH`, `ETP-Flow`, `ETP-Totalizer`.
- **Quality Tags**: Retains standard MPCB telemetry status codes: `["U", "E", "O", "N", "I", "M", "V", "C", "input", "Z", "X", "Y"]`.

### 2.2 ETP-pH Concurrent Scraper Engine
- **Files**: [`scraper/scrape_ph_concurrent.py`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/scraper/scrape_ph_concurrent.py), [`scraper/scrape_ph.py`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/scraper/scrape_ph.py)
- **Implementation**: Utilizes `concurrent.futures.ThreadPoolExecutor` (5 worker threads) for parallel monthly retrieval of pH measurements across 2024 with exponential backoff retries.

### 2.3 Consent to Operate (CTO) Intelligence Collector
- **Directory**: [`scraper/collector/consent/`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/scraper/collector/consent/)
- **Components**:
  - `collector.py`: Execution pipeline entry point.
  - `scraper.py`: Automated Consent Management System (CMS) PDF downloader.
  - `parser.py`: Uses `pdfplumber` to parse structured discharge limits (BOD max mg/L, COD max mg/L, TSS max mg/L, pH range 5.5-9.0, max daily flow volume).
  - `ddddocr CAPTCHA Solver`: Employs Python `ddddocr` for automated optical character recognition on portal CAPTCHAs.
  - `database.py`: PostgreSQL transactional interface for `consents`, `consent_limits`, and `consent_download_logs`.

### 2.4 Inspection Schedule Collector
- **Directory**: [`scraper/collector/inspection/`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/scraper/collector/inspection/)
- **Implementation**: Uses `Playwright` async Chromium headless browser (`collector.py`, `scraper.py`) to query inspection tables from MPCB's Central Inspection System (CIS).

### 2.5 CDP Network Interception & Selenium Prototypes
- **Files**: [`scraper/mpcb_scraper_v4.py`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/scraper/mpcb_scraper_v4.py) (Chrome DevTools Protocol interceptor), [`scraper/mpcb_scraper_v3.py`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/scraper/mpcb_scraper_v3.py) (Selenium prototype).
- **Purpose**: Used during initial discovery to inspect network requests and discover the underlying Base64 REST endpoints.

---

## 3. Feature Engineering & Characterization Engine

### 3.1 Raw Telemetry Feature Extraction
- **Data File**: [`Data/RawData/real_features.parquet`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/Data/RawData/real_features.parquet) (18 features per reading).
- **Feature Vector Definitions**:
  1. `value`: Raw measured sensor value.
  2. `rolling_mean`: 24-hour rolling average.
  3. `rolling_std`: 24-hour rolling standard deviation.
  4. `rolling_cov`: Rolling coefficient of variation ($\text{std} / \text{mean}$).
  5. `flatline_flag`: Binary indicator (1 if zero variance for $\ge 6$ consecutive hours).
  6. `corr_ETP-Flow_ETP-pH`: Pearson correlation between Flow and pH.
  7. `corr_ETP-BOD_ETP-COD`: Pearson correlation between BOD and COD.
  8. `corr_ETP-BOD_ETP-Flow`: Pearson correlation between BOD and Flow.
  9. `corr_ETP-BOD_ETP-TSS`: Pearson correlation between BOD and TSS.
  10. `corr_ETP-BOD_ETP-pH`: Pearson correlation between BOD and pH.
  11. `corr_ETP-COD_ETP-Flow`: Pearson correlation between COD and Flow.
  12. `corr_ETP-COD_ETP-TSS`: Pearson correlation between COD and TSS.
  13. `corr_ETP-COD_ETP-pH`: Pearson correlation between COD and pH.
  14. `corr_ETP-Flow_ETP-TSS`: Pearson correlation between Flow and TSS.
  15. `corr_ETP-TSS_ETP-pH`: Pearson correlation between TSS and pH.
  16. `autocorrelation`: Lag-1 autocorrelation coefficient ($r_1$).
  17. `missing_rate`: Fraction of expected readings missing.
  18. `limit_hugging`: Proximity indicator to CTO threshold ($0.95 \le \text{value}/\text{limit} \le 1.00$).

### 3.2 5-Module Dataset Characterization Engine
- **File**: [`Characterization Engine/characterization_engine.py`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/Characterization%20Engine/characterization_engine.py)
- **Output**: [`Characterization Engine/factory_profiles.parquet`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/Characterization%20Engine/factory_profiles.parquet) (33 profile rows).

#### Characterization Modules:
1. **Module 1: Data Availability**: Summarizes `coverage_percentage`, `monitoring_days`, `longest_gap` (hours), and outage counts.
2. **Module 2: Parameter Distributions**: Calculates statistical summary metrics (`mean`, `std`, `min`, `max`, `coeff_variation`) for `pH`, `COD`, `BOD`, and `TSS`.
3. **Module 3: Sensor Health Score (0.0 to 1.0)**:
   $$\text{Penalty} = (0.40 \cdot P_{\text{missing}}) + (0.20 \cdot P_{\text{duplicate}}) + (0.20 \cdot P_{\text{BDL}}) + \left(0.20 \cdot \min\left(\frac{\text{Outages}}{100}, 1.0\right)\right)$$
   $$\text{Sensor Health Score} = \max(0.0, 1.0 - \text{Penalty})$$
4. **Module 4: Inter-Factory Similarity**: Standardizes parameter distributions with `StandardScaler` and computes **Cosine Similarity** to select top 3 peer facilities.
5. **Module 5: Temporal Stability**: Evaluates quarterly mean shifts across Q1-Q4. Flags parameter shifts if pH varies by $> 0.5$ units or concentration parameters vary by $> 25\%$.

---

## 4. Machine Learning Pipeline, Risk Engine & Fingerprints

The composite risk score combines three independent components to calculate an overall risk estimate for each factory.

```
+---------------------------------------------------------------------------------------------------+
|                                  3-PART COMPOSITE RISK ENGINE                                     |
+------------------------------------+--------------------------------+-----------------------------+
|    1. WEAK SUPERVISION MODEL       |    2. ISOLATION FOREST MODEL   |   3. FINGERPRINT ENGINE     |
|   (L2 Logistic Regression)         |   (Unsupervised Scoring)       |  (8 Domain Rule Triggers)   |
|   Weight: 10% (0.10)               |   Weight: 22.5% (0.225)        |  Weight: 67.5% (0.675)      |
+------------------------------------+--------------------------------+-----------------------------+
                                     \               |                /
                                      \              |               /
                                       v             v              v
+---------------------------------------------------------------------------------------------------+
|                        Composite Score = (0.10 * P_tamper) + (0.225 * ISO_norm) + (0.675 * FP_ratio)|
|                        Risk Score = round(Composite * 100, 1)  [Range: 0.0 - 100.0]               |
+---------------------------------------------------------------------------------------------------+
```

### 4.1 8 Industrial Tampering Fingerprints
- **Data Source**: Loaded in [`database/seed_db.py`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/database/seed_db.py) from [`Data/RawData/factory_fingerprint_scores.csv`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/Data/RawData/factory_fingerprint_scores.csv).

| # | Fingerprint Name | Technical Detection Rule / Logic | Trigger Threshold |
|---|---|---|---|
| 1 | `impossible_ph_range` | Identifies extreme non-biological chemical spikes. | $\text{pH} < 2.0$ or $\text{pH} > 12.0$ |
| 2 | `inspection_dip` | Evaluates concentration drops prior to scheduled inspection dates. | Pre-inspection drop $> 30\%$ |
| 3 | `flatline` | Flags static or frozen sensor output sequences. | Zero variance for $> 6$ consecutive hours |
| 4 | `limit_hugging` | Detects persistent values near regulatory discharge thresholds. | Values in $95\%-99\%$ of CTO limit |
| 5 | `correlation_break` | Monitors breakdown of expected chemical relationships (e.g. BOD vs COD). | Correlation drop below baseline |
| 6 | `copy_paste` | Identifies repeated multi-step temporal pattern duplicates. | Sequence match rate $> 5\%$ |
| 7 | `coordinated_missing_data` | Identifies multi-parameter outages occurring simultaneously. | Coordinated outage flag active |
| 8 | `data_integrity` | Checks for corrupted logs, timestamp gaps, or formatting errors. | Format / integrity issue flagged |

### 4.2 Unsupervised Anomaly Detection (Isolation Forest)
- **Training Script**: [`ml_pipeline/train_models.py`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/ml_pipeline/train_models.py)
- **Artifacts**: `iso_forest.joblib`, `iso_scaler.joblib`, `feature_cols.joblib`
- **Model Details**: `n_estimators=100`, `contamination=0.05`, `random_state=42`. Trained on real telemetry features.
- **Score Normalization**:
  Raw `score_samples()` values are mapped to a $0.0 - 1.0$ score using distribution percentiles derived from real telemetry:
  - `ISO_SCORE_NORMAL_ANCHOR` ($P_{75}$) = `-0.3208`
  - `ISO_SCORE_ANOMALOUS_ANCHOR` ($P_{1}$) = `-0.6270`
  $$\text{ISO}_{\text{norm}} = \max\left(0.0, \min\left(1.0, \frac{-0.3208 - \text{iso\_anomaly\_score}}{-0.3208 - (-0.6270)}\right)\right)$$

### 4.3 Weak-Supervised Factory-Level Tamper Model
- **Training Script**: [`ml_pipeline/train_xgboost_weak_supervision.py`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/ml_pipeline/train_xgboost_weak_supervision.py)
- **Artifacts**: `factory_tamper_model.joblib`, `factory_scaler.joblib`, `factory_tamper_feature_cols.joblib`
- **Methodology & Proxy Labels**:
  > ⚠️ **Important Clarification**: Because public OCEMS datasets lack physical ground-truth records of confirmed illegal tampering, this model is trained using **proxy labels** derived from the fingerprint rule engine ($\ge 3$ of 8 fingerprints triggered = proxy positive $y=1$). It serves as a smoothed statistical model over factory-level aggregated telemetry features (`value_mean`, `value_std`, `rolling_mean_mean`, `rolling_mean_std`, `rolling_std_mean`, `rolling_std_std`, `flatline_flag_mean`, `flatline_flag_std`).
- **Validation**: Evaluated via Leave-One-Out Cross Validation (LOOCV):
  - **ROC-AUC**: `0.854`
  - **Spearman Rank Correlation**: `0.677`

### 4.4 Composite Risk Score Mathematical Formulation
- **File**: [`ml_pipeline/risk_engine.py`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/ml_pipeline/risk_engine.py)
- **Formula**:
  $$\text{Composite Score} = (0.10 \cdot P_{\text{tamper}}) + (0.225 \cdot \text{ISO}_{\text{norm}}) + \left(0.675 \cdot \frac{\text{Triggered Fingerprints}}{8}\right)$$
  $$\text{Risk Score} = \text{round}(\text{Composite Score} \cdot 100, 1)$$

### 4.5 Risk Categorization & Recommended Action Triggers
```
+------------------+----------------------------------+--------------------------------------------------------+
|  Risk Category   |          Trigger Bounds          |              Recommended System Action                 |
+------------------+----------------------------------+--------------------------------------------------------+
| CRITICAL         | Score >= 75 OR Fingerprints >= 4 | Flag for immediate physical audit & site inspection   |
| HIGH             | Score >= 50 OR Fingerprints >= 2 | Issue notice of telemetry anomaly & 48h audit schedule |
| MEDIUM           | Score >= 25 OR Fingerprints >= 1 | Recommend sensor calibration check & monitoring        |
| LOW              | Score < 25 AND Fingerprints == 0 | Standard routine surveillance                          |
+------------------+----------------------------------+--------------------------------------------------------+
```

---

## 5. Explainable AI (XAI) & SHAP Attributions

### 5.1 Dual-Model SHAP Explainer Pipeline
- **Script**: [`ml_pipeline/compute_shap_explanations.py`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/ml_pipeline/compute_shap_explanations.py)
- **Output Artifact**: [`Data/RawData/factory_shap_explanations.json`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/Data/RawData/factory_shap_explanations.json)

### 5.2 KernelExplainer & LinearExplainer Methodology
1. **Weak-Supervised Model (10% weight)**: Computed via `shap.LinearExplainer` on the L2 Logistic Regression feature coefficients.
2. **Isolation Forest (22.5% weight)**: Computed using `shap.KernelExplainer` against `iso_forest.score_samples()`. Given high reading volumes (median ~31k readings/factory), SHAP values are computed on a random sample of 150 readings per factory evaluated against 30 background samples.

---

## 6. Backend API & Database Infrastructure Code Trace

### 6.1 Relational Database Schema & Seeding Logic
- **ORM Schema**: [`backend/models.py`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/backend/models.py)
- **Database Engine**: [`forensier.db`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/forensier.db) (SQLite database instance).
- **Seeder Script**: [`database/seed_db.py`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/database/seed_db.py)

#### Primary Database Tables:
- `factories`: Stores `factory_id`, `name`, `industry_type`, `location`, `risk_score`, `risk_category`, `xgb_probability`, `anomaly_score_norm`, `status`.
- `fingerprint_scores`: Magnitude values and 0/1 trigger decisions for all 8 fingerprints.
- `inspection_events`: Scheduled and past inspection records.
- `telemetry_records`: Time-series telemetry entries (`parameter`, `value`, `timestamp`, `quality_code`).
- `alerts`: System notifications for HIGH and CRITICAL risk facilities.
- `consent_limits`: CTO legal discharge parameters.
- `system_thresholds`: System risk weights and operational boundaries.

### 6.2 FastAPI Endpoint Mapping
- **File**: [`backend/main.py`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/backend/main.py)

| HTTP Method | Route Endpoint | Purpose | Backing Source |
|---|---|---|---|
| `POST` | `/api/auth/login` | JWT Authentication route (`admin` / `inspector`). | Config Defaults |
| `GET` | `/api/factories` | Retrieves facility list with risk scores & categories. | `forensier.db` (`factories`) |
| `GET` | `/api/factories/{id}` | Profile details, sensor health score, and peer similarity. | `forensier.db` & Cache |
| `GET` | `/api/factories/{id}/predictions` | Summary prediction object, fingerprints, and action items. | `risk_engine.py` & DB |
| `GET` | `/api/factories/{id}/shap` | Feature SHAP attribution values. | `factory_shap_explanations.json` |
| `GET` | `/api/alerts` | Open High/Critical system alerts. | `forensier.db` (`alerts`) |
| `GET` | `/api/dataset-quality` | Overall data availability & coverage metrics. | `dataset_quality_summary_v2.csv` |

---

## 7. Frontend Architecture & Visualization Layer

The front end is built as a single-page React application using Vite and Vanilla CSS.

- **Component Navigation Structure** ([`frontend/src/components/Sidebar.jsx`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/frontend/src/components/Sidebar.jsx)):
  - **Executive Dashboard** ([`ExecutiveDashboardPage.jsx`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/frontend/src/components/ExecutiveDashboardPage.jsx)): Regional risk summary charts and factory risk tables.
  - **AI Forensic Analysis** ([`AIAnalysisPage.jsx`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/frontend/src/components/AIAnalysisPage.jsx)): Diagnostic breakdown including SHAP contribution bar plots, composite risk score displays, and fingerprint detail panels.
  - **Factory Dossier** ([`FactoryDetailDossierPage.jsx`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/frontend/src/components/FactoryDetailDossierPage.jsx)): Individual facility dossiers, parameter charts vs CTO consent limits, and inspection timelines.
  - **Alerts Portal** ([`AlertsPage.jsx`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/frontend/src/components/AlertsPage.jsx)): List of active system alerts and recommended actions.
  - **Dataset Quality** ([`DatasetQualityPage.jsx`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/frontend/src/components/DatasetQualityPage.jsx)): Coverage metrics, outage logs, and data completeness summaries.
  - **Reports Center** ([`ReportsCenterPage.jsx`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/frontend/src/components/ReportsCenterPage.jsx)): On-demand dossier PDF generator with current-year report IDs (`FR-2026-#{id}`).
  - **Institutional Oversight & Admin Portal** ([`InstitutionalOversightPage.jsx`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/frontend/src/components/InstitutionalOversightPage.jsx), [`AdminPortalPage.jsx`](file:///c:/Users/gauri/OneDrive/Desktop/ForensiAir---AI-powered-surveillance/frontend/src/components/AdminPortalPage.jsx)): System threshold settings, model governance information, and access logs.

---

## 8. Data Integrity Audit: Hardcoded vs Precomputed vs Real Dynamic Data

This section details the origin and processing state of data within the application.

```
+---------------------------------------------------------------------------------------------------+
|                                     DATA INTEGRITY MATRIX                                         |
+------------------------------------+--------------------------------+-----------------------------+
|        REAL & DYNAMIC              |         PRECOMPUTED            |      STATIC / FALLBACK      |
|  - Real Telemetry (1M+ rows)       |  - forensier.db SQLite DB      |  - User Login Credentials   |
|  - 8 Fingerprint Detectors         |  - SHAP JSON Explanations      |  - Default Factory Names    |
|  - Composite Risk Engine           |  - factory_profiles.parquet    |  - Historical Audit Logs    |
|  - Isolation Forest & Weak LR      |                                |  - Dynamic Report ID Year   |
+------------------------------------+--------------------------------+-----------------------------+
```

### 8.1 Real & Dynamically Computed Data
- **MPCB Telemetry**: All 33 core factories use real continuous effluent monitoring data (`Data/RawData/real_features.parquet`), including real parameter measurements, rolling averages, rolling standard deviations, and parameter cross-correlations.
- **Fingerprint Rule Evaluation**: Evaluated from real telemetry anomalies against defined threshold criteria.
- **Machine Learning Inference**: Isolation Forest anomaly scores and Weak-Supervision Logistic Regression probabilities are computed directly from telemetry feature matrices.
- **Composite Risk Calculation**: Computed per factory using the weighted formula ($10\%$ Weak LR + $22.5\%$ Normalized ISO + $67.5\%$ Fingerprints).
- **Search & Alerts Filtering**: Header search filters active factory records live by ID or name, and the notification bell dynamically reflects the count of High/Critical facilities.

### 8.2 Precomputed / Cached Data (Performance Optimization)
- **Database Initialization (`forensier.db`)**: Pre-seeded via `database/seed_db.py` to prevent CPU and memory overhead during server initialization on cloud platforms.
- **SHAP Explanations (`factory_shap_explanations.json`)**: Precomputed per factory to avoid multi-minute live KernelExplainer evaluation times during API requests.
- **Factory Behavioral Profiles (`factory_profiles.parquet`)**: Generated offline by the Characterization Engine from dataset summary files.

### 8.3 Static, Hardcoded, or Fallback Data
- **Authentication Defaults**: Default admin/inspector credentials exist in `backend/config.py` as fallback values when environment variables are unconfigured.
- **Fallback Name Mapping**: `NAME_MAPPING` in `database/seed_db.py` provides default human-readable names for the 33 site IDs (e.g. `site_1369` $\rightarrow$ `"M/s.Privi Specialty Chemicals Ltd(Unit-II)"`) if PostgreSQL connection is unavailable.
- **System Audit Log Entries**: Pre-session historical audit logs in `AdminPortalPage.jsx` display default demonstration entries.
- **PDF Report ID Generation**: Reports in `ReportsCenterPage.jsx` generate IDs using the current calendar year (`FR-2026-#{factory_id}`) as historical export timestamps are not persisted.
- **Synthetic Dataset**: `synthetic_features.parquet` is kept in the repository as a baseline reference from early iterations but is **not used** for production factory risk scoring.
