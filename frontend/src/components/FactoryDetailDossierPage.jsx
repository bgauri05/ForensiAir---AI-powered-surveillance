import React, { useState, useEffect } from 'react';
import { Download, ShieldAlert, ArrowLeft, Factory, FileText, CheckCircle } from 'lucide-react';
import { API_BASE_URL } from '../config';

export function FactoryDetailDossierPage({ onNavigate, selectedFactoryId }) {
  const [factoriesList, setFactoriesList] = useState([]);
  const [selectedFid, setSelectedFid] = useState(selectedFactoryId || '');
  const [factoryData, setFactoryData] = useState(null);
  const [inspections, setInspections] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFactories();
  }, []);

  // 'factories' and 'factory-detail' both render this same component, so
  // switching between them doesn't remount it -- if the user clicks a
  // different factory elsewhere while this page is already mounted, this
  // catches the prop change and re-fetches instead of silently keeping the
  // previously-loaded factory on screen.
  useEffect(() => {
    if (selectedFactoryId && selectedFactoryId !== selectedFid) {
      setSelectedFid(selectedFactoryId);
      fetchFactoryDetail(selectedFactoryId);
    }
  }, [selectedFactoryId]);

  const fetchFactories = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/factories`);
      if (res.ok) {
        const data = await res.json();
        setFactoriesList(data);
        if (data.length > 0) {
          // Previously always defaulted to data[0] regardless of which
          // factory the user actually clicked elsewhere in the app.
          const initialFid = selectedFactoryId || data[0].factory_id;
          setSelectedFid(initialFid);
          fetchFactoryDetail(initialFid);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchFactoryDetail = async (fid) => {
    try {
      const [factoryRes, inspectionsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/factories/${fid}`),
        fetch(`${API_BASE_URL}/api/factories/${fid}/inspections`)
      ]);
      if (factoryRes.ok) {
        setFactoryData(await factoryRes.json());
      }
      setInspections(inspectionsRes.ok ? await inspectionsRes.json() : []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSelectFactory = (fid) => {
    setSelectedFid(fid);
    fetchFactoryDetail(fid);
  };

  if (loading) {
    return <div className="p-8 font-body-md text-[#42474f]">Loading Factory Dossier...</div>;
  }

  const fObj = factoryData || factoriesList[0] || {};
  const isHighRisk = fObj.risk_tier === 'High' || fObj.risk_tier === 'High Risk';
  const isMediumRisk = fObj.risk_tier === 'Medium' || fObj.risk_tier === 'Moderate Risk';

  // Dynamic calculations based on DB factory object
  const regionStr = fObj.region || fObj.district || 'Taloja';
  const licenseNo = fObj.consent_number || 'Not available';
  const plotAddress = fObj.address || 'Not available';
  const plantHead = fObj.contact_person || 'Not available';

  const bodAvg = fObj.avg_bod !== undefined ? `${fObj.avg_bod} mg/L` : 'Not available';
  const codAvg = fObj.avg_cod !== undefined ? `${fObj.avg_cod} mg/L` : 'Not available';
  const phAvg = 'Not available';

  const tamperProbVal = fObj.tamper_probability !== undefined
    ? `${fObj.tamper_probability.toFixed(1)}%`
    : fObj.stage2_prediction?.tamper_probability !== undefined
    ? `${fObj.stage2_prediction.tamper_probability.toFixed(1)}%`
    : 'Not available';

  const anomalyScoreVal = fObj.raw_fingerprint_signals?.anomaly_score !== undefined
    ? fObj.raw_fingerprint_signals.anomaly_score.toFixed(2)
    : fObj.anomaly_score !== undefined
    ? fObj.anomaly_score.toFixed(2)
    : 'Not available';

  const confidenceVal = fObj.stage2_prediction?.confidence_percentage !== undefined
    ? `${fObj.stage2_prediction.confidence_percentage.toFixed(1)}%`
    : 'Not available';

  const tamperType = fObj.stage2_prediction?.predicted_tamper_type || 'Not available';

  return (
    <div className="space-y-6">
      {/* Top Header Banner */}
      <div className="bg-white border-b border-[#E5E7EB] px-8 py-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <button 
                onClick={() => onNavigate('dashboard')}
                className="p-1.5 hover:bg-[#f8f9fb] rounded-full transition-colors"
              >
                <ArrowLeft size={18} className="text-[#00355f]" />
              </button>
              <h2 className="font-headline-lg text-headline-lg text-[#00355f]">{fObj.factory_name || fObj.name}</h2>
              <span className={`px-3 py-1 rounded text-[11px] font-bold uppercase ${
                isHighRisk 
                  ? 'bg-[#D32F2F]/10 text-[#D32F2F] border border-[#D32F2F]/20' 
                  : isMediumRisk 
                  ? 'bg-[#F57C00]/10 text-[#F57C00] border border-[#F57C00]/20' 
                  : 'bg-[#1b6d24]/10 text-[#1b6d24] border border-[#1b6d24]/20'
              }`}>
                {fObj.risk_tier || 'LOW RISK'}
              </span>
            </div>
            <div className="flex flex-wrap gap-6 text-[#42474f] text-body-sm">
              <div>Industry: <span className="font-bold text-[#191c1e]">{fObj.industry || 'Chemical Manufacturing'}</span></div>
              <div>District: <span className="font-bold text-[#191c1e]">{regionStr}</span></div>
              <div>ID: <span className="font-bold text-[#191c1e]">#{fObj.factory_id}</span></div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <select 
              value={selectedFid} 
              onChange={(e) => handleSelectFactory(e.target.value)}
              className="bg-white border border-[#E5E7EB] rounded-lg px-3 py-2 text-body-sm font-bold text-[#00355f] cursor-pointer"
            >
              {factoriesList.map(f => (
                <option key={f.factory_id} value={f.factory_id}>
                  {f.factory_name || f.name} ({f.region || f.district})
                </option>
              ))}
            </select>

            <button className="px-4 py-2 border border-[#E5E7EB] rounded-lg text-body-sm font-bold flex items-center gap-2 hover:bg-[#f8f9fb] bg-white text-[#191c1e]">
              <Download size={16} /> Export Dossier
            </button>
            <button className="px-4 py-2 bg-[#00355f] text-white rounded-lg text-body-sm font-bold flex items-center gap-2 hover:opacity-90 shadow-sm">
              <ShieldAlert size={16} /> Initiate Audit
            </button>
          </div>
        </div>
      </div>

      {/* Main Dossier Content */}
      <div className="px-8 pb-12 max-w-[1600px] mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Dynamic Metadata & License Info */}
        <div className="lg:col-span-4 space-y-6">
          <div className="bg-white border border-[#E5E7EB] p-6 rounded-xl shadow-xs">
            <h3 className="font-label-caps text-label-caps text-[#727780] uppercase mb-4 font-bold">Core Facility Metadata</h3>
            <div className="space-y-4 text-body-sm">
              <div>
                <p className="text-[11px] text-[#727780] font-bold uppercase mb-0.5">Environmental License</p>
                <p className="font-bold text-[#191c1e]">{licenseNo}</p>
              </div>
              <div>
                <p className="text-[11px] text-[#727780] font-bold uppercase mb-0.5">Location / Address</p>
                <p className="font-medium text-[#191c1e]">{plotAddress}</p>
              </div>
              <div>
                <p className="text-[11px] text-[#727780] font-bold uppercase mb-0.5">Inspection Contact</p>
                <p className="font-medium text-[#191c1e]">{plantHead}</p>
              </div>
            </div>
          </div>

          <div className="bg-white border border-[#E5E7EB] p-6 rounded-xl shadow-xs">
            <h3 className="font-label-caps text-label-caps text-[#727780] uppercase mb-4 font-bold">Consent Limit Parameters</h3>
            <div className="space-y-3.5">
              <div className="p-3 bg-[#f8f9fb] rounded-lg border border-[#E5E7EB]">
                <div className="flex justify-between text-body-sm font-bold">
                  <span>BOD Concentration</span>
                  <span className="text-[#D32F2F]">30 mg/L Max Limit</span>
                </div>
                <div className="text-xs text-[#42474f] mt-1">Current telemetry average: <strong className="text-[#191c1e]">{bodAvg}</strong></div>
              </div>
              <div className="p-3 bg-[#f8f9fb] rounded-lg border border-[#E5E7EB]">
                <div className="flex justify-between text-body-sm font-bold">
                  <span>COD Concentration</span>
                  <span className="text-[#F57C00]">250 mg/L Max Limit</span>
                </div>
                <div className="text-xs text-[#42474f] mt-1">Current telemetry average: <strong className="text-[#191c1e]">{codAvg}</strong></div>
              </div>
              <div className="p-3 bg-[#f8f9fb] rounded-lg border border-[#E5E7EB]">
                <div className="flex justify-between text-body-sm font-bold">
                  <span>pH Tolerance Range</span>
                  <span className="text-[#1b6d24]">5.5 - 9.0 pH</span>
                </div>
                <div className="text-xs text-[#42474f] mt-1">Current telemetry average: <strong className="text-[#191c1e]">{phAvg}</strong></div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Dynamic AI Analysis Summary & History */}
        <div className="lg:col-span-8 space-y-6">
          <div className="bg-white border border-[#E5E7EB] p-6 rounded-xl shadow-xs">
            <h3 className="font-headline-md text-headline-md text-[#00355f] mb-4">AI Tamper Risk Evaluation</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
              <div className="p-4 bg-[#f8f9fb] border border-[#E5E7EB] rounded-lg">
                <span className="text-label-caps text-[#727780] font-bold">TAMPER PROBABILITY</span>
                <div className={`font-display-kpi text-display-kpi mt-1 ${isHighRisk ? 'text-[#D32F2F]' : isMediumRisk ? 'text-[#F57C00]' : 'text-[#1b6d24]'}`}>
                  {tamperProbVal}
                </div>
              </div>
              <div className="p-4 bg-[#f8f9fb] border border-[#E5E7EB] rounded-lg">
                <span className="text-label-caps text-[#727780] font-bold">ANOMALY SCORE</span>
                <div className={`font-display-kpi text-display-kpi mt-1 ${isHighRisk ? 'text-[#D32F2F]' : isMediumRisk ? 'text-[#F57C00]' : 'text-[#1b6d24]'}`}>
                  {anomalyScoreVal}
                </div>
              </div>
              <div className="p-4 bg-[#f8f9fb] border border-[#E5E7EB] rounded-lg">
                <span className="text-label-caps text-[#727780] font-bold">CONFIDENCE</span>
                <div className="font-display-kpi text-display-kpi text-[#1b6d24] mt-1">{confidenceVal}</div>
              </div>
            </div>

            <div className="p-4 bg-[#f8f9fb] rounded-lg border border-[#E5E7EB]">
              <div className="font-body-sm font-bold text-[#191c1e] mb-1">Inspector Recommendation</div>
              <p className="text-xs text-[#42474f] leading-relaxed">
                {fObj.stage2_prediction?.note
                  ? fObj.stage2_prediction.note
                  : isHighRisk
                  ? `Stage 2 XGBoost classification detected active "${tamperType}" for ${fObj.factory_name || fObj.name}. Priority physical audit recommended for sensor calibration verification.`
                  : isMediumRisk
                  ? `Moderate telemetry variance detected for ${fObj.factory_name || fObj.name}. Scheduled calibration check recommended within 48 hours.`
                  : `Telemetry for ${fObj.factory_name || fObj.name} is operating within nominal environmental compliance thresholds. Continue routine automated monitoring.`
                }
              </p>
            </div>
          </div>

          <div className="bg-white border border-[#E5E7EB] p-6 rounded-xl shadow-xs">
            <h3 className="font-headline-md text-headline-md text-[#00355f] mb-4">Past Inspection History</h3>
            <div className="space-y-3 text-body-sm">
              {inspections.length === 0 ? (
                <p className="text-xs text-[#727780]">No inspection history on record for this factory.</p>
              ) : inspections.map((insp, idx) => {
                const borderColor = insp.inspection_type === 'High Risk' ? '#D32F2F' : insp.inspection_type === 'Medium Risk' ? '#F57C00' : '#1b6d24';
                const isCompleted = insp.status === 'Completed';
                return (
                  <div key={idx} className="p-3 rounded-r-lg flex justify-between items-center bg-[#f8f9fb]" style={{ borderLeft: `4px solid ${borderColor}` }}>
                    <div>
                      <div className="font-bold text-[#191c1e]">{insp.inspection_type} Inspection</div>
                      <div className="text-xs text-[#42474f]">{insp.inspection_date}</div>
                    </div>
                    <span className={`px-2.5 py-1 text-xs font-bold rounded ${isCompleted ? 'text-[#1b6d24] bg-[#1b6d24]/10' : 'text-[#F57C00] bg-[#F57C00]/10'}`}>
                      {(insp.status || '').toUpperCase()}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
