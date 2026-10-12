import os
import sys
import yaml
import pandas as pd
import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HYBRID_V2_DIR = os.path.join(REPO_ROOT, "experiments", "hybrid_v2")
REAL_PARQUET = os.path.join(REPO_ROOT, "Data", "RawData", "real_features.parquet")

FE_DIR = os.path.join(REPO_ROOT, "Feature Engineering", "Synthetic Data Feature Engineering")
sys.path.insert(0, FE_DIR)

from features import assemble_feature_matrix

def build_features_for_dataset(input_parquet_path, output_parquet_path):
    print(f"\nProcessing telemetry dataset: {input_parquet_path}")
    df_raw = pd.read_parquet(input_parquet_path)
    
    # Load feature engineering config
    config_path = os.path.join(FE_DIR, "config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Standard CPCB CTO Consent Limits
    limits_df = pd.DataFrame([
        {'factory_id': 'site_1129', 'parameter_id': 'ETP-Flow', 'lower_limit': 0, 'upper_limit': 500.0, 'proxy_source_factory_id': None, 'extraction_confidence': 1.0},
        {'factory_id': 'site_1307', 'parameter_id': 'ETP-pH', 'lower_limit': 5.5, 'upper_limit': 9.0, 'proxy_source_factory_id': None, 'extraction_confidence': 1.0},
        {'factory_id': 'site_1629', 'parameter_id': 'ETP-Flow', 'lower_limit': 0, 'upper_limit': 500.0, 'proxy_source_factory_id': None, 'extraction_confidence': 1.0},
        {'factory_id': 'site_1629', 'parameter_id': 'ETP-pH', 'lower_limit': 5.5, 'upper_limit': 9.0, 'proxy_source_factory_id': None, 'extraction_confidence': 1.0},
        {'factory_id': 'site_1631', 'parameter_id': 'ETP-BOD', 'lower_limit': 0, 'upper_limit': 30.0, 'proxy_source_factory_id': None, 'extraction_confidence': 1.0},
        {'factory_id': 'site_1631', 'parameter_id': 'ETP-COD', 'lower_limit': 0, 'upper_limit': 250.0, 'proxy_source_factory_id': None, 'extraction_confidence': 1.0},
        {'factory_id': 'site_1631', 'parameter_id': 'ETP-Flow', 'lower_limit': 0, 'upper_limit': 500.0, 'proxy_source_factory_id': None, 'extraction_confidence': 1.0},
        {'factory_id': 'site_1631', 'parameter_id': 'ETP-TSS', 'lower_limit': 0, 'upper_limit': 100.0, 'proxy_source_factory_id': None, 'extraction_confidence': 1.0},
        {'factory_id': 'site_1631', 'parameter_id': 'ETP-pH', 'lower_limit': 5.5, 'upper_limit': 9.0, 'proxy_source_factory_id': None, 'extraction_confidence': 1.0},
    ])

    # Assemble feature matrix via real pipeline
    df_feat = assemble_feature_matrix(df_raw, limits_df, config)

    # Compute quality_error_rate to complete 28-column schema
    df_feat["quality_error_rate"] = df_feat["quality_code"].isin(["Error", "Out of Range", "E", "O"]).astype(float)

    # Reorder and cast data types to match real_features.parquet exactly
    df_real = pd.read_parquet(REAL_PARQUET)
    target_columns = list(df_real.columns)

    for col in target_columns:
        if col not in df_feat.columns:
            df_feat[col] = np.nan

    df_feat = df_feat[target_columns].copy()

    # Align dtypes
    df_feat["factory_id"] = df_feat["factory_id"].astype("string")
    df_feat["parameter_id"] = df_feat["parameter_id"].astype("string")
    df_feat["timestamp"] = pd.to_datetime(df_feat["timestamp"])

    df_feat.to_parquet(output_parquet_path, index=False)
    print(f"Successfully saved 28-column feature matrix ({len(df_feat):,} rows) to:\n  - {output_parquet_path}")

def run_rebuild_all():
    print("=== REBUILDING FEATURE MATRICES USING REAL PIPELINE CODE ===")
    
    # 1. Control Copy
    ctrl_in = os.path.join(HYBRID_V2_DIR, "control_telemetry.parquet")
    ctrl_out = os.path.join(HYBRID_V2_DIR, "control_features.parquet")
    build_features_for_dataset(ctrl_in, ctrl_out)

    # 2. Code Neutral Variant
    neut_in = os.path.join(HYBRID_V2_DIR, "hybrid_v2_code_neutral_telemetry.parquet")
    neut_out = os.path.join(HYBRID_V2_DIR, "hybrid_v2_code_neutral_features.parquet")
    build_features_for_dataset(neut_in, neut_out)

    # 3. Code Visible Variant
    vis_in = os.path.join(HYBRID_V2_DIR, "hybrid_v2_code_visible_telemetry.parquet")
    vis_out = os.path.join(HYBRID_V2_DIR, "hybrid_v2_code_visible_features.parquet")
    build_features_for_dataset(vis_in, vis_out)

if __name__ == "__main__":
    run_rebuild_all()
