import os
from pathlib import Path

# Database settings
DB_CONFIG = {
    "host": "localhost",
    "port": 5434,
    "user": "postgres",
    "password": "Gauri@123",
    "database": "forensiair"
}

# MPCB portal URLs
CMS_BASE_URL = "https://www.ecmpcb.in/cms/"
CMS_IP_PATCH = "123.252.232.205"

# Directories
PROJECT_ROOT = Path("c:/Users/gauri/OneDrive/Desktop/mpcb_scraper")
CONSENTS_DIR = PROJECT_ROOT / "consents"

# Reference / local cache settings
LY_PROJECT_DIR = Path("c:/Users/gauri/OneDrive/Desktop/LY PROJECT")
LY_PDFS_DIR = LY_PROJECT_DIR / "pdfs"

# Solve and request settings
REQUEST_TIMEOUT = 30
MAX_CAPTCHA_RETRIES = 10
