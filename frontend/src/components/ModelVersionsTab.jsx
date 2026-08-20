import React, { useState } from 'react';
import { GitBranch, ChevronDown, ChevronUp, CheckCircle, Lock, Database } from 'lucide-react';

export function ModelVersionsTab() {
  const [showMetadataPanel, setShowMetadataPanel] = useState(true);

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

  // Diagnostic / supporting models -- Stage 1 and Stage 2 (previously here)
  // have been removed from the app entirely; see backend/main.py and the
  // rest of this component's removal for the full change. Explainability
  // is the only entry left in this group.
  const activeModels = [
    {
      id: 'shap',
      name: 'Explainability — LightGBM Surrogate + SHAP',
      tag: 'v1.1',
      category: 'TreeExplainer Feature Attribution',
      source: 'Data/RawData/factory_shap_attributions.csv (no generator script found in repo)',
      trainedDate: 'Oct 12, 2024',
      status: 'Active',
      lastRetrained: '1 day ago',
      details: 'Global & Local SHAP Feature Importance Attribution Engine'
    }
  ];

  // Version History / Changelog
  const versionHistory = [
    {
      tag: 'v1.2',
      date: 'Oct 12, 2024',
      author: 'AI Security Team',
      description: 'Recalibrated flatline thresholds to per-factory-per-parameter relative scaling and updated Stage 2 XGBoost multiclass loss weights.'
    },
    {
      tag: 'v1.1',
      date: 'Sept 24, 2024',
      author: 'Forensic Analytics Division',
      description: 'Fixed inverted copy-paste autocorrelation signal & added 72h pre-inspection dip detection window for ETP parameters.'
    },
    {
      tag: 'v1.0',
      date: 'Aug 15, 2024',
      author: 'ForensiAir Core Engineering',
      description: 'Initial production deployment of 2-Stage XGBoost & Isolation Forest surveillance pipeline across Taloja & Mahad clusters.'
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

      {/* Diagnostic / Supporting Models -- classification labels and
          per-factory probabilities shown elsewhere in the app, but none
          of these feed the composite score above directly. */}
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="font-headline-md text-headline-md text-[#00355f]">Diagnostic / Supporting Models</h3>
          <span className="bg-[#f8f9fb] text-[#727780] border border-[#E5E7EB] text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1.5">
            Not part of the composite score
          </span>
        </div>

        <div className="space-y-4">
          {activeModels.map((model) => (
            <div key={model.id} className="p-5 bg-white border border-[#E5E7EB] rounded-xl shadow-xs flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div className="space-y-2 max-w-2xl">
                <div className="flex items-center gap-3">
                  <h4 className="font-body-md font-bold text-[#00355f] text-base">{model.name}</h4>
                  <span className="bg-[#00355f] text-white text-[11px] font-bold px-2.5 py-0.5 rounded">
                    {model.tag}
                  </span>
                  <span className="bg-[#1b6d24]/10 text-[#1b6d24] border border-[#1b6d24]/20 text-[10px] font-bold uppercase px-2 py-0.5 rounded">
                    {model.status}
                  </span>
                </div>

                <p className="text-xs text-[#42474f] leading-relaxed">{model.details}</p>

                <div className="flex flex-wrap gap-4 text-xs text-[#727780]">
                  <div>Source: <strong className="text-[#191c1e]">{model.source}</strong></div>
                  <div>Trained Date: <strong className="text-[#191c1e]">{model.trainedDate}</strong></div>
                  <div>Last Retrained: <strong className="text-[#191c1e]">{model.lastRetrained}</strong></div>
                </div>
              </div>

              {/* Action UI Stubs (Read-Only) */}
              <div className="flex items-center gap-2 self-end md:self-center">
                <button
                  disabled
                  title="Model deployment logic is read-only in this version"
                  className="px-3 py-1.5 bg-[#f8f9fb] border border-[#E5E7EB] text-[#727780] rounded text-xs font-bold cursor-not-allowed opacity-60 flex items-center gap-1"
                >
                  <Lock size={12} /> Promote to Active
                </button>
                <button
                  disabled
                  title="Rollback is disabled"
                  className="px-3 py-1.5 bg-[#f8f9fb] border border-[#E5E7EB] text-[#727780] rounded text-xs font-bold cursor-not-allowed opacity-60 flex items-center gap-1"
                >
                  <Lock size={12} /> Rollback
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 3. Version History / Changelog */}
      <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-xs space-y-4">
        <h3 className="font-headline-md text-headline-md text-[#00355f] flex items-center gap-2">
          <GitBranch size={20} className="text-[#00355f]" />
          Version History & Changelog
        </h3>
        <div className="divide-y divide-[#E5E7EB]">
          {versionHistory.map((item, idx) => (
            <div key={idx} className="py-3.5 first:pt-0 last:pb-0 space-y-1">
              <div className="flex justify-between items-center text-body-sm">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-[#00355f]">{item.tag}</span>
                  <span className="text-xs text-[#727780]">• {item.date}</span>
                </div>
                <span className="text-xs text-[#727780] italic">Maintained by {item.author}</span>
              </div>
              <p className="text-xs text-[#42474f] leading-relaxed">{item.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* 4. Training Metadata Panel (Collapsible) */}
      <div className="bg-white border border-[#E5E7EB] rounded-xl shadow-xs overflow-hidden">
        <button
          onClick={() => setShowMetadataPanel(!showMetadataPanel)}
          className="w-full p-6 flex justify-between items-center bg-[#f8f9fb] hover:bg-[#edeef0] transition-colors border-b border-[#E5E7EB] text-left"
        >
          <div className="flex items-center gap-2">
            <Database size={20} className="text-[#00355f]" />
            <h3 className="font-headline-md text-headline-md text-[#00355f]">Pipeline Training Metadata & Parameters</h3>
          </div>
          {showMetadataPanel ? <ChevronUp size={20} className="text-[#00355f]" /> : <ChevronDown size={20} className="text-[#00355f]" />}
        </button>

        {showMetadataPanel && (
          <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6 text-body-sm">
            <div className="space-y-4">
              <div>
                <span className="text-[10px] font-label-caps text-[#727780] uppercase font-bold">TRAINING WINDOW</span>
                <p className="font-bold text-[#191c1e] mt-0.5">Jan 01, 2024 – Oct 01, 2024 (9 Months Telemetry)</p>
              </div>
              <div>
                <span className="text-[10px] font-label-caps text-[#727780] uppercase font-bold">TOTAL TRAINING DATASET</span>
                <p className="font-bold text-[#191c1e] mt-0.5">1,420,500 Rows across 33 Industrial Facilities</p>
              </div>
              <div>
                <span className="text-[10px] font-label-caps text-[#727780] uppercase font-bold">SYNTHETIC GENERATION SEED</span>
                <p className="font-bold text-[#191c1e] mt-0.5">Seed = 42 (Reproducible Injector Sampling)</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <span className="text-[10px] font-label-caps text-[#727780] uppercase font-bold">FEATURE VECTOR DIMENSIONS</span>
                <p className="font-bold text-[#191c1e] mt-0.5">24 Computed Signals (pH, BOD, COD, TSS, Flow, Autocorr, CV, Limit Hugging)</p>
              </div>
              <div>
                <span className="text-[10px] font-label-caps text-[#727780] uppercase font-bold">HARDWARE ENVIROMENT</span>
                <p className="font-bold text-[#191c1e] mt-0.5">PyTorch 2.2 + XGBoost GPU Acceleration (NVIDIA CUDA)</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
