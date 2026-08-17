# import os
# import time
# import argparse
# import yaml

# from loaders import (
#     load_raw,
#     load_cto_limits
# )

# from features import assemble_feature_matrix


# def main():

#     parser = argparse.ArgumentParser(
#         description="Raw OCEMS Feature Engineering Pipeline"
#     )

#     parser.add_argument(
#         "--monitoring-csv",
#         type=str,
#         default="../data/monitoring_data(raw).csv",
#         help="Path to raw telemetry CSV"
#     )

#     parser.add_argument(
#         "--cto-csv",
#         type=str,
#         default="../data/consent_limits.csv",
#         help="Path to CTO consent limits CSV"
#     )

#     parser.add_argument(
#         "--config",
#         type=str,
#         default="config.yaml",
#         help="Configuration file"
#     )

#     parser.add_argument(
#         "--output-parquet",
#         type=str,
#         default="../output/real_features.parquet",
#         help="Output feature matrix"
#     )

#     args = parser.parse_args()

#     start = time.time()

#     # -----------------------------
#     # Load configuration
#     # -----------------------------

#     with open(args.config, "r") as f:
#         config = yaml.safe_load(f)

#     # -----------------------------
#     # Load datasets
#     # -----------------------------

#     print("\nLoading raw telemetry...")

#     telemetry_df = load_raw(
#         args.monitoring_csv
#     )

#     print(f"Telemetry rows : {len(telemetry_df):,}")

#     print("\nLoading CTO limits...")

#     cto_limits_df = load_cto_limits(
#         args.cto_csv
#     )

#     print(f"CTO rows : {len(cto_limits_df):,}")

#     # -----------------------------
#     # Feature Engineering
#     # -----------------------------

#     print("\nComputing engineered features...")

#     feature_matrix = assemble_feature_matrix(
#         telemetry_df,
#         config,
#         cto_limits_df
#     )

#     # -----------------------------
#     # Save output
#     # -----------------------------

#     os.makedirs(
#         os.path.dirname(args.output_parquet),
#         exist_ok=True
#     )

#     feature_matrix.to_parquet(
#         args.output_parquet,
#         index=False
#     )

#     # -----------------------------
#     # Diagnostics
#     # -----------------------------

#     elapsed = time.time() - start

#     print("\n======================================")
#     print(" FEATURE ENGINEERING COMPLETE")
#     print("======================================")

#     print(f"\nRows              : {len(feature_matrix):,}")
#     print(f"Columns           : {len(feature_matrix.columns)}")
#     print(f"Execution Time    : {elapsed:.2f} sec")

#     print("\nGenerated Columns")

#     for col in feature_matrix.columns:
#         print(f"  • {col}")

#     print("\nMissing Values (%)")

#     missing = (
#         feature_matrix
#         .isna()
#         .mean()
#         .mul(100)
#         .round(2)
#     )

#     print(missing)

#     print(
#         f"\nOutput saved to:\n{args.output_parquet}"
#     )


# if __name__ == "__main__":
#     main()


import os
import time
import argparse
import yaml
import numpy as np

from loaders import (
    load_raw,
    load_cto_limits
)

from features import assemble_feature_matrix


def main():

    parser = argparse.ArgumentParser(
        description="Raw OCEMS Feature Engineering Pipeline"
    )

    parser.add_argument(
        "--monitoring-csv",
        type=str,
        default="../data/monitoring_data(raw).csv",
        help="Path to raw telemetry CSV"
    )

    parser.add_argument(
        "--cto-csv",
        type=str,
        default="../data/consent_limits.csv",
        help="Path to CTO consent limits CSV"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Configuration file"
    )

    parser.add_argument(
        "--output-parquet",
        type=str,
        default="../output/real_features.parquet",
        help="Output feature matrix"
    )

    args = parser.parse_args()

    start = time.time()

    # --------------------------------------------------
    # Load configuration
    # --------------------------------------------------

    with open(args.config, "r") as f:
        config = yaml.safe_load(f)

    # --------------------------------------------------
    # Load datasets
    # --------------------------------------------------

    print("\nLoading raw telemetry...")

    telemetry_df, quality_report_df = load_raw(
        args.monitoring_csv
    )

    print(f"Telemetry rows : {len(telemetry_df):,}")

    print("\nLoading CTO limits...")

    cto_limits_df = load_cto_limits(
        args.cto_csv
    )

    print(f"CTO rows : {len(cto_limits_df):,}")

    # --------------------------------------------------
    # Feature Engineering
    # --------------------------------------------------

    print("\nComputing engineered features...")

    feature_matrix = assemble_feature_matrix(
        telemetry_df,
        cto_limits_df,
        config
    )

    # --------------------------------------------------
    # Attach per-factory data-quality signal
    # --------------------------------------------------
    # error_rate = share of this factory's raw readings that were
    # dropped by the Error/Out-of-Range quality-code filter in
    # load_raw(). Carried into the feature matrix as its own column
    # (not silently discarded) so downstream characterization/ML
    # stages can treat an unusually high error rate as a signal in
    # its own right rather than losing the information entirely.

    feature_matrix = feature_matrix.merge(
        quality_report_df[["factory_id", "error_rate"]].rename(
            columns={"error_rate": "quality_error_rate"}
        ),
        on="factory_id",
        how="left"
    )

    # --------------------------------------------------
    # Save output
    # --------------------------------------------------

    os.makedirs(
        os.path.dirname(args.output_parquet),
        exist_ok=True
    )

    feature_matrix.to_parquet(
        args.output_parquet,
        index=False
    )

    quality_report_path = os.path.join(
        os.path.dirname(args.output_parquet),
        "data_quality_report.csv"
    )
    quality_report_df.to_csv(quality_report_path, index=False)
    print(f"\nPer-factory data quality report saved to:\n{quality_report_path}")

    # --------------------------------------------------
    # Diagnostics
    # --------------------------------------------------

    elapsed = time.time() - start

    print("\n======================================")
    print(" FEATURE ENGINEERING COMPLETE")
    print("======================================")

    print(f"\nRows              : {len(feature_matrix):,}")
    print(f"Columns           : {len(feature_matrix.columns)}")
    print(f"Execution Time    : {elapsed:.2f} sec")

    print("\nGenerated Columns")

    for col in feature_matrix.columns:
        print(f"  • {col}")

    print("\nMissing Values (%)")

    missing = (
        feature_matrix
        .isna()
        .mean()
        .mul(100)
        .round(2)
    )

    print(missing)

    # --------------------------------------------------
    # QC Validation
    # --------------------------------------------------

    print("\n======================================")
    print(" QC VALIDATION")
    print("======================================")

    if "quality_code" in feature_matrix.columns:
        print("\nQuality Code Distribution")
        print(feature_matrix["quality_code"].value_counts())

    if "flatline_flag" in feature_matrix.columns:
        print("\nFlatline Flag Distribution")
        print(
            feature_matrix["flatline_flag"]
            .value_counts(dropna=False)
        )

    if "autocorrelation" in feature_matrix.columns:

        inf_count = np.isinf(
            feature_matrix["autocorrelation"]
        ).sum()

        print(f"\nAutocorrelation Inf Values : {inf_count}")

        print("\nAutocorrelation Summary")
        print(
            feature_matrix["autocorrelation"]
            .describe()
        )

    if "rolling_std" in feature_matrix.columns:
        print("\nRolling Std Summary")
        print(
            feature_matrix["rolling_std"]
            .describe()
        )

    if "missing_rate" in feature_matrix.columns:
        print("\nMissing Rate Summary")
        print(
            feature_matrix["missing_rate"]
            .describe()
        )

    print(
        f"\nOutput saved to:\n{args.output_parquet}"
    )


if __name__ == "__main__":
    main()