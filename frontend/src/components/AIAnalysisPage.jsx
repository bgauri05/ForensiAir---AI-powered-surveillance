import React, { useState, useEffect } from 'react';
import {
  Bolt,
  AlertTriangle,
  Download,
  CheckCircle2,
  XCircle,
  RefreshCw,
  HelpCircle,
  Info,
  ChevronDown,
  ChevronUp,
  Activity,
  FileText,
  Search,
  ExternalLink
} from 'lucide-react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { apiFetch } from '../config';
import { InspectionReportModal } from './InspectionReportModal';

// Parameter measurement definitions with units for wastewater inspectors
const PARAM_METADATA = {
  'ETP-pH': {
    name: 'pH (Acidity / Alkalinity)',
    unit: 'pH Units',
    typicalRange: '5.5 – 9.0',
    description: 'Measures how acidic or alkaline the treated effluent is. Extreme values can damage biological treatment bacteria or receiving waterways.'
  },
  'ETP-BOD': {
    name: 'BOD (Biochemical Oxygen Demand)',
    unit: 'mg/L',
    typicalRange: '≤ 30 mg/L',
    description: 'Amount of dissolved oxygen consumed by microorganisms while decomposing organic matter. High BOD depletes oxygen in streams.'
  },
  'ETP-COD': {
    name: 'COD (Chemical Oxygen Demand)',
    unit: 'mg/L',
    typicalRange: '≤ 250 mg/L',
    description: 'Total oxygen required to chemically oxidize all organic and inorganic compounds in the wastewater. Usually 2 to 3 times higher than BOD.'
  },
  'ETP-TSS': {
    name: 'TSS (Total Suspended Solids)',
    unit: 'mg/L',
    typicalRange: '≤ 100 mg/L',
    description: 'Solid particles suspended in effluent that can be trapped by a laboratory filter. High TSS clouds waterways and settles as sludge.'
  },
  'ETP-Flow': {
    name: 'Effluent Flow Rate',
    unit: 'm³/hr',
    typicalRange: 'Site-specific',
    description: 'Volumetric rate of treated wastewater discharged through the outfall channel into the common effluent grid or water body.'
  }
};

function getParamInfo(paramKey) {
  return PARAM_METADATA[paramKey] || {
    name: paramKey.replace('ETP-', ''),
    unit: 'units',
    typicalRange: 'Standard',
    description: 'Monitored wastewater telemetry stream.'
  };
}

function correlationColor(value) {
  if (value === undefined || value === null || isNaN(value)) return '#f8f9fb';
  // Clamped diverging scale: -1 (red) -> 0 (neutral gray) -> +1 (primary blue)
  const clamped = Math.max(-1, Math.min(1, value));
  if (clamped >= 0) {
    const t = clamped;
    const r = Math.round(255 - t * (255 - 15));
    const g = Math.round(255 - t * (255 - 76));
    const b = Math.round(255 - t * (255 - 129));
    return `rgb(${r}, ${g}, ${b})`;
  }
  const t = -clamped;
  const r = Math.round(255 - t * (255 - 211));
  const g = Math.round(255 - t * (255 - 47));
  const b = Math.round(255 - t * (255 - 47));
  return `rgb(${r}, ${g}, ${b})`;
}

function getCorrelationInterpretation(paramA, paramB, val) {
  const infoA = getParamInfo(paramA);
  const infoB = getParamInfo(paramB);

  if (paramA === paramB) {
    return {
      strength: 'Identical Parameter',
      badge: 'Self-Comparison (1.0)',
      color: 'text-[#00355f]',
      text: `${infoA.name} compared with itself. A measurement always has a perfect 1.0 correlation with itself.`
    };
  }

  if (val === undefined || val === null || isNaN(val)) {
    return {
      strength: 'No Shared Data',
      badge: 'Data Unavailable',
      color: 'text-[#727780]',
      text: `No overlapping readings exist between ${infoA.name} and ${infoB.name} for this facility, so correlation cannot be calculated.`
    };
  }

  if (val >= 0.65) {
    return {
      strength: 'Strong Positive Relationship',
      badge: `r = ${val.toFixed(2)} (Strong Positive)`,
      color: 'text-[#0f4c81]',
      text: `When ${infoA.name} increases, ${infoB.name} almost always increases as well. In biological wastewater treatment, COD and BOD naturally rise and fall together as industrial production organic load changes.`
    };
  } else if (val >= 0.25) {
    return {
      strength: 'Moderate Positive Relationship',
      badge: `r = ${val.toFixed(2)} (Moderate Positive)`,
      color: 'text-[#0f4c81]',
      text: `${infoA.name} and ${infoB.name} tend to move in the same direction, though process variations and chemical treatment stages cause noticeable differences.`
    };
  } else if (val > -0.25) {
    return {
      strength: 'Weak or No Linear Relationship',
      badge: `r = ${val.toFixed(2)} (Near Zero)`,
      color: 'text-[#727780]',
      text: `Changes in ${infoA.name} show little clear straight-line relationship with changes in ${infoB.name} in the available telemetry. They operate largely independently.`
    };
  } else if (val > -0.65) {
    return {
      strength: 'Moderate Negative Relationship',
      badge: `r = ${val.toFixed(2)} (Moderate Negative)`,
      color: 'text-[#D32F2F]',
      text: `When ${infoA.name} increases, ${infoB.name} tends to decrease. For example, increased chemical dosing or dilution can lower pollutant concentration while increasing flow rate.`
    };
  } else {
    return {
      strength: 'Strong Negative Relationship',
      badge: `r = ${val.toFixed(2)} (Strong Negative)`,
      color: 'text-[#D32F2F]',
      text: `When ${infoA.name} increases, ${infoB.name} consistently decreases. An uncharacteristic negative correlation between parameters that normally co-vary can warrant field investigation.`
    };
  }
}

function CorrelationHeatmap({ parameters, pairs, selectedPair, onSelectPair }) {
  const lookup = {};
  pairs.forEach(p => {
    lookup[`${p.param_a}|${p.param_b}`] = p.correlation;
    lookup[`${p.param_b}|${p.param_a}`] = p.correlation;
  });

  const label = (p) => p.replace('ETP-', '');

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <table className="border-collapse">
          <thead>
            <tr>
              <th className="p-2"></th>
              {parameters.map(p => (
                <th key={p} className="p-2 text-[10px] font-bold text-[#727780] uppercase tracking-wider text-center">
                  {label(p)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {parameters.map(rowP => (
              <tr key={rowP}>
                <th className="p-2 text-[10px] font-bold text-[#727780] uppercase tracking-wider text-right">
                  {label(rowP)}
                </th>
                {parameters.map(colP => {
                  const val = rowP === colP ? 1 : lookup[`${rowP}|${colP}`];
                  const isSelected = selectedPair &&
                    ((selectedPair.row === rowP && selectedPair.col === colP) ||
                     (selectedPair.row === colP && selectedPair.col === rowP));

                  return (
                    <td key={colP} className="p-0.5">
                      <button
                        type="button"
                        onClick={() => onSelectPair({ row: rowP, col: colP, val })}
                        className={`w-14 h-14 flex flex-col items-center justify-center text-xs font-bold rounded transition-all focus:outline-none ${
                          isSelected ? 'ring-3 ring-[#00355f] ring-offset-1 scale-105 z-10 relative' : 'hover:opacity-90'
                        }`}
                        style={{
                          backgroundColor: val === undefined ? '#f8f9fb' : correlationColor(val),
                          color: val !== undefined && Math.abs(val) > 0.55 ? '#fff' : '#191c1e'
                        }}
                        title={`Click to inspect relationship: ${label(rowP)} vs ${label(colP)} (r = ${val === undefined ? 'N/A' : val.toFixed(2)})`}
                      >
                        <span>{val === undefined ? '—' : val.toFixed(2)}</span>
                        {rowP === colP && <span className="text-[9px] opacity-75 font-normal">Self</span>}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Visible Color Scale Legend */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-[#f8f9fb] border border-[#E5E7EB] rounded-lg text-xs">
        <span className="font-bold text-[#727780]">Colour Legend:</span>
        <div className="flex items-center gap-1.5">
          <span className="w-3.5 h-3.5 rounded bg-[#D32F2F]"></span>
          <span className="text-[#42474f]">-1.0 (Opposite)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3.5 h-3.5 rounded bg-[#f5b7b7]"></span>
          <span className="text-[#42474f]">-0.5 (Moderate Inverse)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3.5 h-3.5 rounded bg-[#edeef0] border border-[#d1d5db]"></span>
          <span className="text-[#42474f]">0.0 (No Linear Link)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3.5 h-3.5 rounded bg-[#9bc2e6]"></span>
          <span className="text-[#42474f]">+0.5 (Moderate Co-varying)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3.5 h-3.5 rounded bg-[#0f4c81]"></span>
          <span className="text-[#42474f]">+1.0 (Direct Match)</span>
        </div>
      </div>
    </div>
  );
}

export function AIAnalysisPage({ onNavigate, selectedFactoryId: initialFactoryId, currentUser }) {
  const [factories, setFactories] = useState([]);
  const [selectedFactoryId, setSelectedFactoryId] = useState(initialFactoryId || '');
  const [selectedFactoryData, setSelectedFactoryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [refreshResult, setRefreshResult] = useState(null);

  const [telemetry, setTelemetry] = useState(null);
  const [correlation, setCorrelation] = useState(null);
  const [selectedCorrelationPair, setSelectedCorrelationPair] = useState(null);
  const [expandedEpisodeIndex, setExpandedEpisodeIndex] = useState(null);

  // Inspection Report Modal state
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [selectedModalAlert, setSelectedModalAlert] = useState(null);

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchTelemetry = async (fid, parameter) => {
    try {
      const url = parameter
        ? `/api/factories/${fid}/telemetry?parameter=${encodeURIComponent(parameter)}`
        : `/api/factories/${fid}/telemetry`;
      const res = await apiFetch(url);
      setTelemetry(res.ok ? await res.json() : null);
    } catch (err) {
      console.error(err);
      setTelemetry(null);
    }
  };

  const fetchCorrelation = async (fid) => {
    try {
      const res = await apiFetch(`/api/factories/${fid}/correlation-matrix`);
      if (res.ok) {
        const cData = await res.json();
        setCorrelation(cData);
        // Default selected pair to first pair if available
        if (cData.pairs && cData.pairs.length > 0) {
          const first = cData.pairs[0];
          setSelectedCorrelationPair({
            row: first.param_a,
            col: first.param_b,
            val: first.correlation
          });
        } else {
          setSelectedCorrelationPair(null);
        }
      } else {
        setCorrelation(null);
        setSelectedCorrelationPair(null);
      }
    } catch (err) {
      console.error(err);
      setCorrelation(null);
      setSelectedCorrelationPair(null);
    }
  };

  const fetchInitialData = async () => {
    try {
      const res = await apiFetch(`/api/factories`);
      if (res.ok) {
        const data = await res.json();
        setFactories(data);
        if (data.length > 0) {
          const target = (initialFactoryId && data.find(f => f.factory_id === initialFactoryId))
            || data.find(f => f.risk_tier === 'High')
            || data[0];
          setSelectedFactoryId(target.factory_id);
          fetchFactoryAnalysis(target.factory_id, target);
          fetchTelemetry(target.factory_id);
          fetchCorrelation(target.factory_id);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchFactoryAnalysis = async (fid, factoryObj) => {
    try {
      const [predRes, facDetailRes, shapRes, v2Res] = await Promise.all([
        apiFetch(`/api/factories/${fid}/predictions`),
        apiFetch(`/api/factories/${fid}`),
        apiFetch(`/api/factories/${fid}/shap`),
        apiFetch(`/api/factories/${fid}/v2-analysis`)
      ]);

      let predictions = null;
      let detail = factoryObj;
      let explanation = null;
      let v2Analysis = null;

      if (predRes.ok) predictions = await predRes.json();
      if (facDetailRes.ok) detail = await facDetailRes.json();
      if (shapRes.ok) explanation = await shapRes.json();
      if (v2Res.ok) v2Analysis = await v2Res.json();

      const result = { factory: detail, predictions, explanation, v2Analysis };
      setSelectedFactoryData(result);
      return result;
    } catch (err) {
      console.error(err);
      return null;
    }
  };

  const handleSelectFactory = (fid) => {
    setSelectedFactoryId(fid);
    const fObj = factories.find(f => f.factory_id === fid);
    fetchFactoryAnalysis(fid, fObj);
    fetchTelemetry(fid);
    fetchCorrelation(fid);
  };

  const handleTelemetryParamChange = (parameter) => {
    fetchTelemetry(selectedFactoryId, parameter);
  };

  const handleRunAnalysis = async () => {
    setAnalyzing(true);
    setRefreshResult(null);
    const fObj = factories.find(f => f.factory_id === selectedFactoryId);
    const previous = selectedFactoryData;
    const updated = await fetchFactoryAnalysis(selectedFactoryId, fObj);
    setAnalyzing(false);
    if (!updated) {
      setRefreshResult('error');
    } else {
      const changed = JSON.stringify({ p: previous?.predictions, e: previous?.explanation })
        !== JSON.stringify({ p: updated.predictions, e: updated.explanation });
      setRefreshResult(changed ? 'changed' : 'unchanged');
    }
    setTimeout(() => setRefreshResult(null), 6000);
  };

  if (loading) {
    return (
      <div className="p-8 max-w-6xl mx-auto flex flex-col items-center justify-center min-h-[50vh] gap-3 text-[#727780]">
        <div className="w-8 h-8 border-4 border-[#0f4c81] border-t-transparent rounded-full animate-spin"></div>
        <p className="text-body-sm font-medium">Loading AI Analysis and Telemetry...</p>
      </div>
    );
  }

  const fObj = selectedFactoryData?.factory || factories[0] || {};
  const pred = selectedFactoryData?.predictions || {};
  const explanation = selectedFactoryData?.explanation || null;
  const breakdown = explanation?.composite_breakdown || null;
  const fingerprintChecks = explanation?.fingerprint_checks || [];
  const lrShap = explanation?.shap?.tamper_model_shap || null;
  const ifShap = explanation?.shap?.isolation_forest_shap || null;
  const v2Analysis = selectedFactoryData?.v2Analysis || null;

  const isHighRisk = fObj.risk_tier === 'High' || fObj.risk_tier === 'High Risk';
  const isMediumRisk = fObj.risk_tier === 'Medium' || fObj.risk_tier === 'Moderate Risk';

  const tamperProb = pred.tamper_probability !== undefined
    ? `${pred.tamper_probability.toFixed(1)}%`
    : fObj.tamper_probability !== undefined
    ? `${fObj.tamper_probability.toFixed(1)}%`
    : 'Not available';

  const isoScore = pred.isolation_forest?.anomaly_score !== undefined
    ? pred.isolation_forest.anomaly_score.toFixed(2)
    : fObj.raw_fingerprint_signals?.anomaly_score !== undefined
    ? fObj.raw_fingerprint_signals.anomaly_score.toFixed(2)
    : 'Not available';

  const riskColor = isHighRisk ? '#D32F2F' : isMediumRisk ? '#F57C00' : '#1b6d24';

  const fmtRaw = (val, unit) => {
    if (val === null || val === undefined) return 'Not available';
    if (unit === '%') return `${val.toFixed(1)}%`;
    if (unit === 'σ') return `${val.toFixed(2)}σ`;
    return val.toFixed(4);
  };

  const selectedPairInfo = selectedCorrelationPair
    ? getCorrelationInterpretation(selectedCorrelationPair.row, selectedCorrelationPair.col, selectedCorrelationPair.val)
    : null;

  return (
    <div className="p-8 max-w-[1600px] mx-auto space-y-6 print:p-0 print:max-w-full">
      {/* Header & Breadcrumb */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <nav className="flex items-center gap-2 text-[#727780] font-label-caps text-[10px] uppercase tracking-widest mb-2 print:hidden">
            <span className="hover:text-[#00355f] cursor-pointer">Forensics</span>
            <span className="material-symbols-outlined text-xs">chevron_right</span>
            <span className="text-[#191c1e] font-bold">AI Analysis & Inspector Diagnostics</span>
          </nav>
          <h1 className="text-headline-lg font-headline-lg text-[#00355f]">AI Analysis & Telemetry Diagnostics</h1>
          <p className="text-body-md text-[#42474f]">
            Facility: <span className="font-bold text-[#191c1e]">{fObj.factory_name || fObj.name}</span> | ID: #{fObj.factory_id}
          </p>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#00355f]/10 text-[#00355f] border border-[#00355f]/20">
              Historical Development Evaluation Mode
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-[#f8f9fb] text-[#727780] border border-[#E5E7EB]">
              Development telemetry data · Not currently monitoring live plant streams
            </span>
          </div>
        </div>

        {/* Facility Selector & Print Export */}
        <div className="flex flex-wrap items-center gap-3 bg-white border border-[#E5E7EB] p-4 rounded-xl shadow-xs print:hidden">
          <div className="text-right">
            <div className="text-label-caps text-[#727780] uppercase font-bold text-[10px]">Select Monitored Site</div>
            <select
              value={selectedFactoryId}
              onChange={(e) => handleSelectFactory(e.target.value)}
              className="max-w-[200px] text-body-sm font-bold text-[#00355f] bg-[#f8f9fb] border border-[#E5E7EB] rounded px-3 py-1 cursor-pointer focus:outline-none"
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
            className="flex items-center gap-2 bg-[#0f4c81] text-white px-5 py-2 rounded-lg font-bold hover:opacity-90 transition-all text-body-sm shadow-sm disabled:opacity-50"
            title="Reloads the latest saved analysis records for this facility"
          >
            <Bolt size={16} className={analyzing ? 'animate-spin' : ''} />
            <span>{analyzing ? 'Checking...' : 'Refresh Records'}</span>
          </button>
          <button
            onClick={() => window.print()}
            className="flex items-center gap-2 bg-white border border-[#E5E7EB] text-[#00355f] px-4 py-2 rounded-lg font-bold hover:bg-[#f8f9fb] transition-all text-body-sm shadow-xs"
            title="Print or save this diagnostic dossier as PDF"
          >
            <Download size={16} />
            <span>Print Dossier</span>
          </button>
        </div>
      </div>

      {/* Status banner */}
      {refreshResult === 'unchanged' && (
        <div className="p-3 bg-[#e7f0f8] border border-[#00355f]/20 rounded-lg text-xs text-[#00355f] flex items-center gap-2 print:hidden">
          <CheckCircle2 size={16} />
          <span>Evaluation records re-checked — all displayed metrics are current with repository artifacts.</span>
        </div>
      )}

      {/* SECTION 1: Baseline Anomaly Tiers (Prototype Weak Supervision) */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-body-sm font-bold text-[#727780] uppercase tracking-wider">
            1. Preliminary Prototype Risk Indicators (Legacy Weak-Supervision Baseline)
          </h2>
          <span className="text-[11px] text-[#727780]">August 2026 Prototype Formulation</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1: Risk Category */}
          <div className="bg-white border border-[#E5E7EB] p-5 rounded-xl shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start">
                <span className="text-[11px] font-bold text-[#727780] uppercase tracking-wider">Overall Risk Profile</span>
                <AlertTriangle size={18} style={{ color: riskColor }} />
              </div>
              <div className="mt-3 flex items-center gap-2">
                <span className="px-3 py-1 text-xs font-bold rounded-full" style={{ backgroundColor: `${riskColor}1A`, color: riskColor }}>
                  {(fObj.risk_tier || 'LOW').toUpperCase()} PRIORITY
                </span>
              </div>
              <p className="mt-3 text-xs text-[#42474f] leading-relaxed">
                {pred.note
                  ? pred.note
                  : isHighRisk
                  ? `Multiple rule-based checks triggered on ${fObj.factory_name}'s baseline readings.`
                  : isMediumRisk
                  ? `Moderate statistical variation observed on ${fObj.factory_name}.`
                  : `Telemetry parameters are currently within normal baseline ranges for ${fObj.factory_name}.`
                }
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-[#f2f4f6] text-[11px] text-[#727780]">
              <strong>Inspector note:</strong> Priority guide for inspection scheduling; does not establish non-compliance.
            </div>
          </div>

          {/* Card 2: Tamper Probability */}
          <div className="bg-white border border-[#E5E7EB] p-5 rounded-xl shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start">
                <span className="text-[11px] font-bold text-[#727780] uppercase tracking-wider">Statistical Deviation Score</span>
                <HelpCircle size={16} className="text-[#727780]" title="Automated score from legacy logistic regression trained on rule-based flags." />
              </div>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="text-3xl font-bold font-mono" style={{ color: riskColor }}>{tamperProb}</span>
              </div>
              <div className="w-full bg-[#edeef0] h-2 mt-3 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{ width: tamperProb !== 'Not available' ? `${Math.min(100, parseFloat(tamperProb))}%` : '0%', backgroundColor: riskColor }}
                ></div>
              </div>
              <p className="mt-3 text-xs text-[#42474f] leading-relaxed">
                Calculated by an automated statistical model. Higher percentages indicate that sensor readings shared multiple statistical patterns with known anomaly scenarios.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-[#f2f4f6] text-[11px] text-[#727780]">
              <strong>Caution:</strong> Statistical likelihood only. Verify operational logs before drawing conclusions.
            </div>
          </div>

          {/* Card 3: Isolation Forest */}
          <div className="bg-white border border-[#E5E7EB] p-5 rounded-xl shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-start">
                <span className="text-[11px] font-bold text-[#727780] uppercase tracking-wider">Unusual Pattern Score</span>
                <Activity size={16} className="text-[#727780]" title="Isolation Forest anomaly score" />
              </div>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="text-3xl font-bold font-mono" style={{ color: riskColor }}>{isoScore}</span>
                <span className="text-xs font-bold" style={{ color: riskColor }}>
                  ({isHighRisk ? 'Unusual' : isMediumRisk ? 'Borderline' : 'Typical'})
                </span>
              </div>
              <p className="mt-3 text-xs text-[#42474f] leading-relaxed">
                Measures how far these readings drift from typical industrial wastewater data across all monitored regional sites.
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-[#f2f4f6] text-[11px] text-[#727780]">
              <strong>Baseline Comparison:</strong> Compared against 33 regional facilities in Taloja & Mahad.
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 2: ForensiAIR V2 Causal Supervised Model Evaluation */}
      <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-xs space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-headline-md font-headline-md text-[#00355f] flex items-center gap-2">
              <span>2. ForensiAIR V2 Supervised Anomaly Evaluation</span>
            </h2>
            <p className="text-xs text-[#727780] mt-0.5">
              Rigorous 5-fold Leave-One-Factory-Out cross-mechanism evaluation under the frozen protocol at a calibrated budget of 1.0 alert / factory-month.
            </p>
          </div>
          <span className="px-3 py-1 rounded-full text-xs font-bold bg-[#00355f]/10 text-[#00355f] border border-[#00355f]/20">
            Historical Development Evaluation
          </span>
        </div>

        {!v2Analysis ? (
          <div className="p-4 bg-[#f8f9fb] border border-[#E5E7EB] rounded-lg text-xs text-[#727780]">
            V2 evaluation metrics are currently loading or not available for this facility.
          </div>
        ) : (
          <div className="space-y-6">
            {/* Translated Metric Cards with Inspector Everyday Language */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Metric 1: Recall */}
              <div className="p-4 bg-[#f8f9fb] border border-[#E5E7EB] rounded-xl space-y-1">
                <div className="text-[10px] font-bold text-[#727780] uppercase tracking-wider flex items-center justify-between">
                  <span>Known Anomaly Recall</span>
                  <span className="text-[9px] bg-[#00355f]/10 text-[#00355f] px-1.5 py-0.5 rounded font-mono">Sensitivity</span>
                </div>
                <div className="text-2xl font-bold font-mono text-[#0f4c81]">
                  {(v2Analysis.evaluation_metrics?.v2_recall * 100).toFixed(1)}%
                </div>
                <p className="text-[11px] text-[#42474f] leading-tight">
                  Caught <strong>{v2Analysis.evaluation_metrics?.v2_detected_events}</strong> of <strong>{v2Analysis.evaluation_metrics?.events_evaluated}</strong> test anomalies tested on this facility.
                </p>
                <div className="text-[10px] text-[#727780] pt-1 border-t border-[#E5E7EB]">
                  Plain language: Percentage of simulated tampering scenarios the model successfully detected.
                </div>
              </div>

              {/* Metric 2: Clean False Alarm Rate */}
              <div className="p-4 bg-[#f8f9fb] border border-[#E5E7EB] rounded-xl space-y-1">
                <div className="text-[10px] font-bold text-[#727780] uppercase tracking-wider flex items-center justify-between">
                  <span>False-Alarm Rate</span>
                  <span className="text-[9px] bg-[#1b6d24]/10 text-[#1b6d24] px-1.5 py-0.5 rounded font-mono">Budget: ≤1.0</span>
                </div>
                <div className="text-2xl font-bold font-mono text-[#1b6d24]">
                  {v2Analysis.clean_false_alarm_rate_per_month} / mo
                </div>
                <p className="text-[11px] text-[#42474f] leading-tight">
                  Triggered <strong>{v2Analysis.clean_false_alarm_episodes}</strong> alarms during {v2Analysis.exposure_months} months of clean, un-tampered telemetry.
                </p>
                <div className="text-[10px] text-[#727780] pt-1 border-t border-[#E5E7EB]">
                  Plain language: How often ordinary normal factory readings were incorrectly flagged.
                </div>
              </div>

              {/* Metric 3: Improvement over V1 */}
              <div className="p-4 bg-[#f8f9fb] border border-[#E5E7EB] rounded-xl space-y-1">
                <div className="text-[10px] font-bold text-[#727780] uppercase tracking-wider flex items-center justify-between">
                  <span>Comparison vs Frozen V1</span>
                  <span className="text-[9px] bg-[#f2f4f6] text-[#727780] px-1.5 py-0.5 rounded font-mono">Baseline</span>
                </div>
                <div className="text-2xl font-bold font-mono text-[#191c1e]">
                  {v2Analysis.evaluation_metrics?.paired_improvement >= 0 ? '+' : ''}
                  {(v2Analysis.evaluation_metrics?.paired_improvement * 100).toFixed(1)}%
                </div>
                <p className="text-[11px] text-[#42474f] leading-tight">
                  V2 achieved {(v2Analysis.evaluation_metrics?.v2_recall * 100).toFixed(1)}% vs V1's {(v2Analysis.evaluation_metrics?.v1_m1_recall * 100).toFixed(1)}% recall.
                </p>
                <div className="text-[10px] text-[#727780] pt-1 border-t border-[#E5E7EB]">
                  Plain language: Extra anomalies caught by V2 without raising the false-alarm rate.
                </div>
              </div>

              {/* Metric 4: Evaluation Exposure */}
              <div className="p-4 bg-[#f8f9fb] border border-[#E5E7EB] rounded-xl space-y-1">
                <div className="text-[10px] font-bold text-[#727780] uppercase tracking-wider flex items-center justify-between">
                  <span>Telemetry Exposure</span>
                  <span className="text-[9px] bg-[#f2f4f6] text-[#727780] px-1.5 py-0.5 rounded font-mono">Dataset</span>
                </div>
                <div className="text-2xl font-bold font-mono text-[#191c1e]">
                  {v2Analysis.exposure_months} Months
                </div>
                <p className="text-[11px] text-[#42474f] leading-tight">
                  Over {Math.round(v2Analysis.exposure_months * 30.5 * 96).toLocaleString()} individual 15-minute readings evaluated.
                </p>
                <div className="text-[10px] text-[#727780] pt-1 border-t border-[#E5E7EB]">
                  Plain language: Time span of actual historical OCEMS readings used in the test.
                </div>
              </div>
            </div>

            {/* Plain-Language Facility Summary Box */}
            <div className="p-4 bg-[#e7f0f8]/60 border border-[#00355f]/15 rounded-xl text-xs space-y-2">
              <div className="flex items-center gap-2 font-bold text-[#00355f]">
                <Info size={16} />
                <span>Inspector Summary for {v2Analysis.factory_name}</span>
              </div>
              <p className="text-[#42474f] leading-relaxed">
                {v2Analysis.plain_language_summary}
              </p>
            </div>

            {/* Sample Detected Anomaly Episodes Table with Actionable Inspector Guidance */}
            {v2Analysis.recent_detected_episodes?.length > 0 && (
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-xs text-[#00355f] uppercase tracking-wider">
                    Historical Anomaly Findings on This Facility (Click row to expand inspector verification steps)
                  </h3>
                  <span className="text-xs text-[#727780]">
                    {v2Analysis.recent_detected_episodes.length} episodes evaluated
                  </span>
                </div>

                <div className="space-y-2">
                  {v2Analysis.recent_detected_episodes.map((ep, idx) => {
                    const isExpanded = expandedEpisodeIndex === idx;
                    const paramInfo = getParamInfo(ep.parameter);

                    return (
                      <div
                        key={idx}
                        className={`border rounded-lg overflow-hidden transition-all ${
                          isExpanded ? 'border-[#0f4c81] shadow-xs' : 'border-[#E5E7EB] hover:border-[#0f4c81]/40'
                        }`}
                      >
                        {/* Summary Bar */}
                        <div
                          onClick={() => setExpandedEpisodeIndex(isExpanded ? null : idx)}
                          className="p-3 bg-white flex flex-wrap items-center justify-between gap-3 cursor-pointer hover:bg-[#fafbfc]"
                        >
                          <div className="flex items-center gap-3">
                            <span className="font-mono text-xs font-bold bg-[#f2f4f6] text-[#00355f] px-2 py-0.5 rounded">
                              {ep.parameter}
                            </span>
                            <div>
                              <span className="font-bold text-xs text-[#191c1e]">{ep.anomaly_category}</span>
                              <span className="text-[11px] text-[#727780] ml-2">({ep.tamper_type})</span>
                            </div>
                          </div>

                          <div className="flex items-center gap-3 text-xs">
                            <span className="text-[#727780]">Duration: <strong>{ep.duration_hours}h</strong></span>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                              ep.severity === 'obvious' ? 'bg-[#fdecec] text-[#D32F2F]' :
                              ep.severity === 'moderate' ? 'bg-[#fff3e6] text-[#F57C00]' : 'bg-[#e7f0f8] text-[#00355f]'
                            }`}>
                              {ep.severity}
                            </span>
                            <span className="text-[#727780] text-[11px] hidden sm:inline">{ep.start_time.slice(0, 10)}</span>
                            {isExpanded ? <ChevronUp size={16} className="text-[#0f4c81]" /> : <ChevronDown size={16} className="text-[#727780]" />}
                          </div>
                        </div>

                        {/* Actionable Inspector Breakdown Accordion */}
                        {isExpanded && (
                          <div className="p-4 bg-[#f8f9fb] border-t border-[#E5E7EB] space-y-3 text-xs">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                              {/* What happened? */}
                              <div className="p-3 bg-white rounded border border-[#E5E7EB] space-y-1">
                                <div className="font-bold text-[#00355f] text-[11px] uppercase tracking-wider">
                                  1. What happened?
                                </div>
                                <p className="text-[#42474f] leading-relaxed">
                                  {ep.anomaly_category} pattern detected on {paramInfo.name}. The readings exhibited abnormal stability or departure over {ep.duration_hours} hours ({ep.start_time} to {ep.end_time}).
                                </p>
                              </div>

                              {/* Why was it flagged? */}
                              <div className="p-3 bg-white rounded border border-[#E5E7EB] space-y-1">
                                <div className="font-bold text-[#00355f] text-[11px] uppercase tracking-wider">
                                  2. Why was it flagged?
                                </div>
                                <p className="text-[#42474f] leading-relaxed">
                                  Statistical features (rolling variance, similarity, or baseline shift) exceeded the calibrated operating cutoff (τ = 0.97875), indicating an unlikely natural variation.
                                </p>
                              </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                              {/* What could explain it? */}
                              <div className="p-3 bg-white rounded border border-[#E5E7EB] space-y-1">
                                <div className="font-bold text-[#00355f] text-[11px] uppercase tracking-wider">
                                  3. What could explain it? (Plausible causes)
                                </div>
                                <ul className="list-disc list-inside text-[#42474f] space-y-0.5">
                                  <li>Sensor probe fouling, optical glass obscuration, or electrode depletion.</li>
                                  <li>Telemetry transmitter offline in frozen/last-hold transmission mode.</li>
                                  <li>Production shutdown, effluent storage tank recirculation, or plant line washdown.</li>
                                  <li>Artificial upper-bound clipping or manual zero-point calibration adjustments.</li>
                                </ul>
                              </div>

                              {/* What should the inspector verify? */}
                              <div className="p-3 bg-white rounded border border-[#E5E7EB] space-y-1">
                                <div className="font-bold text-[#1b6d24] text-[11px] uppercase tracking-wider flex items-center gap-1">
                                  <CheckCircle2 size={13} /> 4. What should the inspector verify on site?
                                </div>
                                <ul className="list-disc list-inside text-[#42474f] space-y-0.5">
                                  <li>Inspect physical sensor transmitter terminals and verify live loop current (4-20mA).</li>
                                  <li>Review OCEMS maintenance, sensor cleaning, and chemical recalibration logbooks.</li>
                                  <li>Collect an independent grab sample at the discharge outfall weir for certified lab testing.</li>
                                  <li>Cross-reference effluent volume against factory electricity consumption and production shift records.</li>
                                </ul>
                              </div>
                            </div>

                            {/* Action: Document Findings in Verification Report */}
                            <div className="p-3 bg-[#e7f0f8]/60 rounded-lg border border-[#00355f]/20 flex flex-wrap items-center justify-between gap-3">
                              <div>
                                <span className="font-bold text-[#00355f] block text-xs">Document Findings in Verification Report</span>
                                <span className="text-[11px] text-[#727780]">File an official on-site verification report for episode {ep.event_id}.</span>
                              </div>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSelectedModalAlert({
                                    alert_id: ep.event_id,
                                    factory_id: selectedFactoryId,
                                    factory_name: fObj.factory_name || fObj.name,
                                    parameter: ep.parameter,
                                    tamper_type: ep.tamper_type,
                                    tamper_label: `${ep.tamper_type} (${ep.anomaly_category})`,
                                    anomaly_category: ep.anomaly_category,
                                    severity: ep.severity,
                                    start_time: ep.start_time,
                                    end_time: ep.end_time,
                                    duration_hours: ep.duration_hours
                                  });
                                  setIsReportModalOpen(true);
                                }}
                                className="px-3.5 py-1.5 bg-[#00355f] text-white rounded-lg font-bold text-xs hover:bg-[#0f4c81] flex items-center gap-1.5 transition-colors shadow-2xs"
                              >
                                <FileText size={13} />
                                <span>File Verification Report</span>
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* SECTION 3: Telemetry Trend Chart with Inspector Interpretation */}
      <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-xs space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-1">
          <div>
            <h2 className="text-headline-md font-headline-md text-[#00355f]">
              3. Telemetry Trend & Regulatory Consent Limits
            </h2>
            <p className="text-xs text-[#727780] mt-0.5">
              Historical 15-minute sensor readings aggregated to daily averages, overlaid with standard CPCB environmental limits.
            </p>
          </div>

          {telemetry && telemetry.available_parameters.length > 1 && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-[#727780]">Select Sensor:</span>
              <select
                value={telemetry.parameter}
                onChange={(e) => handleTelemetryParamChange(e.target.value)}
                className="text-body-sm font-bold text-[#00355f] bg-[#f8f9fb] border border-[#E5E7EB] rounded px-3 py-1.5 cursor-pointer focus:outline-none"
              >
                {telemetry.available_parameters.map(p => (
                  <option key={p} value={p}>{getParamInfo(p).name}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        {!telemetry ? (
          <p className="text-body-sm text-[#727780]">Telemetry series not available for this factory.</p>
        ) : (
          <div className="space-y-4">
            <div className="text-xs text-[#727780] flex flex-wrap items-center gap-4">
              <span>
                Displaying <strong>{getParamInfo(telemetry.parameter).name}</strong> ({telemetry.unit || getParamInfo(telemetry.parameter).unit})
              </span>
              <span>Source: <strong>{telemetry.source === 'synthetic' ? 'Synthetic development baseline' : 'Real historical OCEMS telemetry'}</strong></span>
              {telemetry.consent_min !== null && telemetry.consent_max !== null && (
                <span className="text-[#00355f] font-semibold">
                  Standard regulatory band: {telemetry.consent_min} – {telemetry.consent_max} {telemetry.unit}
                </span>
              )}
            </div>

            {/* Main Daily Trend Line Chart */}
            <div className="w-full h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={telemetry.series} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#edeef0" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} interval={Math.max(0, Math.floor(telemetry.series.length / 8))} />
                  <YAxis tick={{ fontSize: 10 }} domain={['auto', 'auto']} />
                  <Tooltip
                    labelFormatter={(label) => `Date: ${label}`}
                    formatter={(val) => [`${val} ${telemetry.unit || ''}`, 'Daily Mean']}
                  />
                  {telemetry.consent_min !== null && (
                    <ReferenceLine y={telemetry.consent_min} stroke="#F57C00" strokeDasharray="4 4" label={{ value: `Min: ${telemetry.consent_min}`, fontSize: 10, fill: '#F57C00' }} />
                  )}
                  {telemetry.consent_max !== null && (
                    <ReferenceLine y={telemetry.consent_max} stroke="#D32F2F" strokeDasharray="4 4" label={{ value: `Max: ${telemetry.consent_max}`, fontSize: 10, fill: '#D32F2F' }} />
                  )}
                  <Line
                    type="monotone"
                    dataKey="value_mean"
                    name="Daily Mean"
                    stroke="#0f4c81"
                    strokeWidth={2}
                    isAnimationActive={false}
                    dot={(props) => {
                      const { cx, cy, payload, index } = props;
                      if (cx === undefined || cy === undefined) return null;
                      const flagged = (payload.flatline_pct || 0) > 0.5;
                      return <circle key={`dot-${index}`} cx={cx} cy={cy} r={flagged ? 3.5 : 1.5} fill={flagged ? '#D32F2F' : '#0f4c81'} stroke="none" />;
                    }}
                    activeDot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="flex items-center gap-2 text-xs text-[#727780]">
              <span className="w-2.5 h-2.5 rounded-full bg-[#D32F2F] inline-block"></span>
              <span><strong>Red dots:</strong> Days where &gt;50% of consecutive readings were completely flatlined (zero change).</span>
            </div>

            {/* Limit-Hugging Bar Chart */}
            <div className="pt-2">
              <div className="text-xs font-bold text-[#191c1e] mb-1">
                Near-Limit Concentration (% of daily readings hovering within 5% below consent limit)
              </div>
              <div className="w-full h-[70px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={telemetry.series} margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
                    <XAxis dataKey="date" hide />
                    <YAxis hide domain={[0, 1]} />
                    <Tooltip formatter={(v) => (v === null ? 'N/A' : `${(v * 100).toFixed(1)}%`)} labelFormatter={(label) => `Date: ${label}`} />
                    <Bar dataKey="limit_hugging_pct" fill="#F57C00" isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Plain-Language Explanation for Inspectors (Requirement 2) */}
            <div className="p-4 bg-[#f8f9fb] border border-[#E5E7EB] rounded-xl text-xs space-y-3 mt-4">
              <div className="font-bold text-[#00355f] text-xs uppercase tracking-wider flex items-center gap-1.5">
                <HelpCircle size={15} /> Inspector Guide to Reading This Chart
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[#42474f] leading-relaxed">
                <div>
                  <strong className="text-[#191c1e] block mb-0.5">What am I looking at?</strong>
                  The blue line shows the daily average reading for {getParamInfo(telemetry.parameter).name} across the monitored period. The horizontal dashed lines represent the legal CPCB discharge limits.
                </div>

                <div>
                  <strong className="text-[#191c1e] block mb-0.5">What does it tell me?</strong>
                  It shows whether discharge levels stayed inside safe legal bounds, experienced seasonal shifts, or entered prolonged periods of flatlined readings (indicated by red dots).
                </div>

                <div>
                  <strong className="text-[#191c1e] block mb-0.5">Why does it matter for inspection?</strong>
                  Industrial effluent naturally fluctuates as wastewater batches enter treatment tanks. A line that is unnaturally flat or hugs just beneath the upper legal limit often warrants physical sensor verification.
                </div>

                <div>
                  <strong className="text-[#191c1e] block mb-0.5">What should I check?</strong>
                  If red dots appear, inspect the probe in the outfall chamber to confirm it is immersed in flowing water rather than air or a stagnant test beaker. If readings hover near the maximum line, check automatic chemical dosing pump logs.
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* SECTION 4: Parameter Correlation Matrix with Interactive Inspector Explanation */}
      <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-xs space-y-4">
        <div>
          <h2 className="text-headline-md font-headline-md text-[#00355f]">
            4. Parameter Correlation Matrix
          </h2>
          <p className="text-xs text-[#727780] mt-0.5">
            Statistical relationship between different monitored wastewater measurements over time.
          </p>
        </div>

        {!correlation || correlation.pairs.length === 0 ? (
          <div className="p-4 bg-[#f8f9fb] border border-[#E5E7EB] rounded-lg text-xs text-[#727780]">
            {correlation?.note || 'This facility monitors fewer than two parameters with overlapping records; pairwise correlation cannot be calculated.'}
          </div>
        ) : (
          <div className="space-y-6">
            <CorrelationHeatmap
              parameters={correlation.parameters}
              pairs={correlation.pairs}
              selectedPair={selectedCorrelationPair}
              onSelectPair={setSelectedCorrelationPair}
            />

            {/* Interactive "How are these measurements related?" Section (Requirement 3) */}
            <div className="p-5 bg-[#f8f9fb] border border-[#E5E7EB] rounded-xl space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#E5E7EB] pb-3">
                <h3 className="font-bold text-xs text-[#00355f] uppercase tracking-wider flex items-center gap-1.5">
                  <Activity size={16} /> How Are These Measurements Related?
                </h3>
                {selectedPairInfo && (
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold font-mono bg-white border border-[#E5E7EB] ${selectedPairInfo.color}`}>
                    {selectedPairInfo.badge}
                  </span>
                )}
              </div>

              {selectedCorrelationPair ? (
                <div className="space-y-2">
                  <div className="text-body-sm font-bold text-[#191c1e]">
                    Relationship between {getParamInfo(selectedCorrelationPair.row).name} and {getParamInfo(selectedCorrelationPair.col).name}:
                  </div>
                  <p className="text-xs text-[#42474f] leading-relaxed">
                    {selectedPairInfo.text}
                  </p>
                </div>
              ) : (
                <p className="text-xs text-[#727780]">
                  Click on any cell in the grid above to see a plain-language explanation of how those two parameters relate to each other.
                </p>
              )}

              {/* General Statistical Guide for Wastewater Inspectors */}
              <div className="pt-3 border-t border-[#E5E7EB] grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-[#42474f]">
                <div className="space-y-1">
                  <strong className="text-[#191c1e] block">Understanding Correlation:</strong>
                  <ul className="list-disc list-inside space-y-1 text-[#727780]">
                    <li><strong className="text-[#0f4c81]">Positive correlation (+0.3 to +1.0):</strong> The two measurements tend to increase or decrease together.</li>
                    <li><strong className="text-[#D32F2F]">Negative correlation (-0.3 to -1.0):</strong> When one measurement increases, the other tends to decrease.</li>
                    <li><strong className="text-[#727780]">Weak / near-zero (-0.3 to +0.3):</strong> There is little straight-line relationship between the measurements in the available data.</li>
                  </ul>
                </div>

                <div className="p-3 bg-white border border-[#E5E7EB] rounded-lg space-y-1">
                  <strong className="text-[#00355f] block flex items-center gap-1">
                    <Info size={13} /> Essential Regulatory Inspection Rule
                  </strong>
                  <p className="text-[#42474f] leading-relaxed text-[11px]">
                    <strong>Correlation does not establish causation.</strong> A strong relationship between two measurements does not prove that one causes the other to change. Seasonal factors, treatment chemical dosing, or combined plant discharge lines often influence both parameters simultaneously.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* SECTION 5: Model Evidence & Feature Contributions (SHAP) */}
      <div className="space-y-2">
        <h2 className="text-body-sm font-bold text-[#727780] uppercase tracking-wider">
          5. Model Evidence & Contributing Signals (Feature Importance Diagnostics)
        </h2>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Tamper Model SHAP */}
          <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-xs space-y-3">
            <div className="flex justify-between items-center">
              <h3 className="text-headline-md font-headline-md text-[#00355f]">Supervised Tamper Model Evidence</h3>
              <span className="text-[10px] font-bold bg-[#00355f]/10 text-[#00355f] px-2.5 py-0.5 rounded-full">Linear Model</span>
            </div>

            <p className="text-xs text-[#727780]">
              Shows which facility-level statistical features pushed the model towards an unusual rating (red bars) or normal rating (green bars).
            </p>

            {!lrShap ? (
              <p className="text-body-sm text-[#727780]">Feature contribution breakdown not available for this factory.</p>
            ) : (
              <div className="space-y-3">
                <div className="text-xs text-[#42474f] bg-[#f8f9fb] p-2 rounded border border-[#E5E7EB]">
                  Predicted probability: <strong>{(lrShap.predicted_probability * 100).toFixed(1)}%</strong>
                </div>

                <div className="space-y-2">
                  {lrShap.features.slice(0, 5).map((f, idx) => {
                    const maxAbs = Math.max(...lrShap.features.map(x => Math.abs(x.shap_value_logit)), 0.001);
                    const pct = Math.round((Math.abs(f.shap_value_logit) / maxAbs) * 100);
                    const positive = f.shap_value_logit > 0;

                    return (
                      <div key={idx} className="space-y-1 text-xs">
                        <div className="flex justify-between font-bold text-[#191c1e]">
                          <span>{f.label}</span>
                          <span className={positive ? 'text-[#D32F2F]' : 'text-[#1b6d24]'}>
                            {positive ? '+ Pushed Toward Flagged' : '– Supported Normal'}
                          </span>
                        </div>
                        <div className="w-full h-2.5 bg-[#f2f4f6] rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{ width: `${pct}%`, backgroundColor: positive ? '#D32F2F' : '#1b6d24' }}
                          ></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Isolation Forest SHAP */}
          <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-xs space-y-3">
            <div className="flex justify-between items-center">
              <h3 className="text-headline-md font-headline-md text-[#00355f]">Unsupervised Anomaly Evidence</h3>
              <span className="text-[10px] font-bold bg-[#00355f]/10 text-[#00355f] px-2.5 py-0.5 rounded-full">Isolation Forest</span>
            </div>

            <p className="text-xs text-[#727780]">
              Identifies which sensor parameters exhibited the greatest deviation compared to normal regional telemetry.
            </p>

            {!ifShap ? (
              <p className="text-body-sm text-[#727780]">Feature contribution breakdown not available for this factory.</p>
            ) : (
              <div className="space-y-3">
                <div className="text-xs text-[#42474f] bg-[#f8f9fb] p-2 rounded border border-[#E5E7EB]">
                  Evaluated over {ifShap.n_readings_sampled} readings for this site.
                </div>

                <div className="space-y-2">
                  {ifShap.features.slice(0, 5).map((f, idx) => {
                    const maxAbs = Math.max(...ifShap.features.map(x => Math.abs(x.shap_value)), 0.00001);
                    const pct = Math.round((Math.abs(f.shap_value) / maxAbs) * 100);
                    const anomalous = f.shap_value < 0;

                    return (
                      <div key={idx} className="space-y-1 text-xs">
                        <div className="flex justify-between font-bold text-[#191c1e]">
                          <span>{f.label}</span>
                          <span className={anomalous ? 'text-[#D32F2F]' : 'text-[#1b6d24]'}>
                            {anomalous ? 'Unusual Statistical Behavior' : 'Consistent with Baseline'}
                          </span>
                        </div>
                        <div className="w-full h-2.5 bg-[#f2f4f6] rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{ width: `${pct}%`, backgroundColor: anomalous ? '#D32F2F' : '#1b6d24' }}
                          ></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="p-3 bg-[#f8f9fb] border border-[#E5E7EB] rounded-lg text-[11px] text-[#727780] leading-relaxed">
          <strong>Inspector Caution:</strong> Feature influence indicates which statistical characteristics contributed mathematically to the model's output. It does not establish deliberate physical causation or regulatory violations.
        </div>
      </div>

      {/* SECTION 6: Facility Dossier Navigation Link */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 print:hidden">
        <div className="lg:col-span-2 bg-white border border-[#E5E7EB] p-6 rounded-xl flex flex-col justify-between">
          <div>
            <h3 className="text-headline-md font-headline-md text-[#00355f] mb-2">Facility Compliance Overview</h3>
            <p className="text-body-sm text-[#42474f]">
              {fObj.factory_name} is located in {fObj.region || fObj.district}. Priority classification is currently{' '}
              <strong style={{ color: riskColor }}>{(fObj.risk_tier || 'LOW').toUpperCase()}</strong> based on historical rule-based checks.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-[#f2f4f6] text-xs text-[#727780]">
            Consent to Operate (CTO) status: {fObj.has_cto_context ? 'Active CTO consent limits registered' : 'Limited regulatory baseline context'}
          </div>
        </div>

        <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-xs flex flex-col justify-between">
          <div>
            <h3 className="text-headline-md font-headline-md text-[#00355f] mb-2">Complete Facility Dossier</h3>
            <p className="text-body-sm text-[#42474f]">Access official plant metadata, consent limit documents, and past regulatory inspection records.</p>
          </div>
          <button
            className="w-full mt-6 py-2.5 bg-[#f8f9fb] border border-[#E5E7EB] text-[#00355f] font-bold text-body-sm rounded-lg hover:bg-[#edeef0] transition-colors flex items-center justify-center gap-1.5"
            onClick={() => onNavigate('factory-detail', fObj.factory_id)}
          >
            <span>Open Complete Dossier</span>
            <ExternalLink size={14} />
          </button>
        </div>
      </div>

      {/* Mandatory Regulatory & Investigation Disclaimer */}
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

      {/* Inspection Verification Report Modal */}
      <InspectionReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        alertId={selectedModalAlert?.alert_id}
        alertData={selectedModalAlert}
        currentUser={currentUser}
      />
    </div>
  );
}
