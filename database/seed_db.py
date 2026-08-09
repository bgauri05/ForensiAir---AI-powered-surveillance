import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.database import SessionLocal, init_db, engine
from backend.models import Factory, FingerprintScore, InspectionEvent, TelemetryRecord, Alert, ConsentLimit, SystemThreshold, UserAccess, Base
from ml_pipeline.risk_engine import calculate_composite_risk

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
        PG_URL = "postgresql://postgres:Gauri%40123@localhost:5434/forensiair"
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

MOCK_INITIAL = [
    {"factory_id": "FA-88921", "name": "BlueWave Chemicals", "district": "Northern Industrial Zone", "industry": "Chemical Manufacturing", "status": "Compliant", "risk": 12.0, "risk_cat": "LOW"},
    {"factory_id": "FA-77210", "name": "IronForge Foundry", "district": "Coastal Sector", "industry": "Heavy Metallurgy", "status": "Under Review", "risk": 58.5, "risk_cat": "HIGH"},
    {"factory_id": "FA-44182", "name": "Apex Textile Ltd.", "district": "Urban Fringe", "industry": "Garment & Dyeing", "status": "Critical Breach", "risk": 94.2, "risk_cat": "CRITICAL"},
    {"factory_id": "FA-90112", "name": "Z-Tech Polymers", "district": "Northern Industrial Zone", "industry": "Synthetic Rubber", "status": "Compliant", "risk": 18.4, "risk_cat": "LOW"},
    {"factory_id": "FA-11234", "name": "GreenLeaf Paper", "district": "Coastal Sector", "industry": "Pulp & Paper", "status": "Compliant", "risk": 8.1, "risk_cat": "LOW"},
    {"factory_id": "FA-22561", "name": "Global Glass Works", "district": "Urban Fringe", "industry": "Glass Manufacturing", "status": "Under Review", "risk": 62.0, "risk_cat": "HIGH"},
    {"factory_id": "FA-55310", "name": "Titan Cement", "district": "Northern Industrial Zone", "industry": "Construction Materials", "status": "Compliant", "risk": 14.5, "risk_cat": "LOW"}
]

def seed():
    print("--- 1. Initializing Database Schema ---")
    Base.metadata.drop_all(bind=engine)
    init_db()
    
    db = SessionLocal()
    
    # 1. Add standard mock factories first
    factories_to_add = []
    fingerprints_to_add = []
    
    for m in MOCK_INITIAL:
        f_obj = Factory(
            factory_id=m['factory_id'],
            name=m['name'],
            industry_type=m['industry'],
            location=m['district'],
            total_fingerprints_triggered=0 if m['risk_cat'] == 'LOW' else (2 if m['risk_cat'] == 'HIGH' else 4),
            risk_score=m['risk'],
            risk_category=m['risk_cat'],
            status="Active" if m['risk_cat'] != "CRITICAL" else "Under Review"
        )
        factories_to_add.append(f_obj)
        
        fp_obj = FingerprintScore(
            factory_id=m['factory_id'],
            impossible_ph_range=0.0,
            inspection_dip=0.0,
            flatline=0.42 if m['risk_cat'] == 'CRITICAL' else 0.0,
            limit_hugging=0.28 if m['risk_cat'] == 'CRITICAL' else 0.0,
            correlation_break=0.15 if m['risk_cat'] == 'CRITICAL' else 0.0,
            copy_paste=0.0,
            coordinated_missing_data=0.08 if m['risk_cat'] == 'CRITICAL' else 0.0,
            total_fingerprints_triggered=0 if m['risk_cat'] == 'LOW' else (2 if m['risk_cat'] == 'HIGH' else 4)
        )
        fingerprints_to_add.append(fp_obj)

        if m['risk_cat'] in ["HIGH", "CRITICAL"]:
            alert = Alert(
                factory_id=m['factory_id'],
                alert_type="Effluent Threshold Breach",
                severity=m['risk_cat'],
                message=f"{m['name']} triggered anomalous signal tampering flags. Mandatory audit required.",
                timestamp="2024-12-30 14:00:00",
                status="OPEN"
            )
            db.add(alert)

    # 2. Add real CSV factories
    fp_path = "Data/RawData/factory_fingerprint_scores.csv"
    if not os.path.exists(fp_path):
        fp_path = os.path.join("..", fp_path)
    fp_df = pd.read_csv(fp_path)
    
    pg_mapping = get_pg_factory_mapping()
    
    for idx, row in fp_df.iterrows():
        fid = row['factory_id']
        site_num = fid.split('_')[-1]
        
        if fid in pg_mapping:
            name, dist, ind_type = pg_mapping[fid]
        else:
            ind_type = INDUSTRIES[idx % len(INDUSTRIES)]
            dist = DISTRICTS[idx % len(DISTRICTS)]
            name = f"Industrial Plant {site_num} ({ind_type.split()[0]})"
        
        fp_dict = {
            'impossible_ph_range': float(row.get('impossible_ph_range', 0)),
            'inspection_dip': float(row.get('inspection_dip', 0)),
            'flatline': float(row.get('flatline', 0)),
            'limit_hugging': float(row.get('limit_hugging', 0)),
            'correlation_break': float(row.get('correlation_break', 0)),
            'copy_paste': float(row.get('copy_paste', 0)),
            'coordinated_missing_data': float(row.get('coordinated_missing_data', 0)),
        }
        
        triggered_cnt = int(row.get('total_fingerprints_triggered', 0))
        xgb_prob = min(0.99, max(0.02, triggered_cnt * 0.28 + np.random.uniform(0.01, 0.15)))
        iso_score = 0.1 if triggered_cnt >= 2 else 0.4
        
        risk_res = calculate_composite_risk(xgb_prob, iso_score, fp_dict)
        
        f_obj = Factory(
            factory_id=fid,
            name=name,
            industry_type=ind_type,
            location=dist,
            total_fingerprints_triggered=triggered_cnt,
            risk_score=risk_res['risk_score'],
            risk_category=risk_res['risk_category'],
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
    real_path = "Data/RawData/real_features.parquet"
    if not os.path.exists(real_path):
        real_path = os.path.join("..", real_path)
    
    if os.path.exists(real_path):
        df_real = pd.read_parquet(real_path)
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

