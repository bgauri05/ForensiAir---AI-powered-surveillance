"""
MPCB OCEMS Scraper — FINAL (Requests Edition)
=============================================
This version uses direct Python requests to communicate with the MPCB API.
It avoids Selenium script execution timeouts, browser crashes, and driver version mismatches.
"""

import requests
import base64
import json
import time
import os
import pandas as pd
import sys

# Force stdout/stderr to UTF-8 to avoid encoding crashes on Windows console
if sys.stdout and sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr and sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────
PORTAL_URL     = "https://onlinecems.ecmpcb.in/#/publicPortal/categoryList"
BASE_API_URL   = "https://onlinecems.ecmpcb.in/glens/publicPortal/api/v2.0/"
FACTORY_CSV    = "all_factories.csv"        # 97-factory file
FROM_DATE      = "2024/01/01 00:00:00"
TO_DATE        = "2024/12/31 23:59:59"
OUTPUT_CSV     = "mpcb_etp_data.csv"
LOG_CSV        = "scrape_log.csv"
SLEEP_BETWEEN  = 1.0                         # seconds between requests
CHECKPOINT_N   = 10                         # save every N factories

# ETP parameters to pull
ETP_PARAMS = ["ETP-COD", "ETP-BOD", "ETP-TSS", "ETP-pH",
              "ETP-Flow", "ETP-Totalizer"]

# Quality codes
ALL_QUALITY = ["U","E","O","N","I","M","V","C","input","Z","X","Y"]

# ─────────────────────────────────────────────────────────────────
# CORE API CALLER
# ─────────────────────────────────────────────────────────────────
def call_api(endpoint: str, payload: dict, timeout=15) -> dict:
    """
    Make a POST to /glens/publicPortal/api/v2.0/{endpoint}
    Body must be base64-encoded JSON sent as text/plain.
    Response is base64-encoded JSON.
    """
    url = BASE_API_URL + endpoint
    payload_json = json.dumps(payload)
    payload_b64  = base64.b64encode(payload_json.encode("utf-8")).decode("ascii")

    headers = {
        "Content-Type": "text/plain",
        "Accept": "application/json, text/plain, */*"
    }

    try:
        resp = requests.post(url, headers=headers, data=payload_b64, timeout=timeout)
        if resp.status_code == 200:
            raw = resp.text
            if not raw:
                return None
            try:
                decoded = base64.b64decode(raw).decode("utf-8")
                return json.loads(decoded)
            except Exception:
                # Fallback if raw JSON is returned
                try:
                    return json.loads(raw)
                except Exception:
                    return None
    except Exception:
        pass
    return None

# ─────────────────────────────────────────────────────────────────
# MONTHLY RANGES GENERATOR
# ─────────────────────────────────────────────────────────────────
def get_monthly_ranges():
    """
    Generate month-by-month tuples for the year 2024.
    """
    # 2024 is leap year
    days_in_months = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    ranges = []
    for m in range(1, 13):
        days = days_in_months[m-1]
        from_str = f"2024/{m:02d}/01 00:00:00"
        to_str = f"2024/{m:02d}/{days:02d} 23:59:59"
        ranges.append((m, from_str, to_str))
    return ranges

# ─────────────────────────────────────────────────────────────────
# MATCHING LOGIC
# ─────────────────────────────────────────────────────────────────
def find_match(target_name, target_city, api_factories):
    target_name_clean = target_name.lower().replace("m/s", "").replace(".", "").replace(",", "").replace("-", " ").strip()
    target_city_clean = "taloja" if "taloja" in target_city.lower() else "mahad" if "mahad" in target_city.lower() else None
    
    if not target_city_clean:
        return None
        
    common_words = {
        "limited", "private", "ltd", "pvt", "corp", "co", "india", "pharmaceuticals", 
        "pharmaceutical", "chemicals", "chemical", "industries", "industry", "company", 
        "sciences", "science", "labs", "laboratories", "laboratory", "m/s", "unit", 
        "formerly", "known", "know", "as", "formarly", "formaly"
    }
    target_words = [w for w in target_name_clean.split() if len(w) > 2 and w not in common_words]
    
    best_match = None
    best_score = 0
    
    for f in api_factories:
        api_city = str(f.get("city", ""))
        api_city_clean = "taloja" if "taloja" in api_city.lower() else "mahad" if "mahad" in api_city.lower() else None
        
        if api_city_clean != target_city_clean:
            continue
            
        api_name = str(f.get("industryName", "")).strip()
        api_name_clean = api_name.lower().replace("m/s", "").replace(".", "").replace(",", "").replace("-", " ").strip()
        
        # 1. Substring matches
        if target_name_clean in api_name_clean or api_name_clean in target_name_clean:
            return f
            
        # 2. Word overlap matches
        api_words = [w for w in api_name_clean.split() if len(w) > 2 and w not in common_words]
        overlap = set(target_words) & set(api_words)
        
        if len(overlap) > best_score:
            best_score = len(overlap)
            best_match = f
            
    min_required_overlap = min(2, len(target_words)) if target_words else 1
    if best_score >= min_required_overlap:
        return best_match
        
    return None

# ─────────────────────────────────────────────────────────────────
# SCRAPING LOGIC
# ─────────────────────────────────────────────────────────────────
def run_scrape():
    df_factories = pd.read_csv(FACTORY_CSV)
    
    print(f"\n{'='*55}")
    print(f"Target factories in CSV: {len(df_factories)}")
    print(f"Date range: {FROM_DATE}  →  {TO_DATE}")
    print(f"{'='*55}\n")

    # Get all industries from Chemical category (since Drugs and Pharma is empty on public portal)
    print("Fetching Chemical industries from API...")
    payload_chem = {
        "categoryId": "Chemical",
        "userName": None, "userId": None, "userType": None,
        "userRole": None, "userAccess": None,
        "domain": "onlinecems.ecmpcb.in"
    }
    result_chem = call_api("CategoryDetails", payload_chem, timeout=30)
    api_factories = result_chem.get("bodyContent", []) if result_chem else []
    print(f"Fetched {len(api_factories)} industries from API.")

    # Match target factories
    matched_count = 0
    unmatched_count = 0
    targets_to_scrape = []

    for i, row in df_factories.iterrows():
        name = str(row.get("Industry Name", "")).strip()
        city = str(row.get("City", "")).strip()
        category = str(row.get("Industry Category", "")).strip()
        
        match = find_match(name, city, api_factories)
        if match:
            matched_count += 1
            targets_to_scrape.append({
                "factory": name,
                "city": city,
                "category": category,
                "site_id": match["siteId"],
                "api_name": match["industryName"]
            })
        else:
            unmatched_count += 1
            targets_to_scrape.append({
                "factory": name,
                "city": city,
                "category": category,
                "site_id": None,
                "api_name": None
            })

    print(f"\nMatched targets: {matched_count}")
    print(f"Unmatched targets: {unmatched_count}")
    
    all_records = []
    log_rows = []
    total = len(targets_to_scrape)

    # Monthly ranges for chunking 2024 data
    monthly_ranges = get_monthly_ranges()

    for idx, target in enumerate(targets_to_scrape):
        name = target["factory"]
        city = target["city"]
        category = target["category"]
        site_id = target["site_id"]
        
        print(f"\n[{idx+1}/{total}] {name}")
        print(f"        City: {city} | Category: {category}")
        
        if not site_id:
            print("    ⚠️  siteId not found — skipping")
            log_rows.append({
                "factory": name, "city": city, "category": category,
                "site_id": None, "status": "no_site_id", "records": 0
            })
            continue
            
        print(f"    siteId: {site_id}")
        
        # Fetch month by month
        factory_records = 0
        
        for m, from_date, to_date in monthly_ranges:
            payload_tab = {
                "fromDate": from_date,
                "toDate": to_date,
                "siteId": site_id,
                "stations": ["ETP"],
                "parameters": ETP_PARAMS,
                "criteria": "15min",
                "reportFormat": "tabular",
                "qualityCode": ALL_QUALITY,
                "graphType": "singleParameter",
                "quickRange": False,
                "userName": None, "userId": None, "userType": None,
                "userRole": None, "userAccess": None,
                "domain": "onlinecems.ecmpcb.in"
            }
            
            # Use 15-second timeout for tabular queries to keep scraper moving quickly
            result = call_api("industry-tabular", payload_tab, timeout=15)
            
            if result:
                rows = result.get("parameterDetails", {}).get("bodyContent", [])
                if rows:
                    for r in rows:
                        if isinstance(r, dict):
                            r["factory_name"] = name
                            r["city"] = city
                            r["category"] = category
                            r["site_id"] = site_id
                            all_records.append(r)
                    print(f"      - Month {m:02d}: Got {len(rows)} rows")
                    factory_records += len(rows)
                else:
                    print(f"      - Month {m:02d}: Empty")
            else:
                print(f"      - Month {m:02d}: Timeout/No response")
                
            time.sleep(SLEEP_BETWEEN)
            
        if factory_records == 0:
            print("    ❌ No data returned for the entire year")
            log_rows.append({
                "factory": name, "city": city, "category": category,
                "site_id": site_id, "status": "no_data", "records": 0
            })
        else:
            print(f"    ✅ Got {factory_records:,} rows total")
            log_rows.append({
                "factory": name, "city": city, "category": category,
                "site_id": site_id, "status": "success", "records": factory_records
            })

        # Checkpoint
        if (idx + 1) % CHECKPOINT_N == 0 and all_records:
            ckpt = f"checkpoint_{idx+1}.csv"
            pd.DataFrame(all_records).to_csv(ckpt, index=False)
            print(f"\n  💾 Checkpoint saved: {len(all_records):,} records → {ckpt}")

    # Save final results
    df_out = pd.DataFrame(all_records)
    df_log = pd.DataFrame(log_rows)
    df_out.to_csv(OUTPUT_CSV, index=False)
    df_log.to_csv(LOG_CSV, index=False)

    print(f"\n{'='*55}")
    print("DONE")
    print(f"  Records collected : {len(df_out):,}")
    print(f"  Factories matched : {df_out['factory_name'].nunique() if not df_out.empty else 0}")
    print(f"  Saved to          : {OUTPUT_CSV}")
    print("\nStatus summary:")
    if not df_log.empty:
        print(df_log["status"].value_counts().to_string())
    print(f"{'='*55}")

    return df_out, df_log

if __name__ == "__main__":
    try:
        run_scrape()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
