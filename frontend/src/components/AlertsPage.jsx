import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  ChevronRight,
  ChevronDown,
  ShieldAlert,
  Download,
  Info,
  CheckCircle2,
  Filter,
  FileText
} from 'lucide-react';
import { apiFetch } from '../config';
import { InspectionReportModal } from './InspectionReportModal';

export function AlertsPage({ onNavigate, currentUser }) {
  const [activeTab, setActiveTab] = useState('v2'); // 'v2' or 'legacy'
  const [v2Data, setV2Data] = useState({ alerts: [], total: 0 });
  const [legacyFactories, setLegacyFactories] = useState([]);
  const [reportStatuses, setReportStatuses] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  // Filters & Accordion
  const [selectedType, setSelectedType] = useState('ALL');
  const [selectedSeverity, setSelectedSeverity] = useState('ALL');
  const [expandedAlertId, setExpandedAlertId] = useState(null);

  // Inspection Report Modal state
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [selectedModalAlert, setSelectedModalAlert] = useState(null);
  const [selectedModalReportId, setSelectedModalReportId] = useState(null);

  useEffect(() => {
    fetchAlertsData();
  }, []);

  const fetchAlertsData = async () => {
    setLoading(true);
    setError(false);
    try {
      const [v2Res, facRes, repRes] = await Promise.all([
        apiFetch(`/api/v2/alerts?limit=100&detected_only=true`),
        apiFetch(`/api/factories`),
        apiFetch(`/api/reports/alerts/status`)
      ]);

      if (v2Res.ok) {
        const v2Json = await v2Res.json();
        setV2Data(v2Json);
      } else {
        setError(true);
      }

      if (facRes.ok) {
        const facJson = await facRes.json();
        const flagged = (facJson || [])
          .filter((f) => f.risk_tier === 'High' || f.risk_tier === 'Medium')
          .sort((a, b) => (b.tsi_score || 0) - (a.tsi_score || 0));
        setLegacyFactories(flagged);
      }

      if (repRes.ok) {
        const repJson = await repRes.json();
        setReportStatuses(repJson || {});
      }
    } catch (err) {
      console.error('Error fetching alerts:', err);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  const toggleExpand = (id) => {
    setExpandedAlertId(expandedAlertId === id ? null : id);
  };

  const handleExportCSV = () => {
    const alertsToExport = filteredV2Alerts;
    if (alertsToExport.length === 0) return;

    const headers = [
      'Alert ID',
      'Facility ID',
      'Facility Name',
      'Region',
      'Industry',
      'Parameter',
      'Tamper Type',
      'Anomaly Category',
      'Severity',
      'Start Time',
      'End Time',
      'Duration (Hours)',
      'Duration (Readings)',
      'Observed Pattern',
      'Reason Flagged',
      'Possible Explanations',
      'Recommended Checks',
      'Data Source',
      'Disclaimer'
    ];

    const rows = alertsToExport.map((a) => [
      `"${a.alert_id}"`,
      `"${a.factory_id}"`,
      `"${a.factory_name.replace(/"/g, '""')}"`,
      `"${a.region || ''}"`,
      `"${a.industry || ''}"`,
      `"${a.parameter}"`,
      `"${a.tamper_type}"`,
      `"${a.anomaly_category}"`,
      `"${a.severity}"`,
      `"${a.start_time}"`,
      `"${a.end_time}"`,
      a.duration_hours,
      a.duration_rows,
      `"${(a.evidence?.observed || '').replace(/"/g, '""')}"`,
      `"${(a.evidence?.why_flagged || '').replace(/"/g, '""')}"`,
      `"${(a.evidence?.possible_explanations || '').replace(/"/g, '""')}"`,
      `"${(a.evidence?.recommended_checks?.join('; ') || '').replace(/"/g, '""')}"`,
      `"Historical Development Evaluation"`,
      `"ForensiAIR identifies unusual patterns in wastewater telemetry that may indicate data-quality or data-integrity issues. Alerts are indicators for further investigation and do not establish deliberate tampering, misconduct, or regulatory non-compliance. Possible explanations include sensor faults, maintenance, operational changes, missing data, and transmission issues. Verify readings and operational records before drawing conclusions."`
    ]);

    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `ForensiAIR_V2_Historical_Alerts_Report_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const filteredV2Alerts = (v2Data.alerts || []).filter((a) => {
    if (selectedType !== 'ALL' && a.tamper_type !== selectedType) return false;
    if (selectedSeverity !== 'ALL' && a.severity.toLowerCase() !== selectedSeverity.toLowerCase()) return false;
    return true;
  });

  const getSeverityBadge = (sev) => {
    switch (sev.toLowerCase()) {
      case 'obvious':
        return { text: 'text-[#D32F2F]', bg: 'bg-[#fdecec]', border: 'border-[#D32F2F]/20', label: 'High Deviation' };
      case 'moderate':
        return { text: 'text-[#F57C00]', bg: 'bg-[#fff3e6]', border: 'border-[#F57C00]/20', label: 'Moderate Deviation' };
      default:
        return { text: 'text-[#00355f]', bg: 'bg-[#e7f0f8]', border: 'border-[#00355f]/20', label: 'Subtle Deviation' };
    }
  };

  const getReportBadge = (alertId) => {
    const rep = reportStatuses[String(alertId)];
    if (!rep) {
      return {
        status: 'none',
        label: 'No Verification Report',
        bg: 'bg-[#f2f4f6]',
        text: 'text-[#727780]',
        border: 'border-[#E5E7EB]'
      };
    }
    switch (rep.status) {
      case 'Reviewed':
        return {
          status: 'Reviewed',
          label: 'Reviewed & Verified',
          bg: 'bg-[#e8f5e9]',
          text: 'text-[#1b6d24]',
          border: 'border-[#1b6d24]/30',
          reportId: rep.report_id
        };
      case 'Submitted for Review':
        return {
          status: 'Submitted for Review',
          label: 'Submitted for Review',
          bg: 'bg-[#e7f0f8]',
          text: 'text-[#00355f]',
          border: 'border-[#00355f]/30',
          reportId: rep.report_id
        };
      case 'Further Information Required':
        return {
          status: 'Further Information Required',
          label: 'Further Info Required',
          bg: 'bg-[#fff3e6]',
          text: 'text-[#F57C00]',
          border: 'border-[#F57C00]/30',
          reportId: rep.report_id
        };
      default:
        return {
          status: 'Draft',
          label: 'Draft Report Saved',
          bg: 'bg-[#fef9c3]',
          text: 'text-[#854d0e]',
          border: 'border-[#854d0e]/30',
          reportId: rep.report_id
        };
    }
  };

  const handleOpenReportModal = (alert) => {
    setSelectedModalAlert(alert);
    const rep = reportStatuses[String(alert.alert_id)];
    setSelectedModalReportId(rep ? rep.report_id : null);
    setIsReportModalOpen(true);
  };

  if (loading) {
    return (
      <div className="p-8 max-w-6xl mx-auto flex flex-col items-center justify-center min-h-[50vh] gap-3 text-[#727780]">
        <div className="w-8 h-8 border-4 border-[#0f4c81] border-t-transparent rounded-full animate-spin"></div>
        <p className="text-body-sm font-medium">Loading historical V2 alerts...</p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1.5 rounded-lg bg-[#00355f]/10 text-[#00355f]">
              <AlertTriangle size={20} />
            </span>
            <h1 className="font-headline-lg text-headline-lg text-[#191c1e]">Telemetry Anomaly Alerts</h1>
          </div>
          <p className="text-body-sm text-[#727780]">
            Statistical anomaly episodes detected under the calibrated 1.0 alert / factory-month operating budget (τ = 0.97875).
          </p>
        </div>

        {/* Action Toolbar */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleExportCSV}
            disabled={filteredV2Alerts.length === 0}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-[#E5E7EB] rounded-lg text-xs font-bold text-[#00355f] hover:bg-[#f8f9fb] transition-colors shadow-xs disabled:opacity-50"
          >
            <Download size={14} />
            Export Alert Report (CSV)
          </button>
        </div>
      </div>

      {/* Evaluation Notice Banner */}
      <div className="p-4 bg-[#f8f9fb] border border-[#E5E7EB] rounded-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs">
        <div className="flex items-center gap-3">
          <span className="px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-[#00355f]/10 text-[#00355f] border border-[#00355f]/20">
            Historical Development Evaluation
          </span>
          <span className="text-xs text-[#42474f]">
            Evaluated on 33 development factories. Real-time live inference is pending production pipeline deployment.
          </span>
        </div>
        <div className="text-xs font-semibold text-[#727780]">
          Total Detections: <strong className="text-[#191c1e]">{v2Data.total || 0}</strong> episodes
        </div>
      </div>

      {/* View Switcher: V2 Historical Alerts vs Legacy Risk Watchlist */}
      <div className="flex border-b border-[#E5E7EB] gap-6 text-body-sm font-bold">
        <button
          onClick={() => setActiveTab('v2')}
          className={`pb-3 border-b-2 transition-all flex items-center gap-2 ${
            activeTab === 'v2'
              ? 'border-[#0f4c81] text-[#0f4c81]'
              : 'border-transparent text-[#727780] hover:text-[#191c1e]'
          }`}
        >
          <span>V2 Evaluated Alert Episodes</span>
          <span className="px-2 py-0.5 rounded-full text-xs bg-[#00355f]/10 text-[#00355f]">
            {v2Data.total || 0}
          </span>
        </button>
        <button
          onClick={() => setActiveTab('legacy')}
          className={`pb-3 border-b-2 transition-all flex items-center gap-2 ${
            activeTab === 'legacy'
              ? 'border-[#0f4c81] text-[#0f4c81]'
              : 'border-transparent text-[#727780] hover:text-[#191c1e]'
          }`}
        >
          <span>Legacy Composite Risk Watchlist</span>
          <span className="px-2 py-0.5 rounded-full text-xs bg-[#f2f4f6] text-[#727780]">
            {legacyFactories.length}
          </span>
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="card p-6 flex items-center gap-3 border-[#D32F2F]/30 bg-[#fdecec]/20">
          <ShieldAlert size={20} className="text-[#D32F2F]" />
          <p className="text-body-sm text-[#42474f]">
            Could not reach the backend. Please confirm the server is running on the configured port.
          </p>
        </div>
      )}

      {/* Tab 1: V2 Evaluated Alert Episodes */}
      {activeTab === 'v2' && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-wrap items-center gap-3 p-3 bg-white border border-[#E5E7EB] rounded-xl text-xs">
            <div className="flex items-center gap-1.5 font-bold text-[#727780]">
              <Filter size={14} />
              <span>Filters:</span>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[#727780]">Pattern:</span>
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="bg-[#f8f9fb] border border-[#E5E7EB] rounded px-2.5 py-1 font-bold text-[#00355f] focus:outline-none"
              >
                <option value="ALL">All Patterns</option>
                <option value="T1">T1 — Sensor Flatline</option>
                <option value="T2">T2 — Window Replay</option>
                <option value="T3">T3 — Limit Hugging</option>
                <option value="T7">T7 — Baseline Drift</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[#727780]">Severity:</span>
              <select
                value={selectedSeverity}
                onChange={(e) => setSelectedSeverity(e.target.value)}
                className="bg-[#f8f9fb] border border-[#E5E7EB] rounded px-2.5 py-1 font-bold text-[#00355f] focus:outline-none"
              >
                <option value="ALL">All Severities</option>
                <option value="obvious">High Deviation</option>
                <option value="moderate">Moderate Deviation</option>
                <option value="subtle">Subtle Deviation</option>
              </select>
            </div>

            <div className="ml-auto text-[#727780]">
              Showing <strong>{filteredV2Alerts.length}</strong> of {v2Data.total || 0} episodes
            </div>
          </div>

          {/* Empty state */}
          {filteredV2Alerts.length === 0 && (
            <div className="card p-8 text-center text-body-sm text-[#727780]">
              No alert episodes match the selected filter criteria.
            </div>
          )}

          {/* Alerts List */}
          <div className="space-y-3">
            {filteredV2Alerts.map((alert) => {
              const isExpanded = expandedAlertId === alert.alert_id;
              const sevBadge = getSeverityBadge(alert.severity);
              const repBadge = getReportBadge(alert.alert_id);

              return (
                <div
                  key={alert.alert_id}
                  className={`bg-white border rounded-xl overflow-hidden transition-all shadow-xs ${
                    isExpanded ? 'border-[#0f4c81] shadow-sm' : 'border-[#E5E7EB] hover:border-[#0f4c81]/40'
                  }`}
                >
                  {/* Card Header */}
                  <div
                    onClick={() => toggleExpand(alert.alert_id)}
                    className="p-4 flex flex-wrap items-center justify-between gap-4 cursor-pointer hover:bg-[#fcfdfd]"
                  >
                    <div className="flex items-center gap-4 min-w-0">
                      <div className="w-10 h-10 rounded-xl bg-[#00355f]/5 flex items-center justify-center shrink-0 text-[#00355f] font-mono text-xs font-bold border border-[#00355f]/10">
                        {alert.tamper_type}
                      </div>

                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-body-md text-[#191c1e] truncate">
                            {alert.factory_name}
                          </span>
                          <span className="font-mono text-xs bg-[#f2f4f6] text-[#42474f] px-2 py-0.5 rounded font-semibold">
                            {alert.parameter}
                          </span>
                        </div>
                        <div className="text-xs text-[#727780] flex items-center gap-2 mt-0.5">
                          <span>{alert.anomaly_category}</span>
                          <span>•</span>
                          <span>{alert.region || alert.district}</span>
                          <span>•</span>
                          <span>Duration: {alert.duration_hours}h</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2.5 shrink-0">
                      {repBadge.status !== 'none' && (
                        <span className={`px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider ${repBadge.bg} ${repBadge.text} border ${repBadge.border}`}>
                          {repBadge.label}
                        </span>
                      )}

                      <span className={`px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider ${sevBadge.bg} ${sevBadge.text} border ${sevBadge.border}`}>
                        {sevBadge.label}
                      </span>

                      <span className="text-xs text-[#727780] hidden sm:inline">
                        {alert.start_time ? alert.start_time.slice(0, 10) : ''}
                      </span>

                      {isExpanded ? (
                        <ChevronDown size={18} className="text-[#0f4c81]" />
                      ) : (
                        <ChevronRight size={18} className="text-[#727780]" />
                      )}
                    </div>
                  </div>

                  {/* Expandable Layman-Friendly Details Accordion */}
                  {isExpanded && (
                    <div className="p-6 bg-[#f8f9fb] border-t border-[#E5E7EB] space-y-4 text-xs">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* What was observed */}
                        <div className="bg-white p-4 rounded-lg border border-[#E5E7EB] space-y-1">
                          <div className="font-bold text-[#00355f] flex items-center gap-1.5 uppercase text-[10px] tracking-wider">
                            <Info size={13} /> 1. What was observed
                          </div>
                          <p className="text-[#42474f] leading-relaxed">
                            {alert.evidence?.observed || 'Telemetry readings exhibited an anomalous pattern during this period.'}
                          </p>
                          <div className="text-[11px] text-[#727780] pt-1 border-t border-[#f2f4f6] mt-2">
                            Window: {alert.start_time} to {alert.end_time} ({alert.duration_rows} readings)
                          </div>
                        </div>

                        {/* Why it was flagged */}
                        <div className="bg-white p-4 rounded-lg border border-[#E5E7EB] space-y-1">
                          <div className="font-bold text-[#00355f] flex items-center gap-1.5 uppercase text-[10px] tracking-wider">
                            <AlertTriangle size={13} /> 2. Why it was flagged
                          </div>
                          <p className="text-[#42474f] leading-relaxed">
                            {alert.evidence?.why_flagged || 'Statistical divergence exceeded normal process variation limits.'}
                          </p>
                          <div className="text-[11px] text-[#727780] pt-1 border-t border-[#f2f4f6] mt-2">
                            Operating Cutoff: Score exceeded τ = 0.97875 (1.0 alert/month budget)
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Possible Explanations */}
                        <div className="bg-white p-4 rounded-lg border border-[#E5E7EB] space-y-1">
                          <div className="font-bold text-[#00355f] uppercase text-[10px] tracking-wider">
                            3. Possible Explanations
                          </div>
                          <p className="text-[#42474f] leading-relaxed">
                            {alert.evidence?.possible_explanations || 'Operational causes may include maintenance, sensor issues, or process shutdown.'}
                          </p>
                        </div>

                        {/* What the operator should check next */}
                        <div className="bg-white p-4 rounded-lg border border-[#E5E7EB] space-y-1">
                          <div className="font-bold text-[#00355f] uppercase text-[10px] tracking-wider flex items-center gap-1.5">
                            <CheckCircle2 size={13} className="text-[#1b6d24]" /> 4. Recommended Next Checks
                          </div>
                          <ul className="list-disc list-inside space-y-1 text-[#42474f]">
                            {(alert.evidence?.recommended_checks || []).map((chk, cIdx) => (
                              <li key={cIdx}>{chk}</li>
                            ))}
                          </ul>
                        </div>
                      </div>

                      {/* Footer Actions */}
                      <div className="pt-2 flex flex-wrap justify-between items-center gap-3 text-[11px] text-[#727780]">
                        <div className="flex items-center gap-2">
                          <span>Event ID: <strong className="font-mono text-[#191c1e]">{alert.alert_id}</strong></span>
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${repBadge.bg} ${repBadge.text} border ${repBadge.border}`}>
                            {repBadge.label}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenReportModal(alert);
                            }}
                            className="px-3 py-1 bg-white border border-[#00355f] text-[#00355f] rounded-lg font-bold text-xs hover:bg-[#e7f0f8] flex items-center gap-1.5 transition-colors shadow-2xs"
                          >
                            <FileText size={13} />
                            <span>{repBadge.status !== 'none' ? 'View / Edit Verification Report' : 'File Verification Report'}</span>
                          </button>
                          <button
                            onClick={() => onNavigate('ai-analysis', alert.factory_id)}
                            className="font-bold text-[#00355f] hover:underline flex items-center gap-1"
                          >
                            View Facility Profile <ChevronRight size={12} />
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 2: Legacy Composite Risk Watchlist */}
      {activeTab === 'legacy' && (
        <div className="space-y-4">
          <div className="p-4 bg-[#fff3e6] border border-[#F57C00]/30 rounded-xl text-xs text-[#7a3e00] flex items-center gap-2">
            <Info size={16} className="shrink-0 text-[#F57C00]" />
            <span>
              <strong>Legacy Prototype Watchlist:</strong> These factories are ranked by the pre-V2 composite score
              (heuristic fingerprints + Isolation Forest + proxy logistic regression).
            </span>
          </div>

          <div className="space-y-3">
            {legacyFactories.map((f) => (
              <div
                key={f.factory_id}
                className="card p-4 flex flex-wrap items-center justify-between gap-3 cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => onNavigate('factory-detail', f.factory_id)}
              >
                <div className="flex items-center gap-4 min-w-0">
                  <div
                    className="w-2 h-10 rounded-full shrink-0"
                    style={{ backgroundColor: f.risk_tier === 'High' ? '#D32F2F' : '#F57C00' }}
                  />
                  <div className="min-w-0">
                    <div className="font-bold text-body-md text-[#191c1e] truncate">{f.factory_name}</div>
                    <div className="text-body-sm text-[#727780]">{f.region || f.district}</div>
                  </div>
                </div>
                <div className="flex items-center gap-4 shrink-0">
                  <span
                    className={`px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wide ${
                      f.risk_tier === 'High'
                        ? 'bg-[#fdecec] text-[#D32F2F]'
                        : 'bg-[#fff3e6] text-[#F57C00]'
                    }`}
                  >
                    {f.risk_tier} risk
                  </span>
                  <span className="text-body-sm font-bold text-[#191c1e] w-16 text-right">
                    {f.tsi_score ? f.tsi_score.toFixed(1) : '-'}
                  </span>
                  <ChevronRight size={16} className="text-[#727780]" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

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

      {/* Inspection Verification Report Modal */}
      <InspectionReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        alertId={selectedModalAlert?.alert_id}
        alertData={selectedModalAlert}
        reportId={selectedModalReportId}
        currentUser={currentUser}
        onReportSaved={() => {
          fetchAlertsData();
        }}
      />
    </div>
  );
}
