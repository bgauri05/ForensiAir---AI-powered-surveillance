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

BASE_API_URL   = "https://onlinecems.ecmpcb.in/glens/publicPortal/api/v2.0/"
MATCHED_CSV    = "matched_targets.csv"
SCRAPE_LOG_CSV = "scrape_log.csv"
OUTPUT_CSV     = "mpcb_ph_data.csv"
SLEEP_BETWEEN  = 0.5                         # seconds between requests
CHECKPOINT_N   = 5                           # save every N factories

ALL_QUALITY = ["U","E","O","N","I","M","V","C","input","Z","X","Y"]

def call_api(endpoint: str, payload: dict, timeout=30) -> dict:
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
                try:
                    return json.loads(raw)
                except Exception:
                    return None
    except Exception:
        pass
    return None

def get_monthly_ranges():
    days_in_months = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    ranges = []
    for m in range(1, 13):
        days = days_in_months[m-1]
        from_str = f"2024/{m:02d}/01 00:00:00"
        to_str = f"2024/{m:02d}/{days:02d} 23:59:59"
        ranges.append((m, from_str, to_str))
    return ranges

def run_scrape():
    df_matched = pd.read_csv(MATCHED_CSV)
    df_log = pd.read_csv(SCRAPE_LOG_CSV)
    
    # Filter for factories that were successful in the main scrape
    success_factories = df_log[df_log["status"] == "success"]["factory"].tolist()
    df_targets = df_matched[df_matched["CSV_Name"].isin(success_factories)]
    
    print(f"\n{'='*55}")
    print(f"Target factories to scrape ETP-pH for: {len(df_targets)}")
    print(f"{'='*55}\n")
    
    all_records = []
    monthly_ranges = get_monthly_ranges()
    total = len(df_targets)
    
    for idx, row in df_targets.iterrows():
        name = row["CSV_Name"]
        city = row["CSV_City"]
        category = row["CSV_Category"]
        site_id = row["API_SiteId"]
        
        print(f"\n[{idx+1}/{total}] {name} | site_id: {site_id}")
        
        factory_records = 0
        for m, from_date, to_date in monthly_ranges:
            payload_tab = {
                "fromDate": from_date,
                "toDate": to_date,
                "siteId": site_id,
                "stations": ["ETP"],
                "parameters": ["ETP-pH"],
                "criteria": "15min",
                "reportFormat": "tabular",
                "qualityCode": ALL_QUALITY,
                "graphType": "singleParameter",
                "quickRange": False,
                "userName": None, "userId": None, "userType": None,
                "userRole": None, "userAccess": None,
                "domain": "onlinecems.ecmpcb.in"
            }
            
            result = call_api("industry-tabular", payload_tab, timeout=30)
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
                    print(f"      - Month {m:02d}: Got {len(rows)} ETP-pH rows")
                    factory_records += len(rows)
                else:
                    print(f"      - Month {m:02d}: Empty")
            else:
                print(f"      - Month {m:02d}: Timeout/No response")
            
            time.sleep(SLEEP_BETWEEN)
            
        print(f"    ✅ Got {factory_records:,} ETP-pH rows total for {name}")
        
        # Checkpoint every CHECKPOINT_N factories
        if (idx + 1) % CHECKPOINT_N == 0 and all_records:
            ckpt = f"checkpoint_ph_{idx+1}.csv"
            pd.DataFrame(all_records).to_csv(ckpt, index=False)
            print(f"\n  💾 Checkpoint saved: {len(all_records):,} records → {ckpt}")
            
    # Save final results
    if all_records:
        df_out = pd.DataFrame(all_records)
        df_out.to_csv(OUTPUT_CSV, index=False)
        print(f"\n{'='*55}")
        print("DONE")
        print(f"  Records collected : {len(df_out):,}")
        print(f"  Saved to          : {OUTPUT_CSV}")
        print(f"{'='*55}")
    else:
        print("No ETP-pH data records were collected!")

if __name__ == "__main__":
    try:
        run_scrape()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
