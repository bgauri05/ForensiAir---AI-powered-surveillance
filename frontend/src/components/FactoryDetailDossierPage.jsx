import React, { useState, useEffect } from 'react';
import { ArrowLeft, Factory, Gauge, Target, Activity, ClipboardList, Download, ShieldAlert } from 'lucide-react';
import { apiFetch } from '../config';

export function FactoryDetailDossierPage({ onNavigate, selectedFactoryId }) {
  const [factoriesList, setFactoriesList] = useState([]);
  const [selectedFid, setSelectedFid] = useState(selectedFactoryId || '');
  const [factoryData, setFactoryData] = useState(null);
  const [inspections, setInspections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [auditState, setAuditState] = useState('idle'); // idle | submitting | done | error

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
      const res = await apiFetch(`/api/factories`);
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
        apiFetch(`/api/factories/${fid}`),
        apiFetch(`/api/factories/${fid}/inspections`)
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
    setAuditState('idle');
    fetchFactoryDetail(fid);
  };

  const handleInitiateAudit = async () => {
    if (!selectedFid || auditState === 'submitting') return;
    setAuditState('submitting');
    try {
      const res = await apiFetch(`/api/factories/${selectedFid}/audit`, { method: 'POST' });
      if (!res.ok) throw new Error('Audit request failed');
      await fetchFactoryDetail(selectedFid);
      setAuditState('done');
    } catch (err) {
      console.error(err);
      setAuditState('error');
    }
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-3 text-[var(--color-text-muted)]">
        <span className="material-symbols-outlined animate-spin text-3xl text-[var(--color-primary)]">progress_activity</span>
        <p className="font-body-sm text-body-sm">Loading Factory Dossier...</p>
      </div>
    );
  }

  const fObj = factoryData || factoriesList[0] || {};
  const isHighRisk = fObj.risk_tier === 'High' || fObj.risk_tier === 'High Risk';
  const isMediumRisk = fObj.risk_tier === 'Medium' || fObj.risk_tier === 'Moderate Risk';

  // Dynamic calculations based on DB factory object
  const regionStr = fObj.region || fObj.district || 'Taloja';
  const licenseNo = fObj.consent_number || 'Not available';
  const plotAddress = fObj.address || 'Not available';
  const plantHead = fObj.contact_person || 'Not available';

  const bodAvg = (fObj.avg_bod !== undefined && fObj.avg_bod !== null) ? `${fObj.avg_bod} mg/L` : 'Not available';
  const codAvg = (fObj.avg_cod !== undefined && fObj.avg_cod !== null) ? `${fObj.avg_cod} mg/L` : 'Not available';
  const phAvg = 'Not available';

  const tamperProbVal = fObj.tamper_probability !== undefined
    ? `${fObj.tamper_probability.toFixed(1)}%`
    : 'Not available';

  const anomalyScoreVal = fObj.raw_fingerprint_signals?.anomaly_score !== undefined
    ? fObj.raw_fingerprint_signals.anomaly_score.toFixed(2)
    : fObj.anomaly_score !== undefined
    ? fObj.anomaly_score.toFixed(2)
    : 'Not available';

  const riskColor = isHighRisk ? 'var(--color-danger)' : isMediumRisk ? 'var(--color-warning)' : 'var(--color-success)';

  return (
    <div className="space-y-6 print:space-y-4">
      {/* Top Header Banner */}
      <div className="bg-[var(--color-surface)] border-b border-[var(--color-border)] px-8 py-6 print:px-0 print:py-0 print:border-none">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <button
                onClick={() => onNavigate('dashboard')}
                className="p-1.5 hover:bg-[var(--color-bg)] rounded-full transition-colors print:hidden"
              >
                <ArrowLeft size={18} className="text-[var(--color-primary)]" />
              </button>
              <h2 className="font-headline-lg text-headline-lg text-[var(--color-primary)]">{fObj.factory_name || fObj.name}</h2>
              <span className={`px-3 py-1 rounded text-[11px] font-bold uppercase ${
                isHighRisk
                  ? 'bg-[var(--color-danger)]/10 text-[var(--color-danger)] border border-[var(--color-danger)]/20'
                  : isMediumRisk
                  ? 'bg-[var(--color-warning)]/10 text-[var(--color-warning)] border border-[var(--color-warning)]/20'
                  : 'bg-[var(--color-success)]/10 text-[var(--color-success)] border border-[var(--color-success)]/20'
              }`}>
                {fObj.risk_tier || 'LOW RISK'}
              </span>
            </div>
            <div className="flex flex-wrap gap-6 text-[var(--color-text-secondary)] text-body-sm">
              <div>Industry: <span className="font-bold text-[var(--color-text)]">{fObj.industry || 'Chemical Manufacturing'}</span></div>
              <div>District: <span className="font-bold text-[var(--color-text)]">{regionStr}</span></div>
              <div>ID: <span className="font-bold text-[var(--color-text)]">#{fObj.factory_id}</span></div>
            </div>
          </div>

          <div className="flex items-center gap-3 print:hidden">
            <select
              value={selectedFid}
              onChange={(e) => handleSelectFactory(e.target.value)}
              className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3 py-2 text-body-sm font-bold text-[var(--color-primary)] cursor-pointer transition-colors hover:border-[var(--color-border-strong)] focus:outline-none focus:ring-1 focus:ring-[var(--color-primary)]"
            >
              {factoriesList.map(f => (
                <option key={f.factory_id} value={f.factory_id}>
                  {f.factory_name || f.name} ({f.region || f.district})
                </option>
              ))}
            </select>

            <button onClick={() => window.print()} className="btn btn-secondary flex items-center gap-2">
              <Download size={14} /> Export Dossier
            </button>
            <button
              onClick={handleInitiateAudit}
              disabled={auditState === 'submitting'}
              className={`btn btn-primary flex items-center gap-2 ${auditState === 'submitting' ? 'opacity-60 cursor-wait' : ''}`}
            >
              <ShieldAlert size={14} />
              {auditState === 'submitting' ? 'Submitting...' : auditState === 'done' ? 'Audit Requested' : 'Initiate Audit'}
            </button>
          </div>
        </div>
        {auditState === 'done' && (
          <p className="mt-2 text-body-sm text-[var(--color-success)] print:hidden">
            Audit request recorded for this factory and added to its inspection history below.
          </p>
        )}
        {auditState === 'error' && (
          <p className="mt-2 text-body-sm text-[var(--color-danger)] print:hidden">
            Could not record the audit request. Please try again.
          </p>
        )}
      </div>

      {/* Main Dossier Content */}
      <div className="px-8 pb-12 max-w-[1600px] mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Dynamic Metadata & License Info */}
        <div className="lg:col-span-4 space-y-6">
          <div className="card p-6">
            <h3 className="font-label-caps text-label-caps text-[var(--color-text-muted)] uppercase mb-4 font-bold flex items-center gap-2">
              <Factory size={14} /> Core Facility Metadata
            </h3>
            <div className="space-y-4 text-body-sm">
              <div>
                <p className="text-[11px] text-[var(--color-text-muted)] font-bold uppercase mb-0.5">Environmental License</p>
                <p className={licenseNo === 'Not available' ? 'value-unavailable' : 'font-bold text-[var(--color-text)]'}>{licenseNo}</p>
              </div>
              <div>
                <p className="text-[11px] text-[var(--color-text-muted)] font-bold uppercase mb-0.5">Location / Address</p>
                <p className={plotAddress === 'Not available' ? 'value-unavailable' : 'font-medium text-[var(--color-text)]'}>{plotAddress}</p>
              </div>
              <div>
                <p className="text-[11px] text-[var(--color-text-muted)] font-bold uppercase mb-0.5">Inspection Contact</p>
                <p className={plantHead === 'Not available' ? 'value-unavailable' : 'font-medium text-[var(--color-text)]'}>{plantHead}</p>
              </div>
            </div>
          </div>

          <div className="card p-6">
            <h3 className="font-label-caps text-label-caps text-[var(--color-text-muted)] uppercase mb-4 font-bold flex items-center gap-2">
              <Gauge size={14} /> Consent Limit Parameters
            </h3>
            <div className="space-y-3.5">
              <div className="p-3 bg-[var(--color-bg)] rounded-lg border border-[var(--color-border)]">
                <div className="flex justify-between text-body-sm font-bold">
                  <span>BOD Concentration</span>
                  <span className="text-[var(--color-danger)]">30 mg/L Max Limit</span>
                </div>
                <div className="text-xs text-[var(--color-text-secondary)] mt-1">
                  Current telemetry average: <strong className={bodAvg === 'Not available' ? 'value-unavailable' : 'text-[var(--color-text)]'}>{bodAvg}</strong>
                </div>
              </div>
              <div className="p-3 bg-[var(--color-bg)] rounded-lg border border-[var(--color-border)]">
                <div className="flex justify-between text-body-sm font-bold">
                  <span>COD Concentration</span>
                  <span className="text-[var(--color-warning)]">250 mg/L Max Limit</span>
                </div>
                <div className="text-xs text-[var(--color-text-secondary)] mt-1">
                  Current telemetry average: <strong className={codAvg === 'Not available' ? 'value-unavailable' : 'text-[var(--color-text)]'}>{codAvg}</strong>
                </div>
              </div>
              <div className="p-3 bg-[var(--color-bg)] rounded-lg border border-[var(--color-border)]">
                <div className="flex justify-between text-body-sm font-bold">
                  <span>pH Tolerance Range</span>
                  <span className="text-[var(--color-success)]">5.5 - 9.0 pH</span>
                </div>
                <div className="text-xs text-[var(--color-text-secondary)] mt-1">
                  Current telemetry average: <strong className={phAvg === 'Not available' ? 'value-unavailable' : 'text-[var(--color-text)]'}>{phAvg}</strong>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Dynamic AI Analysis Summary & History */}
        <div className="lg:col-span-8 space-y-6">
          <div className="card p-6">
            <h3 className="font-headline-md text-headline-md text-[var(--color-primary)] mb-4">AI Tamper Risk Evaluation</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
              <div className="p-4 bg-[var(--color-bg)] border border-[var(--color-border)] rounded-lg">
                <span className="text-label-caps text-[var(--color-text-muted)] font-bold flex items-center gap-1.5">
                  <Target size={12} /> TAMPER PROBABILITY
                </span>
                {tamperProbVal === 'Not available' ? (
                  <div className="value-unavailable text-body-sm mt-2">{tamperProbVal}</div>
                ) : (
                  <div className="font-display-kpi text-display-kpi mt-1" style={{ color: riskColor }}>{tamperProbVal}</div>
                )}
              </div>
              <div className="p-4 bg-[var(--color-bg)] border border-[var(--color-border)] rounded-lg">
                <span className="text-label-caps text-[var(--color-text-muted)] font-bold flex items-center gap-1.5">
                  <Activity size={12} /> ANOMALY SCORE
                </span>
                {anomalyScoreVal === 'Not available' ? (
                  <div className="value-unavailable text-body-sm mt-2">{anomalyScoreVal}</div>
                ) : (
                  <div className="font-display-kpi text-display-kpi mt-1" style={{ color: riskColor }}>{anomalyScoreVal}</div>
                )}
              </div>
            </div>

            <div className="p-4 bg-[var(--color-bg)] rounded-lg border border-[var(--color-border)]">
              <div className="font-body-sm font-bold text-[var(--color-text)] mb-1">Inspector Recommendation</div>
              <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed">
                {fObj.note
                  ? fObj.note
                  : isHighRisk
                  ? `Elevated tamper risk detected for ${fObj.factory_name || fObj.name}. Priority physical audit recommended for sensor calibration verification.`
                  : isMediumRisk
                  ? `Moderate telemetry variance detected for ${fObj.factory_name || fObj.name}. Scheduled calibration check recommended within 48 hours.`
                  : `Telemetry for ${fObj.factory_name || fObj.name} is operating within nominal environmental compliance thresholds. Continue routine automated monitoring.`
                }
              </p>
            </div>
          </div>

          <div className="card p-6">
            <h3 className="font-headline-md text-headline-md text-[var(--color-primary)] mb-4 flex items-center gap-2">
              <ClipboardList size={18} /> Past Inspection History
            </h3>
            <div className="space-y-3 text-body-sm">
              {inspections.length === 0 ? (
                <div className="empty-state">
                  <span className="material-symbols-outlined">history_toggle_off</span>
                  <p>No inspection history on record for this factory.</p>
                </div>
              ) : inspections.map((insp, idx) => {
                const borderColor = insp.inspection_type === 'High Risk' ? 'var(--color-danger)' : insp.inspection_type === 'Medium Risk' ? 'var(--color-warning)' : 'var(--color-success)';
                const isCompleted = insp.status === 'Completed';
                return (
                  <div key={idx} className="p-3 rounded-r-lg flex justify-between items-center bg-[var(--color-bg)]" style={{ borderLeft: `4px solid ${borderColor}` }}>
                    <div>
                      <div className="font-bold text-[var(--color-text)]">{insp.inspection_type} Inspection</div>
                      <div className="text-xs text-[var(--color-text-secondary)]">{insp.inspection_date}</div>
                    </div>
                    <span className={`px-2.5 py-1 text-xs font-bold rounded ${isCompleted ? 'text-[var(--color-success)] bg-[var(--color-success)]/10' : 'text-[var(--color-warning)] bg-[var(--color-warning)]/10'}`}>
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
