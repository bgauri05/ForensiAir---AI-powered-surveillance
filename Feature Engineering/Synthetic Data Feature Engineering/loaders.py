import pandas as pd
import numpy as np

def load_synthetic(monitoring_csv_path: str, labels_csv_path: str):
    """
    Reads monitoring_data.csv into long format and labels.csv.
    """
    # Load monitoring data
    df = pd.read_csv(monitoring_csv_path)
    
    # Parse timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Set dtypes
    df['value'] = df['value'].astype('float64')
    df['factory_id'] = df['factory_id'].astype('string')
    df['parameter_id'] = df['parameter_id'].astype('string')
    
    # is_valid column indicating non-null values
    df['is_valid'] = df['value'].notnull()
    
    # Handle quality_code column if present
    if 'quality_code' in df.columns:
        df['quality_code'] = df['quality_code'].astype('string')
    else:
        df['quality_code'] = 'Raw'
        df['quality_code'] = df['quality_code'].astype('string')
    
    # Sort
    df = df.sort_values(by=['factory_id', 'parameter_id', 'timestamp']).reset_index(drop=True)
    
    # Ensure exact columns
    df = df[['factory_id', 'parameter_id', 'timestamp', 'value', 'quality_code', 'is_valid']]
    
    # Load labels
    labels_df = pd.read_csv(labels_csv_path)
    labels_df['start_timestamp'] = pd.to_datetime(labels_df['start_timestamp'])
    labels_df['end_timestamp'] = pd.to_datetime(labels_df['end_timestamp'])
    
    return df, labels_df

def load_real(pg_connection_string: str) -> pd.DataFrame:
    """
    Stub for the database loader on the real-data PC.
    """
    raise NotImplementedError("Implemented on real-data PC — see repo README")


def load_cto_limits(cto_csv_path: str) -> pd.DataFrame:
    """
    Load CTO consent limits.
    """

    cto_df = pd.read_csv(cto_csv_path)

    required_columns = [
        "factory_id",
        "parameter",
        "minimum_limit",
        "maximum_limit"
    ]

    missing = [
        col
        for col in required_columns
        if col not in cto_df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    cto_df = cto_df.rename(
        columns={
            "parameter": "parameter_id",
            "minimum_limit": "lower_limit",
            "maximum_limit": "upper_limit"
        }
    )

    return cto_df