import pandas as pd
import numpy as np
import warnings


def get_window_periods(window_str: str) -> int:
    """
    Computes the number of 15-minute periods in a window string.
    """
    td = pd.to_timedelta(window_str.replace('H', 'h'))
    return int(td / pd.Timedelta(minutes=15))



def compute_rolling_stats(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Computes rolling mean, std and coefficient of variation.

    NOTE:
    These statistics intentionally use every remaining row
    (Raw + L) after the loader filter.

    Only flatline has special handling for L rows.
    """

    w_size = get_window_periods(
        config["windows"]["flatline_window"]
    )

    df_sorted = df.sort_values(
        ["factory_id", "parameter_id", "timestamp"]
    )

    means = []
    stds = []
    covs = []

    for (_, _), group in df_sorted.groupby(
        ["factory_id", "parameter_id"]
    ):

        s = group["value"]

        roll = s.rolling(
            window=w_size,
            min_periods=w_size
        )

        m = roll.mean()

        st = roll.std()

        m_abs = m.abs()
        cv = np.where(m_abs < 1e-6, np.nan, st / m_abs)
        cv = np.where(cv > 10.0, np.nan, cv)

        cv = pd.Series(cv, index=group.index).replace(
            [np.inf, -np.inf],
            np.nan
        )

        means.append(m)
        stds.append(st)
        covs.append(cv)

    stats_df = pd.DataFrame({

        "rolling_mean": pd.concat(means),

        "rolling_std": pd.concat(stds),

        "rolling_cov": pd.concat(covs)

    }).reindex(df_sorted.index)

    return stats_df


def compute_flatline_flag(
    df: pd.DataFrame,
    config: dict
) -> pd.Series:
    """
    QC FIX

    Rolling window still spans the last N timestamps.

    Real dataset:
        - L rows count toward timestamp coverage.
        - L rows are excluded from the std calculation.

    Synthetic dataset:
        - Uses all values (no quality_code exists).

    If fewer than 2 Raw observations remain
    (real dataset), output NaN.
    """

    w_size = get_window_periods(
        config["windows"]["flatline_window"]
    )

    threshold = config["windows"][
        "flatline_std_threshold"
    ]

    df_sorted = df.sort_values(
        ["factory_id", "parameter_id", "timestamp"]
    )

    all_flags = []

    for (_, _), group in df_sorted.groupby(
        ["factory_id", "parameter_id"]
    ):

        values = group["value"].to_numpy()

        result = np.full(
            len(group),
            np.nan,
            dtype=float
        )

        # -----------------------------------------
        # REAL DATASET
        # -----------------------------------------
        if "quality_code" in group.columns:

            quality = group["quality_code"].to_numpy()

            for i in range(w_size - 1, len(group)):

                start = i - w_size + 1

                window_values = values[start:i + 1]
                window_quality = quality[start:i + 1]

                raw_values = window_values[
                    window_quality == "Raw"
                ]

                # QC Option B
                if len(raw_values) < 2:
                    continue

                std = np.std(
                    raw_values,
                    ddof=1
                )

                result[i] = float(
                    std <= 0.0 if threshold == 0 else (std < threshold or std == 0.0)
                )

        # -----------------------------------------
        # SYNTHETIC DATASET
        # -----------------------------------------
        else:

            for i in range(w_size - 1, len(group)):

                start = i - w_size + 1

                window = values[start:i + 1]

                std = np.std(
                    window,
                    ddof=1
                )

                result[i] = float(
                    std <= 0.0 if threshold == 0 else (std < threshold or std == 0.0)
                )

        # -----------------------------------------
        # Append ONCE per group
        # -----------------------------------------
        all_flags.append(
            pd.Series(
                result,
                index=group.index
            )
        )

    flatline = (
        pd.concat(all_flags)
        .reindex(df_sorted.index)
    )

    return pd.Series(
        flatline,
        index=df_sorted.index,
        name="flatline_flag"
    )



def compute_rolling_correlation(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Computes rolling Pearson correlation between available parameter pairs
    per factory using the configured correlation window.

    No QC changes required.
    """

    w_str = config["windows"]["correlation_window"]
    w_size = get_window_periods(w_str)

    # Pivot into wide format
    wide_df = df.pivot(
        index=["factory_id", "timestamp"],
        columns="parameter_id",
        values="value"
    )

    corr_frames = []

    for factory_id, group in wide_df.groupby("factory_id"):

        available_params = [
            col
            for col in group.columns
            if not group[col].isna().all()
        ]

        factory_corr = pd.DataFrame(index=group.index)

        for i in range(len(available_params)):
            for j in range(i + 1, len(available_params)):

                p1 = available_params[i]
                p2 = available_params[j]

                col_name = f"corr_{p1}_{p2}"

                s1 = group[p1]
                s2 = group[p2]

                s1_std = s1.rolling(window=w_size, min_periods=w_size).std()
                s2_std = s2.rolling(window=w_size, min_periods=w_size).std()

                corr = (
                    s1
                    .rolling(
                        window=w_size,
                        min_periods=w_size
                    )
                    .corr(s2)
                )

                # Zero-guard: if either rolling std is 0 or < 1e-9, set correlation to NaN
                corr_guarded = np.where((s1_std < 1e-9) | (s2_std < 1e-9), np.nan, corr)
                # Ensure no infs are left
                corr_guarded = pd.Series(corr_guarded, index=group.index).replace([np.inf, -np.inf], np.nan)

                factory_corr[col_name] = corr_guarded

        corr_frames.append(factory_corr)

    if corr_frames:
        return pd.concat(corr_frames)

    return pd.DataFrame(index=wide_df.index)


def compute_autocorrelation(
    df: pd.DataFrame,
    config: dict
) -> pd.Series:
    """
    Computes lag-based rolling autocorrelation.

    QC FIX:
    Prevent inf / -inf values caused by
    zero-variance rolling windows.
    """

    lag = config["windows"]["autocorr_lag"]

    w_str = config["windows"]["correlation_window"]

    w_size = get_window_periods(w_str)

    df_sorted = df.sort_values(
        ["factory_id", "parameter_id", "timestamp"]
    )

    autocorr_list = []

    for (_, _), group in df_sorted.groupby(
        ["factory_id", "parameter_id"]
    ):

        values = group["value"]

        shifted = values.shift(lag)

        autocorr = values.rolling(
            window=w_size,
            min_periods=w_size
        ).corr(shifted)

        # -----------------------------
        # QC FIX
        # -----------------------------

        autocorr = autocorr.replace(
            [np.inf, -np.inf],
            np.nan
        )

        autocorr_list.append(autocorr)

    autocorr_all = (
        pd.concat(autocorr_list)
        .reindex(df_sorted.index)
    )

    return pd.Series(
        autocorr_all,
        index=df_sorted.index,
        name="autocorrelation"
    )


def compute_missing_rate(
    df: pd.DataFrame,
    config: dict
) -> pd.Series:
    """
    Computes rolling percentage of missing values.

    L readings are retained in the dataset but are not
    considered missing. Only actual NaN values contribute
    to the missing rate.
    """

    w_str = config["windows"]["missing_rate_window"]
    w_size = get_window_periods(w_str)

    df_sorted = df.sort_values(
        ["factory_id", "parameter_id", "timestamp"]
    )

    rates = []

    for (_, _), group in df_sorted.groupby(
        ["factory_id", "parameter_id"]
    ):

        missing = group["value"].isna().astype(float)

        rate = (
            missing
            .rolling(
                window=w_size,
                min_periods=w_size
            )
            .mean()
            * 100
        )

        rates.append(rate)

    missing_rate = (
        pd.concat(rates)
        .reindex(df_sorted.index)
    )

    return pd.Series(
        missing_rate,
        index=df_sorted.index,
        name="missing_rate"
    )
    
    
def compute_limit_hugging(
    df: pd.DataFrame,
    limits_df: pd.DataFrame,
    config: dict
) -> pd.Series:
    """
    Computes whether a reading lies within the configured percentage
    of either the lower or upper CTO limit.
    """

    pct = config["windows"]["limit_hugging_pct"]

    # Map raw parameter names to standard ETP parameter IDs
    limits = limits_df.copy()

    def map_raw_parameter_to_standard(param_name: str) -> str:
        if not isinstance(param_name, str):
            return None
        param_name_lower = param_name.lower().strip()
        if "ph value" in param_name_lower or param_name_lower == "ph":
            return "ETP-pH"
        if "trade effluent" in param_name_lower or "flow" in param_name_lower:
            return "ETP-Flow"
        if "bod" in param_name_lower:
            return "ETP-BOD"
        if "cod" in param_name_lower:
            return "ETP-COD"
        if "tss" in param_name_lower or "suspended solid" in param_name_lower:
            return "ETP-TSS"
        return None

    limits["parameter_id"] = limits["parameter_id"].apply(map_raw_parameter_to_standard)
    limits = limits[limits["parameter_id"].notna()]
    
    # Filter out proxy limits and non-positive limits
    limits = limits[limits["proxy_source_factory_id"].isna()]
    limits = limits[limits["upper_limit"] > 0.0]
    
    # Deduplicate limits per factory and parameter, keeping highest extraction_confidence
    limits = limits.sort_values("extraction_confidence", ascending=False)
    limits = limits.drop_duplicates(subset=["factory_id", "parameter_id"], keep="first")

    # Merge on both factory_id and parameter_id
    df = df.merge(
        limits[["factory_id", "parameter_id", "lower_limit", "upper_limit"]],
        on=["factory_id", "parameter_id"],
        how="left"
    )

    upper_limit = df["upper_limit"]
    lower_limit = df["lower_limit"]

    # Upper hugging: value between (1 - pct) * upper_limit and upper_limit (inclusive)
    upper_hugging = (df["value"] >= (1 - pct) * upper_limit) & (df["value"] <= upper_limit)

    # Lower hugging: only when lower_limit is defined, value between lower_limit and lower_limit + (upper_limit - lower_limit) * pct (inclusive)
    lower_hugging = pd.Series(False, index=df.index)
    has_lower = lower_limit.notna()
    lower_hugging.loc[has_lower] = (df["value"].loc[has_lower] >= lower_limit.loc[has_lower]) & \
                                   (df["value"].loc[has_lower] <= lower_limit.loc[has_lower] + (upper_limit.loc[has_lower] - lower_limit.loc[has_lower]) * pct)

    hugging = upper_hugging | lower_hugging

    # Return NaN where limits do not exist
    hugging_result = np.where(df["upper_limit"].notna(), hugging.astype(float), np.nan)

    return pd.Series(
        hugging_result,
        index=df.index,
        name="limit_hugging"
    )


def compute_bdl_rate(
    df: pd.DataFrame,
    config: dict
) -> pd.Series:
    """
    Computes rolling percentage of BDL (Below Detection Limit) values.
    BDL values are identified where quality_code == 'L'.
    Window logic matches missing_rate.
    """
    w_str = config["windows"]["missing_rate_window"]
    w_size = get_window_periods(w_str)

    df_sorted = df.sort_values(
        ["factory_id", "parameter_id", "timestamp"]
    )

    rates = []

    for (_, _), group in df_sorted.groupby(
        ["factory_id", "parameter_id"]
    ):
        if "quality_code" in group.columns:
            is_bdl = (group["quality_code"] == "L").astype(float)
        else:
            is_bdl = pd.Series(0.0, index=group.index)

        rate = (
            is_bdl
            .rolling(
                window=w_size,
                min_periods=w_size
            )
            .mean()
            * 100.0
        )

        rates.append(rate)

    bdl_rate = (
        pd.concat(rates)
        .reindex(df_sorted.index)
    )

    return pd.Series(
        bdl_rate,
        index=df_sorted.index,
        name="bdl_rate"
    )


def compute_duplicate_run_length(
    df: pd.DataFrame
) -> pd.Series:
    """
    Computes the length of current exact-duplicate-value run per row per factory/parameter.
    Resets to 1 whenever value changes.
    """
    df_sorted = df.sort_values(
        ["factory_id", "parameter_id", "timestamp"]
    )

    all_lengths = []

    for (_, _), group in df_sorted.groupby(
        ["factory_id", "parameter_id"]
    ):
        vals = group["value"].to_numpy()
        n = len(vals)
        lengths = np.ones(n, dtype=float)

        for i in range(1, n):
            v_curr = vals[i]
            v_prev = vals[i - 1]
            if pd.notna(v_curr) and pd.notna(v_prev) and (v_curr == v_prev):
                lengths[i] = lengths[i - 1] + 1.0
            else:
                lengths[i] = 1.0

        all_lengths.append(
            pd.Series(
                lengths,
                index=group.index
            )
        )

    duplicate_run_length = (
        pd.concat(all_lengths)
        .reindex(df_sorted.index)
    )

    return pd.Series(
        duplicate_run_length,
        index=df_sorted.index,
        name="duplicate_run_length"
    )


def compute_cov_severity(
    df: pd.DataFrame
) -> pd.Series:
    """
    Computes graded severity tiers ('none', 'low', 'medium', 'high') of rolling_cov vs factory-param baseline.
    """
    df_sorted = df.sort_values(
        ["factory_id", "parameter_id", "timestamp"]
    )

    all_severities = []

    for (_, _), group in df_sorted.groupby(
        ["factory_id", "parameter_id"]
    ):
        cov = group["rolling_cov"].to_numpy()
        flatline = group["flatline_flag"].to_numpy() if "flatline_flag" in group.columns else np.zeros(len(group))
        valid_cov = cov[~np.isnan(cov)]

        if len(valid_cov) == 0 or np.nanmedian(valid_cov) <= 0:
            baseline = 1e-6
        else:
            baseline = float(np.nanmedian(valid_cov))

        ratio = cov / baseline
        result = np.full(len(group), np.nan, dtype=object)

        for i in range(len(group)):
            if flatline[i] == 1.0:
                result[i] = "high"
            elif np.isnan(cov[i]):
                result[i] = np.nan
            elif ratio[i] <= 0.1 or ratio[i] >= 6.0:
                result[i] = "high"
            elif ratio[i] <= 0.25 or ratio[i] >= 3.0:
                result[i] = "medium"
            elif ratio[i] <= 0.5 or ratio[i] >= 1.5:
                result[i] = "low"
            else:
                result[i] = "none"

        all_severities.append(
            pd.Series(
                result,
                index=group.index,
                dtype=object
            )
        )

    cov_severity = (
        pd.concat(all_severities)
        .reindex(df_sorted.index)
    )

    return pd.Series(
        cov_severity,
        index=df_sorted.index,
        name="cov_severity"
    )


def compute_bod_cod_ratio_and_volatility(
    df: pd.DataFrame,
    config: dict
) -> pd.DataFrame:
    """
    Pivots BOD/COD to align by (factory_id, timestamp), computes BOD/COD ratio (guarded against div-by-~0),
    and computes rolling 7-day std as volatility. Joins back to long format (NaN for non-BOD/COD rows).
    """
    w_str = config["windows"]["missing_rate_window"]
    w_size = get_window_periods(w_str)

    bod_cod_df = df[df["parameter_id"].isin(["ETP-BOD", "ETP-COD"])]

    if bod_cod_df.empty:
        res = pd.DataFrame(index=df.index)
        res["bod_cod_ratio"] = np.nan
        res["bod_cod_ratio_volatility"] = np.nan
        return res

    piv = bod_cod_df.pivot(
        index=["factory_id", "timestamp"],
        columns="parameter_id",
        values="value"
    )

    for c in ["ETP-BOD", "ETP-COD"]:
        if c not in piv.columns:
            piv[c] = np.nan

    bod = piv["ETP-BOD"]
    cod = piv["ETP-COD"]

    ratio = np.where(
        (cod.isna()) | (bod.isna()) | (cod <= 1e-6),
        np.nan,
        bod / cod
    )
    ratio = pd.Series(ratio, index=piv.index).replace([np.inf, -np.inf], np.nan)

    vols = []
    piv["ratio"] = ratio
    for fac_id, grp in piv.groupby("factory_id"):
        vol = grp["ratio"].rolling(window=w_size, min_periods=w_size).std()
        vol = vol.replace([np.inf, -np.inf], np.nan)
        vols.append(vol)

    volatility = pd.concat(vols) if vols else pd.Series(np.nan, index=piv.index)

    ratio_df = pd.DataFrame({
        "bod_cod_ratio": ratio,
        "bod_cod_ratio_volatility": volatility
    }, index=piv.index).reset_index()

    merged = df[["factory_id", "parameter_id", "timestamp"]].merge(
        ratio_df,
        on=["factory_id", "timestamp"],
        how="left"
    )

    is_bod_cod = df["parameter_id"].isin(["ETP-BOD", "ETP-COD"]).values
    merged.loc[~is_bod_cod, "bod_cod_ratio"] = np.nan
    merged.loc[~is_bod_cod, "bod_cod_ratio_volatility"] = np.nan

    merged.index = df.index
    return merged[["bod_cod_ratio", "bod_cod_ratio_volatility"]]


def assemble_feature_matrix(
    raw_df: pd.DataFrame,
    limits_df: pd.DataFrame,
    config: dict
) -> pd.DataFrame:
    """
    Builds the complete feature matrix used for downstream
    ML training.
    """

    df = raw_df.copy()

    # -----------------------------
    # Rolling statistics
    # -----------------------------

    rolling_stats = compute_rolling_stats(
        df,
        config
    )

    df = pd.concat(
        [df, rolling_stats],
        axis=1
    )

    # -----------------------------
    # Flatline detection
    # -----------------------------

    df["flatline_flag"] = compute_flatline_flag(
        df,
        config
    )

    # -----------------------------
    # Rolling correlations
    # -----------------------------

    correlation_df = compute_rolling_correlation(
        df,
        config
    )

    df = df.merge(
        correlation_df,
        left_on=["factory_id", "timestamp"],
        right_index=True,
        how="left"
    )

    # -----------------------------
    # Autocorrelation
    # -----------------------------

    df["autocorrelation"] = compute_autocorrelation(
        df,
        config
    )

    # -----------------------------
    # Missing rate & BDL rate
    # -----------------------------

    df["missing_rate"] = compute_missing_rate(
        df,
        config
    )

    df["bdl_rate"] = compute_bdl_rate(
        df,
        config
    )

    # -----------------------------
    # Duplicate run length
    # -----------------------------

    df["duplicate_run_length"] = compute_duplicate_run_length(
        df
    )

    # -----------------------------
    # CoV severity
    # -----------------------------

    df["cov_severity"] = compute_cov_severity(
        df
    )

    # -----------------------------
    # BOD/COD ratio & volatility
    # -----------------------------

    bod_cod_features = compute_bod_cod_ratio_and_volatility(
        df,
        config
    )

    df["bod_cod_ratio"] = bod_cod_features["bod_cod_ratio"]
    df["bod_cod_ratio_volatility"] = bod_cod_features["bod_cod_ratio_volatility"]

    # -----------------------------
    # Limit hugging
    # -----------------------------

    df["limit_hugging"] = compute_limit_hugging(
        df,
        limits_df,
        config
    )

    return df