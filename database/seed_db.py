import os
import sys
import pandas as pd
import numpy as np
from urllib.parse import quote_plus

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.database import SessionLocal, init_db, engine
from backend.models import Factory, FingerprintScore, InspectionEvent, TelemetryRecord, Alert, ConsentLimit, SystemThreshold, UserAccess, Base
from ml_pipeline.risk_engine import calculate_composite_risk
from ml_pipeline.inference import get_inference_engine

DISTRICTS = ["Northern Industrial Zone", "Coastal Sector", "Urban Fringe"]
INDUSTRIES = [
    "Chemical Manufacturing", "Heavy Metallurgy", "Garment & Dyeing",
    "Synthetic Rubber", "Pulp & Paper", "Glass Manufacturing",
    "Construction Materials", "Pharmaceutical Synthetics", "Petrochemical Refinery"
]

NAME_MAPPING = {
    "site_1131": ("RUPA ORGANICS PVT LTD. Taloja", "Taloja", "Chemical Manufacturing"),
    "site_1138": ("Nixon Chemicals Ltd", "Taloja", "Chemical Manufacturing"),
    "site_1167": ("Super Petroleum Products Private Limited", "Taloja", "Petrochemical Refinery"),
    "site_1200": ("Metallurgical Products India(P) Ltd", "Taloja", "Heavy Metallurgy"),
    "site_1203": ("Anmol Chemicals Pvt. Ltd", "Taloja", "Chemical Manufacturing"),
    "site_1221": ("Zirconium Chemicals Pvt. Ltd", "Taloja", "Chemical Manufacturing"),
    "site_1232": ("M/s.Altaroma Chemicals Pvt Ltd", "Taloja", "Chemical Manufacturing"),
    "site_1247": ("Ducol Organics & Colours Pvt Ltd", "Taloja", "Garment & Dyeing"),
    "site_1256": ("SHREE VINAYAK ORGANICS (I) PVT LTD", "Taloja", "Chemical Manufacturing"),
    "site_1257": ("Dorf Ketal Chemicals India Pvt Ltd", "Taloja", "Petrochemical Refinery"),
    "site_1259": ("EUROCHEM INDUSTRIES", "Taloja", "Chemical Manufacturing"),
    "site_1264": ("Imagico India Pvt Ltd", "Taloja", "Chemical Manufacturing"),
    "site_1280": ("EKVIRA FINE CHEM PVT LTD", "Taloja", "Chemical Manufacturing"),
    "site_1281": ("M/s RAMDEV CHEMI-Pharma PVT LTD", "Taloja", "Pharmaceutical Synthetics"),
    "site_1284": ("CORROGARD CHEMICALS", "Taloja", "Chemical Manufacturing"),
    "site_1285": ("VVL Pharma Pvt Ltd", "Taloja", "Pharmaceutical Synthetics"),
    "site_1310": ("Aezis Global Pvt Ltd", "Mahad", "Chemical Manufacturing"),
    "site_1321": ("M/s. Indo Amines Ltd.", "Mahad", "Drugs and Pharmaceuticals"),
    "site_1369": ("M/s.Privi Specialty Chemicals Ltd(Unit-II)", "Mahad", "Chemical Manufacturing"),
    "site_1376": ("M/s.Privi Speciality Chemicals Limited Unit III", "Mahad", "Chemical Manufacturing"),
    "site_1561": ("GRASIM INDUSTRIES LIMITED", "Mahad", "Chemical Manufacturing"),
    "site_1569": ("M/s.Galaxy Surfactants Limited", "Taloja", "Chemical Manufacturing"),
    "site_1581": ("M/s Memba Chem Industries Private Limited", "Taloja", "Chemical Manufacturing"),
    "site_1668": ("Nouryon Chemicals India Private Limited", "Mahad", "Chemical Manufacturing"),
    "site_1756": ("M/s. Aquapharm Chemicals Pvt. Ltd.", "Mahad", "Chemical Manufacturing"),
    "site_1787": ("SHREE HARI CHEMICALS EXPORT LIMITED", "Mahad", "Chemical Manufacturing"),
    "site_1789": ("sudarshan chemical industries ltd Mahad", "Mahad", "Chemical Manufacturing"),
    "site_1799": ("Privi Speciality Chemicals Limited Unit 10", "Mahad", "Chemical Manufacturing"),
    "site_1905": ("Allnex Resins India Pvt ltd", "Mahad", "Synthetic Rubber"),
    "site_1909": ("Cyklo Pharma Chem Pvt Ltd", "Taloja", "Pharmaceutical Synthetics"),
    "site_2070": ("Prigiv Specialties Pvt Ltd", "Mahad", "Chemical Manufacturing"),
    "site_887": ("Dow Chemical International Pvt Ltd", "Taloja", "Chemical Manufacturing"),
    "site_982": ("PREETI PETROCHEM PVT LTD", "Taloja", "Petrochemical Refinery"),
}

def get_pg_factory_mapping():
    mapping = dict(NAME_MAPPING)
    try:
        import psycopg2

        # QC FIX (2026-08): this used to be a hardcoded connection string with
        # a real username/password committed directly in source. Credentials
        # now come from environment variables -- PG_PASSWORD has no default,
        # so if it isn't set this raises and falls through to the existing
        # except block below, which already handles "no live Postgres
        # available" gracefully via the hardcoded NAME_MAPPING fallback above.
        pg_host = os.getenv("PG_HOST", "localhost")
        pg_port = os.getenv("PG_PORT", "5434")
        pg_database = os.getenv("PG_DATABASE", "forensiair")
        pg_user = os.getenv("PG_USER", "postgres")
        pg_password = os.getenv("PG_PASSWORD")

        if not pg_password:
            raise RuntimeError(
                "PG_PASSWORD environment variable is not set."
            )

        PG_URL = (
            f"postgresql://{pg_user}:{quote_plus(pg_password)}"
            f"@{pg_host}:{pg_port}/{pg_database}"
        )
        conn = psycopg2.connect(PG_URL, connect_timeout=3)
        cur = conn.cursor()
        cur.execute("SELECT site_id, name, category, city FROM factories;")
        for r in cur.fetchall():
            if r[0] and r[1]:
                mapping[r[0]] = (r[1], r[3] or "Taloja", r[2] or "Chemical Manufacturing")
        conn.close()
        print("Successfully fetched factory names dynamically from PostgreSQL database!")
    except Exception as e:
        print(f"Using default PostgreSQL factory dictionary mapping (PostgreSQL connect notice: {e})")
    return mapping

def seed():
    print("--- 1. Initializing Database Schema ---")
    Base.metadata.drop_all(bind=engine)
    init_db()
    
    db = SessionLocal()

    # 1. Add real CSV factories
    factories_to_add = []
    fingerprints_to_add = []

    fp_path = "Data/RawData/factory_fingerprint_scores.csv"
    if not os.path.exists(fp_path):
        fp_path = os.path.join("..", fp_path)
    fp_df = pd.read_csv(fp_path)

    pg_mapping = get_pg_factory_mapping()

    # --------------------------------------------------
    # Real per-factory risk scoring.
    #
    # Isolation Forest scores one READING at a time -- every real reading
    # for a factory is scored individually, and only the resulting scores
    # are averaged into a single per-factory number (never the raw feature
    # values themselves; averaging features like autocorrelation or
    # rolling_std across readings taken at different times would create a
    # synthetic "reading" that never actually happened).
    #
    # QC FIX (2026-08, Phase 2): the tamper-probability model is now a
    # factory-level model (replacing the retired per-reading synthetic
    # XGBoost) -- it was trained on aggregated real-telemetry stats per
    # factory with proxy labels from the fingerprint engine, and only makes
    # sense evaluated once per factory on that same aggregation, not
    # averaged from per-reading predictions. See
    # ml_pipeline/train_xgboost_weak_supervision.py and ml_strategy_plan.md.
    # --------------------------------------------------

    real_path = "Data/RawData/real_features.parquet"
    if not os.path.exists(real_path):
        real_path = os.path.join("..", real_path)
    df_real = pd.read_parquet(real_path) if os.path.exists(real_path) else None

    inference_engine = get_inference_engine()

    def score_factory(fid: str):
        """Returns (tamper_probability, mean_isolation_forest_anomaly_score)
        for a factory. tamper_probability comes from the factory-level
        proxy-label model (Phase 2), evaluated once on this factory's
        aggregated real readings. anomaly_score is Isolation Forest's
        per-reading score, averaged across all of the factory's real
        readings.
        """
        if df_real is None:
            return 0.02, 0.0

        rows = df_real[df_real["factory_id"] == fid]
        if len(rows) == 0:
            return 0.02, 0.0

        xgb_prob = inference_engine.predict_factory_tamper_probability(rows)

        X = rows.reindex(columns=inference_engine.feature_cols)
        X = X.fillna(0.0)
        X_iso_scaled = inference_engine.iso_scaler.transform(X)
        iso_scores = inference_engine.iso_forest.score_samples(X_iso_scaled)

        return xgb_prob, float(np.mean(iso_scores))

    for idx, row in fp_df.iterrows():
        fid = row['factory_id']
        site_num = fid.split('_')[-1]

        if fid in pg_mapping:
            name, dist, ind_type = pg_mapping[fid]
        else:
            ind_type = INDUSTRIES[idx % len(INDUSTRIES)]
            dist = DISTRICTS[idx % len(DISTRICTS)]
            name = f"Industrial Plant {site_num} ({ind_type.split()[0]})"

        # Raw magnitude values -- kept for display (FingerprintScore table
        # stores the actual percentages/z-scores, e.g. "flatline: 12.3%").
        fp_dict = {
            'impossible_ph_range': float(row.get('impossible_ph_range', 0)),
            'inspection_dip': float(row.get('inspection_dip', 0)),
            'flatline': float(row.get('flatline', 0)),
            'limit_hugging': float(row.get('limit_hugging', 0)),
            'correlation_break': float(row.get('correlation_break', 0)),
            'copy_paste': float(row.get('copy_paste', 0)),
            'coordinated_missing_data': float(row.get('coordinated_missing_data', 0)),
            'data_integrity': float(row.get('data_integrity', 0)),
        }

        # Already-thresholded 0/1 trigger decisions from fingerprint_engine.py
        # -- this is what calculate_composite_risk() actually needs, since it
        # has no way to know the right threshold for each raw magnitude above.
        fp_trigger_dict = {
            'impossible_ph_range': int(row.get('trig_impossible_ph_range', 0)),
            'inspection_dip': int(row.get('trig_inspection_dip', 0)),
            'flatline': int(row.get('trig_flatline', 0)),
            'limit_hugging': int(row.get('trig_limit_hugging', 0)),
            'correlation_break': int(row.get('trig_correlation_break', 0)),
            'copy_paste': int(row.get('trig_copy_paste', 0)),
            'coordinated_missing_data': int(row.get('trig_coordinated_missing_data', 0)),
            'data_integrity': int(row.get('trig_data_integrity', 0)),
        }

        triggered_cnt = int(row.get('total_fingerprints_triggered', 0))
        xgb_prob, iso_score = score_factory(fid)

        risk_res = calculate_composite_risk(xgb_prob, iso_score, fp_trigger_dict)
        
        f_obj = Factory(
            factory_id=fid,
            name=name,
            industry_type=ind_type,
            location=dist,
            total_fingerprints_triggered=triggered_cnt,
            risk_score=risk_res['risk_score'],
            risk_category=risk_res['risk_category'],
            xgb_probability=risk_res['xgb_probability'],
            anomaly_score_norm=risk_res['anomaly_score'],
            status="Active" if risk_res['risk_category'] != "CRITICAL" else "Under Review"
        )
        factories_to_add.append(f_obj)
        
        fp_obj = FingerprintScore(
            factory_id=fid,
            impossible_ph_range=fp_dict['impossible_ph_range'],
            inspection_dip=fp_dict['inspection_dip'],
            flatline=fp_dict['flatline'],
            limit_hugging=fp_dict['limit_hugging'],
            correlation_break=fp_dict['correlation_break'],
            copy_paste=fp_dict['copy_paste'],
            coordinated_missing_data=fp_dict['coordinated_missing_data'],
            data_integrity=fp_dict['data_integrity'],
            trig_impossible_ph_range=fp_trigger_dict['impossible_ph_range'],
            trig_inspection_dip=fp_trigger_dict['inspection_dip'],
            trig_flatline=fp_trigger_dict['flatline'],
            trig_limit_hugging=fp_trigger_dict['limit_hugging'],
            trig_correlation_break=fp_trigger_dict['correlation_break'],
            trig_copy_paste=fp_trigger_dict['copy_paste'],
            trig_coordinated_missing_data=fp_trigger_dict['coordinated_missing_data'],
            trig_data_integrity=fp_trigger_dict['data_integrity'],
            total_fingerprints_triggered=triggered_cnt
        )
        fingerprints_to_add.append(fp_obj)
        
        if risk_res['risk_category'] in ["HIGH", "CRITICAL"]:
            alert = Alert(
                factory_id=fid,
                alert_type="Tamper Fingerprint Triggered",
                severity=risk_res['risk_category'],
                message=f"{name} triggered {triggered_cnt} tampering fingerprints. {risk_res['recommended_action']}",
                timestamp="2024-12-30 14:00:00",
                status="OPEN"
            )
            db.add(alert)
            
    db.add_all(factories_to_add)
    db.add_all(fingerprints_to_add)
    
    # 3. Seed inspection events
    insp_path = "Data/RawData/inspection_events_2024.csv"
    if not os.path.exists(insp_path):
        insp_path = os.path.join("..", insp_path)
    if os.path.exists(insp_path):
        insp_df = pd.read_csv(insp_path)
        inspections_to_add = []
        for _, row in insp_df.iterrows():
            insp_obj = InspectionEvent(
                factory_id=row['factory_id'],
                inspection_date=str(row['inspection_date']),
                inspection_type=str(row['inspection_type']),
                status=str(row['status']),
                notes="Routine OCEMS cross-validation audit."
            )
            inspections_to_add.append(insp_obj)
        db.add_all(inspections_to_add)
    
    # 4. Seed sampled telemetry records
    print("--- 2. Seeding Sampled Telemetry Records ---")

    if df_real is not None:
        sample_factories = fp_df['factory_id'].tolist()[:8]
        df_sampled = df_real[df_real['factory_id'].isin(sample_factories)].iloc[::20]
        
        telemetry_to_add = []
        for _, row in df_sampled.iterrows():
            t_obj = TelemetryRecord(
                factory_id=str(row['factory_id']),
                parameter_id=str(row['parameter_id']),
                timestamp=str(row['timestamp']),
                value=float(row['value']),
                rolling_mean=float(row['rolling_mean']) if pd.notnull(row['rolling_mean']) else None,
                rolling_std=float(row['rolling_std']) if pd.notnull(row['rolling_std']) else None,
                flatline_flag=float(row['flatline_flag']) if pd.notnull(row['flatline_flag']) else 0.0,
                limit_hugging=float(row['limit_hugging']) if pd.notnull(row['limit_hugging']) else 0.0,
                autocorrelation=float(row['autocorrelation']) if pd.notnull(row['autocorrelation']) else 0.0,
                is_anomaly=bool(row.get('flatline_flag', 0) > 0 or row.get('limit_hugging', 0) > 0)
            )
            telemetry_to_add.append(t_obj)
            
        db.add_all(telemetry_to_add)

    # 5. Seed Consent Limits, System Thresholds & User Access
    print("--- 3. Seeding Consent Limits, System Thresholds & User Access ---")
    limits = [
        ConsentLimit(parameter_id="pH", parameter_name="pH Level", unit="pH", min_limit=5.5, max_limit=9.0, regulatory_standard="CPCB Standard 2024", category="Effluent Quality"),
        ConsentLimit(parameter_id="BOD", parameter_name="Biochemical Oxygen Demand", unit="mg/L", min_limit=0.0, max_limit=30.0, regulatory_standard="CPCB Standard 2024", category="Effluent Quality"),
        ConsentLimit(parameter_id="COD", parameter_name="Chemical Oxygen Demand", unit="mg/L", min_limit=0.0, max_limit=250.0, regulatory_standard="CPCB Standard 2024", category="Effluent Quality"),
        ConsentLimit(parameter_id="TSS", parameter_name="Total Suspended Solids", unit="mg/L", min_limit=0.0, max_limit=100.0, regulatory_standard="CPCB Standard 2024", category="Effluent Quality"),
        ConsentLimit(parameter_id="FLOW", parameter_name="Effluent Discharge Flow", unit="m³/hr", min_limit=0.0, max_limit=500.0, regulatory_standard="CPCB Standard 2024", category="Flow Monitoring"),
        ConsentLimit(parameter_id="DO", parameter_name="Dissolved Oxygen", unit="mg/L", min_limit=4.0, max_limit=14.0, regulatory_standard="CPCB Standard 2024", category="Effluent Quality"),
        ConsentLimit(parameter_id="TEMP", parameter_name="Water Temperature", unit="°C", min_limit=10.0, max_limit=40.0, regulatory_standard="CPCB Standard 2024", category="Physical Parameter")
    ]
    db.add_all(limits)

    thresholds = [
        SystemThreshold(setting_key="flatline_sensitivity", setting_name="Flatline Sensor Sensitivity", value=0.95, unit="ratio", description="Threshold sensitivity for detects identical consecutive sensor readings."),
        SystemThreshold(setting_key="limit_hugging_tolerance", setting_name="Limit Hugging Tolerance", value=0.02, unit="margin", description="Tolerance margin around regulatory maximum limits for sensors."),
        SystemThreshold(setting_key="correlation_decay_cutoff", setting_name="Correlation Decay Cutoff", value=0.35, unit="r-score", description="Minimum cross-parameter Pearson correlation threshold before triggering anomaly."),
        SystemThreshold(setting_key="missing_data_alert_threshold", setting_name="Missing Data Alert Threshold", value=5.0, unit="%", description="Percentage of missing telemetry records before flagging network gap.")
    ]
    db.add_all(thresholds)

    users = [
        UserAccess(name="Administrator / Global Oversight", email="admin@forensiair.gov.in", role="Administrator", district_access="All Districts", status="Active", last_login="Today, 09:42 AM"),
        UserAccess(name="Director Chen", email="chen.audit@forensiair.gov.in", role="Senior Audit Lead", district_access="Northern Industrial Zone", status="Active", last_login="Today, 08:15 AM"),
        UserAccess(name="Dr. Rajesh Sharma", email="r.sharma@cpcb.gov.in", role="Field Inspector", district_access="Coastal Sector", status="Active", last_login="Yesterday, 17:30 PM"),
        UserAccess(name="Priya Nair", email="pnair@midc.org", role="Data Analyst", district_access="Urban Fringe", status="Active", last_login="Today, 10:05 AM")
    ]
    db.add_all(users)

    db.commit()
    db.close()
    
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed()

