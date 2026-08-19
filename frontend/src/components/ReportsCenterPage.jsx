import React, { useState, useEffect } from 'react';
import { Download, FileText, Calendar, CheckCircle, Search } from 'lucide-react';
import { API_BASE_URL } from '../config';

export function ReportsCenterPage({ onNavigate }) {
  const [factories, setFactories] = useState([]);
  const [selectedFactory, setSelectedFactory] = useState(null);
  const [filterTag, setFilterTag] = useState('All');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFactories();
  }, []);

  const fetchFactories = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/factories`);
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
    try {
      const res = await fetch(`${API_BASE_URL}/api/factories/${fObj.factory_id}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedFactory(data);
      } else {
        setSelectedFactory(fObj);
      }
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
    : activeFac.stage2_prediction?.tamper_probability !== undefined
    ? `${activeFac.stage2_prediction.tamper_probability.toFixed(1)}%`
    : 'Not available';

  const anomalyScoreVal = activeFac.raw_fingerprint_signals?.anomaly_score !== undefined
    ? activeFac.raw_fingerprint_signals.anomaly_score.toFixed(2)
    : activeFac.anomaly_score !== undefined
    ? activeFac.anomaly_score.toFixed(2)
    : 'Not available';

  const tamperType = activeFac.stage2_prediction?.predicted_tamper_type || 'Not available';

  return (
    <div className="h-[calc(100vh-64px)] flex overflow-hidden">
      {/* Left Sidebar: Report Archive List (1/3) */}
      <section className="w-1/3 border-r border-[#E5E7EB] flex flex-col bg-[#f8f9fb]">
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
                  <span className="text-[10px] font-bold text-[#727780] uppercase">FR-2024-#{fItem.factory_id}</span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                    itemHigh ? 'bg-[#D32F2F]/10 text-[#D32F2F]' : itemMed ? 'bg-[#F57C00]/10 text-[#F57C00]' : 'bg-[#1b6d24]/10 text-[#1b6d24]'
                  }`}>
                    {fItem.risk_tier || 'ROUTINE'}
                  </span>
                </div>
                <h3 className="font-body-md font-bold text-[#00355f] mb-1">{fItem.factory_name || fItem.name}</h3>
                <div className="flex justify-between items-center text-xs text-[#727780]">
                  <div className="flex items-center gap-1">
                    <Calendar size={12} />
                    <span>Oct 14, 2024</span>
                  </div>
                  <div className="flex items-center gap-1 text-[#1b6d24] font-semibold">
                    <CheckCircle size={12} />
                    <span>PDF Generated</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Right Column: Dynamic PDF Preview Canvas (2/3) */}
      <section className="w-2/3 flex flex-col bg-[#edeef0] p-8 overflow-y-auto">
        <div className="max-w-3xl mx-auto w-full bg-white border border-[#E5E7EB] rounded-xl p-8 shadow-md space-y-6">
          <div className="flex justify-between items-start border-b border-[#E5E7EB] pb-6">
            <div>
              <span className="text-[10px] font-label-caps text-[#727780] uppercase">OFFICIAL COMPLIANCE DOSSIER</span>
              <h1 className="text-headline-lg font-headline-lg text-[#00355f] mt-1">{activeFac.factory_name || activeFac.name}</h1>
              <p className="text-body-sm text-[#42474f]">District: {regionStr} | License: #{licenseNo}</p>
            </div>
            <button className="bg-[#00355f] text-white px-5 py-2 rounded-lg font-bold text-body-sm flex items-center gap-2 hover:opacity-90 shadow-xs">
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
              Forensic AI evaluation of real-time telemetry from <strong className="text-[#191c1e]">{activeFac.factory_name || activeFac.name}</strong> ({regionStr}) revealed TSI risk score of <strong className="text-[#191c1e]">{activeFac.tsi_score !== undefined ? `${activeFac.tsi_score.toFixed(1)} / 100` : 'Not available'}</strong>. Stage 2 XGBoost model classified primary anomaly pattern as <strong className="text-[#D32F2F]">{tamperType}</strong>. {activeFac.stage2_prediction?.note ? `${activeFac.stage2_prediction.note} ` : ''}Automated compliance audit report compiled for inspector review.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
