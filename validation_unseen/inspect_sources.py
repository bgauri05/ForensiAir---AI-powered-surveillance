import os
import sqlite3
import pandas as pd
import numpy as np

REPO_ROOT = r"c:\Users\gauri\OneDrive\Desktop\ForensiAir---AI-powered-surveillance"
RAW_CSV_PATH = os.path.join(REPO_ROOT, "Data", "RawData", "monitoring_data(raw).csv")
PARQUET_PATH = os.path.join(REPO_ROOT, "Data", "RawData", "real_features.parquet")
DB_PATH = os.path.join(REPO_ROOT, "forensier.db")
CTO_CSV_PATH = os.path.join(REPO_ROOT, "Original Data", "consent_limits.csv")
MISSING_CSV_PATH = os.path.join(REPO_ROOT, "Original Data", "dataset_missing_summary.csv")

UNSEEN_DIR = r"c:\Users\gauri\Downloads\validation"
UNSEEN_FILES = {
    "Cipla": os.path.join(UNSEEN_DIR, "Cipla (1).csv"),
    "Glenmark": os.path.join(UNSEEN_DIR, "Glenmark (1).csv"),
    "Indoco": os.path.join(UNSEEN_DIR, "Indoco (1).csv"),
    "Zydus": os.path.join(UNSEEN_DIR, "Zydus (1).csv")
}

def inspect_sources():
    print("==========================================================================")
    print(" SOURCE FILES SHAPES, COLUMNS, AND DATA TYPES INSPECION")
    print("==========================================================================")
    
    # 1. Raw Telemetry CSV
    print("\n--- 1. Data/RawData/monitoring_data(raw).csv ---")
    df_raw = pd.read_csv(RAW_CSV_PATH, nrows=1000)
    # Get total row count efficiently
    with open(RAW_CSV_PATH, "r", encoding="utf-8") as f:
        total_raw_rows = sum(1 for _ in f) - 1
    print(f"Shape: ({total_raw_rows:,}, {len(df_raw.columns)})")
    print("Columns:", list(df_raw.columns))
    print("Data types:")
    print(df_raw.dtypes)

    # 2. Real Features Parquet
    print("\n--- 2. Data/RawData/real_features.parquet ---")
    df_pq = pd.read_parquet(PARQUET_PATH)
    print(f"Shape: {df_pq.shape}")
    print("Columns:", list(df_pq.columns))
    print("Data types:")
    print(df_pq.dtypes)

    # 3. SQLite DB (forensier.db)
    print("\n--- 3. forensier.db ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    print("Tables in forensier.db:", tables)
    for tbl in tables:
        count_res = cursor.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        cursor.execute(f"PRAGMA table_info({tbl})")
        cols = [col[1] for col in cursor.fetchall()]
        print(f"  Table `{tbl}`: {count_res:,} rows, Columns: {cols}")
    conn.close()

    # 4. Consent Limits CSV
    print("\n--- 4. Original Data/consent_limits.csv ---")
    df_cto = pd.read_csv(CTO_CSV_PATH)
    print(f"Shape: {df_cto.shape}")
    print("Columns:", list(df_cto.columns))
    print("Data types:")
    print(df_cto.dtypes)

    # 5. Missing Summary CSV
    print("\n--- 5. Original Data/dataset_missing_summary.csv ---")
    df_miss = pd.read_csv(MISSING_CSV_PATH)
    print(f"Shape: {df_miss.shape}")
    print("Columns:", list(df_miss.columns))

    # 6. Unseen Test CSVs
    print("\n--- 6. Data/Unseen (*.csv in Downloads/validation) ---")
    for f_name, f_path in UNSEEN_FILES.items():
        df_u = pd.read_csv(f_path)
        print(f"  Factory [{f_name}]: Shape {df_u.shape}, Columns: {list(df_u.columns)}")

if __name__ == "__main__":
    inspect_sources()
