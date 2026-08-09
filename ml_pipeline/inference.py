import os
import joblib
import pandas as pd
import numpy as np
from typing import Dict, Any
from ml_pipeline.risk_engine import calculate_composite_risk

class ForensiAirInference:
    def __init__(self, models_dir: str = None):
        if models_dir is None:
            models_dir = os.path.join(os.path.dirname(__file__), "models")
        self.models_dir = models_dir
        
        self.scaler = joblib.load(os.path.join(models_dir, "scaler.joblib"))
        self.xgb = joblib.load(os.path.join(models_dir, "xgboost_tamper.joblib"))
        self.iso_forest = joblib.load(os.path.join(models_dir, "iso_forest.joblib"))
        self.feature_cols = joblib.load(os.path.join(models_dir, "feature_cols.joblib"))
        self.feature_importances = joblib.load(os.path.join(models_dir, "feature_importances.joblib"))

    def predict_single(self, feature_dict: Dict[str, float], fingerprint_triggers: Dict[str, Any] = None) -> Dict[str, Any]:
        df = pd.DataFrame([feature_dict])
        for col in self.feature_cols:
            if col not in df.columns:
                df[col] = 0.0
        X = df[self.feature_cols].copy().fillna(0.0)
        X_scaled = self.scaler.transform(X)
        
        xgb_prob = float(self.xgb.predict_proba(X_scaled)[0, 1])
        iso_score = float(self.iso_forest.score_samples(X_scaled)[0])
        
        if fingerprint_triggers is None:
            fingerprint_triggers = {}
            
        risk = calculate_composite_risk(xgb_prob, iso_score, fingerprint_triggers)
        
        x_row = X_scaled[0]
        shap_values = []
        for i, col in enumerate(self.feature_cols):
            imp = self.feature_importances.get(col, 0.05)
            impact = float(x_row[i] * imp)
            shap_values.append({
                "feature": col,
                "value": float(X.iloc[0][col]),
                "importance": round(imp, 4),
                "shap_impact": round(impact, 4)
            })
            
        shap_values.sort(key=lambda x: abs(x["shap_impact"]), reverse=True)
        risk["shap_attributions"] = shap_values[:8]
        return risk

_inference_instance = None

def get_inference_engine() -> ForensiAirInference:
    global _inference_instance
    if _inference_instance is None:
        _inference_instance = ForensiAirInference()
    return _inference_instance
