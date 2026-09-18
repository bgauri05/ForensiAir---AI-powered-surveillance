import React, { useState, useEffect } from 'react';
import { Bolt, AlertTriangle, Download, CheckCircle2, XCircle, RefreshCw } from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { apiFetch } from '../config';

function correlationColor(value) {
  // Diverging scale: negative -> danger red, 0 -> near-white, positive -> primary blue.
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

function CorrelationHeatmap({ parameters, pairs }) {
  const lookup = {};
  pairs.forEach(p => {
    lookup[`${p.param_a}|${p.param_b}`] = p.correlation;
    lookup[`${p.param_b}|${p.param_a}`] = p.correlation;
  });
  const label = (p) => p.replace('ETP-', '');
  return (
    <div className="overflow-x-auto">
      <table className="border-collapse">
        <thead>
          <tr>
            <th className="p-2"></th>
            {parameters.map(p => (
              <th key={p} className="p-2 text-[10px] font-bold text-[#727780] uppercase">{label(p)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {parameters.map(rowP => (
            <tr key={rowP}>
              <th className="p-2 text-[10px] font-bold text-[#727780] uppercase text-right">{label(rowP)}</th>
              {parameters.map(colP => {
                const val = rowP === colP ? 1 : lookup[`${rowP}|${colP}`];
                return (
                  <td key={colP} className="p-0">
                    <div
                      className="w-14 h-14 flex items-center justify-center text-xs font-bold"
                      style={{
                        backgroundColor: val === undefined ? '#f8f9fb' : correlationColor(val),
                        color: Math.abs(val || 0) > 0.55 ? '#fff' : '#191c1e'
                      }}
                      title={`${label(rowP)} vs ${label(colP)}: ${val === undefined ? 'n/a' : val.toFixed(3)}`}
                    >
                      {val === undefined ? '—' : val.toFixed(2)}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AIAnalysisPage({ onNavigate, selectedFactoryId: initialFactoryId }) {
  const [factories, setFactories] = useState([]);
  const [selectedFactoryId, setSelectedFactoryId] = useState(initialFactoryId || '');
  const [selectedFactoryData, setSelectedFactoryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  // QC FIX (2026-08): a successful re-fetch of unchanged data looked
  // identical to the button doing nothing at all -- the only feedback was
  // the button's own label flicking back from "Running..." to "Run
  // Analysis". This tracks what handleRunAnalysis's re-fetch actually
  // resolved to: 'changed' | 'unchanged' | 'error', so there's always a
  // real, visible signal tied to the actual fetch outcome. Only set by the
  // explicit Run Analysis click, not by switching factories (which always
  // "changes" the displayed data by definition, so that comparison would
  // be meaningless noise).
  const [refreshResult, setRefreshResult] = useState(null);

  const [telemetry, setTelemetry] = useState(null);
  const [correlation, setCorrelation] = useState(null);

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
      setCorrelation(res.ok ? await res.json() : null);
    } catch (err) {
      console.error(err);
      setCorrelation(null);
    }
  };

  const fetchInitialData = async () => {
    try {
      const res = await apiFetch(`/api/factories`);
      if (res.ok) {
        const data = await res.json();
        setFactories(data);
        if (data.length > 0) {
          // Honor the factory clicked elsewhere in the app (e.g. Dashboard's
          // Priority Risk Factors "Inspect") if it's a real match; otherwise
          // fall back to the first high-risk factory.
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
      const [predRes, facDetailRes, shapRes] = await Promise.all([
        apiFetch(`/api/factories/${fid}/predictions`),
        apiFetch(`/api/factories/${fid}`),
        apiFetch(`/api/factories/${fid}/shap`)
      ]);

      let predictions = null;
      let detail = factoryObj;
      let explanation = null;

      if (predRes.ok) predictions = await predRes.json();
      if (facDetailRes.ok) detail = await facDetailRes.json();
      if (shapRes.ok) explanation = await shapRes.json();

      const result = { factory: detail, predictions, explanation };
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

  // Re-fetches this factory's current predictions/explanation -- model
  // inference is precomputed server-side, not something this button can
  // trigger a live retrain of; what it honestly can do is pull the latest
  // computed state for this factory via the same endpoints used on load.
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
    // Auto-clears so it reads as a one-time confirmation of this click,
    // not a persistent status bar that goes stale.
    setTimeout(() => setRefreshResult(null), 6000);
  };

  if (loading) {
    return <div className="p-8 font-body-md text-[#42474f]">Loading AI Analysis...</div>;
  }

  const fObj = selectedFactoryData?.factory || factories[0] || {};
  const pred = selectedFactoryData?.predictions || {};
  const explanation = selectedFactoryData?.explanation || null;
  const breakdown = explanation?.composite_breakdown || null;
  const fingerprintChecks = explanation?.fingerprint_checks || [];
  const lrShap = explanation?.shap?.tamper_model_shap || null;
  const ifShap = explanation?.shap?.isolation_forest_shap || null;

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

  return (
    <div className="p-8 max-w-[1600px] mx-auto space-y-6 print:p-0 print:max-w-full">
      {/* Header & Breadcrumb */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <nav className="flex items-center gap-2 text-[#727780] font-label-caps text-[10px] uppercase tracking-widest mb-2 print:hidden">
            <span className="hover:text-[#00355f] cursor-pointer">Forensics</span>
            <span className="material-symbols-outlined text-xs">chevron_right</span>
            <span className="text-[#191c1e] font-bold">AI Analysis</span>
          </nav>
          <h1 className="text-headline-lg font-headline-lg text-[#00355f]">AI Analysis</h1>
          <p className="text-body-md text-[#42474f]">
            Facility: <span className="font-bold text-[#191c1e]">{fObj.factory_name || fObj.name}</span> | ID: #{fObj.factory_id}
          </p>
        </div>

        {/* QC FIX (2026-08): no flex-wrap meant this row (select + two
            buttons) forced real horizontal page overflow below ~700px --
            confirmed live at 375px. flex-wrap plus a capped select width
            let it wrap onto its own line instead of pushing the page wide. */}
        <div className="flex flex-wrap items-center gap-3 bg-white border border-[#E5E7EB] p-4 rounded-xl shadow-xs print:hidden">
          <div className="text-right">
            <div className="text-label-caps text-[#727780] uppercase font-bold">Target Facility</div>
            <select
              value={selectedFactoryId}
              onChange={(e) => handleSelectFactory(e.target.value)}
              className="max-w-[180px] text-body-sm font-bold text-[#00355f] bg-[#f8f9fb] border border-[#E5E7EB] rounded px-3 py-1 cursor-pointer focus:outline-none"
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
            className="flex items-center gap-2 bg-[#0f4c81] text-white px-5 py-2.5 rounded-lg font-bold hover:opacity-90 transition-all text-body-sm shadow-sm disabled:opacity-50"
          >
            <Bolt size={18} className={analyzing ? 'animate-spin' : ''} />
            <span>{analyzing ? 'Running...' : 'Run Analysis'}</span>
          </button>
          <button
            onClick={() => window.print()}
            className="flex items-center gap-2 bg-white border border-[#E5E7EB] text-[#00355f] px-5 py-2.5 rounded-lg font-bold hover:bg-[#f8f9fb] transition-all text-body-sm"
          >
            <Download size={18} />
            <span>Export</span>
          </button>
        </div>
      </div>

      {/* Run Analysis feedback -- resolved-state signal for handleRunAnalysis,
          separate from the button's own pending-state label/spin (analyzing).
          Without this, a re-fetch that returned identical data looked exactly
          like the button doing nothing. */}
      {analyzing && (
        <div className="flex items-center gap-2 text-body-sm text-[#727780] print:hidden">
          <RefreshCw size={14} className="animate-spin" />
          Fetching the latest computed state for this factory...
        </div>
      )}
      {!analyzing && refreshResult === 'unchanged' && (
        <div className="flex items-center gap-2 text-body-sm text-[#1b6d24] print:hidden">
          <CheckCircle2 size={14} />
          Refreshed -- data is already current, no change since last check.
        </div>
      )}
      {!analyzing && refreshResult === 'changed' && (
        <div className="flex items-center gap-2 text-body-sm text-[#0f4c81] print:hidden">
          <RefreshCw size={14} />
          Refreshed -- values updated since last check.
        </div>
      )}
      {!analyzing && refreshResult === 'error' && (
        <div className="flex items-center gap-2 text-body-sm text-[#D32F2F] print:hidden">
          <XCircle size={14} />
          Refresh failed -- showing the last successfully loaded data.
        </div>
      )}

      {/* Analysis Results KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="bg-white border border-[#E5E7EB] p-6 rounded-xl shadow-xs flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <span className="text-label-caps text-[#727780] uppercase font-bold">Overall Risk Profile</span>
            <AlertTriangle size={20} style={{ color: riskColor }} />
          </div>
          <div className="mt-4">
            <span className="px-3 py-1 text-label-caps font-bold rounded-full" style={{ backgroundColor: `${riskColor}1A`, color: riskColor }}>
              {(fObj.risk_tier || 'LOW').toUpperCase()}
            </span>
          </div>
          <p className="mt-3 text-body-sm text-[#42474f] italic">
            {pred.note
              ? pred.note
              : isHighRisk
              ? `Elevated tamper risk detected for ${fObj.factory_name}.`
              : isMediumRisk
              ? `Moderate statistical deviation detected for ${fObj.factory_name}.`
              : `Nominal telemetry parameters detected for ${fObj.factory_name}.`
            }
          </p>
        </div>

        <div className="bg-white border border-[#E5E7EB] p-6 rounded-xl shadow-xs">
          <span className="text-label-caps text-[#727780] uppercase font-bold">Tampering Probability</span>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-display-kpi font-display-kpi" style={{ color: riskColor }}>{tamperProb}</span>
          </div>
          <div className="w-full bg-[#edeef0] h-2 mt-4 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full"
              style={{ width: tamperProb !== 'Not available' ? `${Math.min(100, parseFloat(tamperProb))}%` : '0%', backgroundColor: riskColor }}
            ></div>
          </div>
        </div>

        <div className="bg-white border border-[#E5E7EB] p-6 rounded-xl shadow-xs">
          <span className="text-label-caps text-[#727780] uppercase font-bold">Isolation Forest Anomaly Score</span>
          <div className="mt-4 flex items-baseline gap-2">
            <span className="text-display-kpi font-display-kpi" style={{ color: riskColor }}>{isoScore}</span>
            <span className="text-body-sm font-bold" style={{ color: riskColor }}>
              ({isHighRisk ? 'High' : isMediumRisk ? 'Moderate' : 'Low'})
            </span>
          </div>
          <p className="mt-2 text-body-sm text-[#42474f]">
            Statistical distance vs {fObj.region || 'district'} baseline.
          </p>
        </div>
      </div>

      {/* Composite Score Breakdown -- risk_engine.py's real weighted arithmetic */}
      <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-xs">
        <h3 className="text-headline-md font-headline-md text-[#00355f] mb-1">Composite Risk Score Breakdown</h3>
        <p className="text-body-sm text-[#727780] mb-4">The three weighted components that sum to the total risk score below.</p>
        {!breakdown ? (
          <p className="text-body-sm text-[#727780]">Composite breakdown not available for this factory.</p>
        ) : (
          <div className="space-y-4">
            {/* QC FIX (2026-08): w-56 label + w-16 value (288px) plus gaps
                left no room for the bar at 375px wide (card content area is
                ~263px there) -- confirmed live, forced real page overflow.
                Narrower fixed widths below sm:, full size at sm: and up. */}
            {[
              { label: 'Fingerprint Checks', weight: breakdown.fingerprints.weight, detail: `${breakdown.fingerprints.triggered_count} / ${breakdown.fingerprints.total_checks} triggered`, contribution: breakdown.fingerprints.contribution },
              { label: 'Isolation Forest', weight: breakdown.isolation_forest.weight, detail: `normalized anomaly score ${breakdown.isolation_forest.score_norm}`, contribution: breakdown.isolation_forest.contribution },
              { label: 'Factory-Level Tamper Model', weight: breakdown.tamper_model.weight, detail: `predicted probability ${(breakdown.tamper_model.probability * 100).toFixed(1)}%`, contribution: breakdown.tamper_model.contribution },
            ].map((row, idx) => (
              <div key={idx} className="flex items-center gap-3 sm:gap-4">
                <div className="w-28 sm:w-56 shrink-0">
                  <div className="font-bold text-body-sm text-[#191c1e]">{row.label}</div>
                  <div className="text-xs text-[#727780]">{(row.weight * 100).toFixed(1)}% weight · {row.detail}</div>
                </div>
                <div className="flex-1 h-3 bg-[#f2f4f6] rounded-full overflow-hidden">
                  <div className="h-full rounded-full bg-[#0f4c81]" style={{ width: `${Math.min(100, (row.contribution / breakdown.total_risk_score) * 100 || 0)}%` }}></div>
                </div>
                <div className="w-14 sm:w-16 text-right font-bold text-body-sm text-[#191c1e]">{row.contribution}</div>
              </div>
            ))}
            <div className="flex items-center gap-3 sm:gap-4 pt-3 border-t border-[#E5E7EB]">
              <div className="w-28 sm:w-56 shrink-0 font-bold text-body-sm text-[#00355f]">Total Risk Score</div>
              <div className="flex-1"></div>
              <div className="w-14 sm:w-16 text-right font-display-kpi text-headline-md" style={{ color: riskColor }}>{breakdown.total_risk_score}</div>
            </div>
          </div>
        )}
      </div>

      {/* Fingerprint Checks -- all 8, real values, real thresholds */}
      <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-xs">
        <h3 className="text-headline-md font-headline-md text-[#00355f] mb-4">Fingerprint Checks</h3>
        {fingerprintChecks.length === 0 ? (
          <p className="text-body-sm text-[#727780]">Fingerprint check detail not available for this factory.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {fingerprintChecks.map((chk) => (
              <div key={chk.key} className={`p-3 rounded-lg border flex items-start gap-3 ${chk.triggered ? 'bg-[#D32F2F]/5 border-[#D32F2F]/20' : 'bg-[#f8f9fb] border-[#E5E7EB]'}`}>
                {chk.triggered
                  ? <XCircle size={18} className="text-[#D32F2F] shrink-0 mt-0.5" />
                  : <CheckCircle2 size={18} className="text-[#1b6d24] shrink-0 mt-0.5" />
                }
                <div>
                  <div className="font-bold text-body-sm text-[#191c1e]">{chk.label}</div>
                  <div className="text-xs text-[#42474f]">Value: {fmtRaw(chk.raw_value, chk.unit)}</div>
                  <div className="text-xs text-[#727780]">Trigger: {chk.threshold_desc}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Telemetry Trend -- real daily-aggregated OCEMS readings vs CPCB consent-limit band */}
      <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-1">
          <h3 className="text-headline-md font-headline-md text-[#00355f]">Telemetry Trend</h3>
          {telemetry && telemetry.available_parameters.length > 1 && (
            <select
              value={telemetry.parameter}
              onChange={(e) => handleTelemetryParamChange(e.target.value)}
              className="text-body-sm font-bold text-[#00355f] bg-[#f8f9fb] border border-[#E5E7EB] rounded px-3 py-1 cursor-pointer focus:outline-none"
            >
              {telemetry.available_parameters.map(p => (
                <option key={p} value={p}>{p.replace('ETP-', '')}</option>
              ))}
            </select>
          )}
        </div>
        {!telemetry ? (
          <p className="text-body-sm text-[#727780]">Telemetry not available for this factory.</p>
        ) : (
          <>
            <p className="text-xs text-[#727780] mb-4">
              Daily-aggregated {telemetry.parameter.replace('ETP-', '')} readings ({telemetry.unit || 'unit n/a'}) from {telemetry.source === 'synthetic' ? 'synthetic data (no real telemetry logged for this parameter)' : 'real OCEMS telemetry'}.
              {telemetry.consent_min !== null && telemetry.consent_max !== null && ` Dashed lines mark the CPCB regulatory standard band (${telemetry.consent_min}–${telemetry.consent_max}).`}
            </p>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={telemetry.series} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#edeef0" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} interval={Math.max(0, Math.floor(telemetry.series.length / 8))} />
                <YAxis tick={{ fontSize: 10 }} domain={['auto', 'auto']} />
                <Tooltip labelFormatter={(label) => `Date: ${label}`} />
                {telemetry.consent_min !== null && (
                  <ReferenceLine y={telemetry.consent_min} stroke="#F57C00" strokeDasharray="4 4" label={{ value: 'Min', fontSize: 10, fill: '#F57C00' }} />
                )}
                {telemetry.consent_max !== null && (
                  <ReferenceLine y={telemetry.consent_max} stroke="#D32F2F" strokeDasharray="4 4" label={{ value: 'Max', fontSize: 10, fill: '#D32F2F' }} />
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
                    return <circle key={`dot-${index}`} cx={cx} cy={cy} r={flagged ? 3 : 1.5} fill={flagged ? '#D32F2F' : '#0f4c81'} stroke="none" />;
                  }}
                  activeDot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
            <div className="flex items-center gap-2 mt-2 text-xs text-[#727780]">
              <span className="w-2 h-2 rounded-full bg-[#D32F2F] inline-block"></span>
              Red dot = day with &gt;50% of readings flatlined
            </div>

            <div className="mt-6">
              <div className="text-xs font-bold text-[#191c1e] mb-1">Limit-Hugging Rate (% of readings that day)</div>
              <ResponsiveContainer width="100%" height={80}>
                <BarChart data={telemetry.series} margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
                  <XAxis dataKey="date" hide />
                  <YAxis hide domain={[0, 1]} />
                  <Tooltip formatter={(v) => (v === null ? 'n/a' : `${(v * 100).toFixed(1)}%`)} labelFormatter={(label) => `Date: ${label}`} />
                  <Bar dataKey="limit_hugging_pct" fill="#F57C00" isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </div>

      {/* Parameter Correlation Matrix -- real, from real_features.parquet's rolling corr_<A>_<B> features */}
      <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-xs">
        <h3 className="text-headline-md font-headline-md text-[#00355f] mb-1">Parameter Correlation Matrix</h3>
        <p className="text-xs text-[#727780] mb-4">
          Mean pairwise correlation between this factory's monitored parameters over the full telemetry history. A sudden real-world break from a typically-correlated pair is one of the eight tampering fingerprint checks above.
        </p>
        {!correlation || correlation.pairs.length === 0 ? (
          <p className="text-body-sm text-[#727780]">{correlation?.note || 'Correlation matrix not available for this factory.'}</p>
        ) : (
          <CorrelationHeatmap parameters={correlation.parameters} pairs={correlation.pairs} />
        )}
      </div>

      {/* SHAP Explanations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-xs">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-headline-md font-headline-md text-[#00355f]">Tamper Model SHAP (Logistic Regression)</h3>
            <span className="text-label-caps font-label-caps bg-[#00355f]/10 text-[#00355f] px-3 py-1 rounded-full font-bold">LinearExplainer</span>
          </div>
          {!lrShap ? (
            <p className="text-body-sm text-[#727780]">SHAP explanation not available for this factory.</p>
          ) : (
            <div className="space-y-4">
              <p className="text-xs text-[#727780]">Values are in log-odds (logit) space -- the model's native additive units. Predicted probability: {(lrShap.predicted_probability * 100).toFixed(1)}%.</p>
              {lrShap.features.slice(0, 6).map((f, idx) => {
                const maxAbs = Math.max(...lrShap.features.map(x => Math.abs(x.shap_value_logit)), 0.001);
                const pct = Math.round((Math.abs(f.shap_value_logit) / maxAbs) * 100);
                const positive = f.shap_value_logit > 0;
                return (
                  <div key={idx} className="space-y-1">
                    <div className="flex justify-between text-body-sm font-bold text-[#191c1e]">
                      <span>{f.label}</span>
                      <span className={positive ? 'text-[#D32F2F]' : 'text-[#1b6d24]'}>{positive ? '+' : ''}{f.shap_value_logit}</span>
                    </div>
                    <div className="w-full h-3 bg-[#f2f4f6] rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: positive ? '#D32F2F' : '#1b6d24' }}></div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-xs">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-headline-md font-headline-md text-[#00355f]">Isolation Forest SHAP</h3>
            <span className="text-label-caps font-label-caps bg-[#00355f]/10 text-[#00355f] px-3 py-1 rounded-full font-bold">KernelExplainer</span>
          </div>
          {!ifShap ? (
            <p className="text-body-sm text-[#727780]">SHAP explanation not available for this factory.</p>
          ) : (
            <div className="space-y-4">
              <p className="text-xs text-[#727780]">
                Averaged over {ifShap.n_readings_sampled} of {ifShap.n_readings_total} real readings for this factory. Mean anomaly score: {ifShap.mean_anomaly_score} (more negative = more anomalous).
              </p>
              {ifShap.features.slice(0, 6).map((f, idx) => {
                const maxAbs = Math.max(...ifShap.features.map(x => Math.abs(x.shap_value)), 0.00001);
                const pct = Math.round((Math.abs(f.shap_value) / maxAbs) * 100);
                const anomalous = f.shap_value < 0;
                return (
                  <div key={idx} className="space-y-1">
                    <div className="flex justify-between text-body-sm font-bold text-[#191c1e]">
                      <span>{f.label}</span>
                      <span className={anomalous ? 'text-[#D32F2F]' : 'text-[#1b6d24]'}>{f.shap_value}</span>
                    </div>
                    <div className="w-full h-3 bg-[#f2f4f6] rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: anomalous ? '#D32F2F' : '#1b6d24' }}></div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Risk Level Indicator + Dossier Link */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 print:hidden">
        <div className="lg:col-span-2 bg-white border border-[#E5E7EB] p-6 rounded-xl flex flex-col">
          <h3 className="text-headline-md font-headline-md text-[#00355f] mb-6">Risk Level Indicator</h3>
          <div className="relative pt-4">
            <div className="flex h-12 w-full rounded-lg overflow-hidden border border-[#E5E7EB]">
              <div className={`flex-1 flex items-center justify-center text-[10px] font-bold uppercase ${!isHighRisk && !isMediumRisk ? 'bg-[#1b6d24] text-white ring-4 ring-[#1b6d24]/30 z-10' : 'bg-[#1b6d24]/20 text-[#1b6d24]'}`}>Low</div>
              <div className={`flex-1 flex items-center justify-center text-[10px] font-bold uppercase ${isMediumRisk ? 'bg-[#F57C00] text-white ring-4 ring-[#F57C00]/30 z-10' : 'bg-yellow-400/20 text-yellow-700'}`}>Medium</div>
              <div className={`flex-1 flex items-center justify-center text-[10px] font-bold uppercase ${isHighRisk ? 'bg-[#D32F2F] text-white ring-4 ring-[#D32F2F]/30 z-10' : 'bg-[#F57C00]/20 text-[#F57C00]'}`}>High</div>
            </div>
          </div>
        </div>

        <div className="bg-white border border-[#E5E7EB] rounded-xl p-6 shadow-xs flex flex-col justify-between">
          <div>
            <h3 className="text-headline-md font-headline-md text-[#00355f] mb-2">Factory Dossier</h3>
            <p className="text-body-sm text-[#42474f]">Full facility metadata, consent limits, and inspection history.</p>
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
