import React, { useState } from 'react';
import { Sliders, ShieldCheck, AlertCircle, Info, Lock, CheckCircle2, ChevronRight, FileText } from 'lucide-react';

export function ThresholdSettingsTab() {
  const [showProposeModal, setShowProposeModal] = useState(false);

  // 8 Fingerprints + Coordinated Missing Data (Locked Empirical Set)
  const thresholdsData = [
    {
      id: 'FP1',
      name: 'FP1 — Flatline Detection',
      description: 'Rolling-window standard deviation invariant signal detection',
      thresholdValue: 'Adaptive (per-factory baseline)',
      isAdaptive: true,
      lastValidated: 'Oct 12, 2024',
      status: 'Validated',
      separationMetric: 'Relative scaling'
    },
    {
      id: 'FP2',
      name: 'FP2 — Correlation Break',
      description: 'Rolling 24h Pearson correlation between COD & BOD effluent streams',
      thresholdValue: '< Regional Baseline (r < 0.65)',
      isAdaptive: false,
      lastValidated: 'Oct 12, 2024',
      status: 'Validated',
      separationMetric: 'Pearson r < 0.65'
    },
    {
      id: 'FP7',
      name: 'FP7 — Limit Hugging',
      description: 'Percentage of telemetry readings within tight band below CTO consent limit',
      thresholdValue: '5.0% Band',
      isAdaptive: false,
      lastValidated: 'Oct 10, 2024',
      status: 'Validated',
      separationMetric: '17x Tampered vs Baseline'
    },
    {
      id: 'FP8',
      name: 'FP8 — Copy-Paste / Autocorrelation',
      description: 'Lag-96 (24h period) autocorrelation pattern repetition rate',
      thresholdValue: 'Autocorrelation > 0.95',
      isAdaptive: false,
      lastValidated: 'Oct 10, 2024',
      status: 'Validated',
      separationMetric: '0.779 vs 0.345 Split'
    },
    {
      id: 'FP11',
      name: 'FP11 — BDL Gaming Rate',
      description: 'Percentage of Below Detection Limit (BDL) zero-variance reporting',
      thresholdValue: '> 15.0% BDL Rate',
      isAdaptive: false,
      lastValidated: 'Oct 08, 2024',
      status: 'Validated',
      separationMetric: 'BDL Ratio Cutoff'
    },
    {
      id: 'FP12',
      name: 'FP12 — Duplicate Run Length',
      description: 'Maximum consecutive identical raw telemetry sensor readings',
      thresholdValue: '> 12 Consecutive Timestamps',
      isAdaptive: false,
      lastValidated: 'Oct 08, 2024',
      status: 'Validated',
      separationMetric: 'Zero Delta Runs'
    },
    {
      id: 'FP13',
      name: 'FP13 — Impossible / Negative Values',
      description: 'Physical hard range bounds violation (e.g. pH ∉ [0,14] or negative concentration)',
      thresholdValue: '> 0.0% Hard Bounds Violations',
      isAdaptive: false,
      lastValidated: 'Oct 05, 2024',
      status: 'Validated',
      separationMetric: 'Physical Bound Breach'
    },
    {
      id: 'FP15',
      name: 'FP15 — CoV Severity',
      description: 'Coefficient of variation cutoff for abnormal parameter dispersion',
      thresholdValue: 'CV Cutoff > 2.50',
      isAdaptive: false,
      lastValidated: 'Oct 05, 2024',
      status: 'Validated',
      separationMetric: 'Dispersion Index'
    },
    {
      id: 'CMD',
      name: 'Coordinated Missing Data',
      description: 'Synchronized telemetry missingness across regional facility clusters',
      thresholdValue: '> 1.5 σ Above Regional Median',
      isAdaptive: false,
      lastValidated: 'Oct 01, 2024',
      status: 'Validated',
      separationMetric: 'Regional Cluster Outage'
    }
  ];

  // TSI Composite Risk Legend
  const riskCategories = [
    {
      tier: 'CRITICAL',
      cutoff: '≥ 75% Composite Risk OR ≥ 4 Fingerprints Triggered',
      color: 'bg-[#D32F2F]',
      badgeBg: 'bg-[#D32F2F]/10 text-[#D32F2F] border-[#D32F2F]/20',
      action: 'Immediate unannounced physical site inspection & automated regulator dispatch.'
    },
    {
      tier: 'HIGH',
      cutoff: '50% – 74% Composite Risk OR ≥ 2 Fingerprints Triggered',
      color: 'bg-[#F57C00]',
      badgeBg: 'bg-[#F57C00]/10 text-[#F57C00] border-[#F57C00]/20',
      action: 'Issue formal notice of telemetry anomaly & schedule audit within 48 hours.'
    },
    {
      tier: 'MEDIUM',
      cutoff: '25% – 49% Composite Risk OR ≥ 1 Fingerprint Triggered',
      color: 'bg-[#E6A100]',
      badgeBg: 'bg-[#E6A100]/10 text-[#8F6400] border-[#E6A100]/30',
      action: 'Flag site for heightened surveillance & mandate sensor calibration report.'
    },
    {
      tier: 'LOW',
      cutoff: '< 25% Composite Risk',
      color: 'bg-[#1b6d24]',
      badgeBg: 'bg-[#1b6d24]/10 text-[#1b6d24] border-[#1b6d24]/20',
      action: 'Routine automated compliance surveillance.'
    }
  ];

  return (
    <div className="p-6 space-y-8">
      {/* 1. Header Banner & Propose Change Stub */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-[#f8f9fb] p-5 rounded-xl border border-[#E5E7EB]">
        <div>
          <div className="flex items-center gap-2">
            <Sliders size={20} className="text-[#00355f]" />
            <h3 className="font-headline-md text-headline-md text-[#00355f]">Empirical Threshold Configuration</h3>
            <span className="bg-[#00355f]/10 text-[#00355f] border border-[#00355f]/20 text-xs font-bold px-2.5 py-0.5 rounded-full flex items-center gap-1">
              <Lock size={12} /> READ-ONLY ENFORCEMENT
            </span>
          </div>
          <p className="text-xs text-[#42474f] mt-1 leading-relaxed">
            Statistically validated signal parameters derived from real OCEMS baseline telemetry. Live direct editing is restricted to preserve empirical integrity.
          </p>
        </div>

        <button 
          onClick={() => setShowProposeModal(true)}
          className="px-4 py-2 bg-white border border-[#E5E7EB] text-[#00355f] rounded-lg font-bold text-xs hover:bg-[#edeef0] transition-colors shadow-xs flex items-center gap-2 shrink-0"
        >
          <FileText size={14} /> Propose Threshold Change
        </button>
      </div>

      {/* 2. Fingerprint Thresholds Table */}
      <div className="bg-white border border-[#E5E7EB] rounded-xl overflow-hidden shadow-xs">
        <div className="p-4 bg-white border-b border-[#E5E7EB] flex justify-between items-center">
          <h4 className="font-body-md font-bold text-[#00355f]">Validated Fingerprint Thresholds (9 Signal Triggers)</h4>
          <span className="text-xs text-[#727780] font-bold">LOCKED EMPIRICAL SET</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#f8f9fb] border-b border-[#E5E7EB]">
                <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase">Fingerprint Name</th>
                <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase">Description</th>
                <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase">Threshold Value</th>
                <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase">Last Validated</th>
                <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase text-right">Status</th>
              </tr>
            </thead>
            <tbody className="text-table-data">
              {thresholdsData.map((row) => (
                <tr key={row.id} className="border-b border-[#E5E7EB] table-row-hover">
                  <td className="px-6 py-3.5 font-bold text-[#00355f] flex items-center gap-2">
                    <span>{row.name}</span>
                  </td>
                  <td className="px-6 py-3.5 text-[#42474f] text-xs max-w-xs">{row.description}</td>
                  <td className="px-6 py-3.5 font-bold text-[#191c1e] text-xs">
                    {row.isAdaptive ? (
                      <span className="px-2.5 py-1 bg-[#0f4c81]/10 text-[#0f4c81] rounded border border-[#0f4c81]/20 font-bold">
                        {row.thresholdValue}
                      </span>
                    ) : (
                      <span className="font-mono bg-[#f8f9fb] px-2 py-1 rounded border border-[#E5E7EB]">
                        {row.thresholdValue}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-3.5 text-[#727780] text-xs">{row.lastValidated}</td>
                  <td className="px-6 py-3.5 text-right">
                    <span className="px-2.5 py-1 bg-[#1b6d24]/10 text-[#1b6d24] border border-[#1b6d24]/20 rounded text-[11px] font-bold uppercase inline-flex items-center gap-1">
                      <CheckCircle2 size={12} /> {row.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Informational Footer Note */}
        <div className="p-4 bg-[#f8f9fb] border-t border-[#E5E7EB] text-xs text-[#727780] flex items-start gap-2">
          <Info size={16} className="text-[#0f4c81] shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            <strong>Statistical Note:</strong> Thresholds are derived from statistical validation against real OCEMS data (see Model Versions changelog). Changes require formal re-validation against the full 33-factory baseline before deployment.
          </p>
        </div>
      </div>

      {/* 3. TSI Composite Scoring Config Section */}
      <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-xs space-y-6">
        <div>
          <div className="flex justify-between items-center">
            <h3 className="font-headline-md text-headline-md text-[#00355f]">TSI Composite Scoring Configuration</h3>
            <span className="text-xs font-bold text-[#727780] bg-[#f8f9fb] px-3 py-1 rounded border border-[#E5E7EB]">
              Fingerprint Weights ($w_i$): Equal Weighting Engine (v1.0 — 8.4% per signal, 8 tracked signals)
            </span>
          </div>
          <p className="text-xs text-[#42474f] mt-1">
            Ensemble weighting formula combining a factory-level tamper model ($10\%$), Unsupervised Isolation Forest ($22.5\%$), and Fingerprint Triggers ($67.5\%$).
          </p>
        </div>

        {/* 4-Row Risk Category Legend Table */}
        <div className="overflow-x-auto border border-[#E5E7EB] rounded-lg">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#f8f9fb] border-b border-[#E5E7EB]">
                <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase w-32">Risk Tier</th>
                <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase">Trigger Cutoff Logic</th>
                <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase">Mandated Regulatory Action</th>
              </tr>
            </thead>
            <tbody className="text-table-data divide-y divide-[#E5E7EB]">
              {riskCategories.map((r) => (
                <tr key={r.tier} className="hover:bg-[#f8f9fb]">
                  <td className="px-6 py-4">
                    <span className={`px-3 py-1 rounded text-xs font-bold uppercase border ${r.badgeBg}`}>
                      {r.tier}
                    </span>
                  </td>
                  <td className="px-6 py-4 font-bold text-[#191c1e] text-xs">{r.cutoff}</td>
                  <td className="px-6 py-4 text-[#42474f] text-xs leading-relaxed">{r.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Propose Threshold Change Modal Stub */}
      {showProposeModal && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex justify-between items-center border-b border-[#E5E7EB] pb-3">
              <h3 className="font-headline-md text-headline-md text-[#00355f] flex items-center gap-2">
                <Lock size={18} className="text-[#F57C00]" /> Propose Threshold Change
              </h3>
              <button 
                onClick={() => setShowProposeModal(false)}
                className="text-[#727780] hover:text-[#191c1e] font-bold text-lg"
              >
                ✕
              </button>
            </div>

            <div className="p-4 bg-[#F57C00]/10 border border-[#F57C00]/20 rounded-lg text-xs text-[#42474f] space-y-2">
              <p className="font-bold text-[#F57C00]">Re-Validation Protocol Required</p>
              <p className="leading-relaxed">
                Direct editing of empirically validated thresholds is locked in production to prevent false positive skew. To modify thresholds:
              </p>
              <ol className="list-decimal pl-4 space-y-1 text-[#191c1e]">
                <li>Submit proposed parameter adjustments in a sandbox branch.</li>
                <li>Run automated cross-validation against the full 33-factory real-telemetry baseline.</li>
                <li>Submit formal review to the Environmental Audit Committee.</li>
              </ol>
            </div>

            <div className="text-right pt-2">
              <button 
                onClick={() => setShowProposeModal(false)}
                className="px-4 py-2 bg-[#00355f] text-white text-xs font-bold rounded-lg hover:opacity-90"
              >
                Acknowledge Protocol
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
