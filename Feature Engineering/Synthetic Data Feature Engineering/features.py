import pandas as pd
import numpy as np
import warnings


def get_window_periods(window_str: str) -> int:
    """
    Computes the number of 15-minute periods in a window string.
    """
    td = pd.to_timedelta(window_str)
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

        cv = st / m

        cv = cv.replace(
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
                    std < threshold
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
                    std < threshold
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

                factory_corr[col_name] = (
                    group[p1]
                    .rolling(
                        window=w_size,
                        min_periods=w_size
                    )
                    .corr(group[p2])
                )

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

    w_str = config["windows"]["missing_rate_window"]

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

    df = df.merge(
        limits_df,
        on="parameter_id",
        how="left"
    )

    lower_threshold = (
        df["lower_limit"] +
        (df["upper_limit"] - df["lower_limit"]) * pct
    )

    upper_threshold = (
        df["upper_limit"] -
        (df["upper_limit"] - df["lower_limit"]) * pct
    )

    hugging = (
        (df["value"] <= lower_threshold) |
        (df["value"] >= upper_threshold)
    )

    return pd.Series(
        hugging.astype(float),
        index=df.index,
        name="limit_hugging"
    )


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
    # Missing rate
    # -----------------------------

    df["missing_rate"] = compute_missing_rate(
        df,
        config
    )

    # -----------------------------
    # Limit hugging
    # -----------------------------

    df["limit_hugging"] = compute_limit_hugging(
        df,
        limits_df,
        config
    )

    return df