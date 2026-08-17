import os
import joblib
import pandas as pd
from typing import Dict, Any
from ml_pipeline.risk_engine import calculate_composite_risk

# QC FIX (2026-08, Phase 2): the primary tamper model used to be an XGBoost
# classifier trained 100% on synthetic data, scored per reading. It over-
# flagged 45.7% of real readings and was retired after a weak-supervision
# retrain attempt at the same per-reading granularity also failed validation
# (see train_xgboost_weak_supervision.py header for the full story). It has
# been replaced by a factory-level logistic regression, trained on real
# telemetry aggregated per factory with proxy labels from the fingerprint
# engine's own trigger counts (3+ of 8 triggered = proxy-tampered). Passed
# leave-one-out CV: AUC 0.854, Spearman(predicted prob, real trigger count)
# 0.677. See ml_strategy_plan.md and train_xgboost_weak_supervision.py.
#
# This must exactly match the raw columns aggregated in
# train_xgboost_weak_supervision.py's load_factory_level_data().
FACTORY_LEVEL_RAW_COLS = ['value', 'rolling_mean', 'rolling_std', 'flatline_flag']


class ForensiAirInference:
    def __init__(self, models_dir: str = None):
        if models_dir is None:
            models_dir = os.path.join(os.path.dirname(__file__), "models")
        self.models_dir = models_dir

        # QC FIX (2026-08): Isolation Forest has its own scaler, fit on real
        # data only -- see train_models.py.
        self.iso_scaler = joblib.load(os.path.join(models_dir, "iso_scaler.joblib"))
        self.iso_forest = joblib.load(os.path.join(models_dir, "iso_forest.joblib"))
        self.feature_cols = joblib.load(os.path.join(models_dir, "feature_cols.joblib"))

        # QC FIX (2026-08, Phase 2): factory-level proxy-label model,
        # replacing the retired per-reading synthetic XGBoost. See module
        # docstring comment above.
        self.factory_scaler = joblib.load(os.path.join(models_dir, "factory_scaler.joblib"))
        self.factory_model = joblib.load(os.path.join(models_dir, "factory_tamper_model.joblib"))
        self.factory_feature_cols = joblib.load(os.path.join(models_dir, "factory_tamper_feature_cols.joblib"))

    def predict_factory_tamper_probability(self, factory_readings: pd.DataFrame) -> float:
        """
        factory_readings: all real feature rows for ONE factory (must
        contain the columns in FACTORY_LEVEL_RAW_COLS). Aggregates them
        into the same mean/std feature set the factory-level model was
        trained on and returns a single tamper probability for that
        factory as a whole. This model only makes sense at factory
        granularity -- it was trained on aggregated stats, not individual
        readings (see train_xgboost_weak_supervision.py for why the
        per-reading version of this approach failed validation).
        """
        agg = {}
        for col in FACTORY_LEVEL_RAW_COLS:
            agg[f"{col}_mean"] = float(factory_readings[col].mean())
            agg[f"{col}_std"] = float(factory_readings[col].std()) if len(factory_readings) > 1 else 0.0

        row = pd.DataFrame([agg]).reindex(columns=self.factory_feature_cols).fillna(0.0)
        row_scaled = self.factory_scaler.transform(row)
        return float(self.factory_model.predict_proba(row_scaled)[0, 1])

    def predict_single(self, feature_dict: Dict[str, float], fingerprint_triggers: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Per-reading scoring. QC NOTE (2026-08, Phase 2): the tamper-model
        term (xgb_prob) can NOT be computed here -- the validated
        replacement model only operates on factory-level aggregates, not a
        single reading, so this always passes xgb_prob=0.0 to
        calculate_composite_risk(). For a real factory-level risk score
        (the one actually used in the live pipeline) see
        predict_factory_tamper_probability() above and how it's used in
        database/seed_db.py's score_factory(). This method is kept for any
        caller that only wants a single reading's isolation-forest anomaly
        score plus fingerprint-driven risk, not the full composite.
        """
        df = pd.DataFrame([feature_dict])
        for col in self.feature_cols:
            if col not in df.columns:
                df[col] = 0.0
        X = df[self.feature_cols].copy().fillna(0.0)
        X_iso_scaled = self.iso_scaler.transform(X)

        iso_score = float(self.iso_forest.score_samples(X_iso_scaled)[0])

        if fingerprint_triggers is None:
            fingerprint_triggers = {}

        risk = calculate_composite_risk(0.0, iso_score, fingerprint_triggers)
        return risk

_inference_instance = None

def get_inference_engine() -> ForensiAirInference:
    global _inference_instance
    if _inference_instance is None:
        _inference_instance = ForensiAirInference()
    return _inference_instance
