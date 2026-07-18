"""
MPCB OCEMS Scraper v3
=====================
Fixed: correct public portal URL + correct category names from decoded API response
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import pandas as pd
import json, time, base64

# ─────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────
# IMPORTANT: Use the PUBLIC portal, not the login page
PORTAL_URL   = "https://onlinecems.ecmpcb.in/#/publicPortal/categoryList"
CHROMEDRIVER = "chromedriver.exe"
FROM_DATE    = "2023/06/06 00:00:00"
TO_DATE      = "2024/06/06 00:00:00"
OUTPUT_FILE  = "mpcb_ocems_dataset.csv"
SLEEP_SEC    = 4

# Confirmed category IDs from the decoded CategoryListPublic response
# "Chemical" and "Drugs_and_Pharmaceuticals" are the exact IDs
TARGET_CATEGORIES = {
    "Chemical":                  "Chemical",
    "Drugs_and_Pharmaceuticals": "Drugs and Pharmaceuticals"
}

ALL_QUALITY_CODES = ["U","E","O","N","I","M","V","C","input","Z","X","Y"]
EFFLUENT_PARAMS   = ["ETP-COD","ETP-BOD","ETP-TSS","ETP.pH","ETP-Flow"]
EMISSION_PARAMS   = ["SO2","NOX","PM","Flow","Temp"]

QUALITY_CODE_MAP = {
    "U":"Raw_Unvalidated","E":"Error","O":"Out_of_Range",
    "N":"Negative","I":"Invalid","M":"Maintenance",
    "V":"Validated","C":"Span_Calibration","Z":"Zero_Calibration",
    "X":"Expected_Calibration","Y":"Dynamic_Limit","input":"Manual_Input"
}

# ─────────────────────────────────────────────────────────
# BROWSER
# ─────────────────────────────────────────────────────────
def start_browser():
    opts = Options()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    service = Service(CHROMEDRIVER)
    driver  = webdriver.Chrome(service=service, options=opts)
    driver.set_script_timeout(60)

    # Go directly to the PUBLIC portal — not the login page
    print("🌐 Opening public portal...")
    driver.get(PORTAL_URL)
    time.sleep(5)

    # Confirm we're on the right page
    current = driver.current_url
    print(f"   Current URL: {current}")
    if "login" in current:
        print("   ⚠️  Landed on login page — redirecting to public portal...")
        driver.get("https://onlinecems.ecmpcb.in/#/publicPortal/categoryList")
        time.sleep(4)

    print(f"✅ Browser ready")
    return driver


# ─────────────────────────────────────────────────────────
# API CALLER — runs JS inside browser (no CORS)
# ─────────────────────────────────────────────────────────
def call_api(driver, endpoint, payload: dict):
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    js = """
        var done = arguments[0];
        fetch('/glens/publicPortal/api/v2.0/""" + endpoint + """', {
            method: 'POST',
            headers: {
                'Content-Type': 'text/plain',
                'Accept': 'application/json, text/plain, */*'
            },
            body: atob('""" + encoded + """')
        })
        .then(r => r.text())
        .then(text => done(text))
        .catch(err => done(JSON.stringify({error: err.toString()})));
    """
    try:
        result = driver.execute_async_script(js)
        if not result:
            return None
        # The API returns base64-encoded JSON — decode it
        try:
            decoded = base64.b64decode(result).decode('utf-8')
            return json.loads(decoded)
        except Exception:
            # Maybe it returned plain JSON directly
            try:
                return json.loads(result)
            except Exception:
                print(f"   Raw response: {result[:200]}")
                return None
    except Exception as e:
        print(f"   ⚠️  JS error: {e}")
        return None


# ─────────────────────────────────────────────────────────
# STEP 1 — Get industry list with siteIds
# ─────────────────────────────────────────────────────────
def get_all_industries(driver):
    """
    Call CategoryDetails for each target category.
    Returns list of industries with their siteIds.
    """
    print("\n📋 Fetching industry list...")
    all_industries = []

    for cat_id, cat_label in TARGET_CATEGORIES.items():
        print(f"   Trying category: {cat_id}")

        # Try multiple payload variations — we don't know exact field name yet
        payloads_to_try = [
            {"categoryId": cat_id},
            {"category": cat_id},
            {"category": cat_label},
            {"industryCategory": cat_id},
        ]

        for payload in payloads_to_try:
            payload.update({
                "userName": None, "userId": None, "userType": None,
                "userRole": None, "userAccess": None,
                "domain": "onlinecems.ecmpcb.in"
            })

            result = call_api(driver, "CategoryDetails", payload)

            if result and result.get("bodyContent"):
                industries = result["bodyContent"]
                if industries:  # not empty list
                    print(f"   ✅ {cat_id}: {len(industries)} industries (payload: {list(payload.keys())[0]})")
                    for ind in industries:
                        ind["categoryFetched"] = cat_id
                    all_industries.extend(industries)
                    break
            time.sleep(1)
        else:
            print(f"   ⚠️  No data returned for {cat_id}")

        time.sleep(2)

    print(f"\n✅ Total industries: {len(all_industries)}")
    if all_industries:
        print("   Keys in response:", list(all_industries[0].keys()))
        print("   First entry:", json.dumps(all_industries[0], indent=2))

    return all_industries


# ─────────────────────────────────────────────────────────
# STEP 2 — Get siteId for a specific factory
# ─────────────────────────────────────────────────────────
def get_site_id(driver, industry_name):
    payloads_to_try = [
        {"industryName": industry_name},
        {"name": industry_name},
        {"industry": industry_name},
    ]
    for payload in payloads_to_try:
        payload.update({
            "userName": None, "userId": None, "userType": None,
            "userRole": None, "userAccess": None,
            "domain": "onlinecems.ecmpcb.in"
        })
        result = call_api(driver, "industryDetailsCustomReport", payload)
        if result and result.get("bodyContent"):
            body = result["bodyContent"]
            items = body if isinstance(body, list) else [body]
            for item in items:
                for key in ["siteId","site_id","id","industryId","siteID"]:
                    if item.get(key):
                        return item[key], item
    return None, None


# ─────────────────────────────────────────────────────────
# STEP 3 — Fetch 15-min OCEMS data
# ─────────────────────────────────────────────────────────
def fetch_data(driver, site_id, stations, parameters):
    payload = {
        "fromDate":    FROM_DATE,
        "toDate":      TO_DATE,
        "siteId":      site_id,
        "stations":    stations,
        "parameters":  parameters,
        "criteria":    "15min",
        "reportFormat":"tabular",
        "qualityCode": ALL_QUALITY_CODES,
        "graphType":   "singleParameter",
        "quickRange":  False,
        "userName": None, "userId": None, "userType": None,
        "userRole": None, "userAccess": None,
        "domain": "onlinecems.ecmpcb.in"
    }
    return call_api(driver, "industry-tabular", payload)


# ─────────────────────────────────────────────────────────
# STEP 4 — Full scrape
# ─────────────────────────────────────────────────────────
def scrape_all(driver, factory_csv):
    df_factories = pd.read_csv(factory_csv)
    all_records  = []
    status_log   = []
    total        = len(df_factories)

    print(f"\n🏭 Full scrape starting: {total} factories")
    print(f"   Date range: {FROM_DATE} → {TO_DATE}\n")

    for i, row in df_factories.iterrows():
        name     = str(row.get("Industry Name", f"Factory_{i}")).strip()
        city     = str(row.get("City", "")).strip().lower()
        category = str(row.get("Industry Category", "")).strip()

        print(f"\n[{i+1}/{total}] {name} | {city}")

        # Get siteId
        site_id, site_info = get_site_id(driver, name)

        if not site_id:
            print(f"   ⚠️  No siteId found — skipping")
            status_log.append({"factory":name,"city":city,"status":"no_site_id","records":0})
            continue

        print(f"   🔑 siteId: {site_id}")

        # Determine stations + parameters
        station_map = {}
        if site_info:
            # Try to extract station info from the site details
            stations_raw = site_info.get("stations") or site_info.get("monitoringStations", [])
            for s in (stations_raw if isinstance(stations_raw, list) else []):
                sname  = s.get("stationName") or s.get("name","")
                params = s.get("parameters", [])
                if sname:
                    station_map[sname] = params

        # Fallback defaults
        if not station_map:
            station_map = {
                "ETP":     EFFLUENT_PARAMS,
                "Stack-1": EMISSION_PARAMS
            }

        factory_records = 0

        for station_name, parameters in station_map.items():
            print(f"   📡 {station_name} | {parameters}")
            result = fetch_data(driver, site_id, [station_name], parameters)

            rows = []
            if result:
                rows = (result.get("bodyContent") or
                        result.get("data") or
                        (result if isinstance(result, list) else []))

            print(f"      {'✅' if rows else '❌'} {len(rows)} records")

            for rec in rows:
                rec.update({
                    "factory_name": name,
                    "city":         city,
                    "category":     category,
                    "station":      station_name,
                    "site_id":      site_id
                })
                all_records.append(rec)

            factory_records += len(rows)
            time.sleep(SLEEP_SEC)

        status_log.append({
            "factory": name, "city": city,
            "status": "success" if factory_records > 0 else "empty",
            "records": factory_records
        })

        # Checkpoint every 10 factories
        if (i+1) % 10 == 0 and all_records:
            ckpt = f"checkpoint_{i+1}.csv"
            pd.DataFrame(all_records).to_csv(ckpt, index=False)
            print(f"\n   💾 Checkpoint: {len(all_records)} records → {ckpt}")

    # Final save
    df_out    = pd.DataFrame(all_records)
    df_status = pd.DataFrame(status_log)
    df_out.to_csv(OUTPUT_FILE, index=False)
    df_status.to_csv("scrape_status.csv", index=False)

    print(f"\n{'='*50}")
    print(f"✅ DONE")
    print(f"   Records   : {len(df_out):,}")
    print(f"   Factories : {df_out['factory_name'].nunique() if not df_out.empty else 0}")
    print(f"   Saved to  : {OUTPUT_FILE}")
    print(f"\nStatus breakdown:")
    print(df_status['status'].value_counts().to_string())
    return df_out


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    driver = start_browser()

    try:
        # TEST — get industry list and save siteIds
        industries = get_all_industries(driver)

        if industries:
            df = pd.DataFrame(industries)
            df.to_csv("industry_list_with_siteids.csv", index=False)
            print(f"\n✅ Saved → industry_list_with_siteids.csv")
            print(f"   Columns: {list(df.columns)}")
            print(f"\n   Open industry_list_with_siteids.csv and confirm")
            print(f"   you can see siteId values like 'site_1004'")
            print(f"   Then uncomment scrape_all() below and re-run\n")
        else:
            print("\n⚠️  Still no industries returned.")
            print("   Check industry_list_with_siteids.csv is empty")
            print("   The portal may still be timing out — try after 10pm")

        # FULL SCRAPE — uncomment this when test above works:
        # scrape_all(driver, 'all_factories.csv')

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        input("\n⏸  Press ENTER to close browser...")
        driver.quit()
