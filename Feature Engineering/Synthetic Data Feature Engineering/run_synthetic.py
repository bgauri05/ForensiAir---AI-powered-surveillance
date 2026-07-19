# import os
# import argparse
# import yaml
# import pandas as pd
# import numpy as np
# from loaders import (
#     load_synthetic,
#     load_cto_limits
# )
# from features import assemble_feature_matrix

# def main():
#     parser = argparse.ArgumentParser(description="ForensiAIR Feature Engineering Runner")
#     parser.add_argument('--monitoring-csv', type=str, default='../output/monitoring_data.csv',
#                         help='Path to monitoring_data.csv')
#     parser.add_argument('--labels-csv', type=str, default='../output/labels.csv',
#                         help='Path to labels.csv')
#     parser.add_argument('--config', type=str, default='config.yaml',
#                         help='Path to config.yaml')
#     parser.add_argument('--output-parquet', type=str, default='../output/synthetic_features.parquet',
#                         help='Path to save output Parquet file')
#     args = parser.parse_args()

#     # Load config.yaml
#     if not os.path.exists(args.config):
#         # Fallback to local path if running from parent
#         args.config = 'forensiair_features/config.yaml'
#     with open(args.config, 'r') as f:
#         config = yaml.safe_load(f)

#     # Resolve default paths if running from parent folder
#     if not os.path.exists(args.monitoring_csv) and os.path.exists('output/monitoring_data.csv'):
#         args.monitoring_csv = 'output/monitoring_data.csv'
#     if not os.path.exists(args.labels_csv) and os.path.exists('output/labels.csv'):
#         args.labels_csv = 'output/labels.csv'
#     if not os.path.exists(args.output_parquet) and os.path.exists('output'):
#         args.output_parquet = 'output/synthetic_features.parquet'

#     print(f"Loading datasets:\n  Monitoring: {args.monitoring_csv}\n  Labels: {args.labels_csv}")
#     df, labels_df = load_synthetic(args.monitoring_csv, args.labels_csv)
    
#     print("\nComputing features and assembling matrix (CTO limits = None)...")
#     feature_matrix = assemble_feature_matrix(df, config, cto_limits_df=None)
    
#     print("\nMapping label intervals onto feature matrix...")
#     # Initialize labeling columns
#     feature_matrix['is_tampered'] = False
#     feature_matrix['tamper_type'] = pd.Series([None] * len(feature_matrix), dtype=object)
#     feature_matrix['severity'] = pd.Series([None] * len(feature_matrix), dtype=object)
    
#     # Fast window matching using query mask
#     matched_events_count = 0
#     for idx, row in labels_df.iterrows():
#         mask = (
#             (feature_matrix['factory_id'] == row['factory_id']) &
#             (feature_matrix['parameter_id'] == row['parameter_id']) &
#             (feature_matrix['timestamp'] >= row['start_timestamp']) &
#             (feature_matrix['timestamp'] <= row['end_timestamp'])
#         )
#         if mask.any():
#             feature_matrix.loc[mask, 'is_tampered'] = True
#             feature_matrix.loc[mask, 'tamper_type'] = row['tamper_type']
#             feature_matrix.loc[mask, 'severity'] = row['severity']
#             matched_events_count += 1
            
#     print(f"Successfully matched {matched_events_count} of {len(labels_df)} events from labels.csv.")
    
#     # Ensure output directory exists
#     out_dir = os.path.dirname(args.output_parquet)
#     if out_dir:
#         os.makedirs(out_dir, exist_ok=True)
        
#     print(f"Saving output Parquet to: {args.output_parquet}")
#     feature_matrix.to_parquet(args.output_parquet, index=False)
    
#     # Output Diagnostics
#     print("\n================== DIAGNOSTICS ==================")
#     print(f"Total rows in feature matrix: {len(feature_matrix)}")
#     print("\nValue counts for 'is_tampered':")
#     print(feature_matrix['is_tampered'].value_counts())
    
#     print("\nValue counts for 'tamper_type' in feature matrix:")
#     print(feature_matrix['tamper_type'].value_counts(dropna=False))
    
#     print("\nOriginal labels.csv distribution for comparison:")
#     print(labels_df['tamper_type'].value_counts())
    
#     print("\nSanity Check: Mapped labels vs original counts matching:")
#     missing_matches = len(labels_df) - matched_events_count
#     if missing_matches == 0:
#         print("[PASS] All labeled events were successfully mapped to the time series.")
#     else:
#         print(f"[WARNING] {missing_matches} labeled events did not match any timestamps in the feature matrix.")

# if __name__ == '__main__':
#     main()


import os
import argparse
import yaml
import pandas as pd
import numpy as np

from loaders import (
    load_synthetic,
    load_cto_limits
)

from features import assemble_feature_matrix


def main():

    parser = argparse.ArgumentParser(
        description="ForensiAIR Feature Engineering Runner"
    )

    parser.add_argument(
        '--monitoring-csv',
        type=str,
        default='../output/monitoring_data.csv',
        help='Path to monitoring_data.csv'
    )

    parser.add_argument(
        '--labels-csv',
        type=str,
        default='../output/labels.csv',
        help='Path to labels.csv'
    )

    parser.add_argument(
        '--cto-csv',
        type=str,
        default='../output/consent_limits.csv',
        help='Path to consent_limits.csv'
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to config.yaml'
    )

    parser.add_argument(
        '--output-parquet',
        type=str,
        default='../output/synthetic_features.parquet',
        help='Path to save output Parquet file'
    )

    args = parser.parse_args()

    # --------------------------------------------------
    # Load config
    # --------------------------------------------------

    if not os.path.exists(args.config):
        args.config = 'forensiair_features/config.yaml'

    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # --------------------------------------------------
    # Resolve paths
    # --------------------------------------------------

    if (
        not os.path.exists(args.monitoring_csv)
        and os.path.exists('output/monitoring_data.csv')
    ):
        args.monitoring_csv = 'output/monitoring_data.csv'

    if (
        not os.path.exists(args.labels_csv)
        and os.path.exists('output/labels.csv')
    ):
        args.labels_csv = 'output/labels.csv'

    if (
        not os.path.exists(args.cto_csv)
        and os.path.exists('output/consent_limits.csv')
    ):
        args.cto_csv = 'output/consent_limits.csv'

    if (
        not os.path.exists(args.output_parquet)
        and os.path.exists('output')
    ):
        args.output_parquet = 'output/synthetic_features.parquet'

    # --------------------------------------------------
    # Load datasets
    # --------------------------------------------------

    print(
        f"Loading datasets:"
        f"\n  Monitoring: {args.monitoring_csv}"
        f"\n  Labels: {args.labels_csv}"
        f"\n  CTO Limits: {args.cto_csv}"
    )

    df, labels_df = load_synthetic(
        args.monitoring_csv,
        args.labels_csv
    )

    cto_limits_df = load_cto_limits(
        args.cto_csv
    )

    # --------------------------------------------------
    # Feature Engineering
    # --------------------------------------------------

    print("\nComputing feature matrix...")

    feature_matrix = assemble_feature_matrix(
        df,
        cto_limits_df,
        config
    )

    # --------------------------------------------------
    # Label Mapping
    # --------------------------------------------------

    print("\nMapping label intervals onto feature matrix...")

    feature_matrix["is_tampered"] = False
    feature_matrix["tamper_type"] = pd.Series(
        [None] * len(feature_matrix),
        dtype=object
    )

    feature_matrix["severity"] = pd.Series(
        [None] * len(feature_matrix),
        dtype=object
    )

    matched_events_count = 0

    for _, row in labels_df.iterrows():

        mask = (

            (feature_matrix["factory_id"] == row["factory_id"]) &

            (feature_matrix["parameter_id"] == row["parameter_id"]) &

            (feature_matrix["timestamp"] >= row["start_timestamp"]) &

            (feature_matrix["timestamp"] <= row["end_timestamp"])

        )

        if mask.any():

            feature_matrix.loc[
                mask,
                "is_tampered"
            ] = True

            feature_matrix.loc[
                mask,
                "tamper_type"
            ] = row["tamper_type"]

            feature_matrix.loc[
                mask,
                "severity"
            ] = row["severity"]

            matched_events_count += 1

    print(
        f"Successfully matched "
        f"{matched_events_count} of "
        f"{len(labels_df)} events."
    )

    # --------------------------------------------------
    # Save
    # --------------------------------------------------

    out_dir = os.path.dirname(
        args.output_parquet
    )

    if out_dir:
        os.makedirs(
            out_dir,
            exist_ok=True
        )

    print(
        f"\nSaving feature matrix to:\n"
        f"{args.output_parquet}"
    )

    feature_matrix.to_parquet(
        args.output_parquet,
        index=False
    )

    # --------------------------------------------------
    # Diagnostics
    # --------------------------------------------------

    print("\n================ DIAGNOSTICS ================\n")

    print(
        f"Rows: {len(feature_matrix)}"
    )

    print(
        "\nTampered distribution:"
    )

    print(
        feature_matrix["is_tampered"]
        .value_counts()
    )

    print(
        "\nTamper types:"
    )

    print(
        feature_matrix["tamper_type"]
        .value_counts(dropna=False)
    )

    print(
        "\nOriginal label distribution:"
    )

    print(
        labels_df["tamper_type"]
        .value_counts()
    )

    print(
        "\nAutocorrelation infinities:"
    )

    print(

        np.isinf(
            feature_matrix["autocorrelation"]
        ).sum()

    )

    print(
        "\nSanity Check:"
    )

    missing = (
        len(labels_df)
        - matched_events_count
    )

    if missing == 0:

        print(
            "[PASS] All events mapped successfully."
        )

    else:

        print(
            f"[WARNING] {missing} events "
            "did not match."
        )


if __name__ == "__main__":
    main()