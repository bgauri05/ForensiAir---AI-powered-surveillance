import os
import sys
import pandas as pd
import numpy as np

# Path to the raw data files
DATA_DIR = r"c:\Users\gauri\Downloads\validation"

FACTORY_FILES = {
    "Cipla": "Cipla (1).csv",
    "Glenmark": "Glenmark (1).csv",
    "Indoco": "Indoco (1).csv",
    "Zydus": "Zydus (1).csv"
}

CANONICAL_PARAMS = ["ETP-BOD", "ETP-COD", "ETP-pH", "ETP-Flow", "ETP-TSS"]

def normalize_csv(factory_name: str, csv_path: str) -> pd.DataFrame:
    """
    Loads raw CSV for a factory, normalizes column names to canonical schema:
    [timestamp, ETP-BOD, ETP-COD, ETP-pH, ETP-Flow, ETP-TSS]
    Handles 'NA' values, missing columns, and column order differences.
    """
    df = pd.read_csv(csv_path)
    
    # Identify time column
    time_col = None
    for c in df.columns:
        if c.strip().lower() in ["time", "timestamp", "datetime"]:
            time_col = c
            break
    if time_col is None:
        time_col = df.columns[0]
        
    # Map parameter columns
    col_mapping = {time_col: "timestamp"}
    for c in df.columns:
        if c == time_col:
            continue
        c_lower = c.lower()
        if "bod" in c_lower:
            col_mapping[c] = "ETP-BOD"
        elif "cod" in c_lower:
            col_mapping[c] = "ETP-COD"
        elif "ph" in c_lower:
            col_mapping[c] = "ETP-pH"
        elif "flow" in c_lower:
            col_mapping[c] = "ETP-Flow"
        elif "tss" in c_lower:
            col_mapping[c] = "ETP-TSS"
            
    df = df.rename(columns=col_mapping)
    
    # Convert timestamp
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    
    # Ensure all canonical parameter columns exist
    for p in CANONICAL_PARAMS:
        if p not in df.columns:
            df[p] = np.nan
        else:
            # Replace string NA with NaN and force float numeric type
            df[p] = pd.to_numeric(df[p], errors="coerce")
            
    # Keep canonical columns in order
    canonical_cols = ["timestamp"] + CANONICAL_PARAMS
    df = df[canonical_cols].sort_values("timestamp").reset_index(drop=True)
    
    # Drop rows where timestamp itself is NaN (if any header/footer invalid row)
    df = df.dropna(subset=["timestamp"]).reset_index(drop=True)
    
    return df

def convert_to_long_format(factory_name: str, df_wide: pd.DataFrame) -> pd.DataFrame:
    """
    Converts normalized wide DataFrame into long format expected by ForensiAIR feature engine:
    [factory_id, parameter_id, timestamp, value, quality_code]
    """
    long_rows = []
    for param in CANONICAL_PARAMS:
        if param in df_wide.columns:
            sub = pd.DataFrame({
                "factory_id": factory_name,
                "parameter_id": param,
                "timestamp": df_wide["timestamp"],
                "value": df_wide[param],
                "quality_code": "Raw"
            })
            long_rows.append(sub)
            
    long_df = pd.concat(long_rows, ignore_index=True)
    long_df = long_df.sort_values(["factory_id", "parameter_id", "timestamp"]).reset_index(drop=True)
    return long_df

def get_default_cto_limits() -> pd.DataFrame:
    """
    Generates standard CPCB CTO consent limits for the 4 unseen factories.
    """
    factories = ["Cipla", "Glenmark", "Indoco", "Zydus"]
    records = []
    for f in factories:
        records.append({"factory_id": f, "parameter_id": "ETP-pH", "lower_limit": 5.5, "upper_limit": 9.0, "extraction_confidence": 1.0, "proxy_source_factory_id": np.nan})
        records.append({"factory_id": f, "parameter_id": "ETP-BOD", "lower_limit": np.nan, "upper_limit": 30.0, "extraction_confidence": 1.0, "proxy_source_factory_id": np.nan})
        records.append({"factory_id": f, "parameter_id": "ETP-COD", "lower_limit": np.nan, "upper_limit": 250.0, "extraction_confidence": 1.0, "proxy_source_factory_id": np.nan})
        records.append({"factory_id": f, "parameter_id": "ETP-TSS", "lower_limit": np.nan, "upper_limit": 100.0, "extraction_confidence": 1.0, "proxy_source_factory_id": np.nan})
        records.append({"factory_id": f, "parameter_id": "ETP-Flow", "lower_limit": np.nan, "upper_limit": 1000.0, "extraction_confidence": 1.0, "proxy_source_factory_id": np.nan})
    return pd.DataFrame(records)

if __name__ == "__main__":
    print("Testing unseen factory loader...")
    for f_name, f_file in FACTORY_FILES.items():
        path = os.path.join(DATA_DIR, f_file)
        wide = normalize_csv(f_name, path)
        long = convert_to_long_format(f_name, wide)
        print(f"[{f_name}] Wide rows: {len(wide)}, Date range: {wide['timestamp'].min()} to {wide['timestamp'].max()}")
        print(f"        Valid values per param:")
        for p in CANONICAL_PARAMS:
            valid_cnt = wide[p].notna().sum()
            print(f"          {p}: {valid_cnt} non-null / {len(wide)}")
