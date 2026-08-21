import React, { useState, useEffect } from 'react';
import { Download } from 'lucide-react';
import { apiFetch } from '../config';

// QC FIX (2026-08): report IDs were hardcoded as FR-2024-#{factory_id} --
// a static "2024" regardless of the real date. There's no persisted
// report-generation timestamp anywhere in the backend (these dossiers are
// rendered live, on demand, not stored), so the honest real value is the
// current year at render time, not an invented per-report date.
const REPORT_YEAR = new Date().getFullYear();

export function ReportsCenterPage({ onNavigate }) {
  const [factories, setFactories] = useState([]);
  const [selectedFactory, setSelectedFactory] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [filterTag, setFilterTag] = useState('All');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFactories();
  }, []);

  const fetchFactories = async () => {
    try {
      const res = await apiFetch(`/api/factories`);
      if (res.ok) {
        const data = await res.json();
        setFactories(data);
        if (data.length > 0) {
          fetchFactoryReport(data[0]);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchFactoryReport = async (fObj) => {
    setExplanation(null);
    try {
      const [factoryRes, shapRes] = await Promise.all([
        apiFetch(`/api/factories/${fObj.factory_id}`),
        apiFetch(`/api/factories/${fObj.factory_id}/shap`)
      ]);
      setSelectedFactory(factoryRes.ok ? await factoryRes.json() : fObj);
      if (shapRes.ok) setExplanation(await shapRes.json());
    } catch (err) {
      setSelectedFactory(fObj);
    }
  };

  const filteredFactories = factories.filter(f => {
    if (filterTag === 'Critical') return f.risk_tier === 'High';
    if (filterTag === 'Routine') return f.risk_tier === 'Low' || f.risk_tier === 'Medium';
    return true;
  });

  if (loading) {
    return <div className="p-8 font-body-md text-[#42474f]">Loading Reports Center...</div>;
  }

  const activeFac = selectedFactory || factories[0] || {};
  const isHigh = activeFac.risk_tier === 'High' || activeFac.risk_tier === 'High Risk';
  const isMedium = activeFac.risk_tier === 'Medium' || activeFac.risk_tier === 'Moderate Risk';

  const regionStr = activeFac.region || activeFac.district || 'Taloja';
  const licenseNo = activeFac.consent_number || 'Not available';

  const tamperProbVal = activeFac.tamper_probability !== undefined
    ? `${activeFac.tamper_probability.toFixed(1)}%`
    : 'Not available';

  const anomalyScoreVal = activeFac.raw_fingerprint_signals?.anomaly_score !== undefined
    ? activeFac.raw_fingerprint_signals.anomaly_score.toFixed(2)
    : activeFac.anomaly_score !== undefined
    ? activeFac.anomaly_score.toFixed(2)
    : 'Not available';

  return (
    <div className="h-[calc(100vh-64px)] flex overflow-hidden print:h-auto print:block">
      {/* Left Sidebar: Report Archive List (1/3) -- hidden when printing, only
          the dossier preview on the right should end up in the exported PDF. */}
      <section className="w-1/3 border-r border-[#E5E7EB] flex flex-col bg-[#f8f9fb] print:hidden">
        <div className="p-4 border-b border-[#E5E7EB] space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-headline-md text-headline-md text-[#00355f]">Reports Center</h2>
            <span className="bg-[#00355f]/10 text-[#00355f] text-[10px] font-bold px-2 py-1 rounded">
              {factories.length} REPORTS
            </span>
          </div>

          <div className="flex flex-wrap gap-2">
            {['All', 'Critical', 'Routine'].map(tag => (
              <button
                key={tag}
                onClick={() => setFilterTag(tag)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  filterTag === tag 
                    ? 'bg-[#00355f] text-white font-bold' 
                    : 'bg-white text-[#727780] border border-[#E5E7EB] hover:border-[#00355f]'
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto divide-y divide-[#E5E7EB]">
          {filteredFactories.map((fItem) => {
            const isSelected = activeFac.factory_id === fItem.factory_id;
            const itemHigh = fItem.risk_tier === 'High';
            const itemMed = fItem.risk_tier === 'Medium';

            return (
              <div 
                key={fItem.factory_id}
                onClick={() => fetchFactoryReport(fItem)}
                className={`p-4 cursor-pointer transition-colors ${
                  isSelected ? 'bg-white border-l-4 border-[#00355f]' : 'hover:bg-white border-l-4 border-transparent'
                }`}
              >
                <div className="flex justify-between items-start mb-1">
                  <span className="text-[10px] font-bold text-[#727780] uppercase">FR-{REPORT_YEAR}-#{fItem.factory_id}</span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                    itemHigh ? 'bg-[#D32F2F]/10 text-[#D32F2F]' : itemMed ? 'bg-[#F57C00]/10 text-[#F57C00]' : 'bg-[#1b6d24]/10 text-[#1b6d24]'
                  }`}>
                    {fItem.risk_tier || 'ROUTINE'}
                  </span>
                </div>
                <h3 className="font-body-md font-bold text-[#00355f] mb-1">{fItem.factory_name || fItem.name}</h3>
                <div className="text-xs text-[#727780]">
                  {fItem.region || fItem.district || 'Not available'}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Right Column: Dynamic PDF Preview Canvas (2/3) */}
      <section className="w-2/3 flex flex-col bg-[#edeef0] p-8 overflow-y-auto print:w-full print:bg-white print:p-0 print:overflow-visible">
        <div className="max-w-3xl mx-auto w-full bg-white border border-[#E5E7EB] rounded-xl p-8 shadow-md space-y-6 print:max-w-full print:border-none print:shadow-none print:rounded-none">
          <div className="flex justify-between items-start border-b border-[#E5E7EB] pb-6">
            <div>
              <span className="text-[10px] font-label-caps text-[#727780] uppercase">OFFICIAL COMPLIANCE DOSSIER</span>
              <h1 className="text-headline-lg font-headline-lg text-[#00355f] mt-1">{activeFac.factory_name || activeFac.name}</h1>
              <p className="text-body-sm text-[#42474f]">District: {regionStr} | License: #{licenseNo}</p>
            </div>
            <button onClick={() => window.print()} className="bg-[#00355f] text-white px-5 py-2 rounded-lg font-bold text-body-sm flex items-center gap-2 hover:opacity-90 shadow-xs print:hidden">
              <Download size={16} /> Download PDF
            </button>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-[#f8f9fb] rounded-lg border border-[#E5E7EB]">
              <div className="text-[10px] font-label-caps text-[#727780] uppercase font-bold">TAMPER PROBABILITY</div>
              <div className={`text-display-kpi text-display-kpi mt-1 ${isHigh ? 'text-[#D32F2F]' : isMedium ? 'text-[#F57C00]' : 'text-[#1b6d24]'}`}>
                {tamperProbVal}
              </div>
            </div>
            <div className="p-4 bg-[#f8f9fb] rounded-lg border border-[#E5E7EB]">
              <div className="text-[10px] font-label-caps text-[#727780] uppercase font-bold">ANOMALY SCORE</div>
              <div className={`text-display-kpi text-display-kpi mt-1 ${isHigh ? 'text-[#D32F2F]' : isMedium ? 'text-[#F57C00]' : 'text-[#1b6d24]'}`}>
                {anomalyScoreVal}
              </div>
            </div>
          </div>

          <div className="space-y-3 pt-4 border-t border-[#E5E7EB]">
            <h3 className="font-headline-md text-headline-md text-[#00355f]">Executive Summary & Evidence</h3>
            <p className="text-body-sm text-[#42474f] leading-relaxed">
              Forensic AI evaluation of real-time telemetry from <strong className="text-[#191c1e]">{activeFac.factory_name || activeFac.name}</strong> ({regionStr}) revealed TSI risk score of <strong className="text-[#191c1e]">{activeFac.tsi_score !== undefined ? `${activeFac.tsi_score.toFixed(1)} / 100` : 'Not available'}</strong>. {activeFac.note ? `${activeFac.note} ` : ''}Automated compliance audit report compiled for inspector review.
            </p>
          </div>

          {/* Composite Score Breakdown -- same /shap endpoint and arithmetic as the AI Analysis & Explainability page */}
          <div className="space-y-3 pt-4 border-t border-[#E5E7EB]">
            <h3 className="font-headline-md text-headline-md text-[#00355f]">Composite Risk Score Breakdown</h3>
            {!explanation?.composite_breakdown ? (
              <p className="text-body-sm text-[#727780]">Composite breakdown not available for this factory.</p>
            ) : (
              <table className="w-full text-body-sm">
                <tbody>
                  <tr className="border-b border-[#E5E7EB]">
                    <td className="py-1.5 text-[#42474f]">Fingerprint Checks ({(explanation.composite_breakdown.fingerprints.weight * 100).toFixed(1)}% weight, {explanation.composite_breakdown.fingerprints.triggered_count}/{explanation.composite_breakdown.fingerprints.total_checks} triggered)</td>
                    <td className="py-1.5 text-right font-bold text-[#191c1e]">{explanation.composite_breakdown.fingerprints.contribution}</td>
                  </tr>
                  <tr className="border-b border-[#E5E7EB]">
                    <td className="py-1.5 text-[#42474f]">Isolation Forest ({(explanation.composite_breakdown.isolation_forest.weight * 100).toFixed(1)}% weight)</td>
                    <td className="py-1.5 text-right font-bold text-[#191c1e]">{explanation.composite_breakdown.isolation_forest.contribution}</td>
                  </tr>
                  <tr className="border-b border-[#E5E7EB]">
                    <td className="py-1.5 text-[#42474f]">Factory-Level Tamper Model ({(explanation.composite_breakdown.tamper_model.weight * 100).toFixed(1)}% weight)</td>
                    <td className="py-1.5 text-right font-bold text-[#191c1e]">{explanation.composite_breakdown.tamper_model.contribution}</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 font-bold text-[#00355f]">Total Risk Score</td>
                    <td className="py-1.5 text-right font-bold text-[#00355f]">{explanation.composite_breakdown.total_risk_score}</td>
                  </tr>
                </tbody>
              </table>
            )}
          </div>

          {/* Fingerprint Checks -- which of the 8 triggered, and why */}
          <div className="space-y-3 pt-4 border-t border-[#E5E7EB]">
            <h3 className="font-headline-md text-headline-md text-[#00355f]">Fingerprint Check Detail</h3>
            {!explanation?.fingerprint_checks?.length ? (
              <p className="text-body-sm text-[#727780]">Fingerprint check detail not available for this factory.</p>
            ) : (
              <ul className="text-body-sm text-[#42474f] space-y-1">
                {explanation.fingerprint_checks.map((chk) => (
                  <li key={chk.key} className="flex justify-between gap-4">
                    <span className={chk.triggered ? 'font-bold text-[#D32F2F]' : ''}>
                      {chk.triggered ? '⚠ ' : '✓ '}{chk.label}
                    </span>
                    <span className="text-xs text-[#727780]">
                      {chk.raw_value === null ? 'Not available' : `value: ${chk.raw_value.toFixed(2)}${chk.unit}`} (trigger: {chk.threshold_desc})
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* SHAP Explanation Summary -- reuses the same precomputed explanations as the AI Analysis & Explainability page */}
          <div className="space-y-3 pt-4 border-t border-[#E5E7EB]">
            <h3 className="font-headline-md text-headline-md text-[#00355f]">SHAP Feature Attribution</h3>
            {!explanation?.shap ? (
              <p className="text-body-sm text-[#727780]">SHAP explanation not available for this factory.</p>
            ) : (
              <div className="grid grid-cols-2 gap-6 text-body-sm">
                <div>
                  <div className="text-xs font-bold text-[#727780] uppercase mb-1">Tamper Model (top drivers)</div>
                  <ul className="space-y-0.5 text-[#42474f]">
                    {explanation.shap.tamper_model_shap?.features.slice(0, 3).map((f, idx) => (
                      <li key={idx}>{f.label}: <strong className={f.shap_value_logit > 0 ? 'text-[#D32F2F]' : 'text-[#1b6d24]'}>{f.shap_value_logit > 0 ? '+' : ''}{f.shap_value_logit}</strong></li>
                    ))}
                  </ul>
                </div>
                <div>
                  <div className="text-xs font-bold text-[#727780] uppercase mb-1">Isolation Forest (top drivers)</div>
                  <ul className="space-y-0.5 text-[#42474f]">
                    {explanation.shap.isolation_forest_shap?.features.slice(0, 3).map((f, idx) => (
                      <li key={idx}>{f.label}: <strong className={f.shap_value < 0 ? 'text-[#D32F2F]' : 'text-[#1b6d24]'}>{f.shap_value}</strong></li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
