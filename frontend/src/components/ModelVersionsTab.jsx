import React from 'react';
import { CheckCircle } from 'lucide-react';

// QC FIX (2026-08): this tab used to also render a "Diagnostic / Supporting
// Models" section (an "Explainability -- LightGBM Surrogate + SHAP" entry
// citing Data/RawData/factory_shap_attributions.csv, a file CLAUDE.md
// documents as orphaned -- no generator script, matches the removed
// Stage-2 model's feature set, unused by the backend), a "Version History /
// Changelog" (fake authorship like "AI Security Team", fake dates, and a
// reference to the removed Stage 2 XGBoost model), and a "Training
// Metadata" panel (invented row counts, a fake random seed, and
// "PyTorch 2.2 + XGBoost GPU Acceleration (NVIDIA CUDA)" -- this repo uses
// neither PyTorch nor XGBoost). None of it corresponded to anything real in
// this repo. Removed entirely rather than reworded, since there's no real
// data to back any of it with. The Live Composite Scoring Pipeline below is
// the only real, verifiable content this tab has -- confirmed against
// risk_engine.py, train_models.py, and train_xgboost_weak_supervision.py.
export function ModelVersionsTab() {
  // The three literal inputs to ml_pipeline/risk_engine.py's
  // calculate_composite_risk() -- these, weighted 67.5% / 22.5% / 10%,
  // are what actually produce every tamper_probability/risk_score shown
  // anywhere in this app. Confirmed against risk_engine.py, train_models.py,
  // and train_xgboost_weak_supervision.py before writing this copy.
  const pipelineModels = [
    {
      id: 'fingerprints',
      name: 'Fingerprint Engine — Rule-Based Detection',
      weight: '67.5%',
      category: 'Domain logic, not a trained model',
      details: '8 rule-based checks: flatline, limit hugging, correlation break, copy-paste/autocorrelation, impossible pH range, inspection dip, coordinated missing data, data integrity. The single largest component of the composite risk score.'
    },
    {
      id: 'isolation-forest',
      name: 'Isolation Forest — Unsupervised Anomaly Detector',
      weight: '22.5%',
      category: 'Unsupervised · single global model',
      source: 'Real OCEMS telemetry (Data/RawData/real_features.parquet)',
      details: 'scikit-learn IsolationForest (100 estimators, contamination=0.05), fit on real telemetry with its own StandardScaler. One global model shared across all 33 factories -- not per-factory.'
    },
    {
      id: 'tamper-model',
      name: 'Tamper Model — Factory-Level Logistic Regression',
      weight: '10%',
      category: 'Supervised · proxy-labeled · smallest, least-trusted component',
      source: 'Real telemetry aggregated per factory',
      details: 'Replaced the old per-reading XGBoost model (retired after over-flagging 45.7% of real readings on a synthetic/real distribution mismatch). Trained on proxy labels only -- 3+ of 8 fingerprints triggered = proxy-tampered -- not real confirmed tampering cases. Validated via leave-one-out CV: AUC 0.854, Spearman 0.677. Deployment weight kept deliberately low until real confirmed cases exist to validate further against.'
    }
  ];

  return (
    <div className="p-6 space-y-8">
      {/* Live Composite Scoring Pipeline -- the actual inputs to
          calculate_composite_risk(), weighted 67.5% / 22.5% / 10% */}
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="font-headline-md text-headline-md text-[#00355f]">Live Composite Scoring Pipeline</h3>
          <span className="bg-[#1b6d24]/10 text-[#1b6d24] border border-[#1b6d24]/20 text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1.5">
            <CheckCircle size={14} /> Drives every Tamper Probability shown in this app
          </span>
        </div>
        <p className="text-xs text-[#42474f] leading-relaxed">
          These three components are the literal, weighted inputs to <code className="font-mono bg-[#f8f9fb] px-1.5 py-0.5 rounded border border-[#E5E7EB]">calculate_composite_risk()</code> -- every tamper_probability / risk_score number in this app comes from this formula.
        </p>

        <div className="space-y-4">
          {pipelineModels.map((model) => (
            <div key={model.id} className="p-5 bg-white border border-[#E5E7EB] rounded-xl shadow-xs flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div className="space-y-2 max-w-2xl">
                <div className="flex items-center gap-3">
                  <h4 className="font-body-md font-bold text-[#00355f] text-base">{model.name}</h4>
                  <span className="bg-[#00355f]/10 text-[#00355f] border border-[#00355f]/20 text-[11px] font-bold px-2.5 py-0.5 rounded">
                    {model.weight} weight
                  </span>
                </div>

                <p className="text-xs text-[#727780] font-semibold uppercase tracking-wide">{model.category}</p>
                <p className="text-xs text-[#42474f] leading-relaxed">{model.details}</p>

                {model.source && (
                  <div className="text-xs text-[#727780]">
                    Source: <strong className="text-[#191c1e]">{model.source}</strong>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
