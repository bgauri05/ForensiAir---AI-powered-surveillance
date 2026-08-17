import React, { useState, useEffect } from 'react';
import { Download, ChevronRight, Filter, Calendar } from 'lucide-react';
import { API_BASE_URL } from '../config';

export function ExecutiveDashboardPage({ onNavigate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

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
        const summary = await sumRes.json();
        const factories = await facRes.json();
        
        setData({
          kpis: {
            total_factories: summary.total_factories || 33,
            monitored_today: Math.round((summary.total_factories || 33) * 0.85),
            high_risk_factories: summary.high_risk_count || 5,
            active_alerts: (summary.high_risk_count || 5) + (summary.medium_risk_count || 8),
            avg_data_quality: 94.8
          },
          risk_distribution: [
            { label: 'Low Risk Compliance', count: summary.low_risk_count || 20, color: '#1b6d24' },
            { label: 'Moderate Risk', count: summary.medium_risk_count || 8, color: '#F57C00' },
            { label: 'Critical High Risk', count: summary.high_risk_count || 5, color: '#D32F2F' }
          ],
          factories: factories,
          recent_alerts: (factories || []).slice(0, 5).map(f => ({
            factory_id: f.factory_id,
            factory_name: f.factory_name,
            district: f.region || 'North Industrial',
            risk_level: (f.risk_tier || 'Low').toUpperCase(),
            time: '2 mins ago',
            status: f.risk_tier === 'High' ? 'Under AI Review' : 'Monitored'
          })),
          activity_timeline: [
            { time: '10:45 AM', title: 'TSI Risk Re-calculation Completed', desc: 'Canonical 10-signal TSI engine recomputed scores for 33 factories.' },
            { time: '09:30 AM', title: 'Coordinated Missing Data Flagged', desc: 'High missing rate correlation (r > 0.6) detected for site_1569 <-> site_1909.' },
            { time: '08:15 AM', title: 'Stage 2 XGBoost Inferences Updated', desc: '9-class multi-class tamper detector processed 1,138,064 records.' }
          ],
          priority_risk_factors: (factories || []).filter(f => f.risk_tier === 'High' || f.risk_tier === 'High Risk').slice(0, 3).map(f => ({
            name: f.factory_name,
            avg_risk: `${f.tamper_probability ? (f.tamper_probability * 100).toFixed(1) : '85.0'} (High)`
          })),
          data_integrity: [
            { sensor: "SO2 Sensors", uptime: "98%" },
            { sensor: "NO2 Scanners", uptime: "94%" },
            { sensor: "Thermal Nodes", uptime: "89%" },
            { sensor: "Satellite Imaging", uptime: "96%" }
          ]
        });
      } else {
        setData(getFallbackDashboard());
      }
    } catch (err) {
      setData(getFallbackDashboard());
    } finally {
      setLoading(false);
    }
  };

  if (loading || !data) {
    return <div className="p-8 font-body-md text-[#42474f]">Loading Executive Dashboard...</div>;
  }

  const { 
    kpis = {}, 
    risk_distribution = [], 
    recent_alerts = [], 
    activity_timeline = [], 
    priority_risk_factors = [], 
    data_integrity = [] 
  } = data || {};

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

      {/* 5 KPI Section Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
        {/* Total Factories */}
        <div className="bg-white border border-[#E5E7EB] p-5 rounded-xl shadow-xs">
          <div className="flex justify-between items-start mb-2">
            <span className="font-label-caps text-label-caps text-[#42474f] uppercase">Total Factories</span>
            <span className="material-symbols-outlined text-[#00355f] text-xl">factory</span>
          </div>
          <div className="font-display-kpi text-display-kpi text-[#191c1e]">{kpis.total_factories?.toLocaleString()}</div>
          <div className="flex items-center gap-1 mt-2">
            <span className="text-[#1b6d24] font-bold text-xs">+1.2%</span>
            <span className="text-[#42474f] text-[11px]">from last month</span>
          </div>
        </div>

        {/* Monitored Today */}
        <div className="bg-white border border-[#E5E7EB] p-5 rounded-xl shadow-xs">
          <div className="flex justify-between items-start mb-2">
            <span className="font-label-caps text-label-caps text-[#42474f] uppercase">Monitored Today</span>
            <span className="material-symbols-outlined text-[#00355f] text-xl">visibility</span>
          </div>
          <div className="font-display-kpi text-display-kpi text-[#191c1e]">{kpis.monitored_today}</div>
          <div className="w-full bg-[#edeef0] mt-3 h-1.5 rounded-full overflow-hidden">
            <div className="bg-[#00355f] h-full rounded-full" style={{ width: '85%' }}></div>
          </div>
          <div className="text-[#42474f] text-[11px] mt-1">85.0% of total capacity</div>
        </div>

        {/* High Risk */}
        <div className="bg-white border border-[#E5E7EB] p-5 rounded-xl shadow-xs border-l-4 border-l-[#D32F2F]">
          <div className="flex justify-between items-start mb-2">
            <span className="font-label-caps text-label-caps text-[#D32F2F] uppercase">High Risk Factories</span>
            <span className="material-symbols-outlined text-[#D32F2F] text-xl">warning</span>
          </div>
          <div className="font-display-kpi text-display-kpi text-[#D32F2F]">{kpis.high_risk_factories}</div>
          <div className="flex items-center gap-1 mt-2">
            <span className="text-[#D32F2F] font-bold text-xs">+2</span>
            <span className="text-[#42474f] text-[11px]">new detections</span>
          </div>
        </div>

        {/* Active Alerts */}
        <div className="bg-white border border-[#E5E7EB] p-5 rounded-xl shadow-xs">
          <div className="flex justify-between items-start mb-2">
            <span className="font-label-caps text-label-caps text-[#42474f] uppercase">Active Alerts</span>
            <span className="material-symbols-outlined text-[#F57C00] text-xl">notifications_active</span>
          </div>
          <div className="font-display-kpi text-display-kpi text-[#191c1e]">{kpis.active_alerts}</div>
          <div className="flex items-center gap-1 mt-2">
            <span className="text-[#42474f] text-[11px]">18 require urgent action</span>
          </div>
        </div>

        {/* Data Quality */}
        <div className="bg-white border border-[#E5E7EB] p-5 rounded-xl shadow-xs">
          <div className="flex justify-between items-start mb-2">
            <span className="font-label-caps text-label-caps text-[#42474f] uppercase">Avg Data Quality</span>
            <span className="material-symbols-outlined text-[#1b6d24] text-xl">verified</span>
          </div>
          <div className="font-display-kpi text-display-kpi text-[#191c1e]">{kpis.avg_data_quality}%</div>
          <div className="flex items-center gap-1 mt-2">
            <span className="text-[#1b6d24] font-bold text-xs">High Confidence</span>
          </div>
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
            <option>North Industrial</option>
            <option>Central Metro</option>
            <option>East Coastal</option>
          </select>

          <select 
            value={industryFilter} 
            onChange={(e) => setIndustryFilter(e.target.value)}
            className="bg-[#f8f9fb] border border-[#E5E7EB] rounded px-3 py-1.5 text-body-sm font-medium text-[#191c1e] focus:outline-none focus:ring-1 focus:ring-[#00355f]"
          >
            <option>All Industries</option>
            <option>Petrochemicals</option>
            <option>Metallurgy</option>
            <option>Textiles & Dyeing</option>
          </select>

          <select 
            value={riskFilter} 
            onChange={(e) => setRiskFilter(e.target.value)}
            className="bg-[#f8f9fb] border border-[#E5E7EB] rounded px-3 py-1.5 text-body-sm font-medium text-[#191c1e] focus:outline-none focus:ring-1 focus:ring-[#00355f]"
          >
            <option>Risk: All Levels</option>
            <option>Critical</option>
            <option>High</option>
            <option>Low</option>
          </select>

          <div className="relative flex items-center">
            <Calendar size={14} className="absolute left-3 text-[#727780]" />
            <input 
              className="bg-[#f8f9fb] border border-[#E5E7EB] rounded pl-9 pr-3 py-1.5 text-body-sm font-medium text-[#191c1e]" 
              type="text" 
              readOnly 
              value="Oct 01, 2024 - Oct 31, 2024"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button className="px-4 py-1.5 text-[#00355f] font-bold text-body-sm hover:underline">Clear All</button>
          <button className="bg-[#00355f]/10 text-[#00355f] px-4 py-1.5 rounded font-bold text-body-sm border border-[#00355f]/20 hover:bg-[#00355f]/20 transition-all">Apply View</button>
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
                <circle cx="18" cy="18" fill="transparent" r="16" stroke="#1b6d24" strokeDasharray="65, 100" strokeDashoffset="0" strokeWidth="3"></circle>
                <circle cx="18" cy="18" fill="transparent" r="16" stroke="#F57C00" strokeDasharray="25, 100" strokeDashoffset="-65" strokeWidth="3"></circle>
                <circle cx="18" cy="18" fill="transparent" r="16" stroke="#D32F2F" strokeDasharray="10, 100" strokeDashoffset="-90" strokeWidth="3"></circle>
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="font-display-kpi text-3xl font-bold text-[#191c1e]">33</span>
                <span className="text-[10px] font-label-caps text-[#42474f] uppercase">Total Sites</span>
              </div>
            </div>
          </div>

          <div className="space-y-3 pt-4 border-t border-[#E5E7EB]">
            {risk_distribution.map((item, idx) => (
              <div key={idx} className="flex items-center justify-between text-body-sm">
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
                  <th className="py-3 px-4">Time</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="text-table-data">
                {recent_alerts.map((row, idx) => (
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
                    <td className="py-3.5 px-4 text-[#42474f]">{row.time}</td>
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

      {/* Row 3 Grid: Activity Timeline, Priority Risk Factors, Data Integrity */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Activity Timeline */}
        <div className="bg-white border border-[#E5E7EB] p-6 rounded-xl">
          <h3 className="font-headline-md text-headline-md text-[#00355f] mb-4">Activity Timeline</h3>
          <div className="space-y-4">
            {activity_timeline.map((act, idx) => (
              <div key={idx} className="border-l-2 border-[#00355f] pl-3">
                <div className="text-[10px] font-label-caps text-[#00355f] tracking-wider">{act.time}</div>
                <div className="text-body-sm font-bold text-[#191c1e] mt-0.5">{act.title}</div>
                <div className="text-xs text-[#42474f] mt-0.5">{act.desc}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Priority Risk Factors */}
        <div className="bg-white border border-[#E5E7EB] p-6 rounded-xl">
          <h3 className="font-headline-md text-headline-md text-[#00355f] mb-4">Priority Risk Factors</h3>
          <div className="space-y-3">
            {priority_risk_factors.map((item, idx) => (
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

        {/* Data Integrity */}
        <div className="bg-white border border-[#E5E7EB] p-6 rounded-xl">
          <h3 className="font-headline-md text-headline-md text-[#00355f] mb-4">Data Integrity</h3>
          <div className="space-y-3.5">
            {data_integrity.map((sen, idx) => (
              <div key={idx}>
                <div className="flex justify-between text-body-sm font-medium mb-1">
                  <span>{sen.sensor}</span>
                  <span className="text-[#1b6d24] font-bold">{sen.uptime}</span>
                </div>
                <div className="w-full h-1.5 bg-[#edeef0] rounded-full overflow-hidden">
                  <div className="h-full bg-[#1b6d24] rounded-full" style={{ width: sen.uptime }}></div>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 p-3 bg-[#e0f2fe] rounded-lg text-xs text-[#0369a1] font-medium leading-relaxed">
            ℹ Sensor calibration recommended for 4 districts to maintain confidence levels.
          </div>
        </div>
      </div>
    </div>
  );
}

function getFallbackDashboard() {
  return {
    kpis: { total_factories: 33, monitored_today: 28, high_risk_factories: 5, active_alerts: 13, avg_data_quality: 94.8 },
    risk_distribution: [
      { label: "Low Risk Compliance", count: 20, color: "#1b6d24" },
      { label: "Moderate Risk", count: 8, color: "#F57C00" },
      { label: "Critical High Risk", count: 5, color: "#D32F2F" }
    ],
    recent_alerts: [
      { factory_name: "RUPA ORGANICS PVT LTD. Taloja", district: "Taloja", risk_level: "CRITICAL", time: "12:45 PM", status: "Under AI Review" },
      { factory_name: "Dorf Ketal Chemicals India Pvt Ltd", district: "Taloja", risk_level: "HIGH", time: "11:20 AM", status: "Investigating" },
      { factory_name: "SHREE HARI CHEMICALS EXPORT LIMITED", district: "Mahad", risk_level: "HIGH", time: "10:05 AM", status: "Resolved" }
    ],
    activity_timeline: [
      { time: "JUST NOW", title: "Thermal scan completed at RUPA ORGANICS PVT LTD. Taloja", desc: "Variance detected within 2% margin." },
      { time: "12 MIN AGO", title: "Compliance Cert Issued", desc: "Dorf Ketal Chemicals India Pvt Ltd passed audit." }
    ],
    priority_risk_factors: [
      { name: "RUPA ORGANICS PVT LTD. Taloja", avg_risk: "88.4 (High)" },
      { name: "Super Petroleum Products Private Limited", avg_risk: "72.1 (Moderate)" }
    ],
    data_integrity: [
      { sensor: "SO2 Sensors", uptime: "98%" },
      { sensor: "NO2 Scanners", uptime: "94%" },
      { sensor: "Thermal Nodes", uptime: "89%" },
      { sensor: "Satellite Imaging", uptime: "96%" }
    ]
  };
}
