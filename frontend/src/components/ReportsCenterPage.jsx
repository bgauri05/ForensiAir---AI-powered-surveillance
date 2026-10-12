import React, { useState, useEffect } from 'react';
import {
  Download,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ShieldCheck,
  Plus,
  Filter,
  Search,
  ChevronRight,
  User,
  Calendar,
  Building2,
  RefreshCw
} from 'lucide-react';
import { apiFetch } from '../config';
import { InspectionReportModal } from './InspectionReportModal';

const REPORT_YEAR = new Date().getFullYear();

export function ReportsCenterPage({ onNavigate, currentUser }) {
  const [mainView, setMainView] = useState('verification_reports'); // 'verification_reports' or 'compliance_dossiers'
  
  // Verification Reports state
  const [reports, setReports] = useState([]);
  const [reportsLoading, setReportsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedReportId, setSelectedReportId] = useState(null);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);

  // Existing Dossiers state
  const [factories, setFactories] = useState([]);
  const [selectedFactory, setSelectedFactory] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [filterTag, setFilterTag] = useState('All');
  const [factoriesLoading, setFactoriesLoading] = useState(true);

  useEffect(() => {
    fetchVerificationReports();
    fetchFactories();
  }, []);

  const fetchVerificationReports = async () => {
    setReportsLoading(true);
    try {
      const res = await apiFetch('/api/reports?limit=100');
      if (res.ok) {
        const data = await res.json();
        setReports(data.reports || []);
      }
    } catch (err) {
      console.error('Failed to load verification reports:', err);
    } finally {
      setReportsLoading(false);
    }
  };

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
      setFactoriesLoading(false);
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

  const handleOpenReport = (rptId) => {
    setSelectedReportId(rptId);
    setIsReportModalOpen(true);
  };

  const handleNewReport = () => {
    setSelectedReportId(null);
    setIsReportModalOpen(true);
  };

  // Filter verification reports
  const filteredReports = reports.filter(r => {
    if (statusFilter !== 'ALL' && r.status !== statusFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchName = (r.factory_name || '').toLowerCase().includes(q);
      const matchId = (r.report_id || '').toLowerCase().includes(q);
      const matchAlert = (r.alert_id || '').toLowerCase().includes(q);
      const matchFindings = (r.findings || '').toLowerCase().includes(q);
      if (!matchName && !matchId && !matchAlert && !matchFindings) return false;
    }
    return true;
  });

  // KPI Metrics
  const totalReportsCount = reports.length;
  const submittedCount = reports.filter(r => r.status === 'Submitted for Review').length;
  const reviewedCount = reports.filter(r => r.status === 'Reviewed').length;
  const draftsCount = reports.filter(r => r.status === 'Draft' || r.status === 'Further Information Required').length;

  // Filter factories for dossier view
  const filteredFactories = factories.filter(f => {
    if (filterTag === 'Critical') return f.risk_tier === 'High';
    if (filterTag === 'Routine') return f.risk_tier === 'Low' || f.risk_tier === 'Medium';
    return true;
  });

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
    <div className="p-8 max-w-[1600px] mx-auto space-y-6">
      {/* Top Header & Section Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-headline-lg font-headline-lg text-[#00355f] flex items-center gap-2">
            <FileText size={28} />
            <span>Reports & Compliance Verification Center</span>
          </h1>
          <p className="text-body-sm text-[#727780] mt-1">
            Database-backed inspector verification dossiers, on-site findings documentation & compliance summaries.
          </p>
        </div>

        {/* Primary View Switcher */}
        <div className="flex items-center gap-2 bg-white border border-[#E5E7EB] p-1.5 rounded-xl shadow-xs shrink-0">
          <button
            onClick={() => setMainView('verification_reports')}
            className={`px-4 py-2 rounded-lg font-bold text-xs transition-colors flex items-center gap-2 ${
              mainView === 'verification_reports'
                ? 'bg-[#00355f] text-white shadow-xs'
                : 'text-[#727780] hover:text-[#191c1e] hover:bg-[#f8f9fb]'
            }`}
          >
            <ShieldCheck size={16} />
            <span>Inspector Verification Reports</span>
            <span className={`px-2 py-0.5 rounded-full text-[10px] ${
              mainView === 'verification_reports' ? 'bg-white/20 text-white' : 'bg-[#f2f4f6] text-[#727780]'
            }`}>
              {totalReportsCount}
            </span>
          </button>

          <button
            onClick={() => setMainView('compliance_dossiers')}
            className={`px-4 py-2 rounded-lg font-bold text-xs transition-colors flex items-center gap-2 ${
              mainView === 'compliance_dossiers'
                ? 'bg-[#00355f] text-white shadow-xs'
                : 'text-[#727780] hover:text-[#191c1e] hover:bg-[#f8f9fb]'
            }`}
          >
            <Download size={16} />
            <span>Facility Compliance Dossiers</span>
          </button>
        </div>
      </div>

      {/* VIEW 1: INSPECTOR VERIFICATION REPORTS */}
      {mainView === 'verification_reports' && (
        <div className="space-y-6">
          {/* KPI Dashboard Summary */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white border border-[#E5E7EB] p-5 rounded-xl shadow-xs space-y-1">
              <div className="text-[10px] font-bold text-[#727780] uppercase tracking-wider flex items-center justify-between">
                <span>Total Verification Reports</span>
                <FileText size={16} className="text-[#00355f]" />
              </div>
              <div className="text-3xl font-bold font-mono text-[#00355f]">{totalReportsCount}</div>
              <p className="text-[11px] text-[#727780]">Registered on-site inspection dossiers</p>
            </div>

            <div className="bg-white border border-[#E5E7EB] p-5 rounded-xl shadow-xs space-y-1">
              <div className="text-[10px] font-bold text-[#727780] uppercase tracking-wider flex items-center justify-between">
                <span>Pending Admin Review</span>
                <Clock size={16} className="text-[#00355f]" />
              </div>
              <div className="text-3xl font-bold font-mono text-[#0f4c81]">{submittedCount}</div>
              <p className="text-[11px] text-[#727780]">Awaiting administrator approval</p>
            </div>

            <div className="bg-white border border-[#E5E7EB] p-5 rounded-xl shadow-xs space-y-1">
              <div className="text-[10px] font-bold text-[#727780] uppercase tracking-wider flex items-center justify-between">
                <span>Reviewed & Verified</span>
                <CheckCircle2 size={16} className="text-[#1b6d24]" />
              </div>
              <div className="text-3xl font-bold font-mono text-[#1b6d24]">{reviewedCount}</div>
              <p className="text-[11px] text-[#727780]">Compliance decision finalized</p>
            </div>

            <div className="bg-white border border-[#E5E7EB] p-5 rounded-xl shadow-xs space-y-1">
              <div className="text-[10px] font-bold text-[#727780] uppercase tracking-wider flex items-center justify-between">
                <span>Drafts / Queries Open</span>
                <AlertTriangle size={16} className="text-[#F57C00]" />
              </div>
              <div className="text-3xl font-bold font-mono text-[#F57C00]">{draftsCount}</div>
              <p className="text-[11px] text-[#727780]">Drafts or further info required</p>
            </div>
          </div>

          {/* Action Toolbar & Filters */}
          <div className="bg-white border border-[#E5E7EB] p-4 rounded-xl shadow-xs flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2 bg-[#f8f9fb] border border-[#E5E7EB] px-3 py-1.5 rounded-lg text-xs">
                <Search size={14} className="text-[#727780]" />
                <input
                  type="text"
                  placeholder="Search facility, report ID, or findings..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-transparent text-xs text-[#191c1e] focus:outline-none w-48 sm:w-64"
                />
              </div>

              <div className="flex items-center gap-2 text-xs">
                <span className="font-bold text-[#727780]">Status:</span>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="bg-[#f8f9fb] border border-[#E5E7EB] rounded px-3 py-1.5 font-bold text-[#00355f] focus:outline-none"
                >
                  <option value="ALL">All Statuses</option>
                  <option value="Submitted for Review">Submitted for Review</option>
                  <option value="Reviewed">Reviewed & Closed</option>
                  <option value="Further Information Required">Further Info Required</option>
                  <option value="Draft">Drafts Only</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={fetchVerificationReports}
                className="p-2 border border-[#E5E7EB] rounded-lg hover:bg-[#f8f9fb] text-[#727780] transition-colors"
                title="Refresh verification reports"
              >
                <RefreshCw size={15} />
              </button>

              <button
                onClick={handleNewReport}
                className="flex items-center gap-2 bg-[#00355f] text-white px-4 py-2 rounded-lg font-bold text-xs hover:bg-[#0f4c81] transition-colors shadow-xs"
              >
                <Plus size={15} />
                <span>File Verification Report</span>
              </button>
            </div>
          </div>

          {/* Verification Reports Table / Grid */}
          {reportsLoading ? (
            <div className="p-12 text-center text-xs text-[#727780] bg-white border border-[#E5E7EB] rounded-xl flex items-center justify-center gap-3">
              <div className="w-6 h-6 border-3 border-[#00355f] border-t-transparent rounded-full animate-spin"></div>
              <span>Loading verification reports from database...</span>
            </div>
          ) : filteredReports.length === 0 ? (
            <div className="p-12 text-center text-xs text-[#727780] bg-white border border-[#E5E7EB] rounded-xl space-y-2">
              <p className="font-bold text-sm text-[#191c1e]">No verification reports found</p>
              <p>No reports match the selected criteria. Click "File Verification Report" to document on-site checks.</p>
            </div>
          ) : (
            <div className="bg-white border border-[#E5E7EB] rounded-xl overflow-hidden shadow-xs">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-[#f8f9fb] border-b border-[#E5E7EB] text-[#727780] font-bold uppercase tracking-wider text-[10px]">
                    <th className="p-3.5">Report ID</th>
                    <th className="p-3.5">Facility & Linked Alert</th>
                    <th className="p-3.5">Inspection Date</th>
                    <th className="p-3.5">Inspector</th>
                    <th className="p-3.5">Outcome</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E5E7EB]">
                  {filteredReports.map((r) => {
                    return (
                      <tr key={r.report_id} className="hover:bg-[#fafbfc] transition-colors">
                        <td className="p-3.5 font-mono font-bold text-[#00355f]">
                          {r.report_id}
                        </td>
                        <td className="p-3.5">
                          <div className="font-bold text-[#191c1e]">{r.factory_name || r.factory_id}</div>
                          <div className="text-[11px] text-[#727780] font-mono">
                            Alert ID: {r.alert_id}
                          </div>
                        </td>
                        <td className="p-3.5 text-[#42474f]">
                          {r.inspection_date}
                        </td>
                        <td className="p-3.5">
                          <div className="font-medium text-[#191c1e]">{r.inspector_name || r.inspector_id}</div>
                          <div className="text-[10px] text-[#727780]">Field Inspector</div>
                        </td>
                        <td className="p-3.5">
                          <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold capitalize ${
                            r.outcome === 'explained' ? 'bg-[#e8f5e9] text-[#1b6d24]' :
                            r.outcome === 'inconclusive' ? 'bg-[#fff3e6] text-[#F57C00]' :
                            r.outcome === 'unexplained' ? 'bg-[#fdecec] text-[#D32F2F]' :
                            'bg-[#e7f0f8] text-[#00355f]'
                          }`}>
                            {r.outcome.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="p-3.5">
                          <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                            r.status === 'Reviewed' ? 'bg-[#e8f5e9] text-[#1b6d24] border border-[#1b6d24]/30' :
                            r.status === 'Submitted for Review' ? 'bg-[#e7f0f8] text-[#00355f] border border-[#00355f]/30' :
                            r.status === 'Further Information Required' ? 'bg-[#fff3e6] text-[#F57C00] border border-[#F57C00]/30' :
                            'bg-[#f2f4f6] text-[#727780] border border-[#E5E7EB]'
                          }`}>
                            {r.status}
                          </span>
                        </td>
                        <td className="p-3.5 text-right">
                          <button
                            onClick={() => handleOpenReport(r.report_id)}
                            className="px-3 py-1 bg-white border border-[#00355f] text-[#00355f] rounded-lg font-bold text-xs hover:bg-[#e7f0f8] transition-colors"
                          >
                            Open & Review
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* VIEW 2: FACILITY COMPLIANCE DOSSIERS (THE PRESERVED VIEW) */}
      {mainView === 'compliance_dossiers' && (
        <div className="flex flex-col md:h-[calc(100vh-180px)] md:flex-row md:overflow-hidden print:h-auto print:block">
          {/* Left Sidebar: Report Archive List (1/3) */}
          <section className="w-full md:w-1/3 border-r border-[#E5E7EB] flex flex-col bg-[#f8f9fb] print:hidden">
            <div className="p-4 border-b border-[#E5E7EB] space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-headline-md text-headline-md text-[#00355f]">Dossiers List</h2>
                <span className="bg-[#00355f]/10 text-[#00355f] text-[10px] font-bold px-2 py-1 rounded">
                  {factories.length} SITES
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
          <section className="w-full md:w-2/3 flex flex-col bg-[#edeef0] p-8 overflow-y-auto print:w-full print:bg-white print:p-0 print:overflow-visible">
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

              {/* Composite Score Breakdown */}
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

              {/* Fingerprint Checks */}
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

              {/* SHAP Explanation Summary */}
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
      )}

      {/* Verification Report Dialog / Modal */}
      <InspectionReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        reportId={selectedReportId}
        currentUser={currentUser}
        onReportSaved={() => {
          fetchVerificationReports();
        }}
      />
    </div>
  );
}
