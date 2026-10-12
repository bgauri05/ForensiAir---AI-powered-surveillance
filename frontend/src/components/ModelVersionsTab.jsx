import React, { useState, useEffect } from 'react';
import { CheckCircle, Shield, AlertTriangle, Layers, Info, FileText } from 'lucide-react';
import { apiFetch } from '../config';

export function ModelVersionsTab() {
  const [modelInfo, setModelInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchModelInfo();
  }, []);

  const fetchModelInfo = async () => {
    try {
      const res = await apiFetch('/api/v2/model-info');
      if (res.ok) {
        setModelInfo(await res.json());
      }
    } catch (err) {
      console.error('Error fetching V2 model info:', err);
    } finally {
      setLoading(false);
    }
  };

  const legacyPipelineModels = [
    {
      id: 'fingerprints',
      name: 'Fingerprint Engine — Rule-Based Detection',
      weight: '67.5%',
      category: 'Domain logic, not a trained model',
      details: '8 rule-based checks: flatline, limit hugging, correlation break, copy-paste/autocorrelation, impossible pH range, inspection dip, coordinated missing data, data integrity. Pre-V2 heuristic baseline.'
    },
    {
      id: 'isolation-forest',
      name: 'Isolation Forest — Unsupervised Anomaly Detector',
      weight: '22.5%',
      category: 'Unsupervised · single global model',
      source: 'Real OCEMS telemetry (Data/RawData/real_features.parquet)',
      details: 'scikit-learn IsolationForest (100 estimators, contamination=0.05), fit on real telemetry with its own StandardScaler. One global model shared across all 33 factories.'
    },
    {
      id: 'tamper-model',
      name: 'Tamper Model — Factory-Level Logistic Regression',
      weight: '10%',
      category: 'Supervised · proxy-labeled · smallest component',
      source: 'Real telemetry aggregated per factory',
      details: 'Trained on weak proxy labels (3+ of 8 fingerprints triggered = proxy-tampered), not real confirmed tampering cases. Pre-V2 weak supervision prototype.'
    }
  ];

  return (
    <div className="p-6 space-y-8 max-w-5xl">
      {/* SECTION 1: ForensiAIR V2 Causal Supervised Model */}
      <div className="space-y-4">
        <div className="flex flex-wrap justify-between items-center gap-3">
          <div>
            <h3 className="font-headline-md text-headline-md text-[#00355f] flex items-center gap-2">
              <span>ForensiAIR V2 Causal Supervised Detector</span>
            </h3>
            <p className="text-xs text-[#727780] mt-0.5">
              Protocol Frozen: <code className="font-mono bg-[#f8f9fb] px-1.5 py-0.5 rounded border border-[#E5E7EB]">v2-protocol-frozen</code> (Git: 8c98d3d2) · Stage 2 LOFO Evaluation
            </p>
          </div>
          <span className="bg-[#00355f]/10 text-[#00355f] border border-[#00355f]/20 text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1.5">
            <Shield size={14} /> Historical Development Evaluation
          </span>
        </div>

        {/* V2 Architecture Card */}
        <div className="p-5 bg-white border border-[#E5E7EB] rounded-xl shadow-xs space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-3 bg-[#f8f9fb] rounded-lg border border-[#E5E7EB]">
              <div className="text-[10px] font-bold text-[#727780] uppercase tracking-wider">Model Architecture</div>
              <div className="font-bold text-body-sm text-[#00355f] mt-1">HistGradientBoostingClassifier</div>
              <div className="text-xs text-[#42474f] mt-0.5">max_depth=6, lr=0.1, iter=200, l2=1.0, balanced weights</div>
            </div>

            <div className="p-3 bg-[#f8f9fb] rounded-lg border border-[#E5E7EB]">
              <div className="text-[10px] font-bold text-[#727780] uppercase tracking-wider">Feature Engineering</div>
              <div className="font-bold text-body-sm text-[#00355f] mt-1">45 Causal Rolling Features</div>
              <div className="text-xs text-[#42474f] mt-0.5">Windows w ∈ &#123;16, 48, 96, 288&#125; (4h–72h), expanding past MAD scaled</div>
            </div>

            <div className="p-3 bg-[#f8f9fb] rounded-lg border border-[#E5E7EB]">
              <div className="text-[10px] font-bold text-[#727780] uppercase tracking-wider">Calibrated Budget</div>
              <div className="font-bold text-body-sm text-[#00355f] mt-1">1.0 Alert / Factory-Month</div>
              <div className="text-xs text-[#42474f] mt-0.5">Cutoff τ = 0.97875 (328 clean episodes on 327.61 fac-mo)</div>
            </div>
          </div>

          {/* Reconciled Cross-Mechanism Validation Metrics */}
          <div className="space-y-2 pt-2 border-t border-[#f2f4f6]">
            <h4 className="font-bold text-xs text-[#00355f] uppercase tracking-wider">
              Reconciled Cross-Mechanism Validation Results (Primary Non-No-Op Events)
            </h4>

            <div className="overflow-x-auto border border-[#E5E7EB] rounded-lg">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-[#f8f9fb] border-b border-[#E5E7EB] text-[#727780] font-bold">
                    <th className="py-2.5 px-3">Evaluation Direction</th>
                    <th className="py-2.5 px-3">Test Events</th>
                    <th className="py-2.5 px-3">V2 Recall</th>
                    <th className="py-2.5 px-3">Frozen V1 M1</th>
                    <th className="py-2.5 px-3">Paired Difference</th>
                    <th className="py-2.5 px-3">Statistical Significance</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-[#f2f4f6] hover:bg-[#fafbfc]">
                    <td className="py-2.5 px-3 font-semibold text-[#191c1e]">
                      Direction 1: Train Mechanism A → Test Mechanism B
                    </td>
                    <td className="py-2.5 px-3 text-[#727780]">2,553 events</td>
                    <td className="py-2.5 px-3 font-bold text-[#00355f]">17.31% [11.8%, 22.9%]</td>
                    <td className="py-2.5 px-3 text-[#727780]">15.39%</td>
                    <td className="py-2.5 px-3 font-semibold text-[#191c1e]">+1.92% [-3.3%, +6.9%]</td>
                    <td className="py-2.5 px-3 text-[#727780]">Includes 0 (Indistinguishable)</td>
                  </tr>
                  <tr className="hover:bg-[#fafbfc]">
                    <td className="py-2.5 px-3 font-semibold text-[#191c1e]">
                      Direction 2: Train Mechanism B → Test Mechanism A
                    </td>
                    <td className="py-2.5 px-3 text-[#727780]">1,899 events</td>
                    <td className="py-2.5 px-3 font-bold text-[#1b6d24]">30.60% [23.0%, 37.5%]</td>
                    <td className="py-2.5 px-3 text-[#727780]">10.16%</td>
                    <td className="py-2.5 px-3 font-bold text-[#1b6d24]">+20.43% [+13.0%, +27.3%]</td>
                    <td className="py-2.5 px-3 font-bold text-[#1b6d24]">Statistically Significant (V2 Superior)</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <p className="text-[11px] text-[#727780] leading-relaxed pt-1">
              *Metric Reconciliation Note: The preliminary 14.68% figure reflected the frozen V1 baseline on all 2,698 raw Mechanism B events before no-op filtering (396/2,698). The protocol-frozen post-hoc analysis on primary non-no-op events establishes 17.31% (Direction 1) and 30.60% (Direction 2).
            </p>
          </div>

          {/* Operating Budget Notice */}
          <div className="p-3 bg-[#fff3e6] border border-[#F57C00]/20 rounded-lg text-xs text-[#7a3e00] flex items-start gap-2">
            <Info size={16} className="shrink-0 text-[#F57C00] mt-0.5" />
            <div>
              <strong>Operating Budget Calibration Notice:</strong> The 1.0 alert / factory-month false-alarm rate was calibrated on 33 development factories under frozen protocol rules. This is a development operating benchmark and does not constitute an empirical guarantee for unseen production telemetry.
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 2: Legacy Prototype Scoring Pipeline (August 2026 Baseline) */}
      <div className="space-y-4 pt-4 border-t border-[#E5E7EB]">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="font-headline-md text-headline-md text-[#727780]">Legacy Prototype Scoring Pipeline (Pre-V2 Baseline)</h3>
            <p className="text-xs text-[#727780]">Historical 3-tier weak supervision prototype created in August 2026.</p>
          </div>
          <span className="bg-[#f2f4f6] text-[#727780] text-xs font-bold px-3 py-1 rounded-full">
            Legacy Baseline
          </span>
        </div>

        <div className="space-y-3">
          {legacyPipelineModels.map((model) => (
            <div key={model.id} className="p-4 bg-white border border-[#E5E7EB] rounded-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4 opacity-80">
              <div className="space-y-1.5 max-w-2xl">
                <div className="flex items-center gap-3">
                  <h4 className="font-body-md font-bold text-[#42474f] text-sm">{model.name}</h4>
                  <span className="bg-[#f2f4f6] text-[#727780] text-[11px] font-bold px-2 py-0.5 rounded">
                    {model.weight} weight
                  </span>
                </div>
                <p className="text-xs text-[#727780] uppercase tracking-wide">{model.category}</p>
                <p className="text-xs text-[#727780] leading-relaxed">{model.details}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Mandatory Investigation & Regulatory Disclaimer */}
      <div className="card p-5 bg-[#f8f9fb] border-l-4 border-l-[#0f4c81] flex flex-col sm:flex-row gap-4 items-start">
        <div className="p-2 bg-[#0f4c81]/10 text-[#0f4c81] rounded-lg shrink-0">
          <FileText size={20} className="text-[#0f4c81]" />
        </div>
        <div className="space-y-1">
          <h4 className="font-bold text-body-sm text-[#00355f]">
            Regulatory Notice & Investigation Disclaimer
          </h4>
          <p className="text-xs text-[#42474f] leading-relaxed">
            ForensiAIR identifies unusual patterns in wastewater telemetry that may indicate data-quality
            or data-integrity issues. Alerts are indicators for further investigation and do not establish
            deliberate tampering, misconduct, or regulatory non-compliance. Possible explanations include
            sensor faults, maintenance, operational changes, missing data, and transmission issues. Verify
            readings and operational records before drawing conclusions.
          </p>
        </div>
      </div>
    </div>
  );
}
