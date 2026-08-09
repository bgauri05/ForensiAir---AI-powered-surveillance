import os
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from xgboost import XGBClassifier

FEATURE_COLS = [
    'value', 'rolling_mean', 'rolling_std', 'rolling_cov', 'flatline_flag',
    'corr_ETP-Flow_ETP-pH', 'corr_ETP-BOD_ETP-COD', 'corr_ETP-BOD_ETP-Flow',
    'corr_ETP-BOD_ETP-TSS', 'corr_ETP-BOD_ETP-pH', 'corr_ETP-COD_ETP-Flow',
    'corr_ETP-COD_ETP-TSS', 'corr_ETP-COD_ETP-pH', 'corr_ETP-Flow_ETP-TSS',
    'corr_ETP-TSS_ETP-pH', 'autocorrelation', 'missing_rate', 'limit_hugging'
]

def train():
    output_dir = os.path.join(os.path.dirname(__file__), "models")
    os.makedirs(output_dir, exist_ok=True)
    
    print("--- 1. Loading Synthetic Features & Labeled Dataset ---")
    syn_path = "Data/SynData/synthetic_features.parquet"
    if not os.path.exists(syn_path):
        syn_path = os.path.join("..", syn_path)
    df_syn = pd.read_parquet(syn_path)
    print(f"Loaded Synthetic dataset: {df_syn.shape}")
    
    X_syn = df_syn[FEATURE_COLS].copy()
    X_syn = X_syn.fillna(X_syn.median())
    y_syn_binary = df_syn['is_tampered'].astype(int)
    
    scaler = StandardScaler()
    X_syn_scaled = scaler.fit_transform(X_syn)
    
    print("\n--- 2. Training Supervised XGBoost Classifier ---")
    xgb = XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        eval_metric='logloss',
        n_jobs=-1
    )
    xgb.fit(X_syn_scaled, y_syn_binary)
    y_pred_xgb = xgb.predict(X_syn_scaled)
    y_prob_xgb = xgb.predict_proba(X_syn_scaled)[:, 1]
    
    print(f"XGBoost F1-Score: {f1_score(y_syn_binary, y_pred_xgb):.4f}")
    print(f"XGBoost Precision: {precision_score(y_syn_binary, y_pred_xgb):.4f}")
    print(f"XGBoost Recall: {recall_score(y_syn_binary, y_pred_xgb):.4f}")
    print(f"XGBoost ROC-AUC: {roc_auc_score(y_syn_binary, y_prob_xgb):.4f}")
    
    print("\n--- 3. Training Isolation Forest on Real Features ---")
    real_path = "Data/RawData/real_features.parquet"
    if not os.path.exists(real_path):
        real_path = os.path.join("..", real_path)
    df_real = pd.read_parquet(real_path)
    
    X_real = df_real[FEATURE_COLS].copy().fillna(X_syn.median())
    X_real_scaled = scaler.transform(X_real)
    
    sample_idx = np.random.choice(len(X_real_scaled), size=min(100000, len(X_real_scaled)), replace=False)
    iso_forest = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42,
        n_jobs=-1
    )
    iso_forest.fit(X_real_scaled[sample_idx])
    
    print("\n--- 4. Saving Artifacts ---")
    joblib.dump(scaler, os.path.join(output_dir, "scaler.joblib"))
    joblib.dump(xgb, os.path.join(output_dir, "xgboost_tamper.joblib"))
    joblib.dump(iso_forest, os.path.join(output_dir, "iso_forest.joblib"))
    joblib.dump(FEATURE_COLS, os.path.join(output_dir, "feature_cols.joblib"))
    
    importances = dict(zip(FEATURE_COLS, xgb.feature_importances_.tolist()))
    joblib.dump(importances, os.path.join(output_dir, "feature_importances.joblib"))
    
    print(f"Successfully saved all models to {output_dir}")

if __name__ == "__main__":
    train()
