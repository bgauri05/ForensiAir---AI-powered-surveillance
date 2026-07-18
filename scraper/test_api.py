import requests
import base64
import json

def call_api(endpoint: str, payload: dict, timeout=45) -> dict:
    url = "https://onlinecems.ecmpcb.in/glens/publicPortal/api/v2.0/" + endpoint
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
            decoded = base64.b64decode(raw).decode("utf-8")
            return json.loads(decoded)
    except Exception as e:
        print("Error calling API:", e)
    return None

print("Querying industry-tabular with multiple pH parameters...")
payload_tab = {
    "fromDate": "2024/01/01 00:00:00",
    "toDate": "2024/01/01 23:59:59",
    "siteId": "site_1799",
    "stations": ["ETP"],
    "parameters": ["ETP-COD", "ETP-BOD", "ETP-TSS", "ETP-Flow", "ETP.pH", "ETP-pH", "pH", "ph", "ETP_pH", "ETP pH"],
    "criteria": "15min",
    "reportFormat": "tabular",
    "qualityCode": ["U","E","O","N","I","M","V","C","input","Z","X","Y"],
    "graphType": "singleParameter",
    "quickRange": False,
    "userName": None, "userId": None, "userType": None,
    "userRole": None, "userAccess": None,
    "domain": "onlinecems.ecmpcb.in"
}
result = call_api("industry-tabular", payload_tab)
if result:
    rows = result.get("parameterDetails", {}).get("bodyContent", [])
    if rows:
        print("First row keys in response:")
        print(sorted(list(rows[0].keys())))
        print("\nFirst row sample:")
        print(rows[0])
    else:
        print("Empty bodyContent")
else:
    print("API failed or timed out")
