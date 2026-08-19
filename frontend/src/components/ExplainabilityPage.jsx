import React, { useState, useEffect } from 'react';
import { Download, Gavel, ChevronRight, HelpCircle } from 'lucide-react';
import { API_BASE_URL } from '../config';

export function ExplainabilityPage({ onNavigate }) {
  const [factories, setFactories] = useState([]);
  const [selectedFactoryId, setSelectedFactoryId] = useState('');
  const [shapData, setShapData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/factories`);
      if (res.ok) {
        const data = await res.json();
        setFactories(data);
        if (data.length > 0) {
          const firstHighRisk = data.find(f => f.risk_tier === 'High') || data[0];
          setSelectedFactoryId(firstHighRisk.factory_id);
          fetchShap(firstHighRisk.factory_id);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchShap = async (fid) => {
    try {
      const [sRes, fRes, pRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/factories/${fid}/shap`),
        fetch(`${API_BASE_URL}/api/factories/${fid}`),
        fetch(`${API_BASE_URL}/api/factories/${fid}/predictions`)
      ]);

      let shapList = null;
      let fac = null;
      let pred = null;

      if (sRes.ok) shapList = await sRes.json();
      if (fRes.ok) fac = await fRes.json();
      if (pRes.ok) pred = await pRes.json();

      setShapData({
        shap: shapList,
        factory: fac,
        prediction: pred
      });
    } catch (err) {
      console.error(err);
    }
  };

  const handleSelectFactory = (fid) => {
    setSelectedFactoryId(fid);
    fetchShap(fid);
  };

  if (loading) {
    return <div className="p-8 font-body-md text-[#42474f]">Loading Explainability & Reasoning...</div>;
  }

  const fObj = shapData?.factory || factories[0] || {};
  const predObj = shapData?.prediction?.stage2_model || fObj.stage2_prediction || {};
  const isHighRisk = fObj.risk_tier === 'High' || fObj.risk_tier === 'High Risk';
  const isMediumRisk = fObj.risk_tier === 'Medium' || fObj.risk_tier === 'Moderate Risk';

  // Format real SHAP features from database API response
  const rawShapList = Array.isArray(shapData?.shap) ? shapData.shap : [];
  
  const topShap = rawShapList.slice(0, 5).map(item => {
    const sVal = Math.abs(item.shap_value || 0);
    const pctVal = Math.min(95, Math.max(15, Math.round(sVal * 100)));
    return {
      feature: item.fingerprint_name || 'Not available',
      contribution: item.shap_value !== undefined ? item.shap_value.toFixed(2) : 'Not available',
      pct: pctVal,
      direction: item.direction || 'NEUTRAL'
    };
  });

  const predictedTamperClass = predObj.predicted_tamper_type || 'Not available';

  const tamperProbVal = predObj.tamper_probability !== undefined
    ? `${predObj.tamper_probability.toFixed(1)}%`
    : fObj.tamper_probability !== undefined
    ? `${fObj.tamper_probability.toFixed(1)}%`
    : 'Not available';

  return (
    <div className="p-8 max-w-[1600px] mx-auto space-y-8">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <nav className="flex items-center gap-2 text-[#727780] font-label-caps text-[10px] uppercase tracking-widest mb-2">
            <span>ANOMALY DETECTION</span>
            <span className="material-symbols-outlined text-xs">chevron_right</span>
            <span>ANALYSIS</span>
            <span className="material-symbols-outlined text-xs">chevron_right</span>
            <span className="text-[#00355f] font-bold">EXPLAINABILITY</span>
          </nav>
          <h2 className="text-headline-lg font-headline-lg text-[#00355f]">Why was this factory flagged?</h2>
          <p className="text-body-md text-[#42474f] mt-1">
            Facility: <span className="font-bold text-[#191c1e]">{fObj.factory_name || fObj.name}</span> | ID: #{fObj.factory_id}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select 
            value={selectedFactoryId} 
            onChange={(e) => handleSelectFactory(e.target.value)}
            className="text-body-sm font-bold text-[#00355f] bg-white border border-[#E5E7EB] rounded-lg px-4 py-2 cursor-pointer focus:outline-none"
          >
            {factories.map(f => (
              <option key={f.factory_id} value={f.factory_id}>
                {f.factory_name || f.name} ({f.region || f.district})
              </option>
            ))}
          </select>

          <button className="px-4 py-2 border border-[#E5E7EB] rounded-lg text-body-sm font-bold text-[#191c1e] flex items-center gap-2 hover:bg-[#f8f9fb] transition-all bg-white">
            <Download size={16} /> Export Analysis
          </button>
          <button className="px-4 py-2 bg-[#00355f] text-white rounded-lg text-body-sm font-bold flex items-center gap-2 hover:opacity-90 transition-all shadow-sm">
            <Gavel size={16} /> Escalate Case
          </button>
        </div>
      </div>

      {/* Grid: SHAP Feature Importance + Meta-Data Card */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* SHAP Feature Importance */}
        <div className="lg:col-span-8 bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-xs">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-headline-md font-headline-md text-[#00355f] flex items-center gap-2">
              <span className="material-symbols-outlined text-[#00355f]" style={{ fontVariationSettings: "'FILL' 1" }}>analytics</span>
              SHAP Feature Attributions ({fObj.factory_name || fObj.name})
            </h3>
            <span className="text-label-caps font-label-caps bg-[#00355f]/10 text-[#00355f] px-3 py-1 rounded-full font-bold">
              LIGHTGBM SHAP EXPLAINER
            </span>
          </div>

          <div className="space-y-6">
            {topShap.length === 0 ? (
              <p className="text-body-sm text-[#727780]">No SHAP attribution data available for this factory.</p>
            ) : topShap.map((item, idx) => (
              <div key={idx} className="space-y-2">
                <div className="flex justify-between text-body-sm font-bold text-[#191c1e]">
                  <span>{item.feature}</span>
                  <span className={item.pct > 50 ? 'text-[#D32F2F]' : 'text-[#F57C00]'}>
                    +{item.contribution} SHAP Value ({item.direction})
                  </span>
                </div>
                <div className="w-full h-4 bg-[#f2f4f6] rounded-full overflow-hidden">
                  <div 
                    className="h-full rounded-full transition-all duration-1000" 
                    style={{ 
                      width: `${item.pct}%`, 
                      backgroundColor: item.pct > 50 ? '#D32F2F' : item.pct > 30 ? '#F57C00' : '#1b6d24' 
                    }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Inference Decision Details */}
        <div className="lg:col-span-4 bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-xs flex flex-col justify-between">
          <div>
            <h3 className="text-headline-md font-headline-md text-[#00355f] mb-4">Model Decision Summary</h3>
            <div className="p-4 bg-[#f8f9fb] rounded-lg border border-[#E5E7EB] space-y-3">
              <div>
                <div className="text-[10px] font-label-caps text-[#727780] uppercase">Predicted Class</div>
                <div className={`text-body-md font-bold ${isHighRisk ? 'text-[#D32F2F]' : isMediumRisk ? 'text-[#F57C00]' : 'text-[#1b6d24]'}`}>
                  {predictedTamperClass}
                </div>
              </div>
              <div>
                <div className="text-[10px] font-label-caps text-[#727780] uppercase font-bold">Tamper Probability</div>
                <div className={`text-display-kpi font-display-kpi ${isHighRisk ? 'text-[#D32F2F]' : isMediumRisk ? 'text-[#F57C00]' : 'text-[#1b6d24]'}`}>
                  {tamperProbVal}
                </div>
              </div>
              <div>
                <div className="text-[10px] font-label-caps text-[#727780] uppercase font-bold">TSI Score</div>
                <div className="text-body-sm font-semibold text-[#191c1e]">{fObj.tsi_score !== undefined ? `${fObj.tsi_score.toFixed(1)} / 100` : 'Not available'}</div>
              </div>
            </div>
          </div>

          <button 
            className="w-full mt-6 py-2.5 bg-[#f8f9fb] border border-[#E5E7EB] text-[#00355f] font-bold text-body-sm rounded-lg hover:bg-[#edeef0] transition-colors"
            onClick={() => onNavigate('factory-detail', fObj.factory_id)}
          >
            View Complete Factory Dossier →
          </button>
        </div>
      </div>
    </div>
  );
}
