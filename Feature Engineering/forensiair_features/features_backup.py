import pandas as pd
import numpy as np
import warnings

def get_window_periods(window_str: str) -> int:
    """
    Computes the number of periods of 15 minutes corresponding to the given window string.
    """
    td = pd.to_timedelta(window_str)
    return int(td / pd.Timedelta(minutes=15))

def compute_rolling_stats(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Computes rolling mean, rolling std, and coefficient of variation (CoV)
    per factory_id + parameter_id at flatline_window.
    """
    w_str = config['windows']['flatline_window']
    w_size = get_window_periods(w_str)
    
    df_sorted = df.sort_values(['factory_id', 'parameter_id', 'timestamp'])
    
    means = []
    stds = []
    covs = []
    
    for (fac_id, param_id), group in df_sorted.groupby(['factory_id', 'parameter_id']):
        s = group['value']
        roll = s.rolling(window=w_size, min_periods=w_size)
        m = roll.mean()
        st = roll.std()
        cv = st / m
        cv = cv.replace([np.inf, -np.inf], np.nan)
        
        means.append(m)
        stds.append(st)
        covs.append(cv)
        
    stats_df = pd.DataFrame({
        'rolling_mean': pd.concat(means),
        'rolling_std': pd.concat(stds),
        'rolling_cov': pd.concat(covs)
    }).reindex(df_sorted.index)
    
    return stats_df

def compute_flatline_flag(df: pd.DataFrame, config: dict) -> pd.Series:
    """
    Flag runs where rolling std < flatline_std_threshold.
    Excludes is_valid==False (NaN) rows from the calculation.
    """
    w_str = config['windows']['flatline_window']
    w_size = get_window_periods(w_str)
    threshold = config['windows']['flatline_std_threshold']
    
    df_sorted = df.sort_values(['factory_id', 'parameter_id', 'timestamp'])
    
    flags = []
    for (fac_id, param_id), group in df_sorted.groupby(['factory_id', 'parameter_id']):
        s = group['value']
        st = s.rolling(window=w_size, min_periods=w_size).std()
        flag = np.where(st.isna(), np.nan, (st < threshold).astype(float))
        flags.append(pd.Series(flag, index=group.index))
        
    flatline_flag = pd.concat(flags).reindex(df_sorted.index)
    return pd.Series(flatline_flag, index=df_sorted.index, name='flatline_flag')

def compute_rolling_correlation(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Computes rolling Pearson correlation between available parameter pairs
    at correlation_window, computed per factory_id.
    """
    w_str = config['windows']['correlation_window']
    w_size = get_window_periods(w_str)
    
    # Pivot to wide format
    wide_df = df.pivot(index=['factory_id', 'timestamp'], columns='parameter_id', values='value')
    
    corr_dfs = []
    # Group by factory_id
    for fac_id, group in wide_df.groupby('factory_id'):
        cols = [c for c in group.columns if not group[c].isna().all()]
        pairs = []
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                pairs.append(sorted([cols[i], cols[j]]))
        
        pairs = sorted(list(set(tuple(p) for p in pairs)))
        
        fac_corr = pd.DataFrame(index=group.index)
        for p1, p2 in pairs:
            col_name = f"corr_{p1}_{p2}"
            s1 = group[p1]
            s2 = group[p2]
            r_corr = s1.rolling(window=w_size, min_periods=w_size).corr(s2)
            fac_corr[col_name] = r_corr
            
        corr_dfs.append(fac_corr)
        
    if len(corr_dfs) > 0:
        all_corr_df = pd.concat(corr_dfs)
    else:
        all_corr_df = pd.DataFrame(index=wide_df.index)
        
    return all_corr_df

def compute_autocorrelation(df: pd.DataFrame, config: dict) -> pd.Series:
    """
    Computes lag-96 autocorrelation per factory+parameter over a trailing 7-day window.
    """
    lag = config['windows']['autocorr_lag']
    w_str = config['windows']['missing_rate_window']
    w_size = get_window_periods(w_str)
    
    df_sorted = df.sort_values(['factory_id', 'parameter_id', 'timestamp'])
    
    autocorr_list = []
    for (fac_id, param_id), group in df_sorted.groupby(['factory_id', 'parameter_id']):
        s = group['value']
        s_shifted = s.shift(lag)
        r_corr = s.rolling(window=w_size, min_periods=w_size).corr(s_shifted)
        autocorr_list.append(r_corr)
        
    autocorr_all = pd.concat(autocorr_list).reindex(df_sorted.index)
    return pd.Series(autocorr_all, index=df_sorted.index, name='autocorrelation')

def compute_missing_rate(df: pd.DataFrame, config: dict) -> pd.Series:
    """
    Computes rolling percentage of is_valid==False over missing_rate_window.
    """
    w_str = config['windows']['missing_rate_window']
    w_size = get_window_periods(w_str)
    
    df_sorted = df.sort_values(['factory_id', 'parameter_id', 'timestamp'])
    
    rates = []
    for (fac_id, param_id), group in df_sorted.groupby(['factory_id', 'parameter_id']):
        is_missing = (~group['is_valid']).astype(float)
        rate = is_missing.rolling(window=w_size, min_periods=w_size).mean() * 100
        rates.append(rate)
        
    missing_rate = pd.concat(rates).reindex(df_sorted.index)
    return pd.Series(missing_rate, index=df_sorted.index, name='missing_rate')

def compute_limit_hugging(df: pd.DataFrame, cto_limits_df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Computes distance-to-limit ratio and limit hugging flag.
    If cto_limits_df is None, skips gracefully and returns NaNs.
    """
    features = pd.DataFrame(index=df.index)
    features['limit_ratio_max'] = np.nan
    features['limit_ratio_min'] = np.nan
    features['limit_hugging_max'] = np.nan
    features['limit_hugging_min'] = np.nan
    
    if cto_limits_df is None:
        warnings.warn("CTO limits not provided, limit_hugging features skipped")
        return features
        
    pct = config['windows'].get('limit_hugging_pct', 0.05)
    
    map_rules = {
        'ETP-pH': ['pH', 'pH Value'],
        'ETP-Flow': ['Trade effluent'],
        'ETP-BOD': ['BOD 3 days 27oC', 'BOD mg/l', 'BOD (3 days 27oC )', 'BOD (3 days 27°C)', 'BOD (3 days 27°C)', 'BOD (3 days 27ºC)', 'BOD (3 days 27ºC)'],
        'ETP-COD': ['COD', 'COD mg/l'],
        'ETP-TSS': ['TSS', 'Total Suspended solids', 'Suspended Solids', 'Suspended Solid mg/l', 'Total Suspended solid (TSS)']
    }
    
    # Pre-calculate limits per (factory_id, parameter_id)
    limits_map = {}
    for (f_id, p_id), grp in df.groupby(['factory_id', 'parameter_id']):
        sub = cto_limits_df[cto_limits_df['factory_id'] == f_id]
        max_lim = np.nan
        min_lim = np.nan
        
        if len(sub) > 0:
            names = map_rules.get(p_id, [p_id])
            matched = sub[sub['parameter'].str.contains('|'.join(names), case=False, na=False)]
            if len(matched) == 0:
                part = p_id.split('-')[1] if '-' in p_id else p_id
                matched = sub[sub['parameter'].str.contains(part, case=False, na=False)]
            
            if len(matched) > 0:
                row = matched.sort_values(by='extraction_confidence', ascending=False).iloc[0]
                max_lim = row.get('maximum_limit', np.nan)
                min_lim = row.get('minimum_limit', np.nan)
                
        limits_map[(f_id, p_id)] = (min_lim, max_lim)
        
    keys = list(zip(df['factory_id'], df['parameter_id']))
    limits_vals = [limits_map.get(k, (np.nan, np.nan)) for k in keys]
    min_lims = np.array([v[0] for v in limits_vals])
    max_lims = np.array([v[1] for v in limits_vals])
    
    vals = df['value'].values
    
    features['limit_ratio_max'] = np.where(pd.notna(max_lims) & (max_lims > 0), vals / max_lims, np.nan)
    features['limit_ratio_min'] = np.where(pd.notna(min_lims) & (min_lims > 0), vals / min_lims, np.nan)
    
    features['limit_hugging_max'] = np.where(
        pd.notna(max_lims) & (max_lims > 0),
        (vals >= (1 - pct) * max_lims) & (vals <= max_lims),
        np.nan
    ).astype(float)
    
    features['limit_hugging_min'] = np.where(
        pd.notna(min_lims) & (min_lims > 0),
        (vals <= (1 + pct) * min_lims) & (vals >= min_lims),
        np.nan
    ).astype(float)
    
    return features

def assemble_feature_matrix(df: pd.DataFrame, config: dict, cto_limits_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Assembles all individual feature series/dataframes into a single unified wide DataFrame.
    """
    stats = compute_rolling_stats(df, config)
    flatline = compute_flatline_flag(df, config)
    autocorr = compute_autocorrelation(df, config)
    missing = compute_missing_rate(df, config)
    limit_hugging = compute_limit_hugging(df, cto_limits_df, config)
    corr = compute_rolling_correlation(df, config)
    
    feature_matrix = pd.concat([
        df[['factory_id', 'parameter_id', 'timestamp', 'value', 'is_valid']],
        stats,
        flatline,
        autocorr,
        missing,
        limit_hugging
    ], axis=1)
    
    feature_matrix = feature_matrix.merge(corr, on=['factory_id', 'timestamp'], how='left')
    
    # Sort for deterministic output
    feature_matrix = feature_matrix.sort_values(by=['factory_id', 'parameter_id', 'timestamp']).reset_index(drop=True)
    return feature_matrix
