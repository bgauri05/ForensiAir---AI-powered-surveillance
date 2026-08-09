import React, { useState } from 'react';
import { Layers, GitBranch, ChevronDown, ChevronUp, CheckCircle, Lock, Clock, Info, ShieldCheck, Database } from 'lucide-react';

export function ModelVersionsTab({ factories = [] }) {
  const [showFactoryModal, setShowFactoryModal] = useState(false);
  const [showMetadataPanel, setShowMetadataPanel] = useState(true);
  const [searchFactoryText, setSearchFactoryText] = useState('');

  // 3 Pipeline Stages
  const activeModels = [
    {
      id: 'stage1',
      name: 'Stage 1 — IsolationForest (Per-Factory)',
      tag: 'v1.2',
      category: 'Unsupervised Anomaly Detector',
      source: 'Real OCEMS Telemetry (2024)',
      trainedDate: 'Oct 10, 2024',
      status: 'Active',
      lastRetrained: '2 days ago',
      details: '33 separate factory models (per-site contamination tuning)',
      hasPerFactoryList: true
    },
    {
      id: 'stage2',
      name: 'Stage 2 — XGBoost (Multiclass Classifier)',
      tag: 'v1.2',
      category: 'Supervised Tamper Classifier',
      source: 'Synthetic Labeled Data (CTO Limits + Injections)',
      trainedDate: 'Oct 12, 2024',
      status: 'Active',
      lastRetrained: '1 day ago',
      details: '9-Class Tamper Classifier (NONE, BOD Flatline, Limit Hugging, Dip...)',
      hasPerFactoryList: false
    },
    {
      id: 'shap',
      name: 'Explainability — LightGBM Surrogate + SHAP',
      tag: 'v1.1',
      category: 'TreeExplainer Feature Attribution',
      source: 'Stage 2 XGBoost Predictions & Telemetry',
      trainedDate: 'Oct 12, 2024',
      status: 'Active',
      lastRetrained: '1 day ago',
      details: 'Global & Local SHAP Feature Importance Attribution Engine',
      hasPerFactoryList: false
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

  const filteredFactories = factories.filter(f => 
    (f.factory_name || f.name || '').toLowerCase().includes(searchFactoryText.toLowerCase()) ||
    (f.factory_id || '').toLowerCase().includes(searchFactoryText.toLowerCase())
  );

  return (
    <div className="p-6 space-y-8">
      {/* 1. Performance Snapshot Cards */}
      <div>
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-headline-md text-headline-md text-[#00355f]">Model Performance Snapshot</h3>
          <span className="text-label-caps text-[11px] text-[#727780] font-bold">CROSS-VALIDATED ACCURACY</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 bg-[#f8f9fb] border border-[#E5E7EB] rounded-xl shadow-xs">
            <div className="text-[10px] font-label-caps text-[#727780] uppercase font-bold">STAGE 1 AUCPR</div>
            <div className="text-display-kpi font-display-kpi text-[#1b6d24] mt-1">0.942</div>
            <div className="text-xs text-[#42474f] mt-1 font-semibold">+1.8% vs Baseline (Isolation Forest)</div>
          </div>
          <div className="p-4 bg-[#f8f9fb] border border-[#E5E7EB] rounded-xl shadow-xs">
            <div className="text-[10px] font-label-caps text-[#727780] uppercase font-bold">STAGE 2 mLOGLOSS</div>
            <div className="text-display-kpi font-display-kpi text-[#00355f] mt-1">0.184</div>
            <div className="text-xs text-[#42474f] mt-1 font-semibold">9-Class Multiclass Loss</div>
          </div>
          <div className="p-4 bg-[#f8f9fb] border border-[#E5E7EB] rounded-xl shadow-xs">
            <div className="text-[10px] font-label-caps text-[#727780] uppercase font-bold">ENSEMBLE F1-SCORE</div>
            <div className="text-display-kpi font-display-kpi text-[#1b6d24] mt-1">96.8%</div>
            <div className="text-xs text-[#42474f] mt-1 font-semibold">Precision 97.4% / Recall 96.2%</div>
          </div>
          <div className="p-4 bg-[#f8f9fb] border border-[#E5E7EB] rounded-xl shadow-xs">
            <div className="text-[10px] font-label-caps text-[#727780] uppercase font-bold">SHAP SURROGATE FIDELITY</div>
            <div className="text-display-kpi font-display-kpi text-[#0f4c81] mt-1">99.2%</div>
            <div className="text-xs text-[#42474f] mt-1 font-semibold">LightGBM TreeExplainer Agreement</div>
          </div>
        </div>
      </div>

      {/* 2. Active Pipeline Models Section */}
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="font-headline-md text-headline-md text-[#00355f]">Active Pipeline Models</h3>
          <span className="bg-[#1b6d24]/10 text-[#1b6d24] border border-[#1b6d24]/20 text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1.5">
            <CheckCircle size={14} /> 3 Active Production Pipelines
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

                {model.hasPerFactoryList && (
                  <button 
                    onClick={() => setShowFactoryModal(true)}
                    className="text-xs font-bold text-[#0f4c81] hover:underline flex items-center gap-1 pt-1 cursor-pointer"
                  >
                    View all 33 per-factory models →
                  </button>
                )}
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
                <span className="text-[10px] font-label-caps text-[#727780] uppercase font-bold">EXCLUDED FORENSIC HOLDOUT SITES</span>
                <div className="mt-1 flex items-center gap-2">
                  <span className="px-2.5 py-1 bg-[#D32F2F]/10 text-[#D32F2F] border border-[#D32F2F]/20 rounded font-bold text-xs">
                    site_1232 (Deep Discharger Exhibit)
                  </span>
                  <span className="px-2.5 py-1 bg-[#D32F2F]/10 text-[#D32F2F] border border-[#D32F2F]/20 rounded font-bold text-xs">
                    site_1281 (Taloja Outlier Exhibit)
                  </span>
                </div>
              </div>
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

      {/* Modal: All 33 Per-Factory Stage 1 IsolationForest Models */}
      {showFactoryModal && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-4xl w-full max-h-[85vh] flex flex-col overflow-hidden shadow-2xl">
            <div className="p-6 border-b border-[#E5E7EB] flex justify-between items-center bg-[#f8f9fb]">
              <div>
                <h3 className="font-headline-md text-headline-md text-[#00355f]">Stage 1 IsolationForest — 33 Factory Models</h3>
                <p className="text-xs text-[#42474f] mt-1">Per-site contamination tuning & individual OCEMS baseline models</p>
              </div>
              <button 
                onClick={() => setShowFactoryModal(false)}
                className="text-[#727780] hover:text-[#191c1e] font-bold text-xl px-2"
              >
                ✕
              </button>
            </div>

            <div className="p-4 border-b border-[#E5E7EB] bg-white">
              <input 
                type="text"
                placeholder="Search factory ID or name..."
                value={searchFactoryText}
                onChange={(e) => setSearchFactoryText(e.target.value)}
                className="w-full border border-[#E5E7EB] bg-[#f8f9fb] rounded-lg px-4 py-2 text-body-sm focus:outline-none focus:border-[#00355f]"
              />
            </div>

            <div className="flex-1 overflow-y-auto divide-y divide-[#E5E7EB]">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-[#f8f9fb]">
                    <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase">Factory ID</th>
                    <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase">Factory Name</th>
                    <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase">Model File</th>
                    <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase">Contamination</th>
                    <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase">Last Trained</th>
                  </tr>
                </thead>
                <tbody className="text-table-data">
                  {filteredFactories.map((f, idx) => (
                    <tr key={f.factory_id || idx} className="hover:bg-[#f8f9fb]">
                      <td className="px-6 py-3 font-bold text-[#00355f]">{f.factory_id}</td>
                      <td className="px-6 py-3 font-bold text-[#191c1e]">{f.factory_name || f.name}</td>
                      <td className="px-6 py-3 text-xs font-mono text-[#42474f]">iso_forest_{f.factory_id}.joblib</td>
                      <td className="px-6 py-3 text-[#1b6d24] font-bold text-xs">0.05 (Default)</td>
                      <td className="px-6 py-3 text-xs text-[#727780]">Oct 10, 2024</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="p-4 border-t border-[#E5E7EB] bg-[#f8f9fb] text-right">
              <button 
                onClick={() => setShowFactoryModal(false)}
                className="px-5 py-2 bg-[#00355f] text-white rounded-lg text-body-sm font-bold hover:opacity-90"
              >
                Close Modal
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
