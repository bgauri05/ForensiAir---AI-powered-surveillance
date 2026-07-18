import os
import csv
import io
import psycopg2
from datetime import datetime, timezone
from dotenv import load_dotenv

QUALITY_MAP = {
    'U': 'Raw',
    'V': 'Validated',
    'E': 'Error',
    'O': 'Out of Range',
    'N': 'Negative',
    'I': 'Invalid',
    'M': 'Maintenance',
    'C': 'Span Calibration',
    'Z': 'Zero Calibration',
    'X': 'Expected Calibration',
    'Y': 'Dynamic Limit',
    'input': 'Manual Input'
}

def parse_cell(cell_str):
    if not cell_str:
        return None, None
    cell_str = cell_str.strip()
    if cell_str.startswith("['NA'") or cell_str.startswith('["NA"'):
        return None, None
    
    cleaned = cell_str.strip('[]')
    parts = cleaned.split(',')
    if len(parts) == 2:
        val_str = parts[0].strip()
        code_str = parts[1].strip(" '\"")
        try:
            return float(val_str), code_str
        except ValueError:
            return None, None
    return None, None

def main():
    # 1. Load backend env to get DATABASE_URL
    dotenv_path = "c:/Users/gauri/OneDrive/Desktop/forensiair/backend/.env"
    load_dotenv(dotenv_path=dotenv_path, override=True)
    database_url = os.getenv("DATABASE_URL")
    
    print("Connecting to database:", database_url)
    conn = psycopg2.connect(database_url)
    conn.autocommit = True
    cur = conn.cursor()
    
    # 2. Clear existing ETP-pH entries to ensure idempotency
    print("Cleaning up any existing ETP-pH records from monitoring_data...")
    cur.execute("DELETE FROM monitoring_data WHERE parameter_id = 'ETP-pH';")
    print(f"Removed {cur.rowcount} records.")
    
    # 3. Open ETP-pH CSV file
    csv_path = "c:/Users/gauri/OneDrive/Desktop/mpcb_scraper/mpcb_ph_data.csv"
    if not os.path.exists(csv_path):
        print(f"CSV file not found: {csv_path}")
        return
        
    print("Opening CSV file:", csv_path)
    
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        header = next(reader)
        
        # 4. Map columns
        time_idx = header.index("Time")
        factory_idx = header.index("factory_name")
        city_idx = header.index("city")
        category_idx = header.index("category")
        site_idx = header.index("site_id")
        
        param_columns = {}
        for idx, col in enumerate(header):
            if '_' in col and not col.startswith('factory_') and col != 'site_id':
                parts = col.split('_')
                param_columns[idx] = (parts[0], parts[1])
                
        print(f"Mapped {len(param_columns)} parameter columns.")
        
        # 4b. Extract unique factories and check if they exist in DB, if not insert them
        print("Scanning CSV for unique factories...")
        f.seek(0)
        next(reader) # skip header
        
        factories_dict = {}
        for row in reader:
            if len(row) > site_idx:
                site_id = row[site_idx]
                if site_id and site_id not in factories_dict:
                    factories_dict[site_id] = {
                        "site_id": site_id,
                        "name": row[factory_idx],
                        "category": row[category_idx],
                        "city": row[city_idx],
                        "state": "Maharashtra"
                    }
                    
        print(f"Found {len(factories_dict)} unique factories in CSV.")
        
        # Check against existing factories in DB
        cur.execute("SELECT site_id FROM factories;")
        existing_ids = {r[0] for r in cur.fetchall()}
        
        inserted_factories = 0
        for site_id, fact in factories_dict.items():
            if site_id not in existing_ids:
                print(f"  [NEW FACTORY] Inserting missing factory: {site_id} - {fact['name']}")
                cur.execute("""
                    INSERT INTO factories (site_id, name, category, city, state, created_at)
                    VALUES (%s, %s, %s, %s, %s, NOW());
                """, (fact["site_id"], fact["name"], fact["category"], fact["city"], fact["state"]))
                inserted_factories += 1
                
        print(f"Inserted {inserted_factories} new factories into the database.")
        
        # Reset file pointer for streaming monitoring data
        f.seek(0)
        next(reader) # skip header
        
        # 5. Parse and load monitoring data
        print("Streaming and inserting ETP-pH data...")
        
        # Keep track of counts per factory-parameter for download_logs
        log_counts = {}
        seen_keys = set()
        
        batch_size = 100000
        buffer = io.StringIO()
        rows_processed = 0
        copied_count = 0
        duplicate_count = 0
        
        now_str = datetime.now(timezone.utc).isoformat()
        
        for row in reader:
            if len(row) <= site_idx:
                continue
                
            site_id = row[site_idx]
            timestamp_str = row[time_idx] + ":00" # Format: YYYY-MM-DD HH:MM:SS
            
            # Process each parameter column (should be ETP-pH)
            for col_idx, (param_id, suffix) in param_columns.items():
                val, code = parse_cell(row[col_idx])
                if val is not None:
                    key = (site_id, param_id, timestamp_str)
                    if key in seen_keys:
                        duplicate_count += 1
                        continue
                    seen_keys.add(key)
                    
                    q_code = QUALITY_MAP.get(code, code)
                    # Write to TSV buffer for fast COPY
                    buffer.write(f"{site_id}\t{param_id}\t{timestamp_str}\t{val}\t{q_code}\t{now_str}\n")
                    
                    log_key = (site_id, param_id)
                    log_counts[log_key] = log_counts.get(log_key, 0) + 1
                    copied_count += 1
                    
            rows_processed += 1
            if rows_processed % batch_size == 0:
                # Flush buffer to PostgreSQL
                buffer.seek(0)
                cur.copy_from(buffer, 'monitoring_data', 
                              columns=('factory_id', 'parameter_id', 'timestamp', 'value', 'quality_code', 'created_at'))
                buffer = io.StringIO()
                print(f"Processed {rows_processed} rows... Loaded {copied_count} records. Skipped {duplicate_count} duplicates.")
                
        # Flush remaining buffer
        if buffer.tell() > 0:
            buffer.seek(0)
            cur.copy_from(buffer, 'monitoring_data', 
                          columns=('factory_id', 'parameter_id', 'timestamp', 'value', 'quality_code', 'created_at'))
            
        print(f"Successfully loaded total of {copied_count} ETP-pH monitoring data records! (Skipped {duplicate_count} duplicate entries)")
        
        # 6. Insert download logs
        print("Inserting download logs...")
        for (site_id, param_id), count in log_counts.items():
            # Delete old download log for ETP-pH for this factory to prevent duplicate counts
            cur.execute("""
                DELETE FROM download_logs WHERE factory_id = %s AND parameter_id = %s;
            """, (site_id, param_id))
            
            cur.execute("""
                INSERT INTO download_logs (factory_id, parameter_id, row_count, started_at, finished_at, status, error_message, created_at)
                VALUES (%s, %s, %s, NOW(), NOW(), 'SUCCESS', NULL, NOW());
            """, (site_id, param_id, count))
            
    print("Database loading complete for ETP-pH!")
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
