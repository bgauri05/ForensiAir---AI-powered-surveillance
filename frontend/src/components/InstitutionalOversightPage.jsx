import React, { useState, useEffect } from 'react';
import { ShieldAlert, AlertTriangle, ChevronRight, CheckCircle, RefreshCw } from 'lucide-react';
import { API_BASE_URL } from '../config';

export function InstitutionalOversightPage({ onNavigate }) {
  const [oversightData, setOversightData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOversight();
  }, []);

  const fetchOversight = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/oversight`);
      if (res.ok) {
        const data = await res.json();
        setOversightData(data);
      } else {
        setOversightData(getFallbackOversight());
      }
    } catch (err) {
      setOversightData(getFallbackOversight());
    } finally {
      setLoading(false);
    }
  };

  if (loading || !oversightData) {
    return <div className="p-8 font-body-md text-[#42474f]">Loading Institutional Oversight...</div>;
  }

  const {
    national_compliance_pct = 88.4,
    active_investigations = 5,
    regional_breakdown = [],
    coordinated_missing_pairs = [],
    inspection_dispatch_queue = []
  } = oversightData;

  return (
    <div className="p-8 max-w-[1600px] mx-auto space-y-8">
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
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <div className="bg-white border border-[#E5E7EB] p-6 rounded-xl shadow-xs">
          <div className="text-label-caps text-[#727780] uppercase font-bold mb-2">NATIONAL COMPLIANCE INDEX</div>
          <div className="font-display-kpi text-display-kpi text-[#1b6d24]">{national_compliance_pct}%</div>
          <div className="text-xs text-[#42474f] mt-2">Target benchmark: 90.0%</div>
        </div>

        <div className="bg-white border border-[#E5E7EB] p-6 rounded-xl shadow-xs border-l-4 border-l-[#D32F2F]">
          <div className="text-label-caps text-[#D32F2F] uppercase font-bold mb-2">ACTIVE ENFORCEMENT CASES</div>
          <div className="font-display-kpi text-display-kpi text-[#D32F2F]">{active_investigations}</div>
          <div className="text-xs text-[#D32F2F] mt-2 font-bold">+2 high-risk factories flagged today</div>
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
                  <div className="text-body-sm font-bold text-[#191c1e]">{item.site_a} ↔ {item.site_b}</div>
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
                  <div className="text-body-sm font-bold text-[#00355f]">{item.factory_name}</div>
                  <div className="text-xs text-[#42474f] mt-0.5">Reason: {item.reason}</div>
                </div>
                <span className={`px-2.5 py-1 text-xs font-bold rounded ${
                  item.priority === 'HIGH' ? 'bg-[#D32F2F]/10 text-[#D32F2F]' : 'bg-[#F57C00]/10 text-[#F57C00]'
                }`}>
                  {item.priority} PRIORITY
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function getFallbackOversight() {
  return {
    national_compliance_pct: 88.4,
    active_investigations: 5,
    regional_breakdown: [
      { region: "Taloja", compliance: "82%" },
      { region: "Mahad", compliance: "91%" },
      { region: "Tarapur", compliance: "86%" }
    ],
    coordinated_missing_pairs: [
      { site_a: "site_1569 (Taloja)", site_b: "site_1909 (Taloja)", correlation: "0.84" },
      { site_a: "site_2011 (Mahad)", site_b: "site_2088 (Mahad)", correlation: "0.76" }
    ],
    inspection_dispatch_queue: [
      { factory_name: "RUPA ORGANICS PVT LTD. Taloja", priority: "HIGH", reason: "Persistent BOD Flatline & Sensor Disconnect" },
      { factory_name: "Dorf Ketal Chemicals India Pvt Ltd", priority: "HIGH", reason: "COD Limit Hugging & Flow Divergence" },
      { factory_name: "Super Petroleum Products Pvt Ltd", priority: "MEDIUM", reason: "Thermal Scan Variance" }
    ]
  };
}
