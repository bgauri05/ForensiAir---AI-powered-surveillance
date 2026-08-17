# import pandas as pd


# def load_raw(monitoring_csv_path: str) -> pd.DataFrame:
#     """
#     Load raw OCEMS telemetry data.
#     """

#     print(f"\nReading telemetry: {monitoring_csv_path}")

#     df = pd.read_csv(monitoring_csv_path)

#     print(f"Rows loaded : {len(df):,}")

#     # -----------------------------
#     # Parse timestamps
#     # -----------------------------

#     df["timestamp"] = pd.to_datetime(
#         df["timestamp"],
#         format="%Y-%m-%d %H:%M:%S",
#         errors="coerce"
#     )

#     nat_count = df["timestamp"].isna().sum()

#     print(f"Invalid timestamps : {nat_count:,}")

#     if nat_count > 0:
#         print("\nExample bad timestamp values:")
#         print(
#             df.loc[
#                 df["timestamp"].isna(),
#                 ["factory_id", "parameter_id", "timestamp"]
#             ].head(20)
#         )

#         raise ValueError(
#             f"{nat_count:,} timestamps could not be parsed."
#         )

#     # -----------------------------
#     # Data types
#     # -----------------------------

#     df["factory_id"] = df["factory_id"].astype("string")
#     df["parameter_id"] = df["parameter_id"].astype("string")
#     df["value"] = pd.to_numeric(df["value"], errors="coerce")

#     df["is_valid"] = df["value"].notna()

#     # -----------------------------
#     # Sort
#     # -----------------------------

#     df = (
#         df.sort_values(
#             ["factory_id", "parameter_id", "timestamp"]
#         )
#         .reset_index(drop=True)
#     )

#     return df[
#         [
#             "factory_id",
#             "parameter_id",
#             "timestamp",
#             "value",
#             "is_valid"
#         ]
#     ]


# def load_cto_limits(cto_csv_path: str) -> pd.DataFrame:
#     """
#     Load CTO consent limits.
#     """

#     cto_df = pd.read_csv(cto_csv_path)

#     required_columns = [
#         "factory_id",
#         "parameter",
#         "minimum_limit",
#         "maximum_limit"
#     ]

#     missing = [
#         col
#         for col in required_columns
#         if col not in cto_df.columns
#     ]

#     if missing:
#         raise ValueError(
#             f"Missing required columns in consent_limits.csv: {missing}"
#         )

#     return cto_df



import pandas as pd


def load_raw(monitoring_csv_path: str):
    """
    Load raw OCEMS telemetry data.
    Applies quality-code filtering before feature computation.

    Keeps:
        - Raw
        - L

    Drops:
        - Error
        - Out of Range

    QC FIX (2026-08):
    This filter used to drop Error/Out of Range rows silently, with only
    an aggregate "rows after filter" count printed. In practice the loss
    is extremely concentrated in a handful of factories (e.g. site_1138
    loses 99.9% of its rows here) instead of spread evenly, which was
    invisible before. This now:
      1. Prints a per-factory breakdown for any factory losing >5% of
         its rows, so concentrated loss can't go unnoticed again.
      2. Returns a per-factory quality report (including an `error_rate`
         column) alongside the telemetry data, so a factory's error
         rate can be carried through as a feature in its own right --
         an unusually high rate of Error-tagged readings may itself be
         a tampering signal, not just noise to discard.

    Returns:
        (telemetry_df, quality_report_df)
    """

    print(f"\nReading telemetry: {monitoring_csv_path}")

    df = pd.read_csv(monitoring_csv_path)

    print(f"Rows loaded : {len(df):,}")

    # -----------------------------
    # Per-factory quality-code breakdown (computed BEFORE filtering
    # so the loss is visible, not silent)
    # -----------------------------

    allowed_quality_codes = ["Raw", "L"]

    dropped_mask = ~df["quality_code"].isin(allowed_quality_codes)

    total_by_factory = (
        df.groupby("factory_id").size().rename("total_rows")
    )
    dropped_by_factory = (
        df[dropped_mask].groupby("factory_id").size().rename("dropped_rows")
    )

    quality_report = pd.concat(
        [total_by_factory, dropped_by_factory], axis=1
    ).fillna(0)
    quality_report["dropped_rows"] = quality_report["dropped_rows"].astype(int)
    quality_report["kept_rows"] = (
        quality_report["total_rows"] - quality_report["dropped_rows"]
    )
    quality_report["error_rate"] = (
        quality_report["dropped_rows"] / quality_report["total_rows"]
    ).round(4)
    quality_report = quality_report.reset_index().rename(
        columns={"index": "factory_id"}
    )
    quality_report = quality_report.sort_values(
        "error_rate", ascending=False
    ).reset_index(drop=True)

    print(
        f"\nQuality-code filter: {dropped_mask.sum():,} of {len(df):,} "
        f"rows tagged Error/Out of Range will be dropped."
    )

    flagged = quality_report[quality_report["error_rate"] > 0.05]
    if len(flagged) > 0:
        print(f"Factories losing >5% of rows to this filter ({len(flagged)}):")
        for _, r in flagged.iterrows():
            print(
                f"  {r['factory_id']:<12} {r['error_rate'] * 100:6.2f}% dropped "
                f" ({int(r['dropped_rows']):,} / {int(r['total_rows']):,} rows)"
            )
    else:
        print("No factory loses more than 5% of its rows to this filter.")

    # -----------------------------
    # Quality-code filtering
    # -----------------------------

    df = df[df["quality_code"].isin(allowed_quality_codes)].copy()

    print(f"Rows after quality-code filter : {len(df):,}")

    # QC validation
    assert not df["quality_code"].isin(
        ["Error", "Out of Range"]
    ).any(), "Error/Out of Range rows still present after filtering."

    # -----------------------------
    # Parse timestamps
    # -----------------------------

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        format="%Y-%m-%d %H:%M:%S",
        errors="coerce"
    )

    nat_count = df["timestamp"].isna().sum()

    print(f"Invalid timestamps : {nat_count:,}")

    if nat_count > 0:
        print("\nExample bad timestamp values:")
        print(
            df.loc[
                df["timestamp"].isna(),
                ["factory_id", "parameter_id", "timestamp"]
            ].head(20)
        )

        raise ValueError(
            f"{nat_count:,} timestamps could not be parsed."
        )

    # -----------------------------
    # Data types
    # -----------------------------

    df["factory_id"] = df["factory_id"].astype("string")
    df["parameter_id"] = df["parameter_id"].astype("string")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # -----------------------------
    # Sort
    # -----------------------------

    df = (
        df.sort_values(
            ["factory_id", "parameter_id", "timestamp"]
        )
        .reset_index(drop=True)
    )

    telemetry_df = df[
        [
            "factory_id",
            "parameter_id",
            "timestamp",
            "value",
            "quality_code"
        ]
    ]

    return telemetry_df, quality_report[
        ["factory_id", "total_rows", "kept_rows", "dropped_rows", "error_rate"]
    ]


# def load_cto_limits(cto_csv_path: str) -> pd.DataFrame:
#     """
#     Load CTO consent limits.
#     """

#     cto_df = pd.read_csv(cto_csv_path)

#     required_columns = [
#         "factory_id",
#         "parameter",
#         "minimum_limit",
#         "maximum_limit"
#     ]

#     missing = [
#         col
#         for col in required_columns
#         if col not in cto_df.columns
#     ]

#     if missing:
#         raise ValueError(
#             f"Missing required columns in consent_limits.csv: {missing}"
#         )

#     return cto_df


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
            f"Missing required columns in consent_limits.csv: {missing}"
        )

    # ---------------------------------
    # Standardize column names
    # ---------------------------------

    cto_df = cto_df.rename(
        columns={
            "parameter": "parameter_id",
            "minimum_limit": "lower_limit",
            "maximum_limit": "upper_limit"
        }
    )

    return cto_df