import React, { useState, useEffect } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { apiFetch } from '../config';

// QC FIX (2026-08): getFallbackOversight() used to activate silently on a
// failed/unreachable /api/oversight (e.g. the backend mid-restart -- not a
// 401, so the auth interceptor doesn't catch it either) with no visible
// indication the numbers on screen were frozen, unlike every other page in
// the app that falls back to demo data (Admin Portal, Dataset Quality).
// isDemoData adds the same "Showing demo data" banner here.
export function InstitutionalOversightPage({ onNavigate }) {
  const [oversightData, setOversightData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isDemoData, setIsDemoData] = useState(false);

  useEffect(() => {
    fetchOversight();
  }, []);

  const fetchOversight = async () => {
    try {
      const res = await apiFetch(`/api/oversight`);
      if (res.ok) {
        const data = await res.json();
        setOversightData(data);
        setIsDemoData(false);
      } else {
        setOversightData(getFallbackOversight());
        setIsDemoData(true);
      }
    } catch (err) {
      setOversightData(getFallbackOversight());
      setIsDemoData(true);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !oversightData) {
    return <div className="p-8 font-body-md text-[#42474f]">Loading Institutional Oversight...</div>;
  }

  const {
    regional_breakdown = {},
    coordinated_missing_pairs = [],
    inspection_dispatch_queue = []
  } = oversightData;

  // BRIDGE FIX (2026-08): the real /api/oversight response has no
  // national_compliance_pct or active_investigations fields -- this
  // component previously fell back to hardcoded defaults (88.4%, 5) for
  // both, silently blended next to real fields (regional_breakdown,
  // coordinated_missing_pairs, inspection_dispatch_queue) with zero visual
  // distinction. No "compliance index" concept exists anywhere in the risk
  // model, so there's no honest formula to compute one -- removed rather
  // than invented. active_investigations *does* have a real, already-
  // present equivalent (count of high-risk factories, matching the
  // Dashboard's "High Risk Factories" KPI), computed here from the real
  // regional_breakdown the endpoint already returns -- zero backend change.
  const activeInvestigations = Object.values(regional_breakdown)
    .reduce((sum, region) => sum + (region.high_risk_count || 0), 0);

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
            <span className="text-[#191c1e] font-bold">Institutional Oversight</span>
          </nav>
          <h2 className="text-headline-lg font-headline-lg text-[#00355f]">Institutional Oversight</h2>
          <p className="text-body-md text-[#42474f] mt-1">Cross-regional industrial compliance, multi-site anomaly detection & enforcement queue.</p>
        </div>

        <button 
          onClick={fetchOversight}
          className="px-4 py-2 bg-white border border-[#E5E7EB] text-[#00355f] font-bold text-body-sm rounded-lg flex items-center gap-2 hover:bg-[#f8f9fb] shadow-xs"
        >
          <RefreshCw size={16} /> Sync Oversight Matrix
        </button>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        <div className="bg-white border border-[#E5E7EB] p-6 rounded-xl shadow-xs border-l-4 border-l-[#D32F2F]">
          <div className="text-label-caps text-[#D32F2F] uppercase font-bold mb-2">ACTIVE ENFORCEMENT CASES</div>
          <div className="font-display-kpi text-display-kpi text-[#D32F2F]">{activeInvestigations}</div>
          <div className="text-xs text-[#42474f] mt-2">Factories currently at High risk tier, nationwide</div>
        </div>

        <div className="bg-white border border-[#E5E7EB] p-6 rounded-xl shadow-xs">
          <div className="text-label-caps text-[#727780] uppercase font-bold mb-2">COORDINATED ANOMALY CLUSTERS</div>
          <div className="font-display-kpi text-display-kpi text-[#F57C00]">{coordinated_missing_pairs.length} Pairs</div>
          <div className="text-xs text-[#42474f] mt-2">Correlated sensor outages (r &gt; 0.6)</div>
        </div>
      </div>

      {/* Grid: Coordinated Missing Pairs + Dispatch Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Coordinated Outages Table */}
        <div className="lg:col-span-6 bg-white border border-[#E5E7EB] p-6 rounded-xl shadow-xs">
          <h3 className="font-headline-md text-headline-md text-[#00355f] mb-4">Coordinated Missing Data Clusters</h3>
          <p className="text-xs text-[#42474f] mb-4">Sites exhibiting synchronized telemetry gaps indicating potential collusion.</p>
          <div className="space-y-3">
            {coordinated_missing_pairs.map((item, idx) => (
              <div key={idx} className="p-4 bg-[#f8f9fb] rounded-lg border border-[#E5E7EB] flex items-center justify-between">
                <div>
                  <div className="text-body-sm font-bold text-[#191c1e]">{item.pair}</div>
                  <div className="text-xs text-[#42474f] mt-0.5">Correlation r = {item.correlation}</div>
                </div>
                <span className="px-2.5 py-1 text-xs font-bold text-[#D32F2F] bg-[#D32F2F]/10 rounded uppercase">
                  Flagged Pair
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Priority Dispatch Queue */}
        <div className="lg:col-span-6 bg-white border border-[#E5E7EB] p-6 rounded-xl shadow-xs">
          <h3 className="font-headline-md text-headline-md text-[#00355f] mb-4">Inspection Dispatch Queue</h3>
          <p className="text-xs text-[#42474f] mb-4">Automated priority queue for physical field inspector dispatch.</p>
          <div className="space-y-3">
            {inspection_dispatch_queue.map((item, idx) => (
              <div key={idx} className="p-4 bg-[#f8f9fb] rounded-lg border border-[#E5E7EB] flex items-center justify-between">
                <div>
                  <div className="text-body-sm font-bold text-[#00355f]">{item.name}</div>
                  <div className="text-xs text-[#42474f] mt-0.5">TSI Score: {item.tsi_score !== undefined ? item.tsi_score.toFixed(1) : 'Not available'} · Rank #{item.rank}</div>
                </div>
                <span className={`px-2.5 py-1 text-xs font-bold rounded ${
                  item.risk_tier === 'High' ? 'bg-[#D32F2F]/10 text-[#D32F2F]' : 'bg-[#F57C00]/10 text-[#F57C00]'
                }`}>
                  {item.priority}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// BRIDGE FIX (2026-08): reshaped to match the real /api/oversight response
// (regional_breakdown is a {region_name: {total_sites, high_risk_count,
// avg_tsi_score}} object, not an array; coordinated_missing_pairs uses a
// single pre-formatted `pair` string; inspection_dispatch_queue uses
// name/tsi_score/rank/risk_tier/priority) so this fallback -- only reached
// if /api/oversight itself is unreachable -- renders with the same field
// names the real data uses instead of showing "undefined".
function getFallbackOversight() {
  return {
    regional_breakdown: {
      Taloja_MIDC: { total_sites: 21, high_risk_count: 14, avg_tsi_score: 27.36 },
      Mahad_MIDC: { total_sites: 12, high_risk_count: 10, avg_tsi_score: 33.77 }
    },
    coordinated_missing_pairs: [
      { pair: "site_1569 <-> site_1909", correlation: 0.711, region: "Taloja MIDC (Shared Grid)" },
      { pair: "site_1247 <-> site_1264", correlation: 0.709, region: "Taloja MIDC (Shared Grid)" }
    ],
    inspection_dispatch_queue: [
      { factory_id: "site_1799", name: "Privi Speciality Chemicals Ltd (Unit 10)", rank: 1, tsi_score: 54.8, risk_tier: "High", priority: "CRITICAL - IMMEDIATE UNANNOUNCED AUDIT" }
    ]
  };
}
