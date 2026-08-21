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
                                          fingerprint_engine.py → Data/RawData/factory_fingerprint_scores.csv
                                          (8 tamper fingerprint checks, real magnitudes + 0/1 trigger decisions,
                                          per factory)
  "Synthetic Data Feature Engineering" → synthetic tamper injection → Data/SynData/synthetic_features.parquet
                                          (kept for reference; no deployed model trains on this anymore, see below)
  ↓
Characterization Engine/characterization_engine.py → factory_profiles.parquet (per-factory behavioral profile)
  ↓
ml_pipeline/train_models.py             → trains IsolationForest (unsupervised, real telemetry only) →
                                            iso_forest.joblib / iso_scaler.joblib
ml_pipeline/train_xgboost_weak_supervision.py → trains the factory-level tamper model: L2-regularized logistic
                                            regression on real telemetry aggregated per factory, proxy-labeled
                                            from fingerprint trigger counts (>=3/8 triggered = proxy-tampered) →
                                            factory_tamper_model.joblib / factory_scaler.joblib /
                                            factory_tamper_feature_cols.joblib
ml_pipeline/compute_shap_explanations.py → real SHAP for both trained models above (shap.LinearExplainer for the
                                            LR tamper model; shap.KernelExplainer against IsolationForest's
                                            score_samples(), sampled per factory -- shap.TreeExplainer was tested
                                            and confirmed non-additive/wrong for IsolationForest, don't use it) →
                                            Data/RawData/factory_shap_explanations.json
ml_pipeline/risk_engine.py     → calculate_composite_risk(): blends the factory-level tamper model probability
                                   (10% weight) + IsolationForest anomaly score (22.5%) + fingerprint trigger
                                   ratio (67.5%) into a 0-100 risk_score / CRITICAL-HIGH-MEDIUM-LOW category
database/seed_db.py             → runs the above and writes results into forensiair.db (SQLite) -- this database,
                                   not any CSV, is what the live backend actually reads
  ↓
backend/ (FastAPI, run standalone, port 8000) -- reads forensiair.db + factory_shap_explanations.json;
  runs no model inference live, only precomputed values (see "Backend data loading" below)
  ↓ (HTTP, hardcoded to http://127.0.0.1:8000, no proxy/env var, centralized in frontend/src/config.js's apiFetch())
frontend/ (React + Vite, port 5173)
```

Stage 1 (per-factory XGBoost) and Stage 2 (9-class tamper-type classifier) existed in earlier iterations of this
repo and have been **fully removed**, backend and frontend both — neither had a training script anywhere in the
repo (undocumented `.joblib` artifacts with no reproducible provenance) and neither ever fed
`calculate_composite_risk()`; they were diagnostic-only. Don't reintroduce this pattern or expect these
files/endpoints to exist.

`backend/main.py`'s `_explain_risk_drivers()` (formerly `_classify_tamper()`) no longer overrides model output
with a guessed label — `tamper_probability` is just the real composite `risk_score`, and its `note` names which
real fingerprint checks are driving a HIGH/CRITICAL score. Read that function before assuming API responses are
anything other than the real composite arithmetic.

### Backend data loading (important gotcha)

`backend/main.py` uses a module-level `_data_cache` dict populated lazily by `get_data_cache()` on first request.
It loads, in order: `Original Data/dataset_quality_summary*.csv`, factory + fingerprint scores from
`forensiair.db` (SQLite, via `_load_factory_scores()` — **not** `Data/RawData/tsi_scores.csv`, which has no
generator script anywhere in this repo and is no longer read), `Data/RawData/factory_shap_explanations.json`
(real precomputed SHAP, see above — replaces the now-unread `Data/RawData/factory_shap_attributions.csv`, which
matched the removed Stage-2 model's feature set and is left on disk untouched and unused — `ModelVersionsTab.jsx`
used to cite it as an "Active" model source with fabricated trained/retrained dates; that whole entry, along with
an invented changelog and a fake training-metadata panel, has since been removed, so nothing in the app reads or
displays this file anymore), `Data/RawData/real_features.parquet`,
`Data/SynData/synthetic_features.parquet`. The backend does **not** load any `.joblib` model file or run live
inference — Stage 1/2 removal took the last live-inference code path with it; `ml_pipeline/models/*.joblib` is
read only by the offline training/SHAP-precompute scripts, never by `backend/main.py`. Paths are resolved
relative to CWD first, then relative to the repo root — **run the backend from the repo root** or these
fallbacks matter. If you add/regenerate a dataset, rerun `database/seed_db.py` and/or
`ml_pipeline/compute_shap_explanations.py` as appropriate; the cache only refreshes on process restart either
way (there is no invalidation).

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
No `requirements.txt` at repo root for backend — dependencies (fastapi, uvicorn, pandas, numpy, pyjwt, sqlalchemy) must be installed manually into the active Python env. `joblib` is not one of them — Stage 1/2 removal took the backend's last `.joblib`-loading code with it; it's only needed by the `ml_pipeline/` training/precompute scripts.

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev       # Vite dev server, default port 5173
npm run build
npm run lint       # oxlint
npm run preview
```
The frontend calls the backend at `http://127.0.0.1:8000` via `apiFetch()` (`frontend/src/config.js`), a thin
wrapper every component uses instead of raw `fetch()` — it centralizes the base URL, attaches
`Authorization: Bearer <token>` from `sessionStorage` on every request, and on any 401 clears the session and
ends it app-wide (see Auth below). There is no `.env`-based override beyond `VITE_API_BASE_URL`, and no Vite
proxy. Both servers must be running locally for the UI to show live data.

### ML pipeline
```bash
cd ml_pipeline
python train_models.py                    # retrains iso_scaler/iso_forest (IsolationForest only now — the
                                            # synthetic-data XGBoost this script used to also train was retired
                                            # for over-flagging real readings; see risk_engine.py)
python train_xgboost_weak_supervision.py   # retrains factory_scaler/factory_tamper_model (LR); standalone,
                                            # does not touch production files itself
python compute_shap_explanations.py        # precomputes real SHAP for both trained models, all factories →
                                            # Data/RawData/factory_shap_explanations.json (needs `pip install
                                            # shap` — only this script needs it, not the backend)
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

The frontend now actually uses this end to end. `frontend/src/components/LoginPage.jsx` calls
`POST /api/auth/login` for real and stores the returned JWT in `sessionStorage` (not `localStorage` — smaller
XSS exposure window; this was an explicit, discussed tradeoff, not a default). Every request goes through
`apiFetch()` (`frontend/src/config.js`), which attaches `Authorization: Bearer <token>` automatically. On any
401, `apiFetch()` clears the token and dispatches a `forensiair:unauthorized` window event; `App.jsx` listens for
it and clears `currentUser`, which is this app's "redirect to login" (no router exists — `App.jsx` renders
`<LoginPage>` whenever `currentUser` is null). A 401 always means the session is dead; a 403 from `require_role`
is left alone — that's a legitimate, informative response about the wrong role, not an auth failure, and isn't
what triggers a forced logout. `GET /api/me` (reuses the same `get_current_user` dependency every protected
route already uses) is what hydrates the real logged-in username/role/session-expiry shown in `Sidebar.jsx` /
`TopHeader.jsx`. The old client-side-only "Role: Admin/Inspector" demo dropdown and the 403 page's self-service
"Switch to Admin Role (Demo Mode)" button are both gone — switching roles now means logging out and back in with
the other test account, the same as a real deployment would require.

Two admin-gated pages worth knowing the real state of: `DatasetQualityPage.jsx` (`GET /api/data-quality`) is a
real, working endpoint and now renders its actual response shape (`dataset_summaries`, per-factory
coverage/missing/duplicate/quality_grade/readiness_score) — it used to assume a shape the backend never
produced, so it silently showed fabricated fallback data even when auth was working. Its fallback dataset (5 fake
factories, a made-up 940,000 record count) has since been removed entirely; a failed fetch or unexpected shape now
renders an honest "Unable to load" screen with a Retry button instead, since a fallback silently masked real
failures (e.g. the backend being mid-restart, which isn't a 401 and so isn't caught by the auth interceptor
either) for as long as the component stayed mounted. `GET /api/admin/users`, by
contrast, is still a `{"status": "not_implemented"}` stub — no user-management DB model exists — and
`AdminPortalPage.jsx`'s Users tab correctly stays in its honest demo-fallback banner state; a 200 response from
that endpoint is not the same as real data, and code reading it checks for an array, not just `res.ok`. Its
Consent Limits tab, by contrast, is real: `GET /api/admin/consent-limits` reads the `consent_limits` table
(regulatory min/max per parameter — pH, BOD, COD, TSS, Flow, DO, Temperature — seeded by `database/seed_db.py`),
replacing an old fabricated per-industry shape that had no endpoint behind it at all. The old Notification Rules
tab (no backing endpoint ever existed) has been removed rather than left as a dead stub.

`SettingsPage.jsx` is real, not a placeholder: it shows the same `currentUser` session data (username, role, JWT
`exp` as session expiry) `App.jsx` already hydrates from `GET /api/me` for `Sidebar.jsx`/`TopHeader.jsx`, plus a
working Logout button. It does not show theme or notification preferences — no user-preferences table exists
anywhere in the backend — and says so rather than inventing controls that wouldn't do anything.

## Frontend structure

Single-page app in `frontend/src/App.jsx` — no router library. Before rendering anything else, it validates any
stored session token against `GET /api/me` and renders `LoginPage.jsx` until a real session exists (see Auth
above). Once logged in, page switching is done via `activeTab` state and a `switch` statement, with `userRole`
(`currentUser.role`, sourced from the real JWT — not a client-side togglable dropdown) gating access to
`dataset-quality` and `administration` tabs client-side only (the real enforcement is still server-side via
`require_role`). Pages live in `frontend/src/components/*Page.jsx`, one per dashboard section (Executive
Dashboard, **AI Analysis** — merged with the former standalone Explainability page, which no longer exists as a
separate route/file — Factory Detail Dossier, Reports Center, Dataset Quality, Admin Portal, Institutional
Oversight, Alerts, Settings). Styling is Tailwind v4 (via `@tailwindcss/vite`) plus some inline styles and `App.css`/`index.css`. Charts use `recharts`, icons use `lucide-react`.

## Notes on repo hygiene

- `Original Data/`, `Data/`, `ml_pipeline/models/*.joblib`, `*.parquet`, and `Data/RawData/factory_shap_explanations.json` (precomputed SHAP, regenerate via `ml_pipeline/compute_shap_explanations.py`) are checked-in data/model artifacts, not generated at build time — treat them as inputs, don't regenerate blindly.
- Several top-level zip files (`ml_pipeline.zip`, `ml_pipeline (2).zip`) appear to be snapshots/backups, not build artifacts — leave them alone unless asked.
- `design/` contains static design references per dashboard page (not application code).
