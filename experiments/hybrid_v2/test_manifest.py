import os
import unittest
import pandas as pd
import numpy as np

HYBRID_V2_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HYBRID_V2_DIR))
REAL_PARQUET = os.path.join(REPO_ROOT, "Data", "RawData", "real_features.parquet")

class TestHybridV2Dataset(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.manifest_path = os.path.join(HYBRID_V2_DIR, "tamper_manifest.csv")
        cls.control_path = os.path.join(HYBRID_V2_DIR, "control_telemetry.parquet")
        cls.neutral_path = os.path.join(HYBRID_V2_DIR, "hybrid_v2_code_neutral_telemetry.parquet")
        cls.visible_path = os.path.join(HYBRID_V2_DIR, "hybrid_v2_code_visible_telemetry.parquet")

        cls.control_feat_path = os.path.join(HYBRID_V2_DIR, "control_features.parquet")
        cls.neutral_feat_path = os.path.join(HYBRID_V2_DIR, "hybrid_v2_code_neutral_features.parquet")
        cls.visible_feat_path = os.path.join(HYBRID_V2_DIR, "hybrid_v2_code_visible_features.parquet")

        cls.manifest = pd.read_csv(cls.manifest_path)
        cls.df_control = pd.read_parquet(cls.control_path)
        cls.df_neutral = pd.read_parquet(cls.neutral_path)
        cls.df_visible = pd.read_parquet(cls.visible_path)

    def test_manifest_event_counts_and_balance(self):
        """Verify total event count >= 300 and balance across types/severities."""
        total_events = len(self.manifest)
        self.assertGreaterEqual(total_events, 300, f"Expected >= 300 total events, got {total_events}")

        # Count per tamper type
        type_counts = self.manifest["tamper_type"].value_counts().to_dict()
        for t_type, count in type_counts.items():
            self.assertGreaterEqual(count, 30, f"Tamper type {t_type} has only {count} events (expected >= 30)")

        # Verify BDL Gaming is marked with detector = 'none'
        bdl_events = self.manifest[self.manifest["tamper_type"] == "BDL GAMING"]
        self.assertTrue((bdl_events["detector_type"] == "none").all(), "BDL Gaming events must be marked with detector_type == 'none'")

        # Verify copy-paste events are multi-day (>= 192 steps = 2 days)
        cp_events = self.manifest[self.manifest["tamper_type"] == "COPY-PASTE"]
        self.assertGreaterEqual(len(cp_events), 30, "Expected >= 30 Copy-Paste events")
        for _, r in cp_events.iterrows():
            self.assertGreaterEqual(r["rows_affected"], 192, f"Copy-Paste event {r['event_id']} affects {r['rows_affected']} rows (< 192 steps / 2 days)")

    def test_manifest_windows_match_telemetry_exactly(self):
        """Verify every manifest window matches data in neutral and visible variants."""
        for idx, row in self.manifest.iterrows():
            fac = row["site"]
            param = row["parameter"]
            start_ts = pd.to_datetime(row["start"])
            end_ts = pd.to_datetime(row["end"])

            # Check neutral variant
            sub_neut = self.df_neutral[
                (self.df_neutral["factory_id"] == fac) &
                (self.df_neutral["parameter_id"] == param) &
                (self.df_neutral["timestamp"] >= start_ts) &
                (self.df_neutral["timestamp"] <= end_ts)
            ]
            self.assertEqual(len(sub_neut), row["rows_affected"], f"Event {row['event_id']} row count mismatch in code-neutral variant")

            # Check visible variant
            sub_vis = self.df_visible[
                (self.df_visible["factory_id"] == fac) &
                (self.df_visible["parameter_id"] == param) &
                (self.df_visible["timestamp"] >= start_ts) &
                (self.df_visible["timestamp"] <= end_ts)
            ]
            self.assertEqual(len(sub_vis), row["rows_affected"], f"Event {row['event_id']} row count mismatch in code-visible variant")

    def test_feature_matrix_schema_matches_real_features(self):
        """Verify feature matrices have exactly 28 columns matching real_features.parquet."""
        real_df = pd.read_parquet(REAL_PARQUET)
        target_cols = list(real_df.columns)
        self.assertEqual(len(target_cols), 28, "real_features.parquet must have 28 columns")

        for feat_path in [self.control_feat_path, self.neutral_feat_path, self.visible_feat_path]:
            feat_df = pd.read_parquet(feat_path)
            self.assertEqual(list(feat_df.columns), target_cols, f"Columns in {os.path.basename(feat_path)} do not match real_features.parquet")
            self.assertEqual(len(feat_df.columns), 28, f"{os.path.basename(feat_path)} must have exactly 28 columns")

if __name__ == "__main__":
    unittest.main()
