"""
Dataset Characterization Engine
================================
Produces a comprehensive behavioral profile row per factory (`factory_profiles.parquet`) for all 33 factories.

Authoritative Reference Inputs (read directly from ChData/):
- real_features.parquet
- dataset_coverage_summary.csv (or _v2.csv)
- dataset_quality_summary.csv (or _v2.csv)
- dataset_statistics_summary.csv (or _v2.csv)
- dataset_parameter_summary.csv (or _v2.csv)

Forensic Exhibit Holdouts:
- site_1232 and site_1281 are excluded when computing normalization scalers, dataset-wide baselines,
  or similarity metrics defining "normal" behavior.
"""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity

# Define holdout factory IDs
HOLDOUT_FACTORIES = ['site_1232', 'site_1281']

# Target parameters for Parameter Distributions module (excluding Flow)
TARGET_PARAMETERS = ['pH', 'COD', 'BOD', 'TSS']

# Sensor Health Score Configuration Weights & Scale Factors
SENSOR_HEALTH_WEIGHT_MISSING = 0.40
SENSOR_HEALTH_WEIGHT_DUPLICATE = 0.20
SENSOR_HEALTH_WEIGHT_BDL = 0.20
SENSOR_HEALTH_WEIGHT_OUTAGES = 0.20
SENSOR_HEALTH_MAX_OUTAGES_CAP = 100.0  # Outage count normalization scale

# Temporal Stability Threshold Configuration Constants
TEMPORAL_SHIFT_THRESHOLD_PH = 0.5            # Absolute shift threshold for pH units
TEMPORAL_SHIFT_THRESHOLD_CONCENTRATION = 0.25 # Relative shift threshold for COD, BOD, TSS (25%)

def resolve_chdata_path(base_dir, filename_base):
    """
    Resolves reference filename supporting both exact _v2.csv and baseline .csv variants.
    """
    v2_name = f"{filename_base}_v2.csv"
    base_name = f"{filename_base}.csv"
    
    v2_path = os.path.join(base_dir, v2_name)
    base_path = os.path.join(base_dir, base_name)
    
    if os.path.exists(v2_path):
        return v2_path
    elif os.path.exists(base_path):
        return base_path
    else:
        raise FileNotFoundError(
            f"Required reference file for '{filename_base}' not found in {base_dir}. "
            f"Checked '{v2_path}' and '{base_path}'."
        )

def load_reference_data(chdata_dir='ChData'):
    """
    Loads all required reference CSV files and parquet data from ChData.
    """
    if not os.path.exists(chdata_dir):
        raise FileNotFoundError(f"ChData directory not found at path: {chdata_dir}")
        
    cov_path = resolve_chdata_path(chdata_dir, 'dataset_coverage_summary')
    qual_path = resolve_chdata_path(chdata_dir, 'dataset_quality_summary')
    stat_path = resolve_chdata_path(chdata_dir, 'dataset_statistics_summary')
    param_path = resolve_chdata_path(chdata_dir, 'dataset_parameter_summary')
    parquet_path = os.path.join(chdata_dir, 'real_features.parquet')
    
    if not os.path.exists(parquet_path):
        raise FileNotFoundError(f"Required real_features.parquet not found at {parquet_path}")

    df_cov = pd.read_csv(cov_path)
    df_qual = pd.read_csv(qual_path)
    df_stat = pd.read_csv(stat_path)
    df_param = pd.read_csv(param_path)
    df_real = pd.read_parquet(parquet_path)
    
    return df_cov, df_qual, df_stat, df_param, df_real

def compute_data_availability(df_cov, df_qual):
    """
    Module 1: Data Availability
    Pulls coverage_percentage, monitoring_days, longest_gap, and number_of_outages.
    """
    cov_cols = ['factory_id', 'coverage_percentage', 'monitoring_days']
    qual_cols = ['factory_id', 'longest_gap', 'number_of_outages']
    
    for c in cov_cols:
        if c not in df_cov.columns:
            raise KeyError(f"Missing required column '{c}' in coverage summary")
    for c in qual_cols:
        if c not in df_qual.columns:
            raise KeyError(f"Missing required column '{c}' in quality summary")

    df_avail = pd.merge(
        df_cov[cov_cols],
        df_qual[qual_cols],
        on='factory_id',
        how='outer'
    )
    return df_avail

def compute_parameter_distributions(df_stat, df_param):
    """
    Module 2: Parameter Distributions
    Pulls mean, std, min, max, CV for pH, COD, BOD, TSS (excluding Flow).
    """
    # Merge statistics and parameter summary to capture coeff_variation
    m = pd.merge(
        df_stat[['factory_id', 'parameter', 'mean', 'standard_deviation', 'minimum', 'maximum']],
        df_param[['factory_id', 'parameter', 'coeff_variation']],
        on=['factory_id', 'parameter'],
        how='outer'
    )
    
    # Normalize parameter names (remove ETP- prefix for clean column names)
    m['param_clean'] = m['parameter'].astype(str).str.replace('ETP-', '', regex=False)
    
    # Filter to target parameters only (pH, COD, BOD, TSS) - exclude Flow
    m = m[m['param_clean'].isin(TARGET_PARAMETERS)]
    
    # Pivot so each parameter has its own set of stats per factory
    piv_mean = m.pivot(index='factory_id', columns='param_clean', values='mean').add_suffix('_mean')
    piv_std = m.pivot(index='factory_id', columns='param_clean', values='standard_deviation').add_suffix('_std')
    piv_min = m.pivot(index='factory_id', columns='param_clean', values='minimum').add_suffix('_min')
    piv_max = m.pivot(index='factory_id', columns='param_clean', values='maximum').add_suffix('_max')
    piv_cv = m.pivot(index='factory_id', columns='param_clean', values='coeff_variation').add_suffix('_cv')
    
    df_dist = pd.concat([piv_mean, piv_std, piv_min, piv_max, piv_cv], axis=1).reset_index()
    return df_dist

def compute_sensor_health_score(df_qual):
    """
    Module 3: Sensor Health Score
    Computes a 0-1 sensor health score per factory using a documented weighted formula
    configured via top-level constants.
    
    Formula:
    - missing_penalty = missing_percentage / 100.0 (weight SENSOR_HEALTH_WEIGHT_MISSING)
    - duplicate_penalty = duplicate_percentage / 100.0 (weight SENSOR_HEALTH_WEIGHT_DUPLICATE)
    - bdl_penalty = bdl_percentage / 100.0 (weight SENSOR_HEALTH_WEIGHT_BDL)
    - outage_penalty = min(number_of_outages / SENSOR_HEALTH_MAX_OUTAGES_CAP, 1.0) (weight SENSOR_HEALTH_WEIGHT_OUTAGES)
    """
    req_cols = ['factory_id', 'missing_percentage', 'duplicate_percentage', 'number_of_outages']
    for c in req_cols:
        if c not in df_qual.columns:
            raise KeyError(f"Missing required column '{c}' in quality summary")
            
    df = df_qual.copy()
    p_missing = df['missing_percentage'] / 100.0
    p_duplicate = df['duplicate_percentage'] / 100.0
    
    # Check for bdl_percentage or fall back to zero_percentage
    bdl_col = 'bdl_percentage' if 'bdl_percentage' in df.columns else 'zero_percentage'
    p_bdl = df[bdl_col] / 100.0
    
    p_outages = (df['number_of_outages'] / SENSOR_HEALTH_MAX_OUTAGES_CAP).clip(upper=1.0)
    
    penalty = (
        SENSOR_HEALTH_WEIGHT_MISSING * p_missing +
        SENSOR_HEALTH_WEIGHT_DUPLICATE * p_duplicate +
        SENSOR_HEALTH_WEIGHT_BDL * p_bdl +
        SENSOR_HEALTH_WEIGHT_OUTAGES * p_outages
    )
    sensor_health_score = (1.0 - penalty).clip(lower=0.0, upper=1.0)
    
    return pd.DataFrame({
        'factory_id': df['factory_id'],
        'sensor_health_score': sensor_health_score
    })

def compute_inter_factory_similarity(df_dist):
    """
    Module 4: Inter-Factory Similarity
    Fits StandardScaler on non-holdout factories only, transforms all factories,
    and calculates Cosine Similarity to assign the top 3 similar factories per factory.
    """
    df_feat = df_dist.set_index('factory_id').copy()
    
    # Exclude holdout factories when fitting scaler
    non_holdouts_df = df_feat[~df_feat.index.isin(HOLDOUT_FACTORIES)]
    
    # Compute non-holdout feature means for imputation
    non_holdout_means = non_holdouts_df.mean()
    
    # Impute missing values (parameters not measured by a factory) using non-holdout mean
    df_imputed = df_feat.fillna(non_holdout_means)
    non_holdouts_imputed = non_holdouts_df.fillna(non_holdout_means)
    
    # Fit scaler strictly on non-holdouts
    scaler = StandardScaler()
    scaler.fit(non_holdouts_imputed)
    
    # Transform all factories (including holdouts)
    scaled_matrix = scaler.transform(df_imputed)
    scaled_df = pd.DataFrame(scaled_matrix, index=df_feat.index, columns=df_feat.columns)
    
    # Cosine similarity matrix across all factories
    sim_matrix = pd.DataFrame(
        cosine_similarity(scaled_df),
        index=df_feat.index,
        columns=df_feat.index
    )
    
    top_sim_data = []
    for f in df_feat.index:
        sims = sim_matrix.loc[f].drop(f) # Exclude self-similarity
        top3 = sims.nlargest(3)
        top_sim_data.append({
            'factory_id': f,
            'similar_factory_1': top3.index[0],
            'similar_factory_1_score': round(float(top3.iloc[0]), 4),
            'similar_factory_2': top3.index[1],
            'similar_factory_2_score': round(float(top3.iloc[1]), 4),
            'similar_factory_3': top3.index[2],
            'similar_factory_3_score': round(float(top3.iloc[2]), 4)
        })
        
    return pd.DataFrame(top_sim_data)

def compute_temporal_stability(df_real):
    """
    Module 5: Temporal Stability
    Splits timestamps from real_features.parquet into Q1-Q4, computes quarterly means,
    evaluates parameter shifts, and produces an objective temporal shift summary.
    
    Shift Evaluation Rule (Configurable via constants):
    - For pH: shift > TEMPORAL_SHIFT_THRESHOLD_PH is considered a meaningful quarterly shift.
    - For COD, BOD, TSS: relative shift > TEMPORAL_SHIFT_THRESHOLD_CONCENTRATION is considered meaningful.
    """
    # Filter out Flow parameters from real features
    df = df_real[df_real['parameter_id'].astype(str).str.replace('ETP-', '', regex=False).isin(TARGET_PARAMETERS)].copy()
    df['quarter'] = pd.to_datetime(df['timestamp']).dt.quarter
    
    # Group by factory_id, parameter_id, quarter to get mean value
    q_stats = df.groupby(['factory_id', 'parameter_id', 'quarter'])['value'].mean().unstack()
    
    records = []
    for f, f_df in df.groupby('factory_id'):
        p_records = []
        any_shift_detected = False
        
        for param in f_df['parameter_id'].unique():
            if (f, param) not in q_stats.index:
                continue
            row = q_stats.loc[(f, param)]
            q_vals = row.dropna()
            if len(q_vals) < 2:
                # Not enough quarters to measure shift
                continue
                
            q_min, q_max = q_vals.min(), q_vals.max()
            abs_shift = q_max - q_min
            overall_mean = q_vals.mean()
            rel_shift = abs_shift / (abs(overall_mean) + 1e-6)
            
            clean_param = str(param).replace('ETP-', '')
            
            # Rule for meaningful shift
            if clean_param == 'pH':
                is_shift = abs_shift > TEMPORAL_SHIFT_THRESHOLD_PH
            else:
                is_shift = rel_shift > TEMPORAL_SHIFT_THRESHOLD_CONCENTRATION
                
            if is_shift:
                any_shift_detected = True
                
            p_records.append(
                f"{clean_param}: Q_min={q_min:.2f}, Q_max={q_max:.2f} (shift={abs_shift:.2f})"
            )
            
        summary_text = "; ".join(p_records) if p_records else "No monitored parameters with quarterly data"
        records.append({
            'factory_id': f,
            'temporal_shift_detected': any_shift_detected,
            'temporal_shift_summary': summary_text
        })
        
    return pd.DataFrame(records)

def generate_factory_profiles(chdata_dir='ChData'):
    """
    Main pipeline orchestrator combining all characterization modules.
    Returns the complete 33-row profile dataframe.
    """
    print(f"Loading reference datasets from '{chdata_dir}'...")
    df_cov, df_qual, df_stat, df_param, df_real = load_reference_data(chdata_dir)
    
    # Verify expected 33 factories exist across reference files
    factories = df_cov['factory_id'].unique()
    if len(factories) != 33:
        raise ValueError(f"Expected 33 factories in dataset, found {len(factories)}")
        
    print(f"Dataset contains {len(factories)} factories (Holdouts: {HOLDOUT_FACTORIES})")
    
    print("Computing Module 1: Data Availability...")
    m1 = compute_data_availability(df_cov, df_qual)
    
    print("Computing Module 2: Parameter Distributions...")
    m2 = compute_parameter_distributions(df_stat, df_param)
    
    print("Computing Module 3: Sensor Health Score...")
    m3 = compute_sensor_health_score(df_qual)
    
    print("Computing Module 4: Inter-Factory Similarity (Holdouts excluded during scaler fit)...")
    m4 = compute_inter_factory_similarity(m2)
    
    print("Computing Module 5: Temporal Stability...")
    m5 = compute_temporal_stability(df_real)
    
    # Merge all modules into single dataframe indexed by factory_id
    profiles = m1.merge(m2, on='factory_id', how='left') \
                 .merge(m3, on='factory_id', how='left') \
                 .merge(m4, on='factory_id', how='left') \
                 .merge(m5, on='factory_id', how='left')
                 
    if len(profiles) != 33:
        raise ValueError(f"Output dataframe row count error! Expected 33 rows, got {len(profiles)}")
        
    for holdout in HOLDOUT_FACTORIES:
        if holdout not in profiles['factory_id'].values:
            raise ValueError(f"Holdout factory '{holdout}' missing from output profiles!")
            
    return profiles

def save_and_display_profiles(profiles):
    """
    Saves profiles parquet to Data/RawData/factory_profiles.parquet and prints column list + sample row.
    """
    primary_dir = os.path.join('Data', 'RawData')
    os.makedirs(primary_dir, exist_ok=True)
    primary_file = os.path.join(primary_dir, 'factory_profiles.parquet')
    profiles.to_parquet(primary_file, index=False)
    print(f"\nSaved factory profiles parquet to: {primary_file}")
    
    print("\n" + "=" * 60)
    print("COMPLETE OUTPUT COLUMN LIST (Total Columns: {})".format(len(profiles.columns)))
    print("=" * 60)
    for i, col in enumerate(profiles.columns, 1):
        print(f"{i:2d}. {col}")
        
    print("\n" + "=" * 60)
    print("COMPLETE EXAMPLE PROFILE ROW (Factory: {})".format(profiles.iloc[0]['factory_id']))
    print("=" * 60)
    sample_row = profiles.iloc[0].to_dict()
    for k, v in sample_row.items():
        print(f"  {k:30s} : {v}")

if __name__ == '__main__':
    try:
        profiles_df = generate_factory_profiles('ChData')
        save_and_display_profiles(profiles_df)
    except Exception as e:
        print(f"\nERROR: Characterization Engine failed: {e}", file=sys.stderr)
        sys.exit(1)
