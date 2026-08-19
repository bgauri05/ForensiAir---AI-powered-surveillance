import React, { useState, useEffect } from 'react';
import { Download, ChevronRight, Filter, Calendar } from 'lucide-react';
import { API_BASE_URL } from '../config';

const REGIONS = ['Taloja', 'Mahad'];
const INDUSTRIES = [
  'Chemical Manufacturing',
  'Drugs & Pharmaceuticals',
  'Garment & Dyeing',
  'Heavy Metallurgy',
  'Petrochemical Refinery',
  'Pharmaceutical Synthetics',
  'Synthetic Rubber'
];

export function ExecutiveDashboardPage({ onNavigate }) {
  const [summary, setSummary] = useState(null);
  const [factories, setFactories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);

  const [districtFilter, setDistrictFilter] = useState('All Districts');
  const [industryFilter, setIndustryFilter] = useState('All Industries');
  const [riskFilter, setRiskFilter] = useState('Risk: All Levels');

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      const [sumRes, facRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/dashboard/summary`),
        fetch(`${API_BASE_URL}/api/factories`)
      ]);

      if (sumRes.ok && facRes.ok) {
        setSummary(await sumRes.json());
        setFactories(await facRes.json());
        setLoadError(false);
      } else {
        setLoadError(true);
      }
    } catch (err) {
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  };

  const clearFilters = () => {
    setDistrictFilter('All Districts');
    setIndustryFilter('All Industries');
    setRiskFilter('Risk: All Levels');
  };

  if (loading) {
    return <div className="p-8 font-body-md text-[#42474f]">Loading Executive Dashboard...</div>;
  }

  if (loadError || !summary) {
    return (
      <div className="p-8 font-body-md text-[#42474f]">
        Unable to load dashboard data. Confirm the backend is running at {API_BASE_URL}.
      </div>
    );
  }

  const filteredFactories = factories.filter(f => {
    if (districtFilter !== 'All Districts' && (f.region || '') !== districtFilter) return false;
    if (industryFilter !== 'All Industries' && (f.industry || '') !== industryFilter) return false;
    if (riskFilter !== 'Risk: All Levels' && (f.risk_tier || '') !== riskFilter) return false;
    return true;
  });

  const riskCounts = { Low: 0, Medium: 0, High: 0 };
  filteredFactories.forEach(f => {
    const tier = f.risk_tier || 'Low';
    if (riskCounts[tier] !== undefined) riskCounts[tier] += 1;
  });

  const riskDistribution = [
    { label: 'Low Risk Compliance', tier: 'Low', count: riskCounts.Low, color: '#1b6d24' },
    { label: 'Moderate Risk', tier: 'Medium', count: riskCounts.Medium, color: '#F57C00' },
    { label: 'Critical High Risk', tier: 'High', count: riskCounts.High, color: '#D32F2F' }
  ];

  const totalFiltered = filteredFactories.length;
  let cumulativeOffset = 0;
  const donutSegments = riskDistribution.map(r => {
    const pct = totalFiltered > 0 ? (r.count / totalFiltered) * 100 : 0;
    const segment = { ...r, pct, dashOffset: -cumulativeOffset };
    cumulativeOffset += pct;
    return segment;
  });

  const recentAlerts = [...filteredFactories]
    .sort((a, b) => (b.tsi_score || 0) - (a.tsi_score || 0))
    .slice(0, 5)
    .map(f => ({
      factory_id: f.factory_id,
      factory_name: f.factory_name,
      district: f.region || 'Not available',
      risk_level: (f.risk_tier || 'Low').toUpperCase(),
      status: f.risk_tier === 'High' ? 'Under AI Review' : 'Monitored'
    }));

  const priorityRiskFactors = filteredFactories
    .filter(f => f.risk_tier === 'High')
    .sort((a, b) => (b.tsi_score || 0) - (a.tsi_score || 0))
    .slice(0, 3)
    .map(f => ({
      name: f.factory_name,
      avg_risk: f.tsi_score !== undefined ? `${f.tsi_score.toFixed(1)} (High)` : 'Not available'
    }));

  return (
    <div className="p-8 max-w-[1600px] mx-auto">
      {/* Header & Breadcrumbs */}
      <div className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <nav className="flex items-center gap-2 text-[#727780] font-label-caps text-[10px] uppercase tracking-widest mb-2">
            <span className="hover:text-[#00355f] cursor-pointer">Executive</span>
            <span className="material-symbols-outlined text-xs">chevron_right</span>
            <span className="text-[#191c1e] font-bold">Dashboard Overview</span>
          </nav>
          <h2 className="font-headline-lg text-headline-lg text-[#00355f]">Executive Dashboard</h2>
          <p className="font-body-md text-[#42474f]">Central monitoring of national environmental compliance and risk metrics.</p>
        </div>
        <button className="bg-[#00355f] text-white px-6 py-2.5 rounded-lg flex items-center gap-2 hover:opacity-90 transition-all font-body-sm font-semibold shadow-sm">
          <Download size={16} />
          Export Report
        </button>
      </div>

      {/* KPI Section Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {/* Total Factories */}
        <div className="bg-white border border-[#E5E7EB] p-5 rounded-xl shadow-xs">
          <div className="flex justify-between items-start mb-2">
            <span className="font-label-caps text-label-caps text-[#42474f] uppercase">Total Factories</span>
            <span className="material-symbols-outlined text-[#00355f] text-xl">factory</span>
          </div>
          <div className="font-display-kpi text-display-kpi text-[#191c1e]">{summary.total_factories?.toLocaleString()}</div>
        </div>

        {/* High Risk */}
        <div className="bg-white border border-[#E5E7EB] p-5 rounded-xl shadow-xs border-l-4 border-l-[#D32F2F]">
          <div className="flex justify-between items-start mb-2">
            <span className="font-label-caps text-label-caps text-[#D32F2F] uppercase">High Risk Factories</span>
            <span className="material-symbols-outlined text-[#D32F2F] text-xl">warning</span>
          </div>
          <div className="font-display-kpi text-display-kpi text-[#D32F2F]">{summary.high_risk_count}</div>
        </div>

        {/* Active Alerts */}
        <div className="bg-white border border-[#E5E7EB] p-5 rounded-xl shadow-xs">
          <div className="flex justify-between items-start mb-2">
            <span className="font-label-caps text-label-caps text-[#42474f] uppercase">Active Alerts</span>
            <span className="material-symbols-outlined text-[#F57C00] text-xl">notifications_active</span>
          </div>
          <div className="font-display-kpi text-display-kpi text-[#191c1e]">{(summary.high_risk_count || 0) + (summary.medium_risk_count || 0)}</div>
        </div>
      </div>

      {/* Global Filters Toolbar */}
      <div className="bg-white border border-[#E5E7EB] p-4 rounded-xl flex flex-wrap items-center justify-between gap-4 mb-8">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 border-r border-[#E5E7EB] pr-4">
            <Filter size={16} className="text-[#727780]" />
            <span className="font-label-caps text-[10px] text-[#42474f] uppercase">Global Filters</span>
          </div>

          <select
            value={districtFilter}
            onChange={(e) => setDistrictFilter(e.target.value)}
            className="bg-[#f8f9fb] border border-[#E5E7EB] rounded px-3 py-1.5 text-body-sm font-medium text-[#191c1e] focus:outline-none focus:ring-1 focus:ring-[#00355f]"
          >
            <option>All Districts</option>
            {REGIONS.map(r => <option key={r}>{r}</option>)}
          </select>

          <select
            value={industryFilter}
            onChange={(e) => setIndustryFilter(e.target.value)}
            className="bg-[#f8f9fb] border border-[#E5E7EB] rounded px-3 py-1.5 text-body-sm font-medium text-[#191c1e] focus:outline-none focus:ring-1 focus:ring-[#00355f]"
          >
            <option>All Industries</option>
            {INDUSTRIES.map(i => <option key={i}>{i}</option>)}
          </select>

          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="bg-[#f8f9fb] border border-[#E5E7EB] rounded px-3 py-1.5 text-body-sm font-medium text-[#191c1e] focus:outline-none focus:ring-1 focus:ring-[#00355f]"
          >
            <option>Risk: All Levels</option>
            <option>High</option>
            <option>Medium</option>
            <option>Low</option>
          </select>

          <div className="relative flex items-center">
            <Calendar size={14} className="absolute left-3 text-[#727780]" />
            <input
              className="bg-[#f8f9fb] border border-[#E5E7EB] rounded pl-9 pr-3 py-1.5 text-body-sm font-medium text-[#191c1e]"
              type="text"
              readOnly
              value={`Data as of ${summary.last_updated}`}
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button className="px-4 py-1.5 text-[#00355f] font-bold text-body-sm hover:underline" onClick={clearFilters}>Clear All</button>
        </div>
      </div>

      {/* Main Grid: Risk Distribution + Recent Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-8">
        {/* Risk Distribution Donut Chart */}
        <div className="lg:col-span-4 bg-white border border-[#E5E7EB] p-6 rounded-xl flex flex-col justify-between">
          <h3 className="font-headline-md text-headline-md text-[#00355f] mb-4 flex items-center justify-between">
            Risk Distribution
            <span className="material-symbols-outlined text-[#727780] cursor-pointer">more_vert</span>
          </h3>

          <div className="flex-1 flex flex-col items-center justify-center relative py-6">
            <div className="relative w-48 h-48">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                <circle cx="18" cy="18" fill="transparent" r="16" stroke="#f1f1f1" strokeWidth="3"></circle>
                {donutSegments.filter(s => s.pct > 0).map(s => (
                  <circle
                    key={s.tier}
                    cx="18" cy="18" fill="transparent" r="16"
                    stroke={s.color}
                    strokeDasharray={`${s.pct}, 100`}
                    strokeDashoffset={s.dashOffset}
                    strokeWidth="3"
                  ></circle>
                ))}
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="font-display-kpi text-3xl font-bold text-[#191c1e]">{totalFiltered}</span>
                <span className="text-[10px] font-label-caps text-[#42474f] uppercase">
                  {totalFiltered === factories.length ? 'Total Sites' : 'Sites Shown'}
                </span>
              </div>
            </div>
          </div>

          <div className="space-y-3 pt-4 border-t border-[#E5E7EB]">
            {riskDistribution.map((item) => (
              <div key={item.tier} className="flex items-center justify-between text-body-sm">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }}></span>
                  <span className="text-[#191c1e]">{item.label}</span>
                </div>
                <span className="font-bold text-[#191c1e]">{item.count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Alerts Table */}
        <div className="lg:col-span-8 bg-white border border-[#E5E7EB] p-6 rounded-xl">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-headline-md text-headline-md text-[#00355f]">Recent Alerts</h3>
            <button
              className="text-[#00355f] text-body-sm font-bold flex items-center gap-1 hover:underline"
              onClick={() => onNavigate('alerts')}
            >
              View All Notifications <ChevronRight size={14} />
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[#E5E7EB] text-[#42474f] font-label-caps text-[11px] uppercase tracking-wider">
                  <th className="py-3 px-4">Factory Name</th>
                  <th className="py-3 px-4">District</th>
                  <th className="py-3 px-4">Risk Level</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="text-table-data">
                {recentAlerts.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-6 px-4 text-center text-[#727780]">No factories match the current filters.</td>
                  </tr>
                ) : recentAlerts.map((row, idx) => (
                  <tr
                    key={idx}
                    className="border-b border-[#E5E7EB] table-row-hover transition-colors cursor-pointer"
                    onClick={() => onNavigate('factory-detail', row.factory_id)}
                  >
                    <td className="py-3.5 px-4 font-bold text-[#00355f]">{row.factory_name}</td>
                    <td className="py-3.5 px-4 text-[#42474f]">{row.district}</td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        row.risk_level === 'CRITICAL' ? 'bg-[#D32F2F]/10 text-[#D32F2F]' :
                        (row.risk_level === 'HIGH' ? 'bg-[#F57C00]/10 text-[#F57C00]' : 'bg-[#1b6d24]/10 text-[#1b6d24]')
                      }`}>
                        {row.risk_level}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-[#191c1e]">
                      <div className="flex items-center gap-2">
                        {row.status === 'Under AI Review' && <span className="w-2 h-2 rounded-full bg-[#F57C00] animate-pulse" />}
                        {row.status}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Priority Risk Factors */}
      <div className="bg-white border border-[#E5E7EB] p-6 rounded-xl">
        <h3 className="font-headline-md text-headline-md text-[#00355f] mb-4">Priority Risk Factors</h3>
        <div className="space-y-3">
          {priorityRiskFactors.length === 0 ? (
            <p className="text-body-sm text-[#727780]">No high-risk factories match the current filters.</p>
          ) : priorityRiskFactors.map((item, idx) => (
            <div key={idx} className="p-3 border border-[#E5E7EB] rounded-lg bg-[#f8f9fb] flex items-center justify-between">
              <div>
                <div className="text-body-sm font-bold text-[#191c1e]">{item.name}</div>
                <div className="text-xs text-[#42474f]">Avg Risk Score: {item.avg_risk}</div>
              </div>
              <button className="text-[#00355f] hover:underline text-xs font-bold" onClick={() => onNavigate('explainability')}>
                Inspect
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
