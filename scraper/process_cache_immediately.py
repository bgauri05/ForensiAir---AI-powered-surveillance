import os
import shutil
import time
from pathlib import Path
from collector.consent.config import DB_CONFIG, PROJECT_ROOT, CONSENTS_DIR, LY_PDFS_DIR
from collector.consent.logger import logger
from collector.consent.database import (
    init_db, get_connection, consent_exists, insert_consent, insert_consent_limits, insert_download_log
)
from collector.consent.collector import MAPPING_DICT, clean_filename
from collector.consent.parser import parse_cto_metadata, parse_cto_limits

def run_cache_only():
    init_db()
    
    # Load factories from DB
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT site_id, name, city FROM factories;")
    factories = cur.fetchall()
    cur.close()
    conn.close()
    
    print(f"Loaded {len(factories)} factories from database.")
    print("Starting cache-only immediate import...")
    
    total_processed = 0
    total_limits_inserted = 0
    
    for site_id, name, city in factories:
        consent_no = MAPPING_DICT.get(site_id, "")
        if not consent_no:
            continue
            
        # check if cached PDF exists
        cached_pdf_path = LY_PDFS_DIR / f"{consent_no}.pdf"
        if not cached_pdf_path.exists():
            continue
            
        print(f"\nProcessing factory: {name} ({site_id})")
        print(f"  Mapped consent: {consent_no}")
        
        # Check if already in DB
        if consent_exists(consent_no):
            print(f"  [SKIPPED] Consent {consent_no} already exists in DB.")
            continue
            
        start_time = time.time()
        
        # Target local storage path
        safe_factory_name = clean_filename(name)
        safe_city_name = clean_filename(city) if city else "Unknown"
        local_dest_path = CONSENTS_DIR / safe_city_name / safe_factory_name / f"CTO_{consent_no}.pdf"
        
        print(f"  Found cached PDF at: {cached_pdf_path}")
        try:
            os.makedirs(local_dest_path.parent, exist_ok=True)
            shutil.copy2(cached_pdf_path, local_dest_path)
            print(f"  Copied PDF to: {local_dest_path}")
            
            # Parse metadata
            meta = parse_cto_metadata(local_dest_path)
            meta["factory_id"] = site_id
            meta["factory_name"] = name
            meta["consent_number"] = consent_no
            meta["pdf_path"] = str(local_dest_path.relative_to(PROJECT_ROOT) if local_dest_path.is_relative_to(PROJECT_ROOT) else local_dest_path)
            meta["source_url"] = None
            
            # Insert consent record
            consent_id = insert_consent(meta)
            if consent_id:
                # Parse limits
                limits = parse_cto_limits(local_dest_path, site_id)
                tables_detected = len(set((lim["page_number"], lim["table_number"]) for lim in limits))
                limits_inserted_count = len(limits)
                
                # Insert limits
                insert_consent_limits(consent_id, limits)
                total_limits_inserted += limits_inserted_count
                print(f"  [SUCCESS] Inserted consent and {limits_inserted_count} limits.")
                
                # Record log
                insert_download_log({
                    "factory": name,
                    "status": "SUCCESS_CACHED",
                    "pdf_downloaded": True,
                    "tables_detected": tables_detected,
                    "limits_extracted": limits_inserted_count,
                    "execution_time": round(time.time() - start_time, 2),
                    "error_message": None
                })
                total_processed += 1
            else:
                print("  [ERROR] Failed to insert consent metadata.")
        except Exception as e:
            print(f"  [ERROR] Failed to process cache file: {e}")

    print(f"\nCache-only import finished.")
    print(f" - Factories imported: {total_processed}")
    print(f" - Limits inserted: {total_limits_inserted}")

if __name__ == '__main__':
    run_cache_only()
