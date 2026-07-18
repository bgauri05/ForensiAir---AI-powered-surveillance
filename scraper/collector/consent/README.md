# Consent to Operate (CTO) Intelligence Collector

This module automatically reads the list of factories from the database, maps each factory to its Consent to Operate (CTO) document, retrieves the CTO PDF (either from the local cache directory or dynamically querying the MPCB CMS portal), parses the PDF using `pdfplumber`, extracts environmental parameter limits (COD, BOD, TSS, pH, Flow, etc.), and stores the results in PostgreSQL.

## Features
- **Dual-Source Mapping**: Uses fuzzy similarity matches and pre-compiled maps to look up MPCB consent numbers.
- **ddddocr Captcha Solver**: Automates portal searching by bypassing captchas dynamically in a 10-attempt loop.
- **Cache-First Performance**: Prioritizes local copying of previously downloaded PDF assets to maximize execution speed.
- **Dynamic Limit Parsing**: Extracts parameter names, limit values (ranges, maximum limits), and units directly from table rows.

## Table Abstractions
1. `consents`: Consent metadata (type, issue date, validity range, etc.).
2. `consent_limits`: Parameter limits (parameter name, min, max, unit, source location, etc.).
3. `consent_download_logs`: Row-level statistics of execution status, error messages, and metrics.

## Running the Collector
To run the ingestion pipeline:
```bash
cd c:\Users\gauri\OneDrive\Desktop\mpcb_scraper\collector\consent
..\..\..\jsw-pms\venv\Scripts\python collector.py
```
