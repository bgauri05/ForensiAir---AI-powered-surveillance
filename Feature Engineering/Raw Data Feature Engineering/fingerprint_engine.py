import os
import pandas as pd
import numpy as np

def main():
    print("Loading datasets...")
    # Load real features parquet
    features_path = r"Data/RawData/real_features.parquet"
    df = pd.read_parquet(features_path)
    
    # Ensure timestamp is datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Load inspection events
    inspections_path = r"Data/RawData/inspection_events_2024.csv"
    inspections_df = pd.read_csv(inspections_path)
    inspections_df['inspection_date'] = pd.to_datetime(inspections_df['inspection_date'])
    
    # Load consent limits
    consent_limits_path = r"Original Data/consent_limits.csv"
    consent_limits = pd.read_csv(consent_limits_path)
    
    # Load dataset missing summary for coordinated missing data
    missing_summary_path = r"Original Data/dataset_missing_summary.csv"
    missing_summary = pd.read_csv(missing_summary_path)
    
    # Exclude holdout sites from baseline / typical calculation
    holdouts = ["site_1232", "site_1281"]
    
    # Get all 33 unique factory IDs
    factories = sorted(df['factory_id'].unique().tolist())
    print(f"Total factories to process: {len(factories)}")
    
    # Initialize results dict
    results = {f: {} for f in factories}
    
    # -------------------------------------------------------------
    # 1. IMPOSSIBLE_PH_RANGE
    # -------------------------------------------------------------
    print("Computing IMPOSSIBLE_PH_RANGE...")
    ph_limits = consent_limits[consent_limits['parameter'].str.lower().isin(['ph', 'ph value'])].copy()
    ph_limits = ph_limits.sort_values('extraction_confidence', ascending=False)
    ph_limits = ph_limits.drop_duplicates(subset=['factory_id'], keep='first')
    
    for fac in factories:
        fac_df = df[(df['factory_id'] == fac) & (df['parameter_id'] == 'ETP-pH') & (df['value'].notna())]
        total_ph_readings = len(fac_df)
        if total_ph_readings == 0:
            results[fac]['impossible_ph_range'] = 0.0
            results[fac]['ph_flagged_count'] = 0
            continue
            
        fac_limits = ph_limits[ph_limits['factory_id'] == fac]
        min_lim = np.nan
        max_lim = np.nan
        if not fac_limits.empty:
            min_lim = fac_limits.iloc[0]['minimum_limit']
            max_lim = fac_limits.iloc[0]['maximum_limit']
            
        values = fac_df['value'].values
        # Physically impossible flag
        flagged = (values < 0) | (values > 14)
        if not np.isnan(min_lim):
            flagged = flagged | (values < min_lim)
        if not np.isnan(max_lim):
            flagged = flagged | (values > max_lim)
            
        flagged_count = int(np.sum(flagged))
        flagged_pct = 100.0 * flagged_count / total_ph_readings
        results[fac]['impossible_ph_range'] = flagged_pct
        results[fac]['ph_flagged_count'] = flagged_count

    # -------------------------------------------------------------
    # 2. INSPECTION_DIP
    # -------------------------------------------------------------
    print("Computing INSPECTION_DIP...")
    # Include ETP-Flow along with pH, COD, BOD, TSS so all factories with Completed inspections have metrics
    param_map = {
        'pH': 'ETP-pH',
        'COD': 'ETP-COD',
        'BOD': 'ETP-BOD',
        'TSS': 'ETP-TSS',
        'Flow': 'ETP-Flow'
    }
    
    # Filter to Completed inspections only
    inspections_completed = inspections_df[inspections_df['status'] == 'Completed']
    
    for fac in factories:
        fac_insps = inspections_completed[inspections_completed['factory_id'] == fac]
        if fac_insps.empty:
            results[fac]['inspection_dip'] = np.nan
            continue
            
        fac_telemetry = df[df['factory_id'] == fac]
        pct_diffs = []
        
        for _, insp_row in fac_insps.iterrows():
            insp_date = insp_row['inspection_date']
            
            # Find latest telemetry timestamp before or equal to inspection_date
            param_before = fac_telemetry[fac_telemetry['timestamp'] < insp_date]
            if param_before.empty:
                # Skip this inspection event entirely if no telemetry exists before it
                continue
                
            latest_ts = param_before['timestamp'].max()
            
            # If the latest telemetry is within the 72h window, anchor at inspection_date.
            # Otherwise, anchor at the latest telemetry timestamp to handle data gaps.
            if latest_ts >= (insp_date - pd.Timedelta(hours=72)):
                anchor_end = insp_date
            else:
                anchor_end = latest_ts + pd.Timedelta(seconds=1)
                
            pre_start = anchor_end - pd.Timedelta(hours=72)
            pre_end = anchor_end
            
            # Baseline window ending before pre_start
            base_start = max(pd.to_datetime("2024-01-01 00:00:00"), pre_start - pd.Timedelta(days=30))
            base_end = pre_start
            
            for param_label, param_id in param_map.items():
                param_df = fac_telemetry[(fac_telemetry['parameter_id'] == param_id) & (fac_telemetry['value'].notna())]
                if param_df.empty:
                    continue
                    
                # Pre-inspection data
                pre_data = param_df[(param_df['timestamp'] >= pre_start) & (param_df['timestamp'] < pre_end)]['value']
                # Baseline data
                base_data = param_df[(param_df['timestamp'] >= base_start) & (param_df['timestamp'] < base_end)]['value']
                
                # If baseline is empty or too small, fall back to the factory's overall mean for this parameter
                if len(base_data) < 5:
                    base_data = param_df['value']
                    
                if len(pre_data) > 0 and len(base_data) > 0:
                    m_pre = pre_data.mean()
                    m_base = base_data.mean()
                    
                    if m_base > 0:
                        pct_diff = 100.0 * (m_pre - m_base) / m_base
                        pct_diffs.append(pct_diff)
                    elif m_base == 0:
                        if m_pre == 0:
                            pct_diffs.append(0.0)
                        else:
                            pct_diffs.append(100.0)
                            
        if len(pct_diffs) > 0:
            results[fac]['inspection_dip'] = np.mean(pct_diffs)
        else:
            results[fac]['inspection_dip'] = np.nan

    # -------------------------------------------------------------
    # 3. FLATLINE
    # -------------------------------------------------------------
    print("Computing FLATLINE...")
    for fac in factories:
        fac_df = df[(df['factory_id'] == fac) & (df['flatline_flag'].notna())]
        if len(fac_df) > 0:
            results[fac]['flatline'] = 100.0 * np.sum(fac_df['flatline_flag'] == 1) / len(fac_df)
        else:
            results[fac]['flatline'] = 0.0

    # -------------------------------------------------------------
    # 4. LIMIT_HUGGING
    # -------------------------------------------------------------
    print("Computing LIMIT_HUGGING...")
    for fac in factories:
        fac_df = df[(df['factory_id'] == fac) & (df['limit_hugging'].notna())]
        if len(fac_df) > 0:
            results[fac]['limit_hugging'] = 100.0 * np.sum(fac_df['limit_hugging'] == 1) / len(fac_df)
        else:
            results[fac]['limit_hugging'] = 0.0

    # -------------------------------------------------------------
    # 5. CORRELATION_BREAK
    # -------------------------------------------------------------
    print("Computing CORRELATION_BREAK...")
    corr_cols = [c for c in df.columns if c.startswith('corr_')]
    
    # Calculate average correlation per factory
    df['row_avg_corr'] = df[corr_cols].mean(axis=1)
    
    for fac in factories:
        fac_df = df[(df['factory_id'] == fac) & (df['row_avg_corr'].notna())]
        if len(fac_df) > 0:
            results[fac]['correlation_break'] = fac_df['row_avg_corr'].mean()
        else:
            results[fac]['correlation_break'] = np.nan
            
    # Calculate dataset-wide typical range (excluding holdouts)
    non_holdout_corrs = [
        results[fac]['correlation_break']
        for fac in factories
        if fac not in holdouts and not np.isnan(results[fac]['correlation_break'])
    ]
    typical_mean = np.mean(non_holdout_corrs)
    typical_std = np.std(non_holdout_corrs)
    corr_threshold = typical_mean - 1.0 * typical_std

    # -------------------------------------------------------------
    # 6. COPY_PASTE
    # -------------------------------------------------------------
    print("Computing COPY_PASTE...")
    for fac in factories:
        fac_df = df[(df['factory_id'] == fac) & (df['autocorrelation'].notna())]
        if len(fac_df) > 0:
            results[fac]['copy_paste'] = 100.0 * np.sum(fac_df['autocorrelation'] > 0.95) / len(fac_df)
        else:
            results[fac]['copy_paste'] = 0.0

    # -------------------------------------------------------------
    # 7. COORDINATED_MISSING_DATA
    # -------------------------------------------------------------
    print("Computing COORDINATED_MISSING_DATA...")
    raw_missing_rates = {}
    for fac in factories:
        fac_missing = missing_summary[missing_summary['factory_id'] == fac]
        if not fac_missing.empty:
            raw_missing_rates[fac] = fac_missing.iloc[0]['missing_percentage']
        else:
            raw_missing_rates[fac] = 0.0
            
    # Calculate typical range for missing data outlier detection (excluding holdouts)
    non_holdout_missing = [
        raw_missing_rates[fac]
        for fac in factories
        if fac not in holdouts
    ]
    typical_median_missing = np.median(non_holdout_missing)
    typical_std_missing = np.std(non_holdout_missing)
    
    # Store standard deviations above the typical dataset median
    for fac in factories:
        results[fac]['coordinated_missing_data'] = (raw_missing_rates[fac] - typical_median_missing) / typical_std_missing

    # -------------------------------------------------------------
    # 8. DATA_INTEGRITY (Error / Out-of-Range quality-code rate)
    # -------------------------------------------------------------
    # Added 2026-08: a factory whose telemetry is disproportionately tagged
    # Error/Out-of-Range by the source system either has failing equipment or
    # is having its bad readings excluded from the record -- either way it's
    # a data-integrity signal that was previously computed (quality_error_rate,
    # from loaders.py's per-factory QC report) but never fed into scoring.
    print("Computing DATA_INTEGRITY...")
    raw_error_rates = {}
    for fac in factories:
        fac_df = df[(df['factory_id'] == fac) & (df['quality_error_rate'].notna())]
        if len(fac_df) > 0:
            raw_error_rates[fac] = 100.0 * float(fac_df['quality_error_rate'].iloc[0])
        else:
            raw_error_rates[fac] = 0.0

    # Calculate typical range for error-rate outlier detection (excluding holdouts)
    non_holdout_error = [
        raw_error_rates[fac]
        for fac in factories
        if fac not in holdouts
    ]
    typical_median_error = np.median(non_holdout_error)
    typical_std_error = np.std(non_holdout_error)

    # Store standard deviations above the typical dataset median
    for fac in factories:
        if typical_std_error > 0:
            results[fac]['data_integrity'] = (raw_error_rates[fac] - typical_median_error) / typical_std_error
        else:
            results[fac]['data_integrity'] = 0.0

    # -------------------------------------------------------------
    # Flagging triggers & aggregating
    # -------------------------------------------------------------
    print("Aggregating scores and flagging triggers...")
    final_rows = []
    for fac in factories:
        r = results[fac]
        
        # Trigger definitions:
        # 1. IMPOSSIBLE_PH_RANGE: > 0%
        trig_ph = 1 if r['impossible_ph_range'] > 0 else 0
        
        # 2. INSPECTION_DIP: Average percent difference < -20.0%
        trig_dip = 1 if (not np.isnan(r['inspection_dip']) and r['inspection_dip'] < -20.0) else 0
        
        # 3. FLATLINE: > 5.0%
        trig_flat = 1 if r['flatline'] > 5.0 else 0
        
        # 4. LIMIT_HUGGING: > 5.0%
        trig_hug = 1 if r['limit_hugging'] > 5.0 else 0
        
        # 5. CORRELATION_BREAK: drops meaningfully below the typical range
        trig_corr = 0
        if not np.isnan(r['correlation_break']):
            if r['correlation_break'] < corr_threshold:
                trig_corr = 1
                
        # 6. COPY_PASTE: > 1.0%
        trig_copy = 1 if r['copy_paste'] > 1.0 else 0
        
        # 7. COORDINATED_MISSING_DATA: > 1.5 standard deviations above the median
        trig_missing = 1 if r['coordinated_missing_data'] > 1.5 else 0

        # 8. DATA_INTEGRITY: > 1.5 standard deviations above the median error rate
        trig_integrity = 1 if r['data_integrity'] > 1.5 else 0

        total_triggered = (
            trig_ph + trig_dip + trig_flat + trig_hug + trig_corr +
            trig_copy + trig_missing + trig_integrity
        )

        final_rows.append({
            'factory_id': fac,
            'impossible_ph_range': r['impossible_ph_range'],
            'inspection_dip': r['inspection_dip'],
            'flatline': r['flatline'],
            'limit_hugging': r['limit_hugging'],
            'correlation_break': r['correlation_break'],
            'copy_paste': r['copy_paste'],
            'coordinated_missing_data': r['coordinated_missing_data'],
            'data_integrity': r['data_integrity'],
            # QC FIX: the raw values above are magnitudes/percentages/z-scores on
            # completely different scales -- a downstream reader can't safely turn
            # them into a yes/no trigger decision without redoing the thresholding
            # logic above (which is what calculate_composite_risk() used to do
            # badly, via a naive "value > 0" check). Save the actual 0/1 decisions
            # this script already computed correctly, so downstream code just
            # reads the answer instead of re-guessing it.
            'trig_impossible_ph_range': trig_ph,
            'trig_inspection_dip': trig_dip,
            'trig_flatline': trig_flat,
            'trig_limit_hugging': trig_hug,
            'trig_correlation_break': trig_corr,
            'trig_copy_paste': trig_copy,
            'trig_coordinated_missing_data': trig_missing,
            'trig_data_integrity': trig_integrity,
            'total_fingerprints_triggered': total_triggered
        })
        
    final_df = pd.DataFrame(final_rows)
    
    # Save output
    output_dir = "Data/RawData"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "factory_fingerprint_scores.csv")
    final_df.to_csv(output_path, index=False)
    print(f"Saved fingerprint scores to {output_path}")
    
    # Print threshold and logic documentation
    print("\n==========================================================================")
    print("FINGERPRINT TRIGGER CRITERIA & THRESHOLDS:")
    print("==========================================================================")
    print(f"1. IMPOSSIBLE_PH_RANGE: Triggered if score > 0.0% (any reading < 0, > 14, or violating CTO limits)")
    print(f"2. INSPECTION_DIP: Triggered if average pre-inspection % drop < -20.0%")
    print(f"3. FLATLINE: Triggered if score > 5.0%")
    print(f"4. LIMIT_HUGGING: Triggered if score > 5.0%")
    print(f"5. CORRELATION_BREAK: Triggered if average correlation < {corr_threshold:.4f} (typical mean - 1.0 * typical std)")
    print(f"6. COPY_PASTE: Triggered if score > 1.0% (fraction of readings with autocorrelation > 0.95)")
    print(f"7. COORDINATED_MISSING_DATA: Triggered if score > 1.5 (deviations above dataset median missing rate)")
    print(f"8. DATA_INTEGRITY: Triggered if score > 1.5 (deviations above dataset median Error/Out-of-Range rate)")
    print("==========================================================================\n")
    
    # Sort and print
    sorted_df = final_df.sort_values(by='total_fingerprints_triggered', ascending=False)
    print("\nFull table sorted by total fingerprints triggered descending:")
    print(sorted_df.to_string(index=False))

if __name__ == "__main__":
    main()
