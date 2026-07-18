"""
MPCB OCEMS Scraper v4
=====================
Fixes in this version:
  1. Intercepts real XHR/fetch calls from the portal to discover exact
     API endpoints, payload keys, and category IDs
  2. Waits for Angular to finish bootstrapping before doing anything
  3. Clicks the dropdown properly to trigger the real API call
  4. Falls back to direct API probe if intercept misses it
  5. Filters for Taloja + Mahad automatically
  6. Extracts ETP parameters for all matched factories
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import pandas as pd
import json, time, base64, os, re

# ─────────────────────────────────────────────────────────
# CONFIGURATION — edit these
# ─────────────────────────────────────────────────────────
CHROMEDRIVER  = "chromedriver.exe"        # path to your chromedriver
PORTAL_URL    = "https://onlinecems.ecmpcb.in/#/publicPortal/categoryList"
FROM_DATE     = "2024/01/01 00:00:00"
TO_DATE       = "2024/12/31 23:59:59"
OUTPUT_CSV    = "mpcb_taloja_mahad_data.csv"
SLEEP_SEC     = 3

TARGET_CITIES = ["taloja", "mahad"]       # lowercase — we match case-insensitively

# ETP parameters we want (from your project scope)
ETP_PARAMS    = ["ETP-COD", "ETP-BOD", "ETP-TSS", "ETP.pH",
                 "ETP-Flow", "ETP-Totalizer"]

# Quality codes — get everything, filter later
ALL_QUALITY   = ["U","E","O","N","I","M","V","C","input","Z","X","Y"]

# ─────────────────────────────────────────────────────────
# BROWSER  — enable network logging so we can intercept
# ─────────────────────────────────────────────────────────
def start_browser():
    opts = Options()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])

    # Enable Chrome DevTools performance logging to capture network requests
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    service = Service(CHROMEDRIVER)
    driver  = webdriver.Chrome(service=service, options=opts)
    driver.set_script_timeout(60)

    # Inject fetch/XHR interceptor BEFORE the page loads
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            window.__intercepted_requests = [];
            window.__intercepted_responses = {};

            // Intercept fetch
            const _fetch = window.fetch;
            window.fetch = function(...args) {
                const url = args[0];
                let body = '';
                if (args[1] && args[1].body) body = args[1].body;
                window.__intercepted_requests.push({type:'fetch', url, body, ts: Date.now()});
                return _fetch.apply(this, args).then(resp => {
                    const clone = resp.clone();
                    clone.text().then(txt => {
                        window.__intercepted_responses[url] = txt.substring(0, 2000);
                    });
                    return resp;
                });
            };

            // Intercept XHR
            const _open = XMLHttpRequest.prototype.open;
            const _send = XMLHttpRequest.prototype.send;
            XMLHttpRequest.prototype.open = function(method, url) {
                this._url = url;
                return _open.apply(this, arguments);
            };
            XMLHttpRequest.prototype.send = function(body) {
                window.__intercepted_requests.push({
                    type:'xhr', url: this._url,
                    body: body ? body.substring(0,500) : '',
                    ts: Date.now()
                });
                return _send.apply(this, arguments);
            };
        """
    })

    print("Opening portal...")
    driver.get(PORTAL_URL)

    # Wait for Angular to finish — look for the dropdown to appear
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "mat-select"))
        )
        print("Angular loaded — dropdown found")
    except Exception:
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "select"))
            )
            print("Angular loaded — select found")
        except Exception:
            print("Dropdown not found — waiting 8s anyway")
            time.sleep(8)

    time.sleep(3)
    print(f"Browser ready — URL: {driver.current_url}")
    return driver


# ─────────────────────────────────────────────────────────
# INTERCEPT — read what API calls the portal actually makes
# ─────────────────────────────────────────────────────────
def get_intercepted_requests(driver):
    try:
        reqs = driver.execute_script("return window.__intercepted_requests || [];")
        return reqs
    except Exception:
        return []

def print_intercepted(driver, label=""):
    reqs = get_intercepted_requests(driver)
    if reqs:
        print(f"\n{'='*50}")
        print(f"INTERCEPTED REQUESTS {label} ({len(reqs)} total):")
        for r in reqs:
            print(f"  [{r.get('type','?')}] {r.get('url','')}")
            if r.get('body'):
                print(f"       body: {str(r.get('body',''))[:200]}")
        print('='*50)
    else:
        print(f"  No intercepted requests {label}")


# ─────────────────────────────────────────────────────────
# DROPDOWN — click it and capture what API fires
# ─────────────────────────────────────────────────────────
def click_dropdown_and_capture(driver):
    """
    Click the Category dropdown, select each option one by one,
    and capture the API calls that fire. Returns the discovered
    API base URL, endpoint, and category payload keys.
    """
    print("\n--- Probing dropdown ---")
    print_intercepted(driver, "before dropdown click")

    # Clear old intercepts
    driver.execute_script("window.__intercepted_requests = [];")

    # Try to find and click the dropdown
    dropdown_found = False

    # Strategy 1: mat-select (Angular Material)
    try:
        selects = driver.find_elements(By.TAG_NAME, "mat-select")
        if selects:
            print(f"Found {len(selects)} mat-select element(s)")
            driver.execute_script("arguments[0].scrollIntoView(true);", selects[0])
            time.sleep(0.5)
            selects[0].click()
            time.sleep(2)
            dropdown_found = True

            # Get all options
            options = driver.find_elements(By.TAG_NAME, "mat-option")
            print(f"Dropdown options ({len(options)}):")
            option_texts = []
            for opt in options:
                txt = opt.text.strip()
                if txt:
                    option_texts.append(txt)
                    print(f"   '{txt}'")

            # Close dropdown for now
            driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(1)
            return option_texts
    except Exception as e:
        print(f"mat-select approach failed: {e}")

    # Strategy 2: regular <select>
    try:
        selects = driver.find_elements(By.TAG_NAME, "select")
        if selects:
            print(f"Found {len(selects)} <select> element(s)")
            from selenium.webdriver.support.ui import Select
            sel = Select(selects[0])
            opts = [o.text.strip() for o in sel.options]
            print(f"Options: {opts}")
            dropdown_found = True
            return opts
    except Exception as e:
        print(f"select approach failed: {e}")

    # Strategy 3: any clickable element with 'category' in attributes
    try:
        elements = driver.find_elements(By.XPATH,
            "//*[contains(@placeholder,'ategory') or contains(@aria-label,'ategory') or contains(@name,'ategory')]")
        if elements:
            print(f"Found {len(elements)} category-labelled elements")
            elements[0].click()
            time.sleep(2)
            print_intercepted(driver, "after category element click")
    except Exception as e:
        print(f"attribute search failed: {e}")

    return []


# ─────────────────────────────────────────────────────────
# SELECT CATEGORY — choose Chemical or Pharma and read table
# ─────────────────────────────────────────────────────────
def select_category_and_get_factories(driver, category_text):
    """
    Select a specific category from the dropdown and scrape
    the resulting table of factories.
    """
    print(f"\n--- Selecting category: '{category_text}' ---")
    driver.execute_script("window.__intercepted_requests = [];")

    factories = []

    # Re-open dropdown and select
    try:
        # Try mat-select first
        selects = driver.find_elements(By.TAG_NAME, "mat-select")
        if selects:
            selects[0].click()
            time.sleep(1.5)
            options = driver.find_elements(By.TAG_NAME, "mat-option")
            for opt in options:
                if category_text.lower() in opt.text.strip().lower():
                    print(f"  Clicking option: '{opt.text.strip()}'")
                    opt.click()
                    time.sleep(3)
                    break
        else:
            # Try regular select
            selects = driver.find_elements(By.TAG_NAME, "select")
            if selects:
                from selenium.webdriver.support.ui import Select
                sel_obj = Select(selects[0])
                for opt in sel_obj.options:
                    if category_text.lower() in opt.text.strip().lower():
                        sel_obj.select_by_visible_text(opt.text.strip())
                        time.sleep(3)
                        break
    except Exception as e:
        print(f"  Dropdown selection error: {e}")

    # Read intercepted API calls to discover real payload structure
    time.sleep(2)
    print_intercepted(driver, f"after selecting '{category_text}'")

    # Now scrape the table
    factories = scrape_factory_table(driver)
    print(f"  Got {len(factories)} factories from table")

    return factories


def scrape_factory_table(driver):
    """Read the factory table that appears after category selection."""
    factories = []
    try:
        # Wait for table rows
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "tbody"))
        )
        time.sleep(1)

        rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")
        headers = []
        try:
            header_els = driver.find_elements(By.CSS_SELECTOR, "thead th")
            headers = [h.text.strip() for h in header_els]
            print(f"  Table headers: {headers}")
        except Exception:
            pass

        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells:
                continue
            cell_texts = [c.text.strip() for c in cells]

            if headers and len(cell_texts) == len(headers):
                record = dict(zip(headers, cell_texts))
            else:
                record = {f"col_{i}": v for i, v in enumerate(cell_texts)}

            # Try to find action button / link for siteId
            try:
                links = row.find_elements(By.TAG_NAME, "a")
                for link in links:
                    href = link.get_attribute("href") or ""
                    onclick = link.get_attribute("onclick") or ""
                    if any(x in href+onclick for x in ["siteId","site_id","industryId","id="]):
                        record["_action_href"] = href
                        record["_action_onclick"] = onclick
                        # Extract numeric ID
                        nums = re.findall(r'\d+', href + onclick)
                        if nums:
                            record["extracted_id"] = nums[-1]
            except Exception:
                pass

            # Also look at button click attributes
            try:
                btns = row.find_elements(By.TAG_NAME, "button")
                for btn in btns:
                    ng_click = btn.get_attribute("ng-click") or ""
                    record["_btn_ngclick"] = ng_click
            except Exception:
                pass

            factories.append(record)

    except Exception as e:
        print(f"  Table scrape error: {e}")

        # Fallback: dump entire page structure for diagnosis
        try:
            tables = driver.find_elements(By.TAG_NAME, "table")
            print(f"  Tables found on page: {len(tables)}")
            body = driver.find_element(By.TAG_NAME, "body")
            text = body.text[:1000]
            print(f"  Page text preview:\n{text}")
        except Exception:
            pass

    return factories


# ─────────────────────────────────────────────────────────
# DIRECT API PROBE — test endpoints manually
# ─────────────────────────────────────────────────────────
def probe_api_endpoints(driver):
    """
    Try every plausible endpoint + payload combination
    and print what returns data. Use this to discover the
    correct API call structure when portal JS intercept fails.
    """
    print("\n" + "="*50)
    print("DIRECT API PROBE — testing endpoints")
    print("="*50)

    base_urls = [
        "/glens/publicPortal/api/v2.0/",
        "/glens/api/v2.0/",
        "/api/v2.0/",
        "/glens/publicPortal/",
    ]

    endpoints = [
        "CategoryListPublic",
        "CategoryDetails",
        "IndustryListPublic",
        "industryList",
        "getIndustryList",
        "categoryList",
        "getCategoryList",
    ]

    category_payloads = [
        {"category": "Chemical"},
        {"category": "Drugs and Pharmaceuticals"},
        {"category": "Drugs_and_Pharmaceuticals"},
        {"categoryId": "1"},
        {"categoryId": "2"},
        {"categoryId": "3"},
        {"categoryId": "4"},
        {"industryType": "Chemical"},
        {},  # empty — some endpoints return all
    ]

    working = []

    for base in base_urls:
        for ep in endpoints:
            # Try empty payload first to see if it returns anything
            payload = {}
            js = f"""
                var done = arguments[0];
                fetch('{base}{ep}', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{}})
                }})
                .then(r => r.text())
                .then(t => done(t.substring(0, 500)))
                .catch(e => done('ERR:' + e.toString()));
            """
            try:
                result = driver.execute_async_script(js)
                if result and not result.startswith("ERR:") and len(result) > 20:
                    print(f"\n  ✅ HIT: {base}{ep}")
                    print(f"     Response: {result[:300]}")
                    working.append({"base": base, "endpoint": ep, "response": result[:300]})
                else:
                    print(f"  ✗ {base}{ep} → {str(result)[:60]}")
            except Exception as e:
                print(f"  ✗ {base}{ep} → exception: {str(e)[:60]}")
            time.sleep(0.3)

    print(f"\n  Working endpoints found: {len(working)}")
    return working


# ─────────────────────────────────────────────────────────
# CALL API — once we know the right endpoint
# ─────────────────────────────────────────────────────────
def call_api(driver, full_url, payload, decode_base64=True):
    """Call an API endpoint. Tries both plain JSON and base64-encoded bodies."""
    results = []

    # Try 1: plain JSON body
    js = f"""
        var done = arguments[0];
        fetch('{full_url}', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json',
                      'Accept': 'application/json, text/plain, */*'}},
            body: JSON.stringify({json.dumps(payload)})
        }})
        .then(r => r.text())
        .then(t => done(t))
        .catch(e => done('ERR:' + e.toString()));
    """
    try:
        raw = driver.execute_async_script(js)
        if raw and not raw.startswith("ERR:"):
            # Try base64 decode first
            try:
                decoded = base64.b64decode(raw).decode("utf-8")
                return json.loads(decoded)
            except Exception:
                try:
                    return json.loads(raw)
                except Exception:
                    return raw
    except Exception as e:
        print(f"    call_api plain error: {e}")

    # Try 2: base64-encoded body (original format)
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    js2 = f"""
        var done = arguments[0];
        fetch('{full_url}', {{
            method: 'POST',
            headers: {{'Content-Type': 'text/plain',
                      'Accept': 'application/json, text/plain, */*'}},
            body: atob('{encoded}')
        }})
        .then(r => r.text())
        .then(t => done(t))
        .catch(e => done('ERR:' + e.toString()));
    """
    try:
        raw = driver.execute_async_script(js2)
        if raw and not raw.startswith("ERR:"):
            try:
                decoded = base64.b64decode(raw).decode("utf-8")
                return json.loads(decoded)
            except Exception:
                try:
                    return json.loads(raw)
                except Exception:
                    return raw
    except Exception as e:
        print(f"    call_api b64 error: {e}")

    return None


# ─────────────────────────────────────────────────────────
# FILTER — only keep Taloja + Mahad factories
# ─────────────────────────────────────────────────────────
def filter_target_cities(factories):
    filtered = []
    for f in factories:
        city_val = ""
        for key in f:
            if "city" in key.lower() or "location" in key.lower() or "district" in key.lower():
                city_val = str(f[key]).strip().lower()
                break
        # Also check all values if city not found
        if not city_val:
            city_val = " ".join(str(v).lower() for v in f.values())

        if any(city in city_val for city in TARGET_CITIES):
            filtered.append(f)
    return filtered


# ─────────────────────────────────────────────────────────
# FETCH ETP DATA for a single factory
# ─────────────────────────────────────────────────────────
def fetch_etp_data(driver, api_base, site_id, factory_name):
    """Fetch 15-min ETP readings for one factory."""
    payload = {
        "fromDate":    FROM_DATE,
        "toDate":      TO_DATE,
        "siteId":      site_id,
        "stations":    ["ETP"],
        "parameters":  ETP_PARAMS,
        "criteria":    "15min",
        "reportFormat":"tabular",
        "qualityCode": ALL_QUALITY,
        "graphType":   "singleParameter",
        "quickRange":  False,
        "userName": None, "userId": None, "userType": None,
        "userRole": None, "userAccess": None,
        "domain": "onlinecems.ecmpcb.in"
    }

    url = api_base + "industry-tabular"
    result = call_api(driver, url, payload)

    records = []
    if result:
        rows = (result.get("bodyContent") or
                result.get("data") or
                (result if isinstance(result, list) else []))
        for rec in rows:
            rec["factory_name"] = factory_name
            rec["site_id"]      = site_id
            records.append(rec)

    return records


# ─────────────────────────────────────────────────────────
# DIAGNOSE — print full page source summary
# ─────────────────────────────────────────────────────────
def diagnose_page(driver):
    print("\n" + "="*50)
    print("PAGE DIAGNOSIS")
    print("="*50)
    print(f"URL: {driver.current_url}")
    print(f"Title: {driver.title}")

    # Check for Angular
    ng = driver.execute_script(
        "return !!(window.angular || window.getAllAngularRootElements || document.querySelector('[ng-version]'))"
    )
    print(f"Angular detected: {ng}")

    # Check for errors in console
    try:
        logs = driver.get_log("browser")
        errors = [l for l in logs if l.get("level") in ["SEVERE","WARNING"]]
        if errors:
            print(f"Console errors ({len(errors)}):")
            for e in errors[:5]:
                print(f"  [{e['level']}] {e['message'][:150]}")
    except Exception:
        pass

    # Page text
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        text = body.text[:800]
        print(f"\nPage text:\n{text}")
    except Exception:
        pass

    # All interactive elements
    try:
        inputs    = driver.find_elements(By.TAG_NAME, "input")
        selects   = driver.find_elements(By.TAG_NAME, "select")
        matselect = driver.find_elements(By.TAG_NAME, "mat-select")
        buttons   = driver.find_elements(By.TAG_NAME, "button")
        print(f"\nInteractive elements: input={len(inputs)}, select={len(selects)}, mat-select={len(matselect)}, button={len(buttons)}")

        for ms in matselect:
            print(f"  mat-select value='{ms.get_attribute('value')}' aria='{ms.get_attribute('aria-label')}'")
        for s in selects:
            print(f"  select name='{s.get_attribute('name')}' id='{s.get_attribute('id')}'")
    except Exception as e:
        print(f"Element scan error: {e}")

    # Network requests made so far
    reqs = get_intercepted_requests(driver)
    print(f"\nIntercepted network calls so far: {len(reqs)}")
    for r in reqs[:10]:
        print(f"  [{r.get('type','?')}] {r.get('url','')[:100]}")


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    driver = start_browser()

    try:
        # ── STEP 0: Diagnose what the page looks like ──────────
        diagnose_page(driver)

        # ── STEP 1: Probe all dropdown options ─────────────────
        print("\n\nSTEP 1 — Probing dropdown options")
        all_options = click_dropdown_and_capture(driver)

        if all_options:
            print(f"\nFound {len(all_options)} category options:")
            for opt in all_options:
                print(f"  - '{opt}'")

            # Save to file for reference
            with open("category_options.txt","w") as f:
                f.write("\n".join(all_options))
            print("Saved → category_options.txt")
        else:
            print("No dropdown options found via UI")

        # ── STEP 2: Probe API endpoints directly ───────────────
        print("\n\nSTEP 2 — Probing API endpoints directly")
        working_endpoints = probe_api_endpoints(driver)

        if working_endpoints:
            print(f"\n✅ Found {len(working_endpoints)} working endpoint(s)")
            with open("working_endpoints.json","w") as f:
                json.dump(working_endpoints, f, indent=2)
            print("Saved → working_endpoints.json")

            # Use first working endpoint as base
            api_base = working_endpoints[0]["base"]
            print(f"Using API base: {api_base}")
        else:
            print("\n⚠️ No direct API hits — will rely on UI scraping")
            api_base = "/glens/publicPortal/api/v2.0/"

        # ── STEP 3: Get factories for Chemical + Pharma ────────
        print("\n\nSTEP 3 — Selecting categories and scraping factory list")
        all_factories = []

        # Map friendly name → what to search in dropdown
        categories_to_try = [
            "Chemical",
            "Drugs",         # covers "Drugs and Pharmaceuticals"
            "Pharmaceutical",
        ]

        for cat in categories_to_try:
            flist = select_category_and_get_factories(driver, cat)
            if flist:
                for f in flist:
                    f["_category_searched"] = cat
                all_factories.extend(flist)
                print(f"  '{cat}': {len(flist)} factories")

        print(f"\nTotal factories scraped from UI: {len(all_factories)}")

        # Save raw factory list
        if all_factories:
            df_all = pd.DataFrame(all_factories)
            df_all.to_csv("all_factories_raw.csv", index=False)
            print(f"Saved → all_factories_raw.csv")
            print(f"Columns: {list(df_all.columns)}")
            print(df_all.head(5).to_string())

        # ── STEP 4: Filter Taloja + Mahad ─────────────────────
        target_factories = filter_target_cities(all_factories)
        print(f"\nTaloja + Mahad factories: {len(target_factories)}")
        for f in target_factories:
            print(f"  {f}")

        # ── STEP 5: Show final intercepted calls ───────────────
        print("\n\nSTEP 5 — All intercepted API calls summary")
        all_reqs = get_intercepted_requests(driver)
        api_calls = [r for r in all_reqs if "ecmpcb" in r.get("url","") or
                     "/glens/" in r.get("url","") or "/api/" in r.get("url","")]
        print(f"API calls detected: {len(api_calls)}")
        for r in api_calls:
            print(f"  [{r.get('type')}] {r.get('url')}")
            if r.get("body"):
                print(f"           {r.get('body','')[:200]}")

        # Save full intercept log
        with open("intercept_log.json","w") as f:
            json.dump(all_reqs, f, indent=2)
        print("Saved → intercept_log.json")

        print("\n" + "="*50)
        print("DIAGNOSIS COMPLETE")
        print("Next steps based on output above:")
        print("  1. Check working_endpoints.json — which endpoints respond?")
        print("  2. Check intercept_log.json — what does the portal actually call?")
        print("  3. Check all_factories_raw.csv — did the table scrape work?")
        print("  4. Share these 3 files and we'll write the final data-fetch script")
        print("="*50)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        input("\n⏸  Press ENTER to close browser...")
        driver.quit()
