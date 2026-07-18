# MPCB Inspection Schedule Ingestion Module

This module automates the process of scraping the last 6 months of historical inspection schedules from the MPCB CIA portal and saving them to your PostgreSQL database.

---

## 1. Project Structure

```text
collector/
└── inspection/
    ├── config.json       # Configurable JSON parameters
    ├── config.py         # Configuration loader wrapper
    ├── logger.py         # Logging setup (console + local rotating file)
    ├── models.py         # Dataclass models for inspection records
    ├── database.py       # PostgreSQL database tables setup and save operations
    ├── scraper.py        # Playwright browser automation and HTML table parser
    ├── collector.py      # Entry point coordinating DB, scraper, and logging
    └── README.md         # Documentation
```

---

## 2. Requirements & Installation

The module requires **Python 3.12** and **PostgreSQL**.

### Step 1: Install Python Packages
Run the following command to install the required dependencies (using your environment or the virtual environment):
```bash
pip install playwright psycopg2-binary
```

### Step 2: Install Playwright Browsers
Initialize Playwright dependencies on your local machine:
```bash
playwright install chromium
```

---

## 3. PostgreSQL Database Setup

The collector is configured to store records in the existing `forensiair` database on port `5434`.

The module automatically initializes two tables upon execution:
1. **`inspection_schedule`**: Stores parsed inspection records, with a unique constraint `(factory_name, inspection_date, inspection_type)` to prevent duplicates.
2. **`inspection_download_logs`**: Stores execution metrics including timestamps, record counts, and run durations.

*If you need to change database connection credentials, update the `"db"` block inside `config.json`.*

---

## 4. Run the Collector

Navigate to the directory and run the main entry point:

```bash
cd c:\Users\gauri\OneDrive\Desktop\mpcb_scraper\collector\inspection
python collector.py
```

### Execution Behavior:
1. The script initializes database tables.
2. Slices the last 6 months into 1-month date chunks to prevent MPCB server timeouts.
3. Spawns a headless Playwright Chromium instance.
4. Scrapes each date range using the `records=ALL` parameter.
5. Dynamically maps headers and carries forward dates across row spans.
6. Automatically retries loading a range up to 3 times on timeout.
7. Saves the records using Postgres bulk insert with a `DO NOTHING` conflict clause.
8. Writes run statistics to `inspection_download_logs`.
9. Outputs a final terminal summary of the run.
