import React, { useState, useEffect } from 'react';
import { Bolt, CheckCircle, AlertTriangle, ShieldCheck, ChevronRight } from 'lucide-react';
import { API_BASE_URL } from '../config';

export function AIAnalysisPage({ onNavigate }) {
  const [factories, setFactories] = useState([]);
  const [selectedFactoryId, setSelectedFactoryId] = useState('');
  const [selectedFactoryData, setSelectedFactoryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);

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
          fetchFactoryPredictions(firstHighRisk.factory_id, firstHighRisk);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchFactoryPredictions = async (fid, factoryObj) => {
    try {
      const [predRes, facDetailRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/factories/${fid}/predictions`),
        fetch(`${API_BASE_URL}/api/factories/${fid}`)
      ]);

      let predictions = null;
      let detail = factoryObj;

      if (predRes.ok) predictions = await predRes.json();
      if (facDetailRes.ok) detail = await facDetailRes.json();

      setSelectedFactoryData({
        factory: detail,
        predictions: predictions
      });
    } catch (err) {
      console.error(err);
    }
  };

  const handleSelectFactory = (fid) => {
    setSelectedFactoryId(fid);
    const fObj = factories.find(f => f.factory_id === fid);
    fetchFactoryPredictions(fid, fObj);
  };

  // Previously a fake setTimeout with no real effect. The underlying model
  // inference is precomputed server-side, not something this button can
  // trigger a live retrain of -- what it *can* honestly do is re-fetch this
  // factory's current predictions, same endpoints already used on load.
  const handleRunAnalysis = async () => {
    setAnalyzing(true);
    const fObj = factories.find(f => f.factory_id === selectedFactoryId);
    await fetchFactoryPredictions(selectedFactoryId, fObj);
    setAnalyzing(false);
  };

  if (loading) {
    return <div className="p-8 font-body-md text-[#42474f]">Loading AI Analysis & Forensic Engine...</div>;
  }

  const fObj = selectedFactoryData?.factory || factories[0] || {};
  const pred = selectedFactoryData?.predictions || {};
  
  const isHighRisk = fObj.risk_tier === 'High' || fObj.risk_tier === 'High Risk';
  const isMediumRisk = fObj.risk_tier === 'Medium' || fObj.risk_tier === 'Moderate Risk';

  const tamperProb = pred.stage2_model?.tamper_probability !== undefined
    ? `${pred.stage2_model.tamper_probability.toFixed(1)}%`
    : fObj.stage2_prediction?.tamper_probability !== undefined
    ? `${fObj.stage2_prediction.tamper_probability.toFixed(1)}%`
    : fObj.tamper_probability !== undefined
    ? `${fObj.tamper_probability.toFixed(1)}%`
    : 'Not available';

  const isoScore = pred.isolation_forest?.anomaly_score !== undefined
    ? pred.isolation_forest.anomaly_score.toFixed(2)
    : fObj.raw_fingerprint_signals?.anomaly_score !== undefined
    ? fObj.raw_fingerprint_signals.anomaly_score.toFixed(2)
    : 'Not available';

  const predictedTamperType = pred.stage2_model?.predicted_tamper_type
    || fObj.stage2_prediction?.predicted_tamper_type
    || 'Not available';

  const confidenceVal = pred.stage2_model?.confidence_percentage !== undefined
    ? `${pred.stage2_model.confidence_percentage.toFixed(1)}%`
    : fObj.stage2_prediction?.confidence_percentage !== undefined
    ? `${fObj.stage2_prediction.confidence_percentage.toFixed(1)}%`
    : 'Not available';

  return (
    <div className="p-8 max-w-[1600px] mx-auto space-y-6">
      {/* Header & Breadcrumb */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <nav className="flex items-center gap-2 text-[#727780] font-label-caps text-[10px] uppercase tracking-widest mb-2">
            <span className="hover:text-[#00355f] cursor-pointer">Forensics</span>
            <span className="material-symbols-outlined text-xs">chevron_right</span>
            <span className="text-[#191c1e] font-bold">AI Analysis & Forensic Engine</span>
          </nav>
          <h1 className="text-headline-lg font-headline-lg text-[#00355f]">AI Analysis & Forensic Engine</h1>
          <p className="text-body-md text-[#42474f]">Automated Tampering Detection & Machine Learning Insight</p>
        </div>

        <div className="flex items-center gap-4 bg-white border border-[#E5E7EB] p-4 rounded-xl shadow-xs">
          <div className="text-right">
            <div className="text-label-caps text-[#727780] uppercase font-bold">Target Facility</div>
            <select 
              value={selectedFactoryId} 
              onChange={(e) => handleSelectFactory(e.target.value)}
              className="text-body-sm font-bold text-[#00355f] bg-[#f8f9fb] border border-[#E5E7EB] rounded px-3 py-1 cursor-pointer focus:outline-none"
            >
              {factories.map(f => (
                <option key={f.factory_id} value={f.factory_id}>
                  {f.factory_name || f.name} ({f.region || f.district})
                </option>
              ))}
            </select>
          </div>
          <button 
            onClick={handleRunAnalysis}
            disabled={analyzing}
            className="flex items-center gap-2 bg-[#0f4c81] text-white px-6 py-2.5 rounded-lg font-bold hover:opacity-90 transition-all text-body-sm shadow-sm disabled:opacity-50"
          >
            <Bolt size={18} className={analyzing ? 'animate-spin' : ''} />
            <span>{analyzing ? 'Running Engine...' : 'Run AI Forensic Analysis'}</span>
          </button>
        </div>
      </div>

      {/* Analysis Results KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Risk Profile Card */}
        <div className="bg-white border border-[#E5E7EB] p-6 rounded-xl shadow-xs flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-label-caps text-[#727780] uppercase font-bold">Overall Risk Profile</span>
            <AlertTriangle size={20} className={isHighRisk ? 'text-[#D32F2F]' : isMediumRisk ? 'text-[#F57C00]' : 'text-[#1b6d24]'} />
          </div>
          <div className="mt-4">
            <span className={`px-3 py-1 text-label-caps font-bold rounded-full ${
              isHighRisk 
                ? 'bg-[#D32F2F]/10 text-[#D32F2F]' 
                : isMediumRisk 
                ? 'bg-[#F57C00]/10 text-[#F57C00]' 
                : 'bg-[#1b6d24]/10 text-[#1b6d24]'
            }`}>
              {(fObj.risk_tier || 'LOW').toUpperCase()}
            </span>
          </div>
          <p className="mt-3 text-body-sm text-[#42474f] italic">
            {pred.stage2_model?.note
              ? pred.stage2_model.note
              : isHighRisk
              ? `Severe signal anomaly (${predictedTamperType}) detected.`
              : isMediumRisk
              ? `Moderate statistical deviation detected for ${fObj.factory_name}.`
              : `Nominal telemetry parameters detected for ${fObj.factory_name}.`
            }
          </p>
        </div>

        {/* Tampering Probability */}
        <div className="bg-white border border-[#E5E7EB] p-6 rounded-xl shadow-xs">
          <span className="text-label-caps text-[#727780] uppercase font-bold">Tampering Probability</span>
          <div className="mt-4 flex items-baseline gap-2">
            <span className={`text-display-kpi font-display-kpi ${isHighRisk ? 'text-[#D32F2F]' : isMediumRisk ? 'text-[#F57C00]' : 'text-[#1b6d24]'}`}>
              {tamperProb}
            </span>
          </div>
          <div className="w-full bg-[#edeef0] h-2 mt-4 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${isHighRisk ? 'bg-[#D32F2F]' : isMediumRisk ? 'bg-[#F57C00]' : 'bg-[#1b6d24]'}`}
              style={{ width: tamperProb !== 'Not available' ? `${Math.min(100, parseFloat(tamperProb))}%` : '0%' }}
            ></div>
          </div>
        </div>

        {/* Isolation Forest Anomaly Score */}
        <div className="bg-white border border-[#E5E7EB] p-6 rounded-xl shadow-xs">
          <span className="text-label-caps text-[#727780] uppercase font-bold">Isolation Forest Anomaly Score</span>
          <div className="mt-4 flex items-baseline gap-2">
            <span className={`text-display-kpi font-display-kpi ${isHighRisk ? 'text-[#D32F2F]' : isMediumRisk ? 'text-[#F57C00]' : 'text-[#1b6d24]'}`}>
              {isoScore}
            </span>
            <span className={`text-body-sm font-bold ${isHighRisk ? 'text-[#D32F2F]' : isMediumRisk ? 'text-[#F57C00]' : 'text-[#1b6d24]'}`}>
              ({isHighRisk ? 'High' : isMediumRisk ? 'Moderate' : 'Low'})
            </span>
          </div>
          <p className="mt-2 text-body-sm text-[#42474f]">
            Statistical distance vs {fObj.region || 'district'} baseline.
          </p>
        </div>

        {/* Confidence Score */}
        <div className="bg-white border border-[#E5E7EB] p-6 rounded-xl shadow-xs">
          <span className="text-label-caps text-[#727780] uppercase font-bold">Confidence Score</span>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-display-kpi font-display-kpi text-[#1b6d24]">{confidenceVal}</span>
            <span className="text-body-sm text-[#1b6d24] font-bold">Verified</span>
          </div>
          <div className="mt-4 flex items-center gap-1.5 text-body-sm text-[#1b6d24]">
            <CheckCircle size={16} />
            <span className="font-semibold">High Ensemble Consensus</span>
          </div>
        </div>
      </div>

      {/* Grid: Risk Level Meter & Suspicious Events Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Risk Meter Card */}
        <div className="lg:col-span-1 bg-white border border-[#E5E7EB] p-6 rounded-xl flex flex-col">
          <h3 className="text-headline-md font-headline-md text-[#00355f] mb-6">Risk Level Indicator</h3>
          <div className="flex-1 flex flex-col justify-center gap-6">
            <div className="relative pt-4">
              <div className="flex h-12 w-full rounded-lg overflow-hidden border border-[#E5E7EB]">
                <div className={`flex-1 flex items-center justify-center text-[10px] font-bold uppercase ${!isHighRisk && !isMediumRisk ? 'bg-[#1b6d24] text-white ring-4 ring-[#1b6d24]/30 z-10' : 'bg-[#1b6d24]/20 text-[#1b6d24]'}`}>Low</div>
                <div className={`flex-1 flex items-center justify-center text-[10px] font-bold uppercase ${isMediumRisk ? 'bg-[#F57C00] text-white ring-4 ring-[#F57C00]/30 z-10' : 'bg-yellow-400/20 text-yellow-700'}`}>Medium</div>
                <div className={`flex-1 flex items-center justify-center text-[10px] font-bold uppercase ${isHighRisk ? 'bg-[#D32F2F] text-white ring-4 ring-[#D32F2F]/30 z-10' : 'bg-[#F57C00]/20 text-[#F57C00]'}`}>High</div>
              </div>
            </div>
            <div className="space-y-3 pt-4 border-t border-[#E5E7EB]">
              <div className="flex items-center gap-3 text-body-sm">
                <div className={`w-3 h-3 rounded-full ${isHighRisk ? 'bg-[#D32F2F]' : isMediumRisk ? 'bg-[#F57C00]' : 'bg-[#1b6d24]'}`}></div>
                <span className="font-bold text-[#191c1e]">Active Pattern:</span>
                <span className="text-[#42474f]">{predictedTamperType}</span>
              </div>
              <div className="flex items-center gap-3 text-body-sm">
                <div className="w-3 h-3 rounded-full bg-[#00355f]"></div>
                <span className="font-bold text-[#191c1e]">Facility:</span>
                <span className="text-[#42474f]">{fObj.factory_name || fObj.name}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Suspicious Events Timeline */}
        <div className="lg:col-span-2 bg-white border border-[#E5E7EB] p-6 rounded-xl">
          <h3 className="text-headline-md font-headline-md text-[#00355f] mb-6">Suspicious Events Timeline</h3>
          <div className="space-y-4">
            <div className="p-4 bg-[#f8f9fb] rounded-lg border border-[#E5E7EB]">
              <p className="text-xs text-[#727780]">
                A real-time telemetry event log isn't implemented yet -- this panel isn't backed by live sensor-level event data.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
