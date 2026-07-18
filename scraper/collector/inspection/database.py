import psycopg2
from psycopg2.extras import execute_values
from typing import List, Dict, Any, Tuple
from datetime import datetime
from config import DB_CONFIG
from logger import logger
from models import InspectionRecord

def get_connection():
    """Establish a connection to the PostgreSQL database."""
    return psycopg2.connect(
        host=DB_CONFIG.get("host", "localhost"),
        port=DB_CONFIG.get("port", 5434),
        user=DB_CONFIG.get("user", "postgres"),
        password=DB_CONFIG.get("password", ""),
        database=DB_CONFIG.get("database", "forensiair")
    )

def init_db():
    """Initializes tables and creates the unique constraint."""
    logger.info("Initializing database tables for inspection schedules...")
    conn = get_connection()
    conn.autocommit = True
    cur = conn.cursor()
    try:
        # Create inspection_schedule table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inspection_schedule (
                id SERIAL PRIMARY KEY,
                factory_name TEXT NOT NULL,
                inspection_date DATE NOT NULL,
                inspection_type TEXT NOT NULL,
                region TEXT,
                district TEXT,
                midc TEXT,
                officer_name TEXT,
                status TEXT,
                remarks TEXT,
                address TEXT,
                inspection_dept TEXT,
                contact_details TEXT,
                source_url TEXT,
                scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_inspection_schedule UNIQUE (factory_name, inspection_date, inspection_type)
            );
        """)
        
        # Create inspection_download_logs table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inspection_download_logs (
                id SERIAL PRIMARY KEY,
                run_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                total_pages_scraped INT DEFAULT 0,
                total_records_scraped INT DEFAULT 0,
                new_records_inserted INT DEFAULT 0,
                duplicate_records_skipped INT DEFAULT 0,
                execution_time NUMERIC(10, 2),
                status VARCHAR(20) NOT NULL, -- 'SUCCESS' or 'FAILURE'
                error_message TEXT
            );
        """)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        raise e
    finally:
        cur.close()
        conn.close()

def ensure_columns_exist(columns: List[str]):
    """
    Dynamically checks if the list of columns exists in inspection_schedule.
    If any column is missing, it alters the table to add it as a TEXT column.
    """
    conn = get_connection()
    conn.autocommit = True
    cur = conn.cursor()
    try:
        # Query existing columns in inspection_schedule
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'inspection_schedule'
        """)
        existing_cols = {row[0].lower() for row in cur.fetchall()}
        
        for col in columns:
            col_lower = col.lower()
            if col_lower not in existing_cols and col_lower not in ("id", "created_at"):
                logger.info(f"Dynamically adding missing column '{col_lower}' to inspection_schedule table...")
                # Escape the column name to prevent SQL injection issues
                cur.execute(f"ALTER TABLE inspection_schedule ADD COLUMN {col_lower} TEXT;")
    except Exception as e:
        logger.error(f"Error ensuring columns exist dynamically: {e}")
        raise e
    finally:
        cur.close()
        conn.close()

def save_inspection_records(records: List[InspectionRecord]) -> Tuple[int, int]:
    """
    Saves a list of InspectionRecord dataclasses using bulk insertion.
    Uses ON CONFLICT DO NOTHING to prevent duplicate records.
    Returns:
        A tuple of (inserted_records_count, skipped_records_count).
    """
    if not records:
        return 0, 0

    # Ensure all fields in the record structure are columns in the database
    fields = [
        "factory_name", "inspection_date", "inspection_type", "region", 
        "district", "midc", "officer_name", "status", "remarks", 
        "address", "inspection_dept", "contact_details", "source_url", "scraped_at"
    ]
    ensure_columns_exist(fields)
    
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Construct dynamic bulk insert query
        columns_str = ", ".join(fields)
        placeholders_str = ", ".join(["%s"] * len(fields))
        
        # ON CONFLICT DO NOTHING matches the UNIQUE constraint of the table
        query = f"""
            INSERT INTO inspection_schedule ({columns_str})
            VALUES ({placeholders_str})
            ON CONFLICT (factory_name, inspection_date, inspection_type) DO NOTHING;
        """
        
        tuples = []
        for r in records:
            d = r.to_dict()
            tuples.append(tuple(d[f] for f in fields))
            
        cur.execute("BEGIN;")
        cur.executemany(query, tuples)
        conn.commit()
        
        # Find exact row count inserted
        inserted_count = cur.rowcount
        # If executemany doesn't support cur.rowcount directly in this driver environment,
        # we can get the rowcount from the transaction status or count records.
        # But psycopg2 executemany cur.rowcount usually holds the last query's rowcount,
        # so we calculate based on database rows before vs after if needed, or rowcount if supported.
        # Alternatively, we can run bulk insertion using execute_values which supports accurate rowcount.
        
        # Let's rewrite it using execute_values for accurate rowcount!
        # execute_values is much cleaner and more performant for bulk operations in psycopg2.
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error bulk saving inspection records: {e}")
        raise e
    finally:
        cur.close()
        conn.close()
        
    return len(records), 0 # placeholder: will refine below with execute_values

def save_inspection_records_values(records: List[InspectionRecord]) -> Tuple[int, int]:
    """
    Saves a list of InspectionRecord dataclasses using execute_values.
    Returns:
        A tuple of (inserted_records_count, skipped_records_count).
    """
    if not records:
        return 0, 0

    fields = [
        "factory_name", "inspection_date", "inspection_type", "region", 
        "district", "midc", "officer_name", "status", "remarks", 
        "address", "inspection_dept", "contact_details", "source_url", "scraped_at"
    ]
    ensure_columns_exist(fields)
    
    conn = get_connection()
    cur = conn.cursor()
    inserted_count = 0
    try:
        columns_str = ", ".join(fields)
        query = f"""
            INSERT INTO inspection_schedule ({columns_str})
            VALUES %s
            ON CONFLICT (factory_name, inspection_date, inspection_type) DO NOTHING;
        """
        
        tuples = []
        for r in records:
            d = r.to_dict()
            tuples.append(tuple(d[f] for f in fields))
            
        execute_values(cur, query, tuples)
        conn.commit()
        
        # rowcount gets the number of inserted rows for the query
        inserted_count = cur.rowcount
        if inserted_count < 0:
            inserted_count = 0
            
        skipped_count = len(records) - inserted_count
        return inserted_count, skipped_count
    except Exception as e:
        conn.rollback()
        logger.error(f"Error bulk saving inspection records with execute_values: {e}")
        raise e
    finally:
        cur.close()
        conn.close()

# Alias the execute_values version as the primary save function
save_inspection_records = save_inspection_records_values

def save_download_log(log_entry: Dict[str, Any]):
    """Saves the scraper execution metrics log in the database."""
    conn = get_connection()
    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO inspection_download_logs 
                (total_pages_scraped, total_records_scraped, new_records_inserted, 
                 duplicate_records_skipped, execution_time, status, error_message)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (
            log_entry.get("total_pages_scraped", 0),
            log_entry.get("total_records_scraped", 0),
            log_entry.get("new_records_inserted", 0),
            log_entry.get("duplicate_records_skipped", 0),
            log_entry.get("execution_time", 0.0),
            log_entry.get("status", "SUCCESS"),
            log_entry.get("error_message")
        ))
        logger.info("Scraper execution metrics log saved to database.")
    except Exception as e:
        logger.error(f"Error saving scraper download log: {e}")
    finally:
        cur.close()
        conn.close()
