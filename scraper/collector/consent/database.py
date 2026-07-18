import psycopg2
from psycopg2.extras import execute_values
from collector.consent.config import DB_CONFIG
from collector.consent.logger import logger

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Create consents table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS consents (
                id SERIAL PRIMARY KEY,
                factory_id VARCHAR(50) NOT NULL,
                factory_name VARCHAR(255) NOT NULL,
                consent_number VARCHAR(100) UNIQUE NOT NULL,
                consent_type VARCHAR(100),
                issue_date DATE,
                valid_from DATE,
                valid_until DATE,
                industry VARCHAR(255),
                pdf_path VARCHAR(500),
                source_url VARCHAR(1000),
                downloaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        
        # Create consent_limits table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS consent_limits (
                id SERIAL PRIMARY KEY,
                consent_id INTEGER REFERENCES consents(id) ON DELETE CASCADE,
                factory_id VARCHAR(50) NOT NULL,
                parameter VARCHAR(100) NOT NULL,
                minimum_limit NUMERIC,
                maximum_limit NUMERIC,
                unit VARCHAR(50),
                condition_text TEXT,
                page_number INTEGER,
                table_number INTEGER,
                extraction_confidence NUMERIC,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        
        # Create dataset_quality_summary table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dataset_quality_summary (
                id SERIAL PRIMARY KEY,
                factory_id VARCHAR(50) UNIQUE NOT NULL REFERENCES factories(site_id) ON DELETE CASCADE,
                site_id VARCHAR(50) NOT NULL,
                factory_name VARCHAR(255) NOT NULL,
                industry_category VARCHAR(255),
                monitoring_start TIMESTAMP,
                monitoring_end TIMESTAMP,
                monitoring_days NUMERIC,
                parameter_count INTEGER DEFAULT 0,
                parameter_list VARCHAR(50)[] DEFAULT '{}',
                total_records INTEGER DEFAULT 0,
                expected_records INTEGER DEFAULT 0,
                coverage_percentage NUMERIC DEFAULT 0.0,
                missing_intervals INTEGER DEFAULT 0,
                na_values INTEGER DEFAULT 0,
                zero_values INTEGER DEFAULT 0,
                duplicate_records INTEGER DEFAULT 0,
                negative_values INTEGER DEFAULT 0,
                longest_gap_minutes INTEGER DEFAULT 0,
                average_records_per_day NUMERIC DEFAULT 0.0,
                cto_available BOOLEAN DEFAULT FALSE,
                cto_parameter_count INTEGER DEFAULT 0,
                inspection_schedule_available BOOLEAN DEFAULT FALSE,
                inspection_count INTEGER DEFAULT 0,
                quality_grade CHAR(1) NOT NULL,
                readiness_score NUMERIC NOT NULL,
                recommended_fingerprints VARCHAR(255)[] DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        
        # Create consent_download_logs table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS consent_download_logs (
                id SERIAL PRIMARY KEY,
                factory VARCHAR(255) NOT NULL,
                status VARCHAR(50) NOT NULL,
                pdf_downloaded BOOLEAN DEFAULT FALSE,
                tables_detected INTEGER DEFAULT 0,
                limits_extracted INTEGER DEFAULT 0,
                execution_time NUMERIC,
                error_message TEXT,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        
        conn.commit()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to initialize database: {e}")
        raise e
    finally:
        cur.close()
        conn.close()

def get_db_factories():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT site_id, name, city FROM factories ORDER BY name;")
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

def consent_exists(consent_number):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM consents WHERE consent_number = %s;", (consent_number,))
        return cur.fetchone() is not None
    finally:
        cur.close()
        conn.close()

def insert_consent(consent_data):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO consents (
                factory_id, factory_name, consent_number, consent_type, 
                issue_date, valid_from, valid_until, industry, pdf_path, source_url
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (consent_number) DO UPDATE SET
                factory_id = EXCLUDED.factory_id,
                factory_name = EXCLUDED.factory_name,
                consent_type = EXCLUDED.consent_type,
                issue_date = EXCLUDED.issue_date,
                valid_from = EXCLUDED.valid_from,
                valid_until = EXCLUDED.valid_until,
                industry = EXCLUDED.industry,
                pdf_path = EXCLUDED.pdf_path,
                source_url = EXCLUDED.source_url,
                downloaded_at = NOW()
            RETURNING id;
        """, (
            consent_data["factory_id"],
            consent_data["factory_name"],
            consent_data["consent_number"],
            consent_data["consent_type"],
            consent_data["issue_date"],
            consent_data["valid_from"],
            consent_data["valid_until"],
            consent_data["industry"],
            consent_data["pdf_path"],
            consent_data["source_url"]
        ))
        consent_id = cur.fetchone()[0]
        conn.commit()
        return consent_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to insert consent {consent_data.get('consent_number')}: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def insert_consent_limits(consent_id, limits):
    if not limits:
        return
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Delete existing limits for this consent to avoid duplicates
        cur.execute("DELETE FROM consent_limits WHERE consent_id = %s;", (consent_id,))
        
        insert_data = []
        for lim in limits:
            insert_data.append((
                consent_id,
                lim["factory_id"],
                lim["parameter"],
                lim.get("minimum_limit"),
                lim.get("maximum_limit"),
                lim.get("unit"),
                lim.get("condition_text"),
                lim.get("page_number"),
                lim.get("table_number"),
                lim.get("extraction_confidence")
            ))
            
        execute_values(cur, """
            INSERT INTO consent_limits (
                consent_id, factory_id, parameter, minimum_limit, maximum_limit,
                unit, condition_text, page_number, table_number, extraction_confidence
            ) VALUES %s;
        """, insert_data)
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to insert consent limits for consent_id {consent_id}: {e}")
    finally:
        cur.close()
        conn.close()

def insert_download_log(log_data):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO consent_download_logs (
                factory, status, pdf_downloaded, tables_detected, 
                limits_extracted, execution_time, error_message
            ) VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (
            log_data["factory"],
            log_data["status"],
            log_data["pdf_downloaded"],
            log_data.get("tables_detected", 0),
            log_data.get("limits_extracted", 0),
            log_data.get("execution_time"),
            log_data.get("error_message")
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to insert download log: {e}")
    finally:
        cur.close()
        conn.close()
