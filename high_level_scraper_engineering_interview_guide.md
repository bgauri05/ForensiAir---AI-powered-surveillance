# 🎯 Master Scraper Engineering & Interview Preparation Guide

This report covers all 23 files across the **ForensiAIR** data scraping and ingestion infrastructure. Each file is presented using a standardized high-level architectural template for software, data, and ML engineering interview preparation.

---

# MODULE 1: Consent to Operate (CTO) Intelligence Collector

----------------------------------------
FILE:
`scraper/collector/consent/config.py`

Purpose (2-3 lines):
Centralizes configuration parameters, environment file paths, database connection details, and resilience bounds for the Consent to Operate (CTO) collector pipeline. It separates environment settings from business logic to prevent hardcoded constants.

Workflow:
When imported, it calculates absolute project directory locations using Python's `pathlib.Path`, sets database connection credentials for PostgreSQL, defines target MPCB URLs, and sets system execution limits like HTTP timeouts and CAPTCHA retry attempts.

Key Technologies & Concepts:

1. Centralized Configuration Management
- What it is:
  A design pattern where environment settings, connection credentials, and system parameters are stored in a single module rather than scattered across code files.
- Why we use it here:
  It allows developers to update database ports, URLs, or folder paths in one place without modifying scraper, parser, or database execution logic.
- Interview Question:
  What is the 12-Factor App methodology principle regarding configuration management, and how should sensitive secrets be stored in production?

2. Object-Oriented File Paths (`pathlib.Path`)
- What it is:
  A modern Python standard library module for creating and manipulating filesystem paths as objects rather than plain text strings.
- Why we use it here:
  It enables dynamic parent directory navigation (`.parents[2]`), operator path joining (`/`), and automatic cross-platform slash formatting between Windows (`\`) and Linux (`/`).
- Interview Question:
  What are the technical advantages of `pathlib.Path` over traditional `os.path` functions?

3. Dynamic Path Resolution (`Path(__file__).resolve()`)
- What it is:
  A technique to determine the canonical absolute path of the currently executing script on disk at runtime.
- Why we use it here:
  It ensures paths like `PROJECT_ROOT` and `CONSENTS_DIR` resolve correctly regardless of which directory or shell the script is executed from.
- Interview Question:
  What is the difference between a relative path and an absolute path, and why can relative paths fail when executing scripts from different working directories?

4. Single Source of Truth (SSoT)
- What it is:
  An architectural principle ensuring every data element or system setting is stored and modified in exactly one location.
- Why we use it here:
  Database credentials (`DB_CONFIG`), portal URLs (`CMS_BASE_URL`), and retry bounds (`MAX_CAPTCHA_RETRIES`) are defined once and shared across `database.py`, `scraper.py`, and `collector.py`.
- Interview Question:
  How does violating the Single Source of Truth principle lead to technical debt and configuration drift in distributed systems?

Summary:
"In one sentence, this file defines all database settings, URL endpoints, directory paths, and resilience limits required by the CTO consent collector module."

Complexity:
⭐ Beginner
----------------------------------------

----------------------------------------
FILE:
`scraper/collector/consent/logger.py`

Purpose (2-3 lines):
Initializes a structured, double-destination logging infrastructure for the consent collector. It captures system events, network attempts, and parsing errors to both terminal console streams and rotating disk log files.

Workflow:
When `setup_logger()` is invoked, it creates a dedicated `logs/` directory if missing, creates a `logging.Logger` instance, attaches a `StreamHandler` for live terminal output, attaches a `RotatingFileHandler` to prevent disk space exhaustion, applies a timestamped log formatter, and returns the configured logger.

Key Technologies & Concepts:

1. Application Logging Framework (`logging`)
- What it is:
  Python's built-in framework for emitting diagnostic events at varying severity levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).
- Why we use it here:
  Replaces basic `print()` statements with structured log messages containing exact timestamps, execution locations, and error severity levels.
- Interview Question:
  Why are standard `print()` statements considered an anti-pattern in production web backend and data pipeline development?

2. Rotating File Handler (`RotatingFileHandler`)
- What it is:
  A specialized log handler that automatically closes the current log file and opens a new one when the file reaches a specified byte size limit.
- Why we use it here:
  It caps log storage at 5 MB per file with up to 3 historical backups, ensuring long-running scrapers never consume 100% of available disk space.
- Interview Question:
  How do log rotation strategies prevent Denial of Service (DoS) conditions caused by unhandled infinite log loops?

3. Stream Handlers (`StreamHandler`)
- What it is:
  A logging handler that redirects formatted log output to Standard Output (`sys.stdout`) or Standard Error (`sys.stderr`).
- Why we use it here:
  Enables developers to monitor live execution progress in terminal consoles while simultaneously persisting logs to disk.
- Interview Question:
  How do containerized microservices (e.g. Docker, Kubernetes) consume logs emitted via Standard Output vs File Handlers?

Summary:
"In one sentence, this file establishes a resilient, double-destination logging mechanism with automated file rotation for real-time monitoring and post-mortem debugging."

Complexity:
⭐ Beginner
----------------------------------------

----------------------------------------
FILE:
`scraper/collector/consent/database.py`

Purpose (2-3 lines):
Manages all relational database persistence operations for Consent to Operate (CTO) metadata, parameter discharge limits, and download execution statistics in PostgreSQL.

Workflow:
It connects to PostgreSQL using `psycopg2`, auto-initializes relational schema tables (`consents`, `consent_limits`, `consent_download_logs`) if they do not exist, and provides transactional helper methods to query existing consent numbers, insert parsed consent records, and record download execution logs.

Key Technologies & Concepts:

1. Relational Database Interface (`psycopg2`)
- What it is:
  The standard Python driver adapter for connecting to and executing SQL queries on PostgreSQL databases.
- Why we use it here:
  Executes low-level, high-speed SQL statements, manages database connection objects, and controls transaction commit/rollback behavior.
- Interview Question:
  What is the difference between a database driver (like `psycopg2`) and an ORM (like `SQLAlchemy` or `Django ORM`)?

2. Data Normalization & Relational Schemas
- What it is:
  Organizing database tables to minimize redundancy by separating general consent metadata from granular parameter limits via Foreign Keys.
- Why we use it here:
  Stores top-level consent details in `consents` while storing individual chemical threshold rows (BOD, COD, TSS limits) in `consent_limits` linked by `consent_id`.
- Interview Question:
  What is the difference between 1st, 2nd, and 3rd Normal Form (3NF) in relational database design?

3. Context Managers for Database Transactions (`with conn.cursor()`)
- What it is:
  A Python construct that ensures database resources, cursors, and connections are properly opened, committed, or closed even if exceptions occur.
- Why we use it here:
  Prevents database connection leaks and guarantees atomic transaction execution across multithreading operations.
- Interview Question:
  What does the ACID acronym stand for in relational database management systems?

Summary:
"In one sentence, this file manages PostgreSQL connection lifecycles, schema initialization, and transactional persistence for CTO document metadata and parameter limits."

Complexity:
⭐⭐ Intermediate
----------------------------------------

----------------------------------------
FILE:
`scraper/collector/consent/parser.py`

Purpose (2-3 lines):
Extracts structured environmental parameter discharge limits (COD, BOD, TSS, pH, Flow) from unstructured Consent to Operate (CTO) PDF documents using table boundary analysis and Regex pattern matching.

Workflow:
It opens a target CTO PDF using `pdfplumber`, iterates over each page extracting text and tabular structures, applies regular expressions to detect chemical parameter names, numeric limit ranges, and units, standardizes parameters, and returns structured dictionaries ready for database insertion.

Key Technologies & Concepts:

1. PDF Tabular Mining (`pdfplumber`)
- What it is:
  A Python library that inspects vector geometry, text character bounding boxes, and table lines within PDF documents.
- Why we use it here:
  Unlike plain text extractors, `pdfplumber` preserves column positions and grid alignments within MPCB consent certificate tables.
- Interview Question:
  Why is extracting structured data from PDF documents inherently difficult compared to parsing HTML or JSON?

2. Regular Expressions (Regex / `re`)
- What it is:
  A domain-specific pattern-matching language used to locate, validate, and extract specific character sequences from text strings.
- Why we use it here:
  Parses complex chemical limit expressions (e.g. `pH 5.5 - 9.0`, `COD < 250 mg/l`, `BOD max 30 mg/l`) and extracts numerical bounds.
- Interview Question:
  What is catastrophic backtracking in Regular Expressions, and how do you prevent it when parsing large documents?

3. Rule-Based Data Normalization
- What it is:
  Transforming messy, varied text inputs into standardized canonical string representations based on pre-defined matching rules.
- Why we use it here:
  Converts variations like `B.O.D.`, `Biochemical Oxygen Demand`, and `BOD (3 days)` into a single clean identifier `ETP-BOD`.
- Interview Question:
  What strategies would you use to clean unstructured data before feeding it into downstream feature engineering pipelines?

Summary:
"In one sentence, this file converts unstructured PDF consent documents into clean, structured parameter discharge limits using PDF table extraction and regular expressions."

Complexity:
⭐⭐⭐ Advanced
----------------------------------------

----------------------------------------
FILE:
`scraper/collector/consent/scraper.py`

Purpose (2-3 lines):
Automates the searching, CAPTCHA solving, and downloading of Consent to Operate (CTO) PDF certificates from the MPCB CMS portal while leveraging local asset caches.

Workflow:
Given a factory name or consent number, it checks local PDF disk caches first. If missing, it queries the MPCB portal, fetches the dynamic CAPTCHA image, passes it to the `ddddocr` machine-learning engine to decode the challenge, submits the search form in a 10-attempt retry loop, and downloads the target PDF document.

Key Technologies & Concepts:

1. Machine Learning CAPTCHA Solving (`ddddocr`)
- What it is:
  An open-source deep-learning OCR library optimized for recognizing distorted alphanumeric text characters inside CAPTCHA images.
- Why we use it here:
  Bypasses portal security challenges automatically without relying on paid human-in-the-loop CAPTCHA solving services.
- Interview Question:
  How do Convolutional Neural Networks (CNNs) process and classify distorted text images in automated OCR systems?

2. Cache-First File Retrieval Strategy
- What it is:
  A performance pattern that checks local storage before issuing expensive external network requests.
- Why we use it here:
  If a PDF was previously downloaded during earlier runs, it copies the local file instantly, cutting execution time from seconds to milliseconds.
- Interview Question:
  What are the trade-offs between local file caching vs distributed memory caching (e.g. Redis) in web scraping pipelines?

3. HTTP Resilience & Retry Loop Patterns
- What it is:
  A control flow structure that retries transiently failing external requests up to a maximum threshold before throwing an error.
- Why we use it here:
  Handles portal CAPTCHA recognition failures and temporary MPCB server timeouts gracefully across up to 10 attempt loops.
- Interview Question:
  What is Exponential Backoff with Jitter, and why is it superior to simple fixed retry delays when querying external APIs?

Summary:
"In one sentence, this file handles automated portal querying, ML-based CAPTCHA solving, cache verification, and downloading of CTO PDF documents."

Complexity:
⭐⭐⭐ Advanced
----------------------------------------

----------------------------------------
FILE:
`scraper/collector/consent/analytics.py`

Purpose (2-3 lines):
Provides diagnostic analytics and statistical quality control checks on the extracted consent data stored in the database.

Workflow:
It queries the PostgreSQL database tables (`consents`, `consent_limits`), calculates summary metrics (total consents processed, parameter distribution counts, missing limit rates), prints formatted diagnostic tables to the terminal console, and logs potential parsing anomalies.

Key Technologies & Concepts:

1. SQL Aggregations (`COUNT`, `GROUP BY`, `HAVING`)
- What it is:
  Relational database queries that group multiple database rows together to compute summary metrics.
- Why we use it here:
  Summarizes how many consent limits were successfully extracted per factory and identifies facilities missing critical parameters.
- Interview Question:
  What is the execution order of a SQL query containing `WHERE`, `GROUP BY`, `HAVING`, and `ORDER BY` clauses?

2. Statistical Quality Assurance (QA)
- What it is:
  Validating that data ingestion output matches expected mathematical distributions and boundary conditions before downstream consumption.
- Why we use it here:
  Ensures that extracted pH ranges, COD limits, and flow thresholds fall within realistic chemical limits before ML feature matrix assembly.
- Interview Question:
  How do data validation frameworks (like `Great Expectations` or `Pydantic`) prevent data drift in production ML pipelines?

Summary:
"In one sentence, this file computes diagnostic statistical metrics and quality assurance checks on extracted consent limits stored in PostgreSQL."

Complexity:
⭐ Beginner
----------------------------------------

----------------------------------------
FILE:
`scraper/collector/consent/collector.py`

Purpose (2-3 lines):
Serves as the main orchestrator entry point for the CTO Consent Intelligence Collector sub-system.

Workflow:
It initializes the logging session, establishes database connection pools, reads the list of active factories from PostgreSQL, invokes `scraper.py` to acquire PDF certificates, triggers `parser.py` to extract chemical discharge limits, saves extracted records into PostgreSQL using `database.py`, and outputs run analytics via `analytics.py`.

Key Technologies & Concepts:

1. Pipeline Orchestration Pattern
- What it is:
  A design pattern where a single master module controls execution order, data passing, and error handling across sub-modules.
- Why we use it here:
  Decouples individual modules (scraper, parser, database) while coordinating their execution in a clear sequential workflow.
- Interview Question:
  What is the difference between monolithic script execution and pipeline orchestration tools like Apache Airflow or Prefect?

2. Defensive Programming & Exception Isolation
- What it is:
  Wrapping individual iteration loops inside `try-except` blocks to prevent single-record failures from crashing the entire application.
- Why we use it here:
  If downloading or parsing a PDF fails for factory #15, the collector logs the error and continues processing factory #16 smoothly.
- Interview Question:
  How do you design batch ETL pipelines to handle partial failures without corrupting database state?

Summary:
"In one sentence, this file coordinates the complete end-to-end flow of searching, downloading, parsing, storing, and analyzing CTO consent certificates."

Complexity:
⭐⭐ Intermediate
----------------------------------------

---

# MODULE 2: MPCB CIA Inspection Schedule Collector

----------------------------------------
FILE:
`scraper/collector/inspection/config.py`

Purpose (2-3 lines):
Loads and validates configurable runtime parameters for the MPCB CIA Inspection Schedule Scraper from a JSON configuration file.

Workflow:
It checks for `config.json`, reads and parses JSON configuration options (database connections, inspection date windows, Playwright browser settings), applies default fallbacks if properties are missing, and exposes a clean Python configuration object.

Key Technologies & Concepts:

1. Configuration File Parsing (`json`)
- What it is:
  Reading and deserializing JSON (JavaScript Object Notation) files into native Python dictionaries.
- Why we use it here:
  Allows non-developers to modify scraping date ranges or browser headless modes without editing Python source code.
- Interview Question:
  What are the advantages and disadvantages of using JSON vs YAML vs TOML for application configuration?

2. Defensive Dictionary Fallbacks
- What it is:
  Using dictionary access methods with default values (`dict.get(key, default)`) to prevent runtime `KeyError` exceptions.
- Why we use it here:
  Ensures that if optional parameters (e.g. `timeout` or `headless`) are omitted from `config.json`, safe defaults are used automatically.
- Interview Question:
  Why is `dict.get("key", default)` preferred over direct bracket indexing `dict["key"]` when reading external inputs?

Summary:
"In one sentence, this file reads, validates, and exposes user-defined JSON configuration options for the inspection scraper."

Complexity:
⭐ Beginner
----------------------------------------

----------------------------------------
FILE:
`scraper/collector/inspection/logger.py`

Purpose (2-3 lines):
Configures dedicated logging handlers specifically for monitoring the inspection schedule scraping sub-system.

Workflow:
It initializes file and stream logging outputs, formats log entries with timestamps, logger names, and severity levels, and writes logs to `collector/inspection/logs/collector.log`.

Key Technologies & Concepts:

1. Isolated Module Logging
- What it is:
  Creating distinct, named loggers (`logging.getLogger("inspection")`) per module rather than using the global root logger.
- Why we use it here:
  Prevents log output pollution and allows filtering inspection scraper logs independently from consent collector logs.
- Interview Question:
  How does logger hierarchy and propagation work in Python's `logging` module?

Summary:
"In one sentence, this file manages dedicated logging streams and file outputs for the inspection schedule sub-system."

Complexity:
⭐ Beginner
----------------------------------------

----------------------------------------
FILE:
`scraper/collector/inspection/models.py`

Purpose (2-3 lines):
Defines strict, immutable data schemas and data structures representing factory inspection records using Python dataclasses.

Workflow:
It defines the `InspectionRecord` class using `@dataclass`. When the scraper parses an inspection schedule HTML table row, it instantiates an `InspectionRecord` object, enforcing attribute types (factory name, inspection date, risk level, status) before passing data down the pipeline.

Key Technologies & Concepts:

1. Python Dataclasses (`@dataclass`)
- What it is:
  A Python decorator introduced in Python 3.7 that automatically generates special methods like `__init__()`, `__repr__()`, and `__eq__()` for data storage classes.
- Why we use it here:
  Provides clean, type-hinted, self-documenting data structures for inspection records without boilerplate class methods.
- Interview Question:
  What is the difference between a standard Python Class, a `@dataclass`, a `NamedTuple`, and a `Pydantic` Model?

2. Type Hinting (`typing`)
- What it is:
  Explicit annotations declaring the expected data types of variables, function parameters, and class attributes.
- Why we use it here:
  Enables static type checking (via `mypy` or IDEs), catching bug assignments (e.g. passing an integer where a string date is expected) early.
- Interview Question:
  Does Python enforce type hints at runtime? Explain how type hints benefit development pipelines.

Summary:
"In one sentence, this file defines type-safe data structure models representing official factory inspection records."

Complexity:
⭐ Beginner
----------------------------------------

----------------------------------------
FILE:
`scraper/collector/inspection/database.py`

Purpose (2-3 lines):
Handles PostgreSQL schema creation and bulk upsert operations for historical inspection schedules and download logs.

Workflow:
It connects to PostgreSQL, creates `inspection_schedule` and `inspection_download_logs` tables with unique composite keys `(factory_name, inspection_date, inspection_type)`, and executes bulk insert SQL commands using `psycopg2.extras.execute_values` with `ON CONFLICT DO NOTHING` clauses to prevent duplicate rows.

Key Technologies & Concepts:

1. Bulk SQL Insert Optimization (`execute_values`)
- What it is:
  A `psycopg2` utility that compiles thousands of insert tuples into a single optimized SQL statement instead of issuing individual `INSERT` queries.
- Why we use it here:
  Increases database insertion speed by up to 100x when inserting thousands of historical inspection records.
- Interview Question:
  Why are individual `INSERT INTO` statements in a loop extremely slow in relational databases, and how do bulk operations resolve this?

2. Idempotent Upserts (`ON CONFLICT DO NOTHING`)
- What it is:
  A database constraint clause that instructs PostgreSQL to silently ignore duplicate inserts if a row with the same unique key already exists.
- Why we use it here:
  Allows the scraper to re-run safely over overlapping date windows without causing duplicate primary key constraint errors.
- Interview Question:
  What is Idempotency in data engineering, and why is it a mandatory requirement for production ETL pipelines?

Summary:
"In one sentence, this file manages PostgreSQL tables and executes high-speed, idempotent bulk inserts for inspection schedule records."

Complexity:
⭐⭐ Intermediate
----------------------------------------

----------------------------------------
FILE:
`scraper/collector/inspection/scraper.py`

Purpose (2-3 lines):
Automates navigation of the JavaScript-heavy MPCB CIA inspection portal and extracts tabular schedule records using headless browser automation.

Workflow:
It launches a Playwright Headless Chromium browser instance, iterates through 1-month date range chunks spanning 6 months, submits form filter queries using `records=ALL`, waits for dynamic HTML table rendering, carries row-span dates forward across grouped rows, and parses rows into `InspectionRecord` models.

Key Technologies & Concepts:

1. Asynchronous Browser Automation (`playwright`)
- What it is:
  A modern, fast, cross-browser automation framework supporting async execution, headless Chrome/Firefox/WebKit rendering, and robust selector waiting.
- Why we use it here:
  Handles complex Single Page Application (SPA) JavaScript rendering on the MPCB CIA portal that standard HTTP `requests` cannot execute.
- Interview Question:
  How does Playwright compare against Selenium WebDriver in terms of architecture, execution speed, and auto-waiting mechanisms?

2. Asynchronous I/O (`asyncio`)
- What it is:
  Python's built-in single-threaded concurrent framework that uses an event loop to handle non-blocking asynchronous I/O tasks.
- Why we use it here:
  Allows Playwright to perform asynchronous network requests and DOM event handling without blocking the main Python thread.
- Interview Question:
  What is the difference between CPU-bound tasks and I/O-bound tasks, and how does `asyncio` handle I/O concurrency?

3. Dynamic HTML Table Parsing & Rowspan State Tracking
- What it is:
  Extracting tabular DOM data while keeping track of merged HTML cells (`<td rowspan="...">`) across sequential table rows.
- Why we use it here:
  The MPCB inspection table groups multiple inspections under a single date cell; state tracking carries the parent date forward to child rows accurately.
- Interview Question:
  How would you parse an HTML table with nested rowspans and colspans using BeautifulSoup or Playwright selectors?

Summary:
"In one sentence, this file uses Playwright headless browser automation to navigate the CIA portal, execute month-sliced searches, and parse HTML inspection tables."

Complexity:
⭐⭐⭐ Advanced
----------------------------------------

----------------------------------------
FILE:
`scraper/collector/inspection/collector.py`

Purpose (2-3 lines):
Acts as the main execution entry point for the inspection schedule collection sub-system.

Workflow:
It initializes config settings and logging, connects to PostgreSQL to prepare database tables, invokes `scraper.py` to extract 6 months of historical inspection schedules, bulk-saves parsed records to database using `database.py`, logs execution metrics, and outputs terminal summaries.

Key Technologies & Concepts:

1. Asynchronous Event Loop Orchestration (`asyncio.run()`)
- What it is:
  The standard entry point function used to execute an asynchronous main function and manage event loop lifecycles.
- Why we use it here:
  Executes the async Playwright scraper pipeline within a synchronous execution entry point script.
- Interview Question:
  What happens under the hood when `asyncio.run()` is called in Python?

2. Execution Telemetry & Performance Monitoring
- What it is:
  Measuring execution runtimes, record counts, and failure rates and persisting them to database log tables (`inspection_download_logs`).
- Why we use it here:
  Provides historical visibility into pipeline performance, data yield, and network dropouts over time.
- Interview Question:
  Why is pipeline telemetry critical for maintaining Data Level Agreements (DLAs) in production enterprise pipelines?

Summary:
"In one sentence, this file coordinates the async execution of the Playwright inspection scraper, database bulk loading, and run telemetry logging."

Complexity:
⭐⭐ Intermediate
----------------------------------------

---

# MODULE 3: OCEMS High-Throughput Telemetry Scrapers

----------------------------------------
FILE:
`scraper/mpcb_scraper_final.py`

Purpose (2-3 lines):
Serves as the primary, production-grade telemetry scraper for extracting continuous 15-minute resolution industrial effluent data across 6 parameters from MPCB OCEMS servers.

Workflow:
It reads target factory lists, constructs month-by-month temporal query windows for 2024, serializes and Base64-encodes JSON payloads, issues HTTP POST requests directly to the MPCB REST API (`industry-tabular`), decodes Base64 JSON responses, extracts telemetry values and quality codes, and saves checkpoints to disk.

Key Technologies & Concepts:

1. Direct REST API Consumption (`requests`)
- What it is:
  Bypassing browser automation completely by making HTTP requests directly to backend REST API endpoints.
- Why we use it here:
  Operates up to 50x faster than Selenium/Playwright while using 95% less RAM and avoiding browser rendering crashes.
- Interview Question:
  How do you use browser developer tools (Network tab) to inspect, reverse-engineer, and replicate private web application API endpoints in Python?

2. Custom Base64 Protocol Encoding/Decoding (`base64`)
- What it is:
  A binary-to-text encoding scheme that represents binary data in an ASCII string format.
- Why we use it here:
  The MPCB API requires JSON POST bodies to be Base64-encoded as `text/plain` requests and returns Base64-encoded JSON text responses.
- Interview Question:
  Why do some APIs use Base64 payload encoding, and how does Base64 differ from encryption algorithms like AES or RSA?

3. Checkpointing Data Persistence Strategy
- What it is:
  Periodically saving intermediate dataset states to disk during long-running data acquisition pipelines.
- Why we use it here:
  Saves progress CSV files (`checkpoint_10.csv` to `checkpoint_90.csv`) every 10 factories, ensuring zero data loss if network connections drop.
- Interview Question:
  How does checkpointing enable fault-tolerant resume capabilities in large distributed data processing jobs?

Summary:
"In one sentence, this file is the production REST API scraper that extracts 15-minute multi-parameter effluent telemetry using Base64 payload encoding and disk checkpointing."

Complexity:
⭐⭐⭐ Advanced
----------------------------------------

----------------------------------------
FILE:
`scraper/scrape_ph_concurrent.py`

Purpose (2-3 lines):
Scales the extraction of high-density ETP-pH telemetry by executing multi-threaded concurrent API requests.

Workflow:
It loads target factory mapping files, breaks dates into monthly ranges, spawns a pool of worker threads using `ThreadPoolExecutor`, dispatches simultaneous Base64 REST API calls to the MPCB server across multiple site IDs, gathers completed thread results, and merges records into checkpoint CSVs.

Key Technologies & Concepts:

1. Multi-Threaded Concurrency (`ThreadPoolExecutor`)
- What it is:
  A high-level interface from Python's `concurrent.futures` module that manages a pool of worker threads for executing asynchronous tasks concurrently.
- Why we use it here:
  Network scraping is I/O-bound; thread concurrency allows Python to issue multiple HTTP requests simultaneously while waiting for server responses.
- Interview Question:
  Explain the Python Global Interpreter Lock (GIL) and why multi-threading is effective for I/O-bound tasks but not CPU-bound tasks.

2. Concurrent Task Gathering (`as_completed`)
- What it is:
  An iterator that yields thread results as soon as individual worker threads complete their execution, regardless of launch order.
- Why we use it here:
  Ensures fast factory requests are processed and stored immediately without waiting for slower background thread requests to finish.
- Interview Question:
  What is the difference between `as_completed()` and `concurrent.futures.wait()` when handling concurrent task futures?

3. Thread-Safe Data Aggregation
- What it is:
  Collecting and merging data from multiple parallel threads without introducing race conditions or memory corruption.
- Why we use it here:
  Thread worker functions return isolated local lists of telemetry records that are safely concatenated in the main coordinator thread.
- Interview Question:
  What is a Race Condition, and what synchronization primitives (e.g. Locks, Semaphores, Queues) exist in Python to prevent them?

Summary:
"In one sentence, this file uses multi-threaded concurrency to extract high-density ETP-pH telemetry across multiple factory sites simultaneously."

Complexity:
⭐⭐⭐ Advanced
----------------------------------------

----------------------------------------
FILE:
`scraper/scrape_ph.py`

Purpose (2-3 lines):
Acts as the single-threaded, sequential reference implementation for scraping ETP-pH telemetry from the MPCB portal.

Workflow:
It iterates sequentially through factory target rows one by one, generates monthly date ranges for 2024, encodes Base64 requests to the `industry-tabular` API, parses pH telemetry values and quality codes, and writes output records to `mpcb_ph_data.csv`.

Key Technologies & Concepts:

1. Sequential Execution Baseline
- What it is:
  Processing data items one after another in a deterministic single-threaded loop.
- Why we use it here:
  Provides a clean, simple baseline implementation used for debugging single-site queries and validating API payload schemas before scaling to multi-threading.
- Interview Question:
  When would a developer deliberately choose a single-threaded architecture over a multi-threaded architecture?

Summary:
"In one sentence, this file is the baseline single-threaded scraper used to query and validate ETP-pH telemetry sequentially."

Complexity:
⭐ Beginner
----------------------------------------

----------------------------------------
FILE:
`scraper/test_api.py`

Purpose (2-3 lines):
Provides a lightweight health check and diagnostic utility to test connection availability and validate API request payload schemas against the MPCB REST server.

Workflow:
It constructs a minimal test payload for a known test site ID, Base64-encodes the request, fires a single HTTP POST request to `BASE_API_URL`, measures response latency, decodes the returned payload, and prints raw response structures to terminal console.

Key Technologies & Concepts:

1. API Health Checking & Probing
- What it is:
  Sending test requests to verify server responsiveness, payload validation rules, and network connectivity before launching full scraping jobs.
- Why we use it here:
  Saves developer time by quickly verifying if MPCB portal endpoints are online or if API schema requirements have changed.
- Interview Question:
  What is the difference between active synthetic monitoring (health probes) and passive telemetry monitoring in production systems?

Summary:
"In one sentence, this file is a diagnostic test utility that verifies MPCB API connectivity and validates payload encoding rules."

Complexity:
⭐ Beginner
----------------------------------------

----------------------------------------
FILE:
`scraper/mpcb_scraper_v4.py`

Purpose (2-3 lines):
Serves as the advanced reverse-engineering prototype that intercepted network XHR traffic using Chrome DevTools Protocol (CDP) to discover hidden MPCB REST endpoints and Base64 payload rules.

Workflow:
It launches Selenium ChromeDriver with CDP performance logging enabled, injects a custom JavaScript fetch/XHR hook (`Page.addScriptToEvaluateOnNewDocument`), navigates the MPCB public portal, intercepts background Angular API traffic, decodes captured payloads, and identifies site IDs for target industrial regions (Taloja & Mahad).

Key Technologies & Concepts:

1. Chrome DevTools Protocol (CDP) Interception
- What it is:
  A low-level protocol allowing developers to inspect, instrument, and hook into Chromium browser network events, DOM states, and JavaScript engines.
- Why we use it here:
  Intercepted background AJAX/XHR network requests triggered by Angular UI actions, capturing secret API endpoints and payload structures.
- Interview Question:
  How does Chrome DevTools Protocol differ from standard Selenium WebDriver actions when inspecting browser traffic?

2. In-Browser JavaScript Hook Injection
- What it is:
  Injecting custom JS code into every new page document before page scripts execute, overriding default browser functions like `window.fetch` and `XMLHttpRequest.send`.
- Why we use it here:
  Allowed the scraper to secretly record every outgoing API payload and incoming API response in a global window buffer (`window.__intercepted_requests`).
- Interview Question:
  How can dynamic monkey-patching in JavaScript be used for network diagnostic tooling and security auditing?

Summary:
"In one sentence, this file is the reverse-engineering prototype that used CDP network interception and JS fetch hooks to discover MPCB's private REST endpoints."

Complexity:
⭐⭐⭐ Advanced
----------------------------------------

----------------------------------------
FILE:
`scraper/mpcb_scraper_v3.py`

Purpose (2-3 lines):
Serves as an early prototype that executed in-browser JavaScript `fetch()` calls via Selenium to bypass browser UI navigation slowdowns.

Workflow:
It opens the MPCB public portal using Selenium ChromeDriver, executes custom JavaScript `fetch()` blocks inside the browser context using `driver.execute_script()`, sends Base64 API requests directly from the browser instance, decodes returned responses, and parses telemetry quality code maps.

Key Technologies & Concepts:

1. In-Browser Script Execution (`execute_script`)
- What it is:
  A Selenium WebDriver capability that executes arbitrary JavaScript snippets directly inside the current browser window context.
- Why we use it here:
  Allowed early prototypes to issue direct API calls while bypassing CORS restrictions and inheriting session cookies active in the browser.
- Interview Question:
  What is the Same-Origin Policy (SOP) and Cross-Origin Resource Sharing (CORS) in web browsers, and how do they impact API scraping?

Summary:
"In one sentence, this file is an early prototype that executed custom JavaScript fetch calls inside a Selenium browser context to query MPCB endpoints."

Complexity:
⭐⭐ Intermediate
----------------------------------------

---

# MODULE 4: Data Cleaning, Storage & Parquet Exporters

----------------------------------------
FILE:
`scraper/load_data.py`

Purpose (2-3 lines):
Ingests raw scraped multi-parameter ETP telemetry CSV files (`mpcb_etp_data.csv`), cleans parameter attributes and timestamps, and bulk-loads structured data into PostgreSQL database tables.

Workflow:
It connects to PostgreSQL, truncates existing target tables (`monitoring_data`, `factories`) for clean ingestion, reads raw scraped CSV rows, cleans parameter strings, maps raw quality codes (`U`, `L`, `E`, `N`) to operational meanings, parses timestamps, and bulk-inserts records into the relational database.

Key Technologies & Concepts:

1. ETL Data Loading Pipeline (Extract, Transform, Load)
- What it is:
  A core data engineering pattern where raw data is extracted from disk/sources, transformed into standardized formats, and loaded into storage systems.
- Why we use it here:
  Transforms messy raw scraper CSV outputs into clean, queryable, normalized relational database tables.
- Interview Question:
  What are the key differences between ETL (Extract, Transform, Load) and ELT (Extract, Load, Transform) data pipeline architectures?

2. PostgreSQL Database Truncation (`TRUNCATE CASCADE`)
- What it is:
  A fast DDL command that removes all rows from a table and its child dependent tables instantly without scanning individual rows.
- Why we use it here:
  Ensures idempotent, clean database re-runs by wiping stale historical data before executing bulk re-loads.
- Interview Question:
  What is the difference between `DELETE FROM table`, `TRUNCATE TABLE`, and `DROP TABLE` in PostgreSQL in terms of performance, transaction logging, and rollback capabilities?

Summary:
"In one sentence, this file cleans raw multi-parameter scraped telemetry CSV records and bulk-loads them into PostgreSQL relational tables."

Complexity:
⭐⭐ Intermediate
----------------------------------------

----------------------------------------
FILE:
`scraper/load_ph.py`

Purpose (2-3 lines):
Handles dedicated cleaning, parameter-scoped deletion, and PostgreSQL bulk loading for high-density ETP-pH telemetry data (`mpcb_ph_data.csv`).

Workflow:
It connects to PostgreSQL, executes scoped deletion targeting only existing `ETP-pH` parameter records, opens `mpcb_ph_data.csv`, standardizes parameter strings to `ETP-pH`, parses timestamps and quality codes, and bulk-inserts pH records into `monitoring_data`.

Key Technologies & Concepts:

1. Parameter-Scoped Table Cleanup (`DELETE WHERE parameter_id = 'ETP-pH'`)
- What it is:
  Selective removal of database records matching specific column filters rather than wiping the entire database table.
- Why we use it here:
  Allows reloading or updating `ETP-pH` datasets independently without destroying existing `ETP-COD` or `ETP-BOD` records stored in `monitoring_data`.
- Interview Question:
  Why is selective table partition deletion preferred over full table truncation in multi-tenant or multi-parameter data warehouses?

Summary:
"In one sentence, this file selectively cleans and reloads ETP-pH telemetry into PostgreSQL without altering other parameter datasets."

Complexity:
⭐⭐ Intermediate
----------------------------------------

----------------------------------------
FILE:
`scraper/export_clean_data.py`

Purpose (2-3 lines):
Extracts cleaned telemetry records from PostgreSQL, pivots long-format monitoring data into wide-format time series per factory, and exports individual factory CSV files for downstream feature engineering.

Workflow:
It queries factory lists from PostgreSQL, extracts raw `(timestamp, parameter_id, value)` tuples per factory, uses `pandas` to pivot parameters into columns, sorts timestamps chronologically, and writes individual cleaned CSV files to `clean_factory_data/site_<id>.csv`.

Key Technologies & Concepts:

1. Data Pivoting (Long-to-Wide Format Transformation)
- What it is:
  Reshaping a tall dataset (where parameter names are rows) into a wide table (where each parameter becomes a dedicated column indexed by timestamp).
- Why we use it here:
  Machine learning feature engineering algorithms require rectangular matrices where columns represent distinct features (`ETP-COD`, `ETP-pH`, `ETP-Flow`) aligned along time index rows.
- Interview Question:
  What is the difference between Long Format (tidy data) and Wide Format data, and when is each format preferred in analytics vs ML?

2. Time Series Reshaping (`pandas.pivot_table`)
- What it is:
  A DataFrame method that reshapes data based on column values, handling index alignment and aggregation.
- Why we use it here:
  Converts multi-parameter database tuples into timestamp-aligned time series DataFrame matrices per factory.
- Interview Question:
  How does `pandas` handle duplicate index timestamps during `pivot_table` operations, and what aggregation functions exist?

Summary:
"In one sentence, this file pivots long-format PostgreSQL telemetry into timestamp-aligned wide time series CSVs per factory for machine learning consumption."

Complexity:
⭐⭐ Intermediate
----------------------------------------

----------------------------------------
FILE:
`scraper/process_cache_immediately.py`

Purpose (2-3 lines):
Scans local PDF cache directories, pre-processes offline PDF assets, and populates PostgreSQL tables without making external internet network requests.

Workflow:
It scans local file directories (`consents/`), identifies unindexed CTO PDF certificates, invokes `parser.py` locally to extract parameter limits, updates PostgreSQL database records, and logs parsing yields.

Key Technologies & Concepts:

1. Offline Batch Processing
- What it is:
  Executing data processing pipelines entirely on local or cached assets without external network reliance.
- Why we use it here:
  Allows instant historical data extraction and testing when offline or when MPCB external portals are down for maintenance.
- Interview Question:
  How do offline caching and batch processing architectures improve pipeline fault tolerance in edge and cloud computing?

Summary:
"In one sentence, this file processes locally cached PDF consent certificates offline to populate PostgreSQL tables without external portal querying."

Complexity:
⭐ Beginner
----------------------------------------
