import os
import re
import time
import psycopg2
from psycopg2.extras import execute_values
from collector.consent.config import DB_CONFIG
from collector.consent.logger import logger

from collector.consent.database import init_db

def get_clean_keywords(name):
    name = re.sub(r'(?i)^m/s\.?\s*', '', name)
    name = re.sub(r'\(.*?\)', '', name)
    name = re.sub(r'[^a-zA-Z0-9\s]', ' ', name)
    
    words = [w.strip().lower() for w in name.split()]
    ignore = {
        'pvt', 'ltd', 'private', 'limited', 'industries', 'chemical', 'chemicals', 
        'india', 'co', 'company', 'corp', 'corporation', 'unit', 'and', 'sons', 'export'
    }
    clean_words = [w for w in words if w and w not in ignore and len(w) > 2]
    return clean_words

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def recalculate_quality_summary():
    logger.info("Initializing Dataset Quality Summary calculation...")
    
    # Initialize DB tables including dataset_quality_summary
    init_db()
    
    conn = get_connection()
    cur = conn.cursor()
    
    # 1. Create table index for fast partitioning if not exists
    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_monitoring_data_fac_param_ts ON monitoring_data(factory_id, parameter_id, timestamp);")
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.warning(f"Could not create monitoring index: {e}")
        
    # 2. Get list of all factories
    cur.execute("SELECT site_id, name, category FROM factories ORDER BY name;")
    factories = cur.fetchall()
    
    summaries = []
    
    for site_id, name, category in factories:
        logger.info(f"Processing quality metrics for factory: {name} ({site_id})")
        start_time = time.time()
        
        # Total records
        cur.execute("SELECT COUNT(*) FROM monitoring_data WHERE factory_id = %s;", (site_id,))
        total_records = cur.fetchone()[0]
        
        # Initialize default values
        monitoring_start = None
        monitoring_end = None
        monitoring_days = 0.0
        parameter_count = 0
        parameter_list = []
        expected_records = 0
        coverage_percentage = 0.0
        missing_intervals = 0
        na_values = 0
        zero_values = 0
        duplicate_records = 0
        negative_values = 0
        longest_gap_minutes = 0
        average_records_per_day = 0.0
        
        if total_records > 0:
            # Min and max timestamp
            cur.execute("SELECT MIN(timestamp), MAX(timestamp) FROM monitoring_data WHERE factory_id = %s;", (site_id,))
            monitoring_start, monitoring_end = cur.fetchone()
            
            if monitoring_start and monitoring_end:
                duration_seconds = (monitoring_end - monitoring_start).total_seconds()
                monitoring_days = round(max(0.1, duration_seconds / 86400.0), 2)
            
            # Parameters list & count
            cur.execute("SELECT DISTINCT parameter_id FROM monitoring_data WHERE factory_id = %s ORDER BY parameter_id;", (site_id,))
            parameter_list = [p[0] for p in cur.fetchall()]
            parameter_count = len(parameter_list)
            
            # Expected records (15-min intervals: 4 per hour, 96 per day per parameter)
            if monitoring_start and monitoring_end:
                intervals = int(duration_seconds / 900.0) + 1
                expected_records = parameter_count * intervals
                
            # Coverage percentage
            if expected_records > 0:
                coverage_percentage = min(100.0, round((total_records / expected_records) * 100, 2))
                
            # NA / Zero / Negative values
            cur.execute("SELECT COUNT(*) FROM monitoring_data WHERE factory_id = %s AND value IS NULL;", (site_id,))
            na_values = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM monitoring_data WHERE factory_id = %s AND value = 0;", (site_id,))
            zero_values = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM monitoring_data WHERE factory_id = %s AND value < 0;", (site_id,))
            negative_values = cur.fetchone()[0]
            
            # Average records per day
            if monitoring_days > 0:
                average_records_per_day = round(total_records / monitoring_days, 2)
                
            # Duplicates
            cur.execute("""
                SELECT COALESCE(SUM(dup_count - 1), 0)
                FROM (
                    SELECT parameter_id, timestamp, COUNT(*) as dup_count
                    FROM monitoring_data
                    WHERE factory_id = %s
                    GROUP BY parameter_id, timestamp
                    HAVING COUNT(*) > 1
                ) t;
            """, (site_id,))
            duplicate_records = int(cur.fetchone()[0])
            
            # Longest gap minutes per parameter
            cur.execute("""
                WITH diffs AS (
                    SELECT 
                        timestamp - LAG(timestamp) OVER (PARTITION BY parameter_id ORDER BY timestamp) as diff
                    FROM monitoring_data
                    WHERE factory_id = %s
                )
                SELECT COALESCE(MAX(EXTRACT(EPOCH FROM diff)/60), 0)
                FROM diffs;
            """, (site_id,))
            longest_gap_minutes = int(cur.fetchone()[0])
            
        # CTO Ingress Metrics
        cur.execute("SELECT id, consent_number FROM consents WHERE factory_id = %s ORDER BY valid_until DESC LIMIT 1;", (site_id,))
        cto_record = cur.fetchone()
        cto_available = cto_record is not None
        
        cto_parameter_count = 0
        if cto_available:
            cur.execute("SELECT COUNT(DISTINCT parameter) FROM consent_limits WHERE consent_id = %s;", (cto_record[0],))
            cto_parameter_count = cur.fetchone()[0]
            
        # Inspection Metrics
        keywords = get_clean_keywords(name)
        unit_match = re.search(r'(?i)unit\s*[-–]?\s*([a-zA-Z0-9]+)', name)
        unit = unit_match.group(1).lower() if unit_match else None
        
        inspection_count = 0
        if keywords:
            sql = "SELECT COUNT(*) FROM inspection_schedule WHERE " + " AND ".join(["factory_name ~* %s"] * len(keywords))
            params = [rf"\y{re.escape(k)}\y" for k in keywords]
            if unit:
                sql += " AND factory_name ~* %s"
                params.append(rf"\y{re.escape(unit)}\y")
                
            cur.execute(sql, tuple(params))
            inspection_count = cur.fetchone()[0]
            
        inspection_schedule_available = inspection_count > 0
        
        # Computed Analytics: Quality Grade
        if coverage_percentage >= 90.0:
            quality_grade = 'A'
        elif coverage_percentage >= 75.0:
            quality_grade = 'B'
        elif coverage_percentage >= 50.0:
            quality_grade = 'C'
        elif coverage_percentage >= 25.0:
            quality_grade = 'D'
        else:
            quality_grade = 'F'
            
        # Computed Analytics: Readiness Score
        # Coverage: 40%
        score_coverage = coverage_percentage * 0.40
        # Monitored parameters: 20% (up to 4 params)
        score_params = (min(parameter_count, 4) / 4.0) * 20.0
        # Presence of CTO: 15%
        score_cto = 15.0 if cto_available else 0.0
        # Presence of Inspection Schedule: 15%
        score_insp = 15.0 if inspection_schedule_available else 0.0
        # Length of monitoring period: 10% (up to 180 days)
        score_duration = (min(monitoring_days, 180) / 180.0) * 10.0
        
        readiness_score = round(score_coverage + score_params + score_cto + score_insp + score_duration, 1)
        
        # Computed Analytics: Recommended Fingerprints
        recommended_fingerprints = []
        if readiness_score >= 80.0 and parameter_count >= 4:
            recommended_fingerprints = ["Multivariate Correlation", "Diurnal Profiling", "Limit Violation Detector", "Compliance Audit"]
        elif readiness_score >= 50.0:
            recommended_fingerprints = ["Single Parameter Trend", "Basic Limit Compliance", "Diurnal Profiling"]
        else:
            recommended_fingerprints = ["Data Gap Recovery", "Sensor Calibration Audit"]
            
        summaries.append((
            site_id, site_id, name, category,
            monitoring_start, monitoring_end, monitoring_days,
            parameter_count, parameter_list,
            total_records, expected_records, coverage_percentage,
            missing_intervals, na_values, zero_values, duplicate_records, negative_values,
            longest_gap_minutes, average_records_per_day,
            cto_available, cto_parameter_count,
            inspection_schedule_available, inspection_count,
            quality_grade, readiness_score, recommended_fingerprints
        ))
        
        logger.info(f"Completed {name} in {time.time() - start_time:.2f}s (Score: {readiness_score}, Grade: {quality_grade})")

    # 3. Batch insert / upsert into dataset_quality_summary
    try:
        cur.execute("DELETE FROM dataset_quality_summary;") # refresh table content
        
        insert_query = """
            INSERT INTO dataset_quality_summary (
                factory_id, site_id, factory_name, industry_category,
                monitoring_start, monitoring_end, monitoring_days,
                parameter_count, parameter_list,
                total_records, expected_records, coverage_percentage,
                missing_intervals, na_values, zero_values, duplicate_records, negative_values,
                longest_gap_minutes, average_records_per_day,
                cto_available, cto_parameter_count,
                inspection_schedule_available, inspection_count,
                quality_grade, readiness_score, recommended_fingerprints
            ) VALUES %s;
        """
        
        execute_values(cur, insert_query, summaries)
        conn.commit()
        logger.info(f"Successfully precomputed and saved quality summary for {len(summaries)} factories.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to upsert dataset_quality_summary: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    recalculate_quality_summary()
