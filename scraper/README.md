# ForensiAIR Consolidated Scraper Infrastructure

This directory contains all data collection, scraping, reverse-engineered API clients, PDF intelligence parsers, and data ingestion loaders for the **ForensiAIR** environmental surveillance platform.

---

## 📁 Directory Structure

```text
scraper/
├── README.md                           # Master scraper documentation (this file)
│
├── 🌐 MPCB OCEMS Telemetry Scrapers (REST API & Concurrency)
│   ├── mpcb_scraper_final.py          # Production REST API scraper (Base64 JSON protocol)
│   ├── scrape_ph_concurrent.py         # Concurrent ThreadPoolExecutor scraper for ETP-pH
│   ├── scrape_ph.py                    # Sequential pH telemetry scraper
│   ├── mpcb_scraper_v3.py             # Selenium JS injection prototype
│   ├── mpcb_scraper_v4.py             # Chrome DevTools Protocol (CDP) network interceptor
│   └── test_api.py                     # Rapid API health check utility
│
├── 🗺️ Target Mapping & Metadata CSVs
│   ├── all_factories.csv               # Base registry of 97 target factories
│   ├── matched_targets.csv             # Clean mapped target list
│   ├── unmatched_targets.csv           # Unmapped facility candidates
│   ├── all_api_factories_in_db.csv     # Complete API siteId registry
│   ├── Taloja_Mahad_Factories.csv      # Target regional facility list
│   ├── working_endpoints.json          # Decoded API endpoint schemas
│   └── intercept_log.json              # CDP network interception logs
│
├── 📥 Data Cleaning & Database Loaders
│   ├── load_data.py                    # Ingests multi-parameter ETP telemetry into PostgreSQL
│   ├── load_ph.py                      # Ingests ETP-pH telemetry into PostgreSQL
│   ├── export_clean_data.py            # Exports cleaned factory CSVs to parquet format
│   └── process_cache_immediately.py    # Process local cached PDF & telemetry assets
│
└── 🧩 Specialized Collectors (`collector/`)
    ├── consent/                        # CTO Consent to Operate Intelligence Collector
    │   ├── collector.py                # Pipeline entrypoint
    │   ├── scraper.py                  # MPCB CMS PDF downloader
    │   ├── parser.py                   # pdfplumber tabular limit extractor
    │   ├── database.py                # PostgreSQL consent tables manager
    │   ├── config.py                  # Dynamic paths & database config
    │   └── ddddocr CAPTCHA solver     # Automated OCR solver loop
    │
    └── inspection/                     # MPCB CIA Inspection Schedule Collector
        ├── collector.py                # Playwright async runner
        ├── scraper.py                  # Headless Chromium table parser
        ├── database.py                # PostgreSQL inspection schedule manager
        └── models.py                  # Inspection data schemas
```

---

## ⚡ Quick Start: Running Scrapers

### 1. Run MPCB OCEMS Telemetry Scraper
```bash
python scraper/mpcb_scraper_final.py
```

### 2. Run High-Speed Concurrent pH Telemetry Scraper
```bash
python scraper/scrape_ph_concurrent.py
```

### 3. Run Consent Document (CTO) Intelligence Collector
```bash
python scraper/collector/consent/collector.py
```

### 4. Run Inspection Schedule Collector
```bash
python scraper/collector/inspection/collector.py
```

### 5. Ingest Raw Telemetry into PostgreSQL Database
```bash
python scraper/load_data.py
python scraper/load_ph.py
```

---

## 🔒 Configuration Notes

All scripts dynamically resolve paths relative to the `scraper/` root directory. If large raw telemetry files (`mpcb_etp_data.csv` / `mpcb_ph_data.csv`) exist on the desktop (`C:\Users\gauri\OneDrive\Desktop\mpcb_scraper\`), the loaders automatically fall back to read from that directory as well.
