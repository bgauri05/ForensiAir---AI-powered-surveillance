import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Shield, Settings, Check, AlertCircle } from 'lucide-react';
import { AddFactoryModal } from './AddFactoryModal';
import { ModelVersionsTab } from './ModelVersionsTab';
import { ThresholdSettingsTab } from './ThresholdSettingsTab';
import { apiFetch } from '../config';

export function AdminPortalPage({ onNavigate }) {
  const [activeTab, setActiveTab] = useState('factories');
  const [factories, setFactories] = useState([]);
  const [users, setUsers] = useState([]);
  const [consentLimits, setConsentLimits] = useState([]);
  const [loading, setLoading] = useState(true);

  const [districtFilter, setDistrictFilter] = useState('');
  const [industryFilter, setIndustryFilter] = useState('');

  const [showAddFactoryModal, setShowAddFactoryModal] = useState(false);
  // Tracks which sections are showing fallback/demo data because their
  // backend endpoint returned an error (factories POST/DELETE aren't
  // implemented in backend/main.py as of this session). Previously this was
  // silent -- the UI looked identical whether data was live or fake.
  // Model Versions and Threshold Settings are deliberately excluded: neither
  // tab's content ever came from /api/admin/models or /api/admin/thresholds
  // (those endpoints don't exist and were never consumed), so a failed fetch
  // to them said nothing true about whether those tabs were live or fake.
  // Consent Limits is real now (GET /api/admin/consent-limits, backed by the
  // consent_limits table) -- still flagged on failure/wrong-shape, same as
  // every other real-but-checkable endpoint here.
  const [demoFlags, setDemoFlags] = useState({});

  useEffect(() => {
    fetchAdminData();
  }, [districtFilter, industryFilter]);

  const fetchAdminData = async () => {
    setLoading(true);
    const flags = {};
    try {
      // BUG FIX: districtFilter/industryFilter were interpolated into the
      // query string unencoded. Harmless while the industry dropdown only
      // offered fake values, but real industries like "Garment & Dyeing" or
      // "Drugs & Pharmaceuticals" contain a literal "&", which truncated the
      // query param and silently returned zero results for the real value.
      const params = new URLSearchParams({ district: districtFilter, industry: industryFilter });
      const fRes = await apiFetch(`/api/admin/factories?${params.toString()}`);
      if (fRes.ok) {
        const fData = await fRes.json();
        setFactories(fData);
      } else {
        setFactories(getFallbackFactories());
        flags.factories = true;
      }

      // GET /api/admin/users is a real, auth-gated endpoint, but still a
      // {"status": "not_implemented"} stub server-side (no user management
      // DB model exists yet) -- a 200 from it is not the same as real data.
      // Checking for an array here (same pattern as Dataset Quality) keeps
      // this section honestly in its demo-fallback state instead of
      // crashing users.map() on the stub object once auth stops 401-ing it.
      const uRes = await apiFetch(`/api/admin/users`);
      if (uRes.ok) {
        const uData = await uRes.json();
        if (Array.isArray(uData)) { setUsers(uData); }
        else { setUsers(getFallbackUsers()); flags.users = true; }
      } else { setUsers(getFallbackUsers()); flags.users = true; }

      // GET /api/admin/consent-limits is real, backed by the consent_limits
      // table -- check for an array same as Users, so a non-2xx or an
      // unexpected shape doesn't render garbage.
      const cRes = await apiFetch(`/api/admin/consent-limits`);
      if (cRes.ok) {
        const cData = await cRes.json();
        if (Array.isArray(cData)) { setConsentLimits(cData); }
        else { setConsentLimits([]); flags.consentLimits = true; }
      } else { setConsentLimits([]); flags.consentLimits = true; }

      setDemoFlags(flags);
    } catch (err) {
      setFactories(getFallbackFactories());
      setUsers(getFallbackUsers());
      setConsentLimits([]);
      setDemoFlags({ factories: true, users: true, consentLimits: true });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteFactory = async (factoryId) => {
    if (!window.confirm(`Are you sure you want to remove factory ${factoryId}?`)) return;
    try {
      const res = await apiFetch(`/api/admin/factories/${factoryId}`, { method: 'DELETE' });
      if (res.ok) {
        fetchAdminData();
      } else {
        alert(`Failed to remove factory ${factoryId}. Server responded with ${res.status}.`);
      }
    } catch (err) {
      console.error('Error deleting factory:', err);
      alert(`Failed to remove factory ${factoryId}. Couldn't reach the backend -- nothing was deleted.`);
    }
  };

  return (
    <div className="p-8 max-w-[1600px] mx-auto space-y-8">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <nav className="flex items-center gap-2 text-[#727780] font-label-caps text-[10px] uppercase tracking-widest mb-2">
            <span>PLATFORM</span>
            <span className="material-symbols-outlined text-xs">chevron_right</span>
            <span className="text-[#00355f] font-bold">ADMINISTRATION PORTAL</span>
          </nav>
          <h2 className="text-headline-lg font-headline-lg text-[#00355f]">Administration Portal</h2>
          <p className="text-body-md text-[#42474f] mt-1">Global management of facility metadata, access levels, and AI model parameters.</p>
        </div>

        <button 
          onClick={() => setShowAddFactoryModal(true)}
          className="bg-[#0f4c81] text-white px-6 py-2.5 rounded-lg font-bold text-body-sm flex items-center gap-2 hover:opacity-90 transition-all shadow-sm"
        >
          <Plus size={18} />
          <span>Add New Factory</span>
        </button>
      </div>

      {/* Tabbed Card Container */}
      <div className="bg-white border border-[#E5E7EB] rounded-xl overflow-hidden shadow-xs">
        <div className="flex flex-wrap border-b border-[#E5E7EB] bg-[#f8f9fb] px-4">
          {[
            { id: 'factories', label: 'Factories' },
            { id: 'users', label: 'Users' },
            { id: 'consent-limits', label: 'Consent Limits' },
            { id: 'models', label: 'Model Versions' },
            { id: 'thresholds', label: 'Threshold Settings' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-6 py-4 font-label-caps text-[13px] tracking-wider transition-colors border-b-2 font-bold ${
                activeTab === tab.id 
                  ? 'border-[#00355f] text-[#00355f] bg-white' 
                  : 'border-transparent text-[#42474f] hover:text-[#00355f]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {(() => {
          const tabToFlag = {
            factories: 'factories', users: 'users', 'consent-limits': 'consentLimits',
          };
          const key = tabToFlag[activeTab];
          if (!key || !demoFlags[key]) return null;
          return (
            <div className="flex items-center gap-2 px-6 py-3 bg-[#fff3e6] border-b border-[#F57C00]/20 text-[#8F6400] text-body-sm font-semibold">
              <AlertCircle size={16} />
              Showing demo data -- this section's backend endpoint isn't available right now, so nothing here reflects your live database.
            </div>
          );
        })()}

        {/* Tab 1: Factories Table */}
        {activeTab === 'factories' && (
          <div>
            <div className="p-4 flex flex-wrap justify-between items-center bg-white border-b border-[#E5E7EB] gap-4">
              <div className="flex gap-4">
                <select 
                  value={districtFilter}
                  onChange={(e) => setDistrictFilter(e.target.value)}
                  className="border border-[#E5E7EB] bg-[#f8f9fb] rounded-lg text-body-sm px-3 py-1.5 focus:outline-none"
                >
                  <option value="">All Districts</option>
                  <option value="Taloja">Taloja</option>
                  <option value="Mahad">Mahad</option>
                </select>

                <select
                  value={industryFilter}
                  onChange={(e) => setIndustryFilter(e.target.value)}
                  className="border border-[#E5E7EB] bg-[#f8f9fb] rounded-lg text-body-sm px-3 py-1.5 focus:outline-none"
                >
                  <option value="">All Industries</option>
                  <option value="Chemical Manufacturing">Chemical Manufacturing</option>
                  <option value="Drugs & Pharmaceuticals">Drugs & Pharmaceuticals</option>
                  <option value="Garment & Dyeing">Garment & Dyeing</option>
                  <option value="Heavy Metallurgy">Heavy Metallurgy</option>
                  <option value="Petrochemical Refinery">Petrochemical Refinery</option>
                  <option value="Pharmaceutical Synthetics">Pharmaceutical Synthetics</option>
                  <option value="Synthetic Rubber">Synthetic Rubber</option>
                </select>
              </div>

              <div className="text-xs font-label-caps text-[#727780]">
                Showing {factories.length} Registered Facilities
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-[#f8f9fb] border-b border-[#E5E7EB]">
                    <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase">Factory ID</th>
                    <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase">Name</th>
                    <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase">District</th>
                    <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase">Industry</th>
                    <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="text-table-data">
                  {factories.map((f) => (
                    <tr key={f.factory_id} className="border-b border-[#E5E7EB] table-row-hover">
                      <td className="px-6 py-3.5 font-bold text-[#00355f]">{f.factory_id}</td>
                      <td className="px-6 py-3.5 font-bold text-[#191c1e]">{f.factory_name}</td>
                      <td className="px-6 py-3.5 text-[#42474f]">{f.region || f.district}</td>
                      <td className="px-6 py-3.5 text-[#42474f]">{f.industry}</td>
                      <td className="px-6 py-3.5 text-right">
                        <button 
                          onClick={() => handleDeleteFactory(f.factory_id)}
                          className="text-[#D32F2F] hover:underline font-bold text-xs"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 2: Users */}
        {activeTab === 'users' && (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#f8f9fb] border-b border-[#E5E7EB]">
                  <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase">User ID</th>
                  <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase">Name</th>
                  <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase">Role</th>
                  <th className="px-6 py-3 font-label-caps text-[11px] text-[#42474f] uppercase">Assigned Region</th>
                </tr>
              </thead>
              <tbody className="text-table-data">
                {users.map((u) => (
                  <tr key={u.user_id} className="border-b border-[#E5E7EB] table-row-hover">
                    <td className="px-6 py-3.5 font-bold text-[#00355f]">{u.user_id}</td>
                    <td className="px-6 py-3.5 font-bold text-[#191c1e]">{u.name}</td>
                    <td className="px-6 py-3.5 text-[#42474f] font-semibold">{u.role}</td>
                    <td className="px-6 py-3.5 text-[#42474f]">{u.region}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Tab 3: Consent Limits -- real regulatory min/max per parameter,
            from the consent_limits table (GET /api/admin/consent-limits) */}
        {activeTab === 'consent-limits' && (
          <div className="p-6 space-y-4">
            <h3 className="font-headline-md text-headline-md text-[#00355f]">Regulatory Consent Limits</h3>
            <p className="text-body-sm text-[#727780]">Industry-wide enforcement standards used across all facilities.</p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {consentLimits.map((c) => (
                <div key={c.parameter_id} className="p-4 border border-[#E5E7EB] rounded-lg bg-[#f8f9fb]">
                  <div className="font-bold text-[#191c1e] text-body-md">{c.parameter_name}</div>
                  <div className="text-[10px] text-[#727780] uppercase font-label-caps mt-0.5">{c.category}</div>
                  <div className="text-xs text-[#42474f] mt-2 space-y-1">
                    <div>Range: <span className="font-bold text-[#1b6d24]">{c.min_limit ?? 'Not available'} - {c.max_limit ?? 'Not available'} {c.unit}</span></div>
                    <div>Standard: <span className="font-semibold">{c.regulatory_standard}</span></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 4: Model Versions */}
        {activeTab === 'models' && (
          <ModelVersionsTab />
        )}

        {/* Tab 5: Threshold Settings */}
        {activeTab === 'thresholds' && (
          <ThresholdSettingsTab />
        )}
      </div>

      {showAddFactoryModal && (
        <AddFactoryModal
          isOpen={showAddFactoryModal}
          onClose={() => setShowAddFactoryModal(false)}
          onFactoryAdded={() => {
            setShowAddFactoryModal(false);
            fetchAdminData();
          }}
        />
      )}
    </div>
  );
}

function getFallbackFactories() {
  return [
    { factory_id: "site_1569", factory_name: "RUPA ORGANICS PVT LTD. Taloja", region: "Taloja", industry: "Chemical Manufacturing" },
    { factory_id: "site_1909", factory_name: "Dorf Ketal Chemicals India Pvt Ltd", region: "Taloja", industry: "Petrochemicals" },
    { factory_id: "site_2011", factory_name: "SHREE HARI CHEMICALS EXPORT LIMITED", region: "Mahad", industry: "Chemical Manufacturing" }
  ];
}

function getFallbackUsers() {
  return [
    { user_id: "U-101", name: "Inspector J. Sterling", role: "Field Inspector", region: "Taloja" },
    { user_id: "U-102", name: "Director Chen", role: "Audit Division Lead", region: "National" }
  ];
}

