# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

ForensiAIR: an AI system that detects **data tampering** in industrial environmental telemetry (OCEMS — pH, COD, BOD, TSS, Flow, SO₂, NOx, etc.) reported by factories to regulators. It does not just flag threshold violations — it engineers "Tampering Fingerprint" features (flatline, limit hugging, correlation break, copy-paste, coordinated missing data, pre-inspection dips, impossible values) and feeds them to ML models to produce a per-factory Tamper Suspicion Index (TSI) and risk tier.

The repo is a monorepo containing the full pipeline: scraping → feature engineering → characterization → ML training → FastAPI backend → React dashboard.

## Architecture / data flow

```
scraper/                       → raw OCEMS telemetry + CTO consent PDFs + inspection schedules (MPCB site)
  ↓ (writes to Postgres and/or Original Data/*.csv)
Original Data/*.csv            → cleaned/exported CSVs (factories, consents, monitoring_data, quality summaries)
  ↓
Feature Engineering/
  "Raw Data Feature Engineering"       → real telemetry → Data/RawData/real_features.parquet
  "Synthetic Data Feature Engineering" → synthetic tamper injection → Data/SynData/synthetic_features.parquet
  ↓
Characterization Engine/characterization_engine.py → factory_profiles.parquet (per-factory behavioral profile)
  ↓
ml_pipeline/train_models.py    → trains StandardScaler, XGBoost (synthetic, supervised), IsolationForest (real, unsupervised)
                                   artifacts saved to ml_pipeline/models/*.joblib
ml_pipeline/inference.py       → loads models, produces per-record predictions
ml_pipeline/risk_engine.py     → calculate_composite_risk(): blends XGBoost prob + IsolationForest anomaly score
                                   + fingerprint trigger count into a 0-100 risk_score / CRITICAL-HIGH-MEDIUM-LOW category
  ↓
backend/ (FastAPI, run standalone, port 8000)
  ↓ (HTTP, hardcoded to http://127.0.0.1:8000, no proxy/env var)
frontend/ (React + Vite, port 5173)
```

There are actually **two parallel model families** in `ml_pipeline/models/`:
- A "Stage 1" per-factory model (`stage1_site_<id>.joblib`) — only exists for ~11 factories (`stage1_matched_sites` in `backend/main.py`); other factories fall back to `"NOT_AVAILABLE"` for stage1 predictions.
- A "Stage 2" global 9-class tamper-type classifier (`xgboost_stage2_tamper.joblib` + `stage2_label_encoder.joblib` + `stage2_scaler.joblib` + `stage2_feature_cols.joblib`) used for every factory.

`backend/main.py` also blends deterministic domain rules on top of raw model output (e.g. it overrides `pred_cls`/`tamper_probability` based on `risk_tier` bands when the model predicts `NONE`/`COMPLIANT`) — read that logic before assuming API responses are pure model output.

### Backend data loading (important gotcha)

`backend/main.py` uses a module-level `_data_cache` dict populated lazily by `get_data_cache()` on first request. It loads, in order: `Original Data/dataset_quality_summary*.csv`, `Data/RawData/tsi_scores.csv`, `Data/RawData/factory_shap_attributions.csv`, `Data/RawData/real_features.parquet`, `Data/SynData/synthetic_features.parquet`, and all `ml_pipeline/models/*.joblib` artifacts. Paths are resolved relative to CWD first, then relative to the repo root — **run the backend from the repo root** or these fallbacks matter. If you add/regenerate a dataset or model artifact, the cache only refreshes on process restart (there is no invalidation).

### Persistence

- `forensiair.db` — SQLite (gitignored), created via `backend/database.py` / `backend/models.py` (SQLAlchemy). Schema: `Factory`, `FingerprintScore`, `InspectionEvent`, `TelemetryRecord`, `Alert`, `ConsentLimit`, `SystemThreshold`, `UserAccess`.
- `database/seed_db.py` seeds SQLite from the ML risk engine output and a hardcoded `NAME_MAPPING` of `site_<id> → (name, region, industry)`. It also has an optional fallback path to read live factory names from a local Postgres instance (`get_pg_factory_mapping()`) if `psycopg2` + a running Postgres are available — this is best-effort and silently falls back to the hardcoded mapping.
- `scraper/` has its own independent Postgres-backed ingestion path (`load_data.py`, `load_ph.py`, `collector/consent`, `collector/inspection`) — this is upstream of everything else and does not feed the FastAPI backend directly; it produces the CSVs under `Original Data/` / `Data/`.

## Commands

### Backend (FastAPI)
```bash
# from repo root
uvicorn backend.main:app --reload --port 8000
```
No `requirements.txt` at repo root for backend — dependencies (fastapi, uvicorn, pandas, numpy, joblib, pyjwt, sqlalchemy) must be installed manually into the active Python env.

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev       # Vite dev server, default port 5173
npm run build
npm run lint       # oxlint
npm run preview
```
The frontend calls the backend directly at `http://127.0.0.1:8000` (hardcoded per-component in `fetch()` calls, e.g. `frontend/src/components/ExecutiveDashboardPage.jsx`) — there is no `.env` or Vite proxy. Both servers must be running locally for the UI to show live data.

### ML pipeline
```bash
cd ml_pipeline
python train_models.py     # retrains scaler/XGBoost/IsolationForest, writes to ml_pipeline/models/
```

### Feature engineering (each has its own `requirements.txt`)
```bash
cd "Feature Engineering/Raw Data Feature Engineering"
python run_raw.py          # → Data/RawData/real_features.parquet; params in config.yaml

cd "Feature Engineering/Synthetic Data Feature Engineering"
python run_synthetic.py    # → Data/SynData/synthetic_features.parquet; params in config.yaml
```

### DB seeding
```bash
python database/seed_db.py   # populates forensiair.db (SQLite) from ML output + NAME_MAPPING
```

There is no test suite currently in this repo.

## Auth

Backend auth (`backend/config.py`, `backend/main.py`) is a minimal JWT scheme with two hardcoded roles: `admin`/`admin123` and `inspector`/`inspector123` (overridable via `ADMIN_USERNAME`/`ADMIN_PASSWORD`/`INSPECTOR_USERNAME`/`INSPECTOR_PASSWORD`/`SECRET_KEY` env vars). Tokens are also accepted as the literal strings `admin_token`/`inspector_token` for quick testing. `require_role([...])` gates admin-only endpoints (data quality, admin users, pipeline status). This is prototype-grade auth, not production security — don't upgrade it opportunistically as part of unrelated changes without flagging it.

## Frontend structure

Single-page app in `frontend/src/App.jsx` — no router library; page switching is done via `activeTab` state and a `switch` statement, with `userRole` state (`admin`/`inspector`) gating access to `dataset-quality` and `administration` tabs client-side only (the real enforcement is server-side via `require_role`). Pages live in `frontend/src/components/*Page.jsx`, one per dashboard section (Executive Dashboard, AI Analysis, Explainability, Factory Detail Dossier, Reports Center, Dataset Quality, Admin Portal, Institutional Oversight). Styling is Tailwind v4 (via `@tailwindcss/vite`) plus some inline styles and `App.css`/`index.css`. Charts use `recharts`, icons use `lucide-react`.

## Notes on repo hygiene

- `Original Data/`, `Data/`, `ml_pipeline/models/*.joblib`, and `*.parquet` files are checked-in data/model artifacts, not generated at build time — treat them as inputs, don't regenerate blindly.
- Several top-level zip files (`ml_pipeline.zip`, `ml_pipeline (2).zip`) appear to be snapshots/backups, not build artifacts — leave them alone unless asked.
- `design/` contains static design references per dashboard page (not application code).
