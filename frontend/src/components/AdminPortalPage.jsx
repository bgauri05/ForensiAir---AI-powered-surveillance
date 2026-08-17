import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, Shield, Settings, Check, AlertCircle } from 'lucide-react';
import { AddFactoryModal } from './AddFactoryModal';
import { ModelVersionsTab } from './ModelVersionsTab';
import { ThresholdSettingsTab } from './ThresholdSettingsTab';
import { API_BASE_URL } from '../config';

export function AdminPortalPage({ onNavigate }) {
  const [activeTab, setActiveTab] = useState('factories');
  const [factories, setFactories] = useState([]);
  const [users, setUsers] = useState([]);
  const [consentLimits, setConsentLimits] = useState([]);
  const [models, setModels] = useState([]);
  const [thresholds, setThresholds] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  const [districtFilter, setDistrictFilter] = useState('');
  const [industryFilter, setIndustryFilter] = useState('');

  const [showAddFactoryModal, setShowAddFactoryModal] = useState(false);

  useEffect(() => {
    fetchAdminData();
  }, [districtFilter, industryFilter]);

  const fetchAdminData = async () => {
    setLoading(true);
    try {
      const fRes = await fetch(`${API_BASE_URL}/api/admin/factories?district=${districtFilter}&industry=${industryFilter}`);
      if (fRes.ok) {
        const fData = await fRes.json();
        setFactories(fData);
      } else {
        setFactories(getFallbackFactories());
      }

      const uRes = await fetch(`${API_BASE_URL}/api/admin/users`);
      if (uRes.ok) setUsers(await uRes.json());
      else setUsers(getFallbackUsers());

      const cRes = await fetch(`${API_BASE_URL}/api/admin/consent-limits`);
      if (cRes.ok) setConsentLimits(await cRes.json());
      else setConsentLimits(getFallbackConsentLimits());

      const mRes = await fetch(`${API_BASE_URL}/api/admin/models`);
      if (mRes.ok) setModels(await mRes.json());
      else setModels(getFallbackModels());

      const tRes = await fetch(`${API_BASE_URL}/api/admin/thresholds`);
      if (tRes.ok) setThresholds(await tRes.json());
      else setThresholds(getFallbackThresholds());

      const nRes = await fetch(`${API_BASE_URL}/api/admin/notifications`);
      if (nRes.ok) setNotifications(await nRes.json());
      else setNotifications(getFallbackNotifications());

    } catch (err) {
      setFactories(getFallbackFactories());
      setUsers(getFallbackUsers());
      setConsentLimits(getFallbackConsentLimits());
      setModels(getFallbackModels());
      setThresholds(getFallbackThresholds());
      setNotifications(getFallbackNotifications());
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteFactory = async (factoryId) => {
    if (!window.confirm(`Are you sure you want to remove factory ${factoryId}?`)) return;
    try {
      await fetch(`${API_BASE_URL}/api/admin/factories/${factoryId}`, { method: 'DELETE' });
      fetchAdminData();
    } catch (err) {
      setFactories(prev => prev.filter(f => f.factory_id !== factoryId));
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
            { id: 'thresholds', label: 'Threshold Settings' },
            { id: 'notifications', label: 'Notification Rules' }
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
                  <option value="Tarapur">Tarapur</option>
                </select>

                <select 
                  value={industryFilter}
                  onChange={(e) => setIndustryFilter(e.target.value)}
                  className="border border-[#E5E7EB] bg-[#f8f9fb] rounded-lg text-body-sm px-3 py-1.5 focus:outline-none"
                >
                  <option value="">All Industries</option>
                  <option value="Chemical Manufacturing">Chemical Manufacturing</option>
                  <option value="Petrochemicals">Petrochemicals</option>
                  <option value="Textile & Dyeing">Textile & Dyeing</option>
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

        {/* Tab 3: Consent Limits */}
        {activeTab === 'consent-limits' && (
          <div className="p-6 space-y-4">
            <h3 className="font-headline-md text-headline-md text-[#00355f]">Industry Consent Limit Enforcements</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {consentLimits.map((c, i) => (
                <div key={i} className="p-4 border border-[#E5E7EB] rounded-lg bg-[#f8f9fb]">
                  <div className="font-bold text-[#191c1e] text-body-md">{c.industry || c.category}</div>
                  <div className="text-xs text-[#42474f] mt-2 space-y-1">
                    <div>BOD Max: <span className="font-bold text-[#D32F2F]">{c.bod_limit || 30} mg/L</span></div>
                    <div>COD Max: <span className="font-bold text-[#F57C00]">{c.cod_limit || 250} mg/L</span></div>
                    <div>pH Range: <span className="font-bold text-[#1b6d24]">{c.ph_min || 5.5} - {c.ph_max || 9.0}</span></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 4: Model Versions */}
        {activeTab === 'models' && (
          <ModelVersionsTab factories={factories} />
        )}

        {/* Tab 5: Threshold Settings */}
        {activeTab === 'thresholds' && (
          <ThresholdSettingsTab />
        )}
      </div>

      {showAddFactoryModal && (
        <AddFactoryModal 
          onClose={() => setShowAddFactoryModal(false)}
          onSuccess={() => {
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

function getFallbackConsentLimits() {
  return [
    { industry: "Chemical Manufacturing", bod_limit: 30, cod_limit: 250, ph_min: 5.5, ph_max: 9.0 },
    { industry: "Petrochemicals", bod_limit: 50, cod_limit: 300, ph_min: 6.0, ph_max: 8.5 }
  ];
}

function getFallbackModels() { return []; }
function getFallbackThresholds() { return []; }
function getFallbackNotifications() { return []; }
