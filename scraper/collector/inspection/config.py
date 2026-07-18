import os
import json
from typing import Dict, Any

# Path to config.json relative to this file
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config() -> Dict[str, Any]:
    """Loads parameters from config.json."""
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Configuration file not found at: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# Global configurations exposed for import
CONFIG = load_config()
DB_CONFIG = CONFIG.get("db", {})
BROWSER_CONFIG = CONFIG.get("browser", {})
PORTAL_URL = CONFIG.get("portal_url", "https://cia.ecmpcb.in/home/inspection_schedule")
DATE_RANGE_MONTHS = CONFIG.get("date_range", {}).get("months", 6)
