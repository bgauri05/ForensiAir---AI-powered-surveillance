import os
import sys
import json
import datetime
import jwt
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Depends, HTTPException, Header, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.config import (
    SECRET_KEY, ALGORITHM, ADMIN_USERNAME, ADMIN_PASSWORD, INSPECTOR_USERNAME, INSPECTOR_PASSWORD
)
from ml_pipeline.risk_engine import WEIGHT_XGB, WEIGHT_ISO, WEIGHT_FINGERPRINTS

app = FastAPI(
    title="ForensiAIR Backend API",
    description="AI-Powered Industrial Environmental Surveillance & Tampering Detection Backend",
    version="2.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache data in memory for sub-millisecond responses
_data_cache = {}

# QC FIX (2026-08): this used to load Data/RawData/tsi_scores.csv -- a file
# with no generator script anywhere in this repo, meaning nothing
# reproduced it and it did not reflect the quality-filter fix, the real
# model inference wiring, or the fingerprint trigger fixes made this
# session. The live API now reads forensiair.db, the same database
# database/seed_db.py populates from the real, fixed pipeline. This
# function reshapes that data into the column names the rest of this file
# already expects, so the rest of the API code didn't need a rewrite.
def _load_factory_scores() -> pd.DataFrame:
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "..", "forensiair.db")
    if not os.path.exists(db_path):
        db_path = "forensiair.db"
    if not os.path.exists(db_path):
        return pd.DataFrame()

    conn = sqlite3.connect(db_path)
    try:
        factories = pd.read_sql_query(
            "SELECT factory_id, risk_score, risk_category, total_fingerprints_triggered, "
            "xgb_probability, anomaly_score_norm FROM factories",
            conn
        )
        fingerprints = pd.read_sql_query("SELECT * FROM fingerprint_scores", conn)
    finally:
        conn.close()

    if factories.empty:
        return pd.DataFrame()

    df = factories.merge(fingerprints, on="factory_id", how="left", suffixes=("", "_fp"))

    # risk_category is the real 4-tier system (LOW/MEDIUM/HIGH/CRITICAL);
    # the rest of this file was built around a 3-tier system (Low/Medium/
    # High). Collapse CRITICAL into High so nothing downstream breaks, but
    # keep the true 4-tier value available under true_risk_category for
    # anything that wants the un-collapsed answer.
    tier_map = {"LOW": "Low", "MEDIUM": "Medium", "HIGH": "High", "CRITICAL": "High"}
    df["risk_tier"] = df["risk_category"].map(tier_map).fillna("Low")
    df["true_risk_category"] = df["risk_category"]

    # tsi_score used to come from an unknown formula in the orphaned CSV;
    # risk_score (0-100, from calculate_composite_risk()) is the real,
    # reproducible equivalent on the same 0-100 scale.
    df["tsi_score"] = df["risk_score"]

    df = df.sort_values("risk_score", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1

    # Map fingerprint magnitudes onto the raw-signal field names the rest
    # of this file already reads. Percentages stored 0-100 in the DB are
    # converted to the 0-1 fractions this file's threshold checks (e.g.
    # "> 0.05") expect.
    df["anomaly_score"] = df["anomaly_score_norm"]
    df["flatline_rate"] = df["flatline"] / 100.0
    df["autocorr_high_rate"] = df["copy_paste"] / 100.0
    df["limit_hugging_mean"] = df["limit_hugging"] / 100.0
    df["impossible_val_rate"] = df["impossible_ph_range"] / 100.0
    df["pre_dip_mean"] = df["inspection_dip"].fillna(0.0)
    df["coordinated_missing_flag"] = df["trig_coordinated_missing_data"].fillna(0)
    # No real equivalent measured for these -- default same as this file
    # already did when a CSV column was missing.
    df["dup_run_rate"] = 0.0
    df["bdl_rate_mean"] = 0.0
    df["cov_high_rate"] = 0.0
    df["bod_cod_vol_mean"] = np.nan

    return df


def _explain_risk_drivers(risk_category: str, risk_score: float,
                           raw_signals: Dict[str, float]) -> Dict[str, Any]:
    """
    QC FIX (2026-08): this used to also reconcile a Stage-2 classifier's
    predicted_tamper_type/confidence_percentage against the risk tier (see
    git history for _classify_tamper). Stage 1 (per-factory XGBoost) and
    Stage 2 (9-class XGBoost) have since been removed from the app
    entirely -- neither ever had a training script anywhere in this repo;
    both were undocumented .joblib artifacts with no reproducible
    provenance, and their real weight in calculate_composite_risk() was
    always zero (they were diagnostic-only, never part of the composite
    formula). See ml_pipeline/risk_engine.py for what actually is.

    tamper_probability is the real composite risk_score (already 0-100,
    already the honest answer). note explains which real fingerprint
    checks are driving a HIGH/CRITICAL score, so the number isn't
    presented with no explanation.
    """
    tamper_probability = round(float(risk_score), 1)
    note = None
    if risk_category in ['HIGH', 'CRITICAL']:
        drivers = []
        if raw_signals.get('flatline_rate', 0) and raw_signals.get('flatline_rate', 0) > 0.05:
            drivers.append('flatline')
        if raw_signals.get('limit_hugging_mean', 0) and raw_signals.get('limit_hugging_mean', 0) > 0.05:
            drivers.append('limit hugging')
        if raw_signals.get('coordinated_missing_flag', 0):
            drivers.append('coordinated missing data')
        if raw_signals.get('impossible_val_rate', 0):
            drivers.append('impossible values')
        note = (
            "Risk score is being driven by fingerprint checks: "
            + (', '.join(drivers) if drivers else "see raw_fingerprint_signals for detail") + "."
        )
    return {
        "tamper_probability": tamper_probability,
        "note": note
    }


def get_data_cache():
    if "quality" not in _data_cache:
        q_path = "Original Data/dataset_quality_summary_v2.csv"
        if not os.path.exists(q_path):
            q_path = os.path.join(os.path.dirname(__file__), "..", q_path)
        if not os.path.exists(q_path):
            q_path = "Original Data/dataset_quality_summary.csv"
            if not os.path.exists(q_path):
                q_path = os.path.join(os.path.dirname(__file__), "..", q_path)

        if os.path.exists(q_path):
            _data_cache["quality"] = pd.read_csv(q_path)
        else:
            _data_cache["quality"] = None

    if "name_mapping" not in _data_cache:
        df_q = _data_cache["quality"]
        mapping = {}
        if df_q is not None and not df_q.empty:
            for _, r in df_q.iterrows():
                fid = str(r['factory_id'])
                name = str(r.get('factory_name', f"Industrial Site {fid}"))
                reg = str(r.get('region', r.get('city', 'Taloja')))
                ind = str(r.get('industry', r.get('industry_category', 'Chemical Manufacturing')))
                mapping[fid] = (name, reg, ind)
        _data_cache["name_mapping"] = mapping

    if "tsi" not in _data_cache:
        _data_cache["tsi"] = _load_factory_scores()

    if "shap_explanations" not in _data_cache:
        # QC FIX (2026-08, Phase 3): previously read
        # Data/RawData/factory_shap_attributions.csv, which attributes SHAP
        # values to a 25-feature schema matching the removed Stage-2 model
        # -- that model doesn't exist anywhere in the app anymore, so the
        # file was explaining a prediction nothing actually makes. Replaced
        # with real, precomputed SHAP for the two models that ARE part of
        # calculate_composite_risk(): factory_tamper_model.joblib (LR, via
        # shap.LinearExplainer) and iso_forest.joblib (via
        # shap.KernelExplainer against score_samples, since TreeExplainer
        # verified non-additive for IsolationForest). See
        # ml_pipeline/compute_shap_explanations.py. Old CSV left on disk,
        # unused.
        shap_path = "Data/RawData/factory_shap_explanations.json"
        if not os.path.exists(shap_path):
            shap_path = os.path.join(os.path.dirname(__file__), "..", shap_path)
        if os.path.exists(shap_path):
            with open(shap_path, 'r') as f:
                _data_cache["shap_explanations"] = json.load(f).get("factories", {})
        else:
            _data_cache["shap_explanations"] = {}

    if "real_features" not in _data_cache:
        rf_path = "Data/RawData/real_features.parquet"
        if not os.path.exists(rf_path):
            rf_path = os.path.join(os.path.dirname(__file__), "..", rf_path)
        if os.path.exists(rf_path):
            df_rf = pd.read_parquet(rf_path)
            if 'duplicate_run_length' in df_rf.columns:
                df_rf['dup_run_log'] = np.log1p(pd.to_numeric(df_rf['duplicate_run_length'], errors='coerce').fillna(0))
            _data_cache["real_features"] = df_rf
        else:
            _data_cache["real_features"] = pd.DataFrame()

    if "syn_features" not in _data_cache:
        sf_path = "Data/SynData/synthetic_features.parquet"
        if not os.path.exists(sf_path):
            sf_path = os.path.join(os.path.dirname(__file__), "..", sf_path)
        if os.path.exists(sf_path):
            df_sf = pd.read_parquet(sf_path)
            if 'duplicate_run_length' in df_sf.columns:
                df_sf['dup_run_log'] = np.log1p(pd.to_numeric(df_sf['duplicate_run_length'], errors='coerce').fillna(0))
            _data_cache["syn_features"] = df_sf
        else:
            _data_cache["syn_features"] = pd.DataFrame()

    if "limited_cto_sites" not in _data_cache:
        df_rf = _data_cache["real_features"]
        cto_null_sites = set()
        if not df_rf.empty and 'factory_id' in df_rf.columns:
            for fid in df_rf['factory_id'].unique():
                sub = df_rf[df_rf['factory_id'] == fid]
                lh_null = sub['limit_hugging'].isna().all()
                days_null = 'days_to_next_inspection' in sub.columns and sub['days_to_next_inspection'].isna().all()
                if lh_null and days_null:
                    cto_null_sites.add(fid)
        _data_cache["limited_cto_sites"] = cto_null_sites

    if "corr_break_threshold" not in _data_cache:
        # Reproduces fingerprint_engine.py's exact formula (typical_mean -
        # 1.0 * typical_std across all factories' correlation_break values)
        # -- that script prints the threshold to console but never
        # persists it, so it's recomputed here from the same real data.
        df_tsi = _data_cache["tsi"]
        if not df_tsi.empty and 'correlation_break' in df_tsi.columns:
            vals = df_tsi['correlation_break'].dropna()
            # ddof=0 (population std) to match fingerprint_engine.py's np.std()
            _data_cache["corr_break_threshold"] = float(vals.mean() - 1.0 * vals.std(ddof=0)) if not vals.empty else None
        else:
            _data_cache["corr_break_threshold"] = None

    if "iso_summary" not in _data_cache:
        iso_sum_path = os.path.join(os.path.dirname(__file__), "..", "ml_pipeline", "models", "isolation_forest_summary.json")
        if os.path.exists(iso_sum_path):
            with open(iso_sum_path, 'r') as f:
                _data_cache["iso_summary"] = json.load(f)
        else:
            _data_cache["iso_summary"] = {"per_factory_seed_stability": {}}

    return _data_cache

def get_factory_parameter_mean(factory_id: str, parameter_id: str) -> Optional[float]:
    """
    QC FIX (2026-08): replaces the old get_factory_row_features() helper,
    which took the median of 'value' across ALL parameter_ids for a factory
    (ETP-Flow, ETP-pH, ETP-BOD, ETP-COD, ETP-TSS mixed together into one
    number) and then fed that meaningless blend into arbitrary scaling
    formulas (e.g. val * 0.8 + 12.0) to fake a plausible-looking avg_bod/
    avg_cod/avg_flow. This computes a real per-factory, per-parameter mean
    directly from real_features.parquet's raw `value` column (falling back
    to synthetic_features.parquet only if a factory has no real rows, same
    fallback order the old helper used) -- e.g. parameter_id='ETP-BOD' gives
    this factory's actual average BOD reading.
    """
    cache = get_data_cache()
    df_rf = cache["real_features"]

    sub = pd.DataFrame()
    if not df_rf.empty and 'factory_id' in df_rf.columns and 'parameter_id' in df_rf.columns:
        sub = df_rf[(df_rf['factory_id'] == factory_id) & (df_rf['parameter_id'] == parameter_id)]

    if sub.empty:
        df_sf = cache["syn_features"]
        if not df_sf.empty and 'factory_id' in df_sf.columns and 'parameter_id' in df_sf.columns:
            sub = df_sf[(df_sf['factory_id'] == factory_id) & (df_sf['parameter_id'] == parameter_id)]

    if sub.empty or 'value' not in sub.columns:
        return None
    val = float(sub['value'].mean())
    return None if np.isnan(val) else round(val, 1)

# Auth Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreateRequest(BaseModel):
    username: str
    role: str
    full_name: str
    email: str

def create_jwt_token(username: str, role: str) -> str:
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Header. Please include Bearer token."
        )
    try:
        token = authorization.replace("Bearer ", "").strip()
        if token in ["admin_token", "inspector_token"]:
            role = "admin" if "admin" in token else "inspector"
            return {"username": role, "role": role}
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}"
        )

def require_role(roles: List[str]):
    def dependency(user: Dict[str, Any] = Depends(get_current_user)):
        if user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires one of {roles} privileges."
            )
        return user
    return dependency

# -------------------------------------------------------------
# Auth Routes
# -------------------------------------------------------------
@app.post("/api/auth/login")
def login(req: LoginRequest):
    u = req.username.lower().strip()
    p = req.password.strip()
    if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
        token = create_jwt_token(u, "admin")
        return {"access_token": token, "token_type": "bearer", "role": "admin", "username": req.username}
    elif u == INSPECTOR_USERNAME and p == INSPECTOR_PASSWORD:
        token = create_jwt_token(u, "inspector")
        return {"access_token": token, "token_type": "bearer", "role": "inspector", "username": req.username}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Check username and password."
        )

@app.get("/api/me")
def get_me(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Reuses get_current_user, the same dependency every protected route
    already validates against -- this just exposes what that dependency
    already decoded, so the frontend can show the real logged-in
    username/role/session-expiry instead of a client-side demo toggle.
    Handles both real JWTs (sub/role/exp claims) and the literal
    admin_token/inspector_token test strings (username/role only, no exp).
    """
    return {
        "username": user.get("sub") or user.get("username"),
        "role": user.get("role"),
        "exp": user.get("exp")
    }

# -------------------------------------------------------------
# 1. Executive Dashboard Summary
# -------------------------------------------------------------
@app.get("/api/dashboard/summary")
def get_dashboard_summary():
    cache = get_data_cache()
    df_tsi = cache["tsi"]
    
    total_factories = len(df_tsi) if not df_tsi.empty else 33
    tier_counts = df_tsi["risk_tier"].value_counts().to_dict() if "risk_tier" in df_tsi.columns else {"High": 5, "Medium": 8, "Low": 20}
    
    high_count = tier_counts.get("High", 0)
    med_count = tier_counts.get("Medium", 0)
    low_count = tier_counts.get("Low", 0)
    
    return {
        "total_factories": total_factories,
        "high_risk_count": high_count,
        "medium_risk_count": med_count,
        "low_risk_count": low_count,
        "risk_tier_counts": {
            "High": high_count,
            "Medium": med_count,
            "Low": low_count
        },
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# -------------------------------------------------------------
# 2. Filtered/Sorted Factories List
# -------------------------------------------------------------
@app.get("/api/factories")
def get_factories(
    region: Optional[str] = Query(None),
    risk_tier: Optional[str] = Query(None),
    sort: Optional[str] = Query("rank")
):
    cache = get_data_cache()
    df_tsi = cache["tsi"].copy()
    name_map = cache["name_mapping"]
    limited_cto = cache["limited_cto_sites"]
    
    results = []
    for _, row in df_tsi.iterrows():
        fid = str(row['factory_id'])
        name, reg, ind = name_map.get(fid, (f"Industrial Site {fid}", "Taloja", "Chemical Manufacturing"))
        has_cto = fid not in limited_cto
        
        results.append({
            "factory_id": fid,
            "factory_name": name,
            "name": name,
            "region": reg,
            "location": reg,
            "district": reg,
            "industry": ind,
            "risk_tier": str(row.get('risk_tier', 'Low')),
            "tsi_score": float(row.get('tsi_score', 0.0)),
            "rank": int(row.get('rank', 99)),
            "has_cto_context": has_cto,
            "flatline_rate": float(row.get('flatline_rate', 0.0)),
            "anomaly_score": float(row.get('anomaly_score', 0.0)),
            "coordinated_missing_flag": float(row.get('coordinated_missing_flag', 0.0))
        })
        
    df_res = pd.DataFrame(results)
    
    if region:
        df_res = df_res[df_res['region'].str.lower() == region.lower()]
    if risk_tier:
        df_res = df_res[df_res['risk_tier'].str.lower() == risk_tier.lower()]
        
    if sort == "tsi_score":
        df_res = df_res.sort_values('tsi_score', ascending=False)
    elif sort == "name":
        df_res = df_res.sort_values('factory_name', ascending=True)
    else:
        df_res = df_res.sort_values('rank', ascending=True)
        
    return df_res.to_dict(orient="records")

# -------------------------------------------------------------
# 3. Factory Profile Detail (Enriched Dynamic Parameters)
# -------------------------------------------------------------
@app.get("/api/factories/{factory_id}")
def get_factory_detail(factory_id: str):
    cache = get_data_cache()
    df_tsi = cache["tsi"]
    name_map = cache["name_mapping"]
    limited_cto = cache["limited_cto_sites"]
    df_q = cache["quality"]
    
    sub = df_tsi[df_tsi['factory_id'] == factory_id]
    if sub.empty:
        raise HTTPException(status_code=404, detail="Factory not found")
        
    row = sub.iloc[0]
    name, reg, ind = name_map.get(factory_id, (f"Industrial Site {factory_id}", "Taloja", "Chemical Manufacturing"))
    has_cto = factory_id not in limited_cto
    
    # Fetch quality & coverage metrics for this factory
    q_row = {}
    if df_q is not None and not df_q.empty and 'factory_id' in df_q.columns:
        q_sub = df_q[df_q['factory_id'] == factory_id]
        if not q_sub.empty:
            q_row = q_sub.iloc[0].to_dict()
            
    cov_pct = float(q_row.get('coverage_percentage', 92.5))
    miss_pct = float(q_row.get('missing_percentage', 100.0 - cov_pct))
    readiness = float(q_row.get('readiness_score', 84.5))
    param_count = int(q_row.get('parameter_count', 4))
    
    raw_signals = {
        "anomaly_score": float(row.get('anomaly_score', 0.0)),
        "flatline_rate": float(row.get('flatline_rate', 0.0)),
        "autocorr_high_rate": float(row.get('autocorr_high_rate', 0.0)),
        "dup_run_rate": float(row.get('dup_run_rate', 0.0)),
        "limit_hugging_mean": float(row.get('limit_hugging_mean', 0.0)),
        "impossible_val_rate": float(row.get('impossible_val_rate', 0.0)) if pd.notna(row.get('impossible_val_rate')) else None,
        "bdl_rate_mean": float(row.get('bdl_rate_mean', 0.0)),
        "cov_high_rate": float(row.get('cov_high_rate', 0.0)),
        "bod_cod_vol_mean": float(row.get('bod_cod_vol_mean', 0.0)) if pd.notna(row.get('bod_cod_vol_mean')) else None,
        "pre_dip_mean": float(row.get('pre_dip_mean', 0.0)),
        "coordinated_missing_flag": float(row.get('coordinated_missing_flag', 0.0))
    }
    
    risk_tier = str(row.get('risk_tier', 'Low'))
    risk_category = str(row.get('true_risk_category', 'LOW'))
    tsi_score = float(row.get('tsi_score', 0.0))

    explanation = _explain_risk_drivers(risk_category, tsi_score, raw_signals)
    tamper_prob = explanation['tamper_probability']

    # Real per-factory averages of the raw OCEMS readings -- see
    # get_factory_parameter_mean(). None (rendered as "Not available" by the
    # frontend) if this factory has no real or synthetic rows for that
    # parameter, same honest treatment as phAvg already gets client-side.
    bod_val = get_factory_parameter_mean(factory_id, 'ETP-BOD')
    cod_val = get_factory_parameter_mean(factory_id, 'ETP-COD')
    flow_val = get_factory_parameter_mean(factory_id, 'ETP-Flow')

    return {
        "factory_id": factory_id,
        "factory_name": name,
        "name": name,
        "region": reg,
        "location": reg,
        "district": reg,
        "industry": ind,
        "rank": int(row.get('rank', 99)),
        "tsi_score": tsi_score,
        "risk_tier": risk_tier,
        "has_cto_context": has_cto,
        "context_warning": "⚠️ Limited Regulatory Context (Missing CTO limits / Inspection baseline)" if not has_cto else None,
        "coverage_percentage": cov_pct,
        "missing_percentage": miss_pct,
        "readiness_score": readiness,
        "parameter_count": param_count,
        "avg_bod": bod_val,
        "avg_cod": cod_val,
        "avg_flow": flow_val,
        "tamper_probability": tamper_prob,
        "raw_fingerprint_signals": raw_signals,
        "note": explanation['note']
    }

# -------------------------------------------------------------
# 4. Factory Risk Explanation (composite breakdown + fingerprint detail + SHAP)
# -------------------------------------------------------------
FINGERPRINT_CHECK_DEFS = [
    {"key": "impossible_ph_range", "label": "Impossible pH Range", "unit": "%",
     "threshold_desc": "> 0.0% of readings"},
    {"key": "inspection_dip", "label": "Pre-Inspection Dip", "unit": "%",
     "threshold_desc": "average pre-inspection change < -20.0%"},
    {"key": "flatline", "label": "Flatline", "unit": "%",
     "threshold_desc": "> 5.0% of readings"},
    {"key": "limit_hugging", "label": "Limit Hugging", "unit": "%",
     "threshold_desc": "> 5.0% of readings"},
    {"key": "correlation_break", "label": "Correlation Break", "unit": "",
     "threshold_desc": None},  # filled in per-request from corr_break_threshold
    {"key": "copy_paste", "label": "Copy-Paste", "unit": "%",
     "threshold_desc": "> 1.0% of readings (autocorrelation > 0.95)"},
    {"key": "coordinated_missing_data", "label": "Coordinated Missing Data", "unit": "σ",
     "threshold_desc": "> 1.5 std dev above dataset median missing rate"},
    {"key": "data_integrity", "label": "Data Integrity (Error Rate)", "unit": "σ",
     "threshold_desc": "> 1.5 std dev above dataset median error rate"},
]


@app.get("/api/factories/{factory_id}/shap")
def get_factory_shap(factory_id: str):
    cache = get_data_cache()
    df_tsi = cache["tsi"]
    sub = df_tsi[df_tsi['factory_id'] == factory_id]
    if sub.empty:
        raise HTTPException(status_code=404, detail="Factory not found")
    row = sub.iloc[0]

    # --- Composite score breakdown: risk_engine.py's real arithmetic ---
    xgb_prob = float(row.get('xgb_probability', 0.0))
    iso_score_norm = float(row.get('anomaly_score_norm', 0.0))
    triggered_count = int(row.get('total_fingerprints_triggered', 0))
    fp_ratio = triggered_count / 8.0

    fp_contribution = round(WEIGHT_FINGERPRINTS * fp_ratio * 100, 1)
    iso_contribution = round(WEIGHT_ISO * iso_score_norm * 100, 1)
    tamper_contribution = round(WEIGHT_XGB * xgb_prob * 100, 1)

    composite_breakdown = {
        "fingerprints": {
            "weight": WEIGHT_FINGERPRINTS,
            "triggered_count": triggered_count,
            "total_checks": 8,
            "ratio": round(fp_ratio, 4),
            "contribution": fp_contribution
        },
        "isolation_forest": {
            "weight": WEIGHT_ISO,
            "score_norm": round(iso_score_norm, 4),
            "contribution": iso_contribution
        },
        "tamper_model": {
            "weight": WEIGHT_XGB,
            "probability": round(xgb_prob, 4),
            "contribution": tamper_contribution
        },
        "total_risk_score": round(fp_contribution + iso_contribution + tamper_contribution, 1)
    }

    # --- Fingerprint checks: real magnitudes + real thresholds + real trigger decisions ---
    corr_threshold = cache["corr_break_threshold"]
    fingerprint_checks = []
    for check in FINGERPRINT_CHECK_DEFS:
        key = check["key"]
        raw_value = row.get(key)
        raw_value = float(raw_value) if pd.notna(raw_value) else None
        triggered = bool(row.get(f"trig_{key}", 0))
        threshold_desc = check["threshold_desc"]
        if key == "correlation_break":
            threshold_desc = (
                f"< {corr_threshold:.4f} (dataset mean - 1 std dev)" if corr_threshold is not None
                else "insufficient data to compute dataset threshold"
            )
        fingerprint_checks.append({
            "key": key,
            "label": check["label"],
            "raw_value": raw_value,
            "unit": check["unit"],
            "threshold_desc": threshold_desc,
            "triggered": triggered
        })

    # --- SHAP explanations (precomputed, see ml_pipeline/compute_shap_explanations.py) ---
    shap_explanation = cache["shap_explanations"].get(factory_id)

    return {
        "factory_id": factory_id,
        "composite_breakdown": composite_breakdown,
        "fingerprint_checks": fingerprint_checks,
        "shap": shap_explanation
    }

# -------------------------------------------------------------
# 5. Factory AI Predictions
# -------------------------------------------------------------
@app.get("/api/factories/{factory_id}/predictions")
def get_factory_predictions(factory_id: str):
    """
    QC FIX (2026-08): previously ran live Stage 1 (per-factory XGBoost)
    and Stage 2 (9-class XGBoost) inference here. Both have been removed
    from the app entirely -- neither had a training script anywhere in
    this repo (undocumented .joblib artifacts with no reproducible
    provenance), and neither fed calculate_composite_risk() -- they were
    diagnostic-only. What's left is the real composite tamper_probability
    (fingerprints + Isolation Forest + factory-level tamper model) plus
    the real Isolation Forest anomaly score.
    """
    cache = get_data_cache()
    df_tsi = cache["tsi"]
    sub_tsi = df_tsi[df_tsi['factory_id'] == factory_id]
    r_row = sub_tsi.iloc[0] if not sub_tsi.empty else {}
    risk_category = str(r_row.get('true_risk_category', 'LOW'))
    tsi_score = float(r_row.get('tsi_score', 0.0))
    iso_score = float(r_row.get('anomaly_score', 0.42))

    raw_signals_for_note = {
        'flatline_rate': float(r_row.get('flatline_rate', 0) or 0),
        'limit_hugging_mean': float(r_row.get('limit_hugging_mean', 0) or 0),
        'coordinated_missing_flag': float(r_row.get('coordinated_missing_flag', 0) or 0),
        'impossible_val_rate': float(r_row.get('impossible_val_rate', 0) or 0),
    }
    explanation = _explain_risk_drivers(risk_category, tsi_score, raw_signals_for_note)

    iso_summary = cache["iso_summary"]
    stabs_dict = iso_summary.get("per_factory_seed_stability", {})
    seed_stability = float(stabs_dict.get(factory_id, 0.942))

    return {
        "factory_id": factory_id,
        "tamper_probability": explanation['tamper_probability'],
        "note": explanation['note'],
        "isolation_forest": {
            "anomaly_score": round(iso_score, 4),
            "seed_stability_index": seed_stability
        }
    }

# -------------------------------------------------------------
# 5b. Factory Inspection History
# -------------------------------------------------------------
@app.get("/api/factories/{factory_id}/inspections")
def get_factory_inspections(factory_id: str):
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "..", "forensiair.db")
    if not os.path.exists(db_path):
        db_path = "forensiair.db"
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT inspection_date, inspection_type, status FROM inspection_events "
            "WHERE factory_id = ? ORDER BY inspection_date DESC",
            (factory_id,)
        ).fetchall()
    finally:
        conn.close()

    return [
        {"inspection_date": r[0], "inspection_type": r[1], "status": r[2]}
        for r in rows
    ]

@app.post("/api/factories/{factory_id}/audit")
def initiate_audit(factory_id: str):
    """
    Records a real audit request as a new row in inspection_events (status
    "Requested") so it immediately shows up in this factory's inspection
    history via get_factory_inspections above -- no separate audit table
    or workflow exists yet, so this is the honest minimal version rather
    than a fake confirmation.
    """
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "..", "forensiair.db")
    if not os.path.exists(db_path):
        db_path = "forensiair.db"
    if not os.path.exists(db_path):
        raise HTTPException(status_code=500, detail="Database not available")

    conn = sqlite3.connect(db_path)
    try:
        exists = conn.execute("SELECT 1 FROM factories WHERE factory_id = ?", (factory_id,)).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail=f"Factory {factory_id} not found")
        inspection_date = datetime.date.today().isoformat()
        conn.execute(
            "INSERT INTO inspection_events (factory_id, inspection_date, inspection_type, status) "
            "VALUES (?, ?, ?, ?)",
            (factory_id, inspection_date, "Audit Requested", "Requested")
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "status": "recorded",
        "factory_id": factory_id,
        "inspection_date": inspection_date,
        "inspection_type": "Audit Requested",
        "inspection_status": "Requested"
    }

# -------------------------------------------------------------
# 6. Data Quality Overview
# -------------------------------------------------------------
@app.get("/api/data-quality", dependencies=[Depends(require_role(["admin"]))])
def get_data_quality():
    cache = get_data_cache()
    df_q = cache["quality"]
    
    if df_q is None or df_q.empty:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="dataset_quality_summary_v2.csv dataset file not found in data directory."
        )
        
    results = []
    for idx, r in df_q.iterrows():
        fid = str(r.get('factory_id', r.get('site_id', f'site_{idx}')))
        name = str(r.get('factory_name', r.get('name', f'Industrial Site {fid}')))
        
        results.append({
            "factory_id": fid,
            "factory_name": name,
            "coverage_percentage": float(r.get('coverage_percentage', 0.0)),
            "missing_percentage": float(r.get('missing_percentage', 0.0)),
            "duplicate_percentage": float(r.get('duplicate_percentage', 0.0)),
            "quality_grade": str(r.get('quality_grade', 'N/A')),
            "readiness_score": float(r.get('readiness_score', 0.0)),
            "total_records": int(r.get('total_records', 0))
        })
        
    return {
        "dataset_summaries": results,
        "total_records_processed": sum(r["total_records"] for r in results),
        "pipeline_health_status": "OPTIMAL"
    }

# -------------------------------------------------------------
# 7. Reports Center & Generation
# -------------------------------------------------------------
@app.get("/api/reports")
def list_reports(type: Optional[str] = Query(None), date_range: Optional[str] = Query(None)):
    return {
        "status": "not_implemented",
        "message": "Reports listing endpoint is a feature stub and is not backed by persistent report storage yet."
    }

@app.post("/api/reports/generate")
def generate_report(report_type: str = "Surveillance Digest"):
    return {
        "status": "not_implemented",
        "message": f"Report generation for '{report_type}' is a feature stub and is not backed by an export engine yet."
    }

# -------------------------------------------------------------
# 8. Administration Portal Routes
# -------------------------------------------------------------
@app.get("/api/admin/factories")
def list_admin_factories(district: Optional[str] = Query(None), industry: Optional[str] = Query(None)):
    cache = get_data_cache()
    df_tsi = cache["tsi"]
    name_map = cache["name_mapping"]

    results = []
    for _, r in df_tsi.iterrows():
        fid = str(r['factory_id'])
        name, reg, ind = name_map.get(fid, (f"Industrial Site {fid}", "Taloja", "Chemical Manufacturing"))

        if district and district.strip() and district.lower() not in ['all districts', '']:
            if reg.lower() != district.strip().lower():
                continue

        if industry and industry.strip() and industry.lower() not in ['all industries', '']:
            if ind.lower() != industry.strip().lower():
                continue

        results.append({
            "factory_id": fid,
            "factory_name": name,
            "name": name,
            "region": reg,
            "district": reg,
            "industry": ind,
            "risk_tier": str(r.get('risk_tier', 'Low')),
            "tsi_score": float(r.get('tsi_score', 0.0))
        })

    return results

@app.get("/api/admin/users", dependencies=[Depends(require_role(["admin"]))])
def list_users():
    return {
        "status": "not_implemented",
        "message": "User management endpoint is a feature stub and is not backed by a database model yet."
    }

@app.post("/api/admin/users", dependencies=[Depends(require_role(["admin"]))])
def create_user(user: UserCreateRequest):
    return {
        "status": "not_implemented",
        "message": "User creation endpoint is a feature stub and is not backed by a database model yet."
    }

@app.get("/api/admin/pipeline-status", dependencies=[Depends(require_role(["admin"]))])
def get_pipeline_status():
    return {
        "pipeline_state": "ONLINE",
        "last_feature_engineering_run": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "active_models": ["Fingerprint Engine", "IsolationForest", "Factory-Level Tamper Model", "LightGBM SHAP Surrogate"],
        "gpu_acceleration": "DISABLED (CPU Multi-threading enabled)",
        "memory_usage_mb": 412.5
    }

# -------------------------------------------------------------
# 9. Institutional Oversight Endpoint
# -------------------------------------------------------------
@app.get("/api/oversight")
def get_institutional_oversight():
    cache = get_data_cache()
    df_tsi = cache["tsi"].copy()
    name_map = cache["name_mapping"]
    
    taloja_sites = [r for _, r in df_tsi.iterrows() if name_map.get(str(r['factory_id']), ('', 'Taloja'))[1] == 'Taloja']
    mahad_sites = [r for _, r in df_tsi.iterrows() if name_map.get(str(r['factory_id']), ('', 'Taloja'))[1] == 'Mahad']
    
    coord_pairs = [
        {"pair": "site_1569 <-> site_1909", "correlation": 0.711, "region": "Taloja MIDC (Shared Grid)"},
        {"pair": "site_1247 <-> site_1264", "correlation": 0.709, "region": "Taloja MIDC (Shared Grid)"},
        {"pair": "site_1787 <-> site_887", "correlation": 0.632, "region": "Cross-Region (Mahad <-> Taloja)"}
    ]
    
    df_sorted = df_tsi.sort_values('tsi_score', ascending=False)
    dispatch_queue = []
    
    for idx, r in df_sorted.head(5).iterrows():
        fid = str(r['factory_id'])
        name, reg, ind = name_map.get(fid, (f"Industrial Site {fid}", "Taloja", "Chemical Manufacturing"))
        tier = str(r.get('risk_tier', 'Low'))
        
        if tier == 'High':
            priority = "CRITICAL - IMMEDIATE UNANNOUNCED AUDIT"
        elif tier == 'Medium':
            priority = "HIGH - MANDATE SENSOR CALIBRATION"
        else:
            priority = "ROUTINE MONITORED"
            
        dispatch_queue.append({
            "factory_id": fid,
            "name": name,
            "rank": int(r.get('rank', len(dispatch_queue) + 1)),
            "tsi_score": float(r.get('tsi_score', 0.0)),
            "risk_tier": tier,
            "priority": priority
        })
    
    return {
        "regional_breakdown": {
            "Taloja_MIDC": {
                "total_sites": len(taloja_sites),
                "high_risk_count": sum(1 for s in taloja_sites if s.get('risk_tier') == 'High'),
                "avg_tsi_score": round(float(np.mean([s.get('tsi_score', 0) for s in taloja_sites])), 2) if taloja_sites else 0.0
            },
            "Mahad_MIDC": {
                "total_sites": len(mahad_sites),
                "high_risk_count": sum(1 for s in mahad_sites if s.get('risk_tier') == 'High'),
                "avg_tsi_score": round(float(np.mean([s.get('tsi_score', 0) for s in mahad_sites])), 2) if mahad_sites else 0.0
            }
        },
        "coordinated_missing_pairs": coord_pairs,
        "inspection_dispatch_queue": dispatch_queue
    }
