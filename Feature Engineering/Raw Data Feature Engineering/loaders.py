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


def load_raw(monitoring_csv_path: str) -> pd.DataFrame:
    """
    Load raw OCEMS telemetry data.
    Applies quality-code filtering before feature computation.

    Keeps:
        - Raw
        - L

    Drops:
        - Error
        - Out of Range
    """

    print(f"\nReading telemetry: {monitoring_csv_path}")

    df = pd.read_csv(monitoring_csv_path)

    print(f"Rows loaded : {len(df):,}")

    # -----------------------------
    # Quality-code filtering
    # -----------------------------

    allowed_quality_codes = ["Raw", "L"]

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

    return df[
        [
            "factory_id",
            "parameter_id",
            "timestamp",
            "value",
            "quality_code"
        ]
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