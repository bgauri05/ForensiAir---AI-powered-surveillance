import os
import shutil
import time
from pathlib import Path
from collector.consent.config import CONSENTS_DIR, LY_PDFS_DIR, PROJECT_ROOT
from collector.consent.logger import logger
from collector.consent.database import (
    init_db, get_db_factories, consent_exists, 
    insert_consent, insert_consent_limits, insert_download_log
)
from collector.consent.scraper import (
    query_cms_for_consent, resolve_blockchain_pdf_link, download_pdf
)
from collector.consent.parser import parse_cto_metadata, parse_cto_limits

# MAPPING_DICT dynamically maps DB site_id to MPCB consent number
MAPPING_DICT = {
    "site_1799": "MPCB-CONSENT-0000232068",  # Privi Speciality Chemicals  Limited  Unit 10
    "site_1232": "MPCB-CONSENT-0000097338",  # M/s.Altaroma Chemicals Pvt Ltd
    "site_1369": "MPCB-CONSENT-0000160698",  # M/s.Privi Specialty Chemicals Ltd(Unit-II)
    "site_1167": "MPCB-CONSENT-0000277184",  # Super Petroleum Products Private Limited
    "site_1206": "MPCB-CONSENT-0000264751",  # Marvel Drugs Pvt. Ltd
    "site_1131": "",  # RUPA ORGANICS PVT LTD. Taloja (requires dynamic search)
    "site_1256": "MPCB-CONSENT-0000101109",  # SHREE VINAYAK ORGANICS (I) PVT LTD
    "site_1376": "MPCB-CONSENT-0000283487",  # M/s.Privi Speciality Chemicals Limited Unit III
    "site_2108": "MPCB-CONSENT-0000115878",  # Oriental Aromatics & Sons Limited
    "site_1787": "MPCB-CONSENT-0000261348",  # SHREE HARI CHEMICALS EXPORT LIMITED
    "site_1756": "MPCB-CONSENT-0000257756",  # M/s. Aquapharm Chemicals Pvt. Ltd.
    "site_2191": "MPCB-CONSENT-0000257756",  # AQUAPHARM CHEMICAL LIMITED
    "site_2196": "MPCB-CONSENT-0000273295",  # M/s. Anmol Chemicals Industries Pvt. Ltd.
    "site_1327": "MPCB-CONSENT-0000071882",  # GAURI ACIDS PVT LTD
    "site_1221": "MPCB-CONSENT-0000151904",  # Zirconium Chemicals Pvt. Ltd
    "site_1214": "MPCB-CONSENT-0000093835",  # Breeze Chemicals Pvt. Ltd
    "site_1581": "MPCB-CONSENT-0000269615",  # M/s Memba Chem Industries Private Limited
    "site_1264": "MPCB-CONSENT-0000137011",  # Imagico India Pvt Ltd
    "site_1909": "MPCB-CONSENT-0000113656",  # Cyklo Pharma Chem Pvt Ltd
    "site_1668": "MPCB-CONSENT-0000266425",  # Nouryon Chemicals India Private Limited
    "site_1257": "MPCB-CONSENT-0000246137",  # Dorf Ketal Chemicals India Pvt Ltd
    "site_1310": "MPCB-CONSENT-0000252627",  # Aezis Global Pvt Ltd
    "site_1260": "MPCB-CONSENT-0000093420",  # MAHAVIR CHEMICALS INDIA
    "site_982": "MPCB-CONSENT-0000237849",  # PREETI PETROCHEM PVT LTD
    "site_1246": "MPCB-CONSENT-0000168469",  # Balajee Rang udyog Pvt Ltd
    "site_1138": "MPCB-CONSENT-0000283848",  # Nixon Chemicals Ltd
    "site_987": "MPCB-CONSENT-0000155316",  # Ricinash Oil Mill Limited
    "site_1203": "MPCB-CONSENT-0000096014",  # Anmol Chemicals Pvt. Ltd
    "site_1284": "MPCB-CONSENT-0000261159",  # CORROGARD CHEMICALS
    "site_1905": "MPCB-CONSENT-0000170084",  # Allnex Resins India Pvt ltd
    "site_1789": "MPCB-CONSENT-0000165835",  # sudarshan chemical industries ltd Mahad
    "site_2181": "MPCB-CONSENT-0000123206",  # Aastrid Life Sciences Private Limited -B 19
    "site_1040": "MPCB-CONSENT-0000132075",  # VASUDHA CHEMICALS PVT LTD
    "site_1285": "MPCB-CONSENT-0000066769",  # VVL Pharma Pvt Ltd
    "site_1261": "MPCB-CONSENT-0000078247",  # Mody Chemi Pharma Pvt Ltd
    "site_1280": "MPCB-CONSENT-0000068369",  # EKVIRA FINE CHEM PVT LTD
    "site_887": "MPCB-CONSENT-0000265460",  # Dow Chemical International Pvt Ltd
    "site_1259": "MPCB-CONSENT-0000074431",  # EUROCHEM INDUSTRIES
    "site_1569": "MPCB-CONSENT-0000272198",  # M/s.Galaxy Surfactants Limited
    "site_2149": "MPCB-CONSENT-0000119895",  # GRASIM INDUSTRIES LIMITED
    "site_1247": "MPCB-CONSENT-0000276347",  # Ducol Organics & Colours Pvt Ltd
    "site_2199": "MPCB-CONSENT-0000254069",  # Indo Amines Limited (Formerly Known as LASA Supergenerics Limited)
    "site_1281": "MPCB-CONSENT-0000078247",  # M/s RAMDEV CHEMI-Pharma PVT LTD
    "site_1286": "MPCB-CONSENT-0000152950",  # SAGARKALA CHEMICALS PVT LTD
    "site_1255": "MPCB-CONSENT-0000261554",  # Range Polymers
    "site_1200": "MPCB-CONSENT-0000243837",  # Metallurgical Products India(P) Ltd
    "site_1279": "MPCB-CONSENT-0000281560",  # Sindhu Organics Pvt. Ltd.
    "site_1680": "MPCB-CONSENT-0000133185",  # Yellowstone Chemicals Pvt. Ltd
    "site_2070": "MPCB-CONSENT-0000148590",  # Prigiv Specialties Pvt Ltd
    "site_2195": "MPCB-CONSENT-0000128179",  # M/s. Ravi Biolife Pvt.Ltd
    "site_1321": "MPCB-CONSENT-0000271943",  # M/s. Indo Amines Ltd.
}

def clean_filename(name):
    # Keep alphanumeric characters and underscores
    return "".join(c if c.isalnum() else "_" for c in name).strip("_")

def run_collector():
    logger.info("Starting Consent to Operate (CTO) Intelligence Collector...")
    init_db()
    
    factories = get_db_factories()
    logger.info(f"Loaded {len(factories)} factories from factories table.")
    
    total_processed = 0
    total_downloaded = 0
    total_limits_inserted = 0
    
    for site_id, name, city in factories:
        start_time = time.time()
        status = "SKIPPED"
        pdf_downloaded = False
        limits_inserted_count = 0
        error_message = None
        
        consent_no = MAPPING_DICT.get(site_id, "")
        
        # Check if we need to search dynamically
        if not consent_no:
            logger.info(f"[{site_id}] No pre-mapped consent number. Performing dynamic live search for '{name}'...")
            doc_url, meta = query_cms_for_consent(name)
            if not doc_url:
                # Try search by city/partial name
                doc_url, meta = query_cms_for_consent(name.split()[0])
            
            if doc_url and meta:
                consent_no = meta.get("consent_number")
                logger.info(f"[{site_id}] Dynamically mapped factory '{name}' to consent {consent_no}.")
            else:
                logger.warning(f"[{site_id}] Live query failed to resolve consent number for '{name}'. Skipping.")
                status = "FAILED_MAPPING"
                error_message = "Failed to resolve consent number via CMS live search"
                insert_download_log({
                    "factory": name,
                    "status": status,
                    "pdf_downloaded": False,
                    "tables_detected": 0,
                    "limits_extracted": 0,
                    "execution_time": round(time.time() - start_time, 2),
                    "error_message": error_message
                })
                continue
                
        # Check if consent already exists in DB
        if consent_exists(consent_no):
            logger.info(f"[{site_id}] Consent {consent_no} already exists in DB. Skipping.")
            status = "SKIPPED_DB_EXISTS"
            insert_download_log({
                "factory": name,
                "status": status,
                "pdf_downloaded": False,
                "tables_detected": 0,
                "limits_extracted": 0,
                "execution_time": round(time.time() - start_time, 2),
                "error_message": None
            })
            continue
            
        # Target local storage path
        safe_factory_name = clean_filename(name)
        safe_city_name = clean_filename(city)
        local_dest_path = CONSENTS_DIR / safe_city_name / safe_factory_name / f"CTO_{consent_no}.pdf"
        
        # 1. Check local cache (LY PROJECT/pdfs) first
        cached_pdf_path = LY_PDFS_DIR / f"{consent_no}.pdf"
        
        if cached_pdf_path.exists():
            logger.info(f"[{site_id}] Found cached PDF locally in LY_PDFS_DIR: {cached_pdf_path}")
            try:
                os.makedirs(local_dest_path.parent, exist_ok=True)
                shutil.copy2(cached_pdf_path, local_dest_path)
                logger.info(f"Copied cached PDF to: {local_dest_path}")
                pdf_downloaded = True
                status = "SUCCESS_CACHED"
            except Exception as e:
                logger.error(f"Failed to copy cached PDF: {e}")
                error_message = f"Failed to copy cached PDF: {e}"
                status = "FAILED_COPY"
        else:
            # 2. Live scrape from CMS portal
            logger.info(f"[{site_id}] PDF not found in cache. Retrieving live link for consent {consent_no}...")
            doc_url, meta = query_cms_for_consent(consent_no)
            if doc_url:
                pdf_url = resolve_blockchain_pdf_link(doc_url)
                if pdf_url:
                    logger.info(f"[{site_id}] Downloading live PDF from resolved link: {pdf_url}")
                    success = download_pdf(pdf_url, local_dest_path)
                    if success:
                        pdf_downloaded = True
                        status = "SUCCESS_LIVE"
                        total_downloaded += 1
                    else:
                        status = "FAILED_DOWNLOAD"
                        error_message = "Failed to download PDF binary from resolved blockchain link"
                else:
                    status = "FAILED_RESOLVING"
                    error_message = "Failed to resolve direct PDF URL from blockchain document page"
            else:
                status = "FAILED_SEARCH"
                error_message = "Failed to locate consent row in live MPCB CMS search"
                
        # 3. Parse and Insert if PDF is available
        tables_detected = 0
        if pdf_downloaded and local_dest_path.exists():
            # Parse metadata
            meta = parse_cto_metadata(local_dest_path)
            meta["factory_id"] = site_id
            meta["factory_name"] = name
            meta["consent_number"] = consent_no
            meta["pdf_path"] = str(local_dest_path.relative_to(PROJECT_ROOT) if local_dest_path.is_relative_to(PROJECT_ROOT) else local_dest_path)
            meta["source_url"] = doc_url if 'doc_url' in locals() else None
            
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
                logger.info(f"[{site_id}] Successfully extracted and inserted {limits_inserted_count} environmental limits.")
            else:
                status = "FAILED_DB_INSERT"
                error_message = "Failed to insert consent metadata into database"
                
        # Record execution log
        execution_time = round(time.time() - start_time, 2)
        insert_download_log({
            "factory": name,
            "status": status,
            "pdf_downloaded": pdf_downloaded,
            "tables_detected": tables_detected,
            "limits_extracted": limits_inserted_count,
            "execution_time": execution_time,
            "error_message": error_message
        })
        
        total_processed += 1
        
    logger.info("\nConsent Collection Summary:")
    logger.info(f" - Total factories processed: {total_processed}/51")
    logger.info(f" - New PDFs downloaded live: {total_downloaded}")
    logger.info(f" - Total consent parameter limits inserted: {total_limits_inserted}")
    logger.info("Consent Collector process finished.")

if __name__ == '__main__':
    run_collector()
