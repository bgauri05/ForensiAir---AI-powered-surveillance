import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, AlertCircle, Lock } from 'lucide-react';
import { apiFetch } from '../config';

// QC FIX (2026-08, Phase 5): /api/data-quality is admin-gated
// (require_role(["admin"])). Real auth now exists and every request sends
// its Authorization header (see config.js apiFetch), so this endpoint
// actually succeeds for a logged-in admin now -- previously it 401'd on
// every load with zero disclosure.
//
// That alone wasn't enough, though: the real endpoint's shape
// ({dataset_summaries: [...], total_records_processed, pipeline_health_status})
// never matched what this page rendered before (coverage_by_factory,
// parameter_stability, an "AI Readiness Grade" concept that doesn't exist
// server-side). This page is now built around the real dataset_summaries
// array -- per-factory coverage/missing/duplicate/quality_grade/readiness_score
// -- instead of assuming a shape the backend never produced. The
// "Parameter Stability Audit" panel is gone (nothing server-side backs
// that concept); replaced with a real Quality Grade Distribution computed
// from the real per-factory quality_grade field.
export function DatasetQualityPage({ onNavigate }) {
  const [qualityData, setQualityData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isDemoData, setIsDemoData] = useState(false);

  useEffect(() => {
    fetchDataQuality();
  }, []);

  const fetchDataQuality = async () => {
    try {
      const res = await apiFetch('/api/data-quality');
      if (res.ok) {
        const data = await res.json();
        if (data && Array.isArray(data.dataset_summaries)) {
          setQualityData(data);
          setIsDemoData(false);
        } else {
          setQualityData(getFallbackDataQuality());
          setIsDemoData(true);
        }
      } else {
        setQualityData(getFallbackDataQuality());
        setIsDemoData(true);
      }
    } catch (err) {
      setQualityData(getFallbackDataQuality());
      setIsDemoData(true);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !qualityData) {
    return <div className="p-8 font-body-md text-[#42474f]">Loading Dataset Quality Overview...</div>;
  }

  const summaries = qualityData.dataset_summaries || [];
  const avg = (key) => summaries.length
    ? summaries.reduce((sum, s) => sum + (s[key] || 0), 0) / summaries.length
    : 0;

  const avgCoverage = avg('coverage_percentage');
  const avgMissing = avg('missing_percentage');
  const avgDuplicate = avg('duplicate_percentage');
  const avgReadiness = avg('readiness_score');
  const totalRecords = qualityData.total_records_processed ?? summaries.reduce((s, x) => s + (x.total_records || 0), 0);
  const pipelineStatus = qualityData.pipeline_health_status || 'Not available';

  const gradeCounts = summaries.reduce((acc, s) => {
    const g = s.quality_grade || 'N/A';
    acc[g] = (acc[g] || 0) + 1;
    return acc;
  }, {});
  const gradeOrder = ['A', 'B', 'C', 'D', 'F', 'N/A'];
  const gradeDistribution = gradeOrder
    .filter(g => gradeCounts[g])
    .map(g => ({ grade: g, count: gradeCounts[g], pct: (gradeCounts[g] / summaries.length) * 100 }));

  const coverageByFactory = [...summaries]
    .sort((a, b) => (a.coverage_percentage || 0) - (b.coverage_percentage || 0))
    .slice(0, 8)
    .map(s => ({ name: s.factory_name, pct: s.coverage_percentage }));

  return (
    <div className="p-8 max-w-[1600px] mx-auto space-y-8">
      {isDemoData && (
        <div className="flex items-center gap-2 px-6 py-3 bg-[#fff3e6] border border-[#F57C00]/20 text-[#8F6400] text-body-sm font-semibold rounded-lg">
          <AlertCircle size={16} />
          Showing demo data -- this section's backend endpoint isn't available right now, so nothing here reflects your live database.
        </div>
      )}

      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <nav className="flex items-center gap-2 text-[#727780] font-label-caps text-[10px] uppercase tracking-widest mb-2">
            <span className="hover:text-[#00355f] cursor-pointer">Surveillance</span>
            <span className="material-symbols-outlined text-xs">chevron_right</span>
            <span className="text-[#191c1e] font-bold">Dataset Quality Overview</span>
          </nav>
          <h2 className="font-headline-lg text-headline-lg text-[#00355f]">Dataset Quality Overview</h2>
          <p className="font-body-md text-[#42474f] mt-1">Institutional audit of environmental sensor network integrity, {summaries.length} facilities.</p>
        </div>
        <div className="flex gap-3">
          <button disabled title="Date-range selection isn't implemented yet -- this is a static historical dataset, not a live daily feed" className="px-4 py-2 bg-white border border-[#E5E7EB] text-[#727780] font-medium rounded-lg flex items-center gap-2 text-body-sm cursor-not-allowed opacity-60">
            <Lock size={14} />
            Last 30 Days
          </button>
          <button disabled title="Report export isn't implemented yet" className="px-4 py-2 bg-[#00355f] text-white font-medium rounded-lg flex items-center gap-2 text-body-sm shadow-sm cursor-not-allowed opacity-60">
            <Lock size={14} />
            Export Audit Report
          </button>
        </div>
      </div>

      {/* 5 KPI Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6">
        <div className="bg-white border border-[#E5E7EB] p-5 rounded-xl shadow-xs">
          <div className="flex justify-between items-start mb-2">
            <span className="font-label-caps text-label-caps text-[#42474f]">AVG COVERAGE</span>
            <span className={`px-2 py-0.5 text-[10px] font-bold rounded border ${avgCoverage >= 95 ? 'bg-[#1b6d24]/10 text-[#1b6d24] border-[#1b6d24]/20' : 'bg-[#F57C00]/10 text-[#F57C00] border-[#F57C00]/20'}`}>
              {avgCoverage >= 95 ? 'HEALTHY' : 'REVIEW'}
            </span>
          </div>
          <div className="font-display-kpi text-display-kpi text-[#00355f]">{avgCoverage.toFixed(1)}%</div>
          <div className="text-[11px] text-[#727780] mt-1 flex items-center gap-1">
            <TrendingUp size={14} /> across {summaries.length} facilities
          </div>
        </div>

        <div className="bg-white border border-[#E5E7EB] p-5 rounded-xl shadow-xs">
          <div className="flex justify-between items-start mb-2">
            <span className="font-label-caps text-label-caps text-[#42474f]">AVG DUPLICATES</span>
            <span className="px-2 py-0.5 bg-[#1b6d24]/10 text-[#1b6d24] text-[10px] font-bold rounded border border-[#1b6d24]/20">LOW</span>
          </div>
          <div className="font-display-kpi text-display-kpi text-[#00355f]">{avgDuplicate.toFixed(2)}%</div>
          <div className="text-[11px] text-[#727780] mt-1 flex items-center gap-1">
            <TrendingDown size={14} /> mean duplicate rate
          </div>
        </div>

        <div className="bg-white border border-[#E5E7EB] p-5 rounded-xl shadow-xs">
          <div className="flex justify-between items-start mb-2">
            <span className="font-label-caps text-label-caps text-[#42474f]">AVG MISSING DATA</span>
            <span className={`px-2 py-0.5 text-[10px] font-bold rounded border ${avgMissing < 5 ? 'bg-[#1b6d24]/10 text-[#1b6d24] border-[#1b6d24]/20' : 'bg-[#F57C00]/10 text-[#F57C00] border-[#F57C00]/20'}`}>
              {avgMissing < 5 ? 'IN TOLERANCE' : 'ELEVATED'}
            </span>
          </div>
          <div className="font-display-kpi text-display-kpi text-[#00355f]">{avgMissing.toFixed(1)}%</div>
          <div className="text-[11px] text-[#42474f] mt-1 flex items-center gap-1">
            Expected &lt; 5.0% threshold
          </div>
        </div>

        <div className="bg-white border border-[#E5E7EB] p-5 rounded-xl shadow-xs">
          <div className="flex justify-between items-start mb-2">
            <span className="font-label-caps text-label-caps text-[#42474f]">TOTAL RECORDS</span>
            <span className="px-2 py-0.5 bg-[#1b6d24]/10 text-[#1b6d24] text-[10px] font-bold rounded border border-[#1b6d24]/20">{pipelineStatus}</span>
          </div>
          <div className="font-display-kpi text-display-kpi text-[#00355f]">{totalRecords.toLocaleString()}</div>
          <div className="text-[11px] text-[#1b6d24] mt-1 flex items-center gap-1 font-semibold">
            across all facilities
          </div>
        </div>

        <div className="bg-white border border-[#E5E7EB] p-5 rounded-xl shadow-xs border-l-4 border-l-[#1b6d24]">
          <div className="flex justify-between items-start mb-2">
            <span className="font-label-caps text-label-caps text-[#1b6d24]">AVG READINESS SCORE</span>
          </div>
          <div className="font-display-kpi text-display-kpi text-[#1b6d24]">{avgReadiness.toFixed(1)}</div>
          <div className="text-[11px] text-[#1b6d24] mt-1 font-bold">
            mean of real per-factory readiness_score
          </div>
        </div>
      </div>

      {/* Grid Section: Coverage by Factory + Quality Grade Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 bg-white border border-[#E5E7EB] p-6 rounded-xl shadow-xs">
          <h3 className="font-headline-md text-headline-md text-[#00355f] mb-1">Lowest Coverage Facilities</h3>
          <p className="text-body-sm text-[#727780] mb-4">Bottom {coverageByFactory.length} of {summaries.length} facilities by real coverage_percentage.</p>
          <div className="space-y-4">
            {coverageByFactory.map((item, idx) => (
              <div key={idx}>
                <div className="flex justify-between text-body-sm font-semibold mb-1">
                  <span className="text-[#191c1e]">{item.name}</span>
                  <span className="text-[#00355f] font-bold">{item.pct?.toFixed(1)}%</span>
                </div>
                <div className="w-full h-2 bg-[#edeef0] rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${item.pct > 95 ? 'bg-[#1b6d24]' : item.pct > 90 ? 'bg-[#F57C00]' : 'bg-[#D32F2F]'}`}
                    style={{ width: `${item.pct}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="lg:col-span-5 bg-white border border-[#E5E7EB] p-6 rounded-xl shadow-xs flex flex-col justify-between">
          <h3 className="font-headline-md text-headline-md text-[#00355f] mb-4">Quality Grade Distribution</h3>
          <div className="space-y-3.5 flex-1">
            {gradeDistribution.map((g, idx) => (
              <div key={idx} className="p-3 border border-[#E5E7EB] rounded-lg bg-[#f8f9fb] flex items-center justify-between">
                <div>
                  <div className="text-body-sm font-bold text-[#191c1e]">Grade {g.grade}</div>
                  <div className="text-xs text-[#42474f]">{g.count} of {summaries.length} facilities</div>
                </div>
                <span className={`px-2.5 py-1 text-xs font-bold rounded ${
                  g.grade === 'A' || g.grade === 'B' ? 'bg-[#1b6d24]/10 text-[#1b6d24]' : g.grade === 'C' ? 'bg-[#F57C00]/10 text-[#F57C00]' : 'bg-[#D32F2F]/10 text-[#D32F2F]'
                }`}>
                  {g.pct.toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function getFallbackDataQuality() {
  return {
    dataset_summaries: [
      { factory_id: 'demo_1', factory_name: 'Galaxy Surfactants Limited', coverage_percentage: 99.2, missing_percentage: 0.8, duplicate_percentage: 0.1, quality_grade: 'A', readiness_score: 92, total_records: 250000 },
      { factory_id: 'demo_2', factory_name: 'Anmol Chemicals Pvt Ltd', coverage_percentage: 97.8, missing_percentage: 2.2, duplicate_percentage: 0.15, quality_grade: 'B', readiness_score: 85, total_records: 180000 },
      { factory_id: 'demo_3', factory_name: 'Super Petroleum Products Pvt Ltd', coverage_percentage: 94.5, missing_percentage: 5.5, duplicate_percentage: 0.2, quality_grade: 'C', readiness_score: 74, total_records: 160000 },
      { factory_id: 'demo_4', factory_name: 'Cyklo Pharma Chem Pvt Ltd', coverage_percentage: 91.2, missing_percentage: 8.8, duplicate_percentage: 0.3, quality_grade: 'D', readiness_score: 61, total_records: 140000 },
      { factory_id: 'demo_5', factory_name: 'Privi Speciality Chemicals Ltd', coverage_percentage: 98.6, missing_percentage: 1.4, duplicate_percentage: 0.12, quality_grade: 'A', readiness_score: 90, total_records: 210000 }
    ],
    total_records_processed: 940000,
    pipeline_health_status: 'DEMO'
  };
}
