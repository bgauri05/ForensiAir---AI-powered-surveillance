import React, { useState, useEffect } from 'react';
import { AlertTriangle, ChevronRight, ShieldAlert } from 'lucide-react';
import { apiFetch } from '../config';

// This nav item previously had no case in App.jsx's switch and silently
// fell through to the Dashboard with no indication anything was wrong.
// There's no dedicated /api/alerts endpoint on the backend yet, so rather
// than inventing mock alert data, this reuses the real /api/factories
// response and surfaces factories the current risk scoring has flagged
// Medium or above -- genuinely real data, just a filtered view of it.
export function AlertsPage({ onNavigate }) {
  const [factories, setFactories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetchFlagged();
  }, []);

  const fetchFlagged = async () => {
    try {
      const res = await apiFetch(`/api/factories`);
      if (res.ok) {
        const data = await res.json();
        const flagged = (data || [])
          .filter((f) => f.risk_tier === 'High' || f.risk_tier === 'Medium')
          .sort((a, b) => (b.tsi_score || 0) - (a.tsi_score || 0));
        setFactories(flagged);
      } else {
        setError(true);
      }
    } catch (err) {
      console.error(err);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  const tierColor = (tier) =>
    tier === 'High'
      ? { text: 'text-[#D32F2F]', bg: 'bg-[#fdecec]', border: 'border-[#D32F2F]/20' }
      : { text: 'text-[#F57C00]', bg: 'bg-[#fff3e6]', border: 'border-[#F57C00]/20' };

  if (loading) {
    return <div className="p-8 text-body-md text-[#42474f]">Loading flagged factories...</div>;
  }

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center gap-3 mb-1">
        <AlertTriangle size={22} className="text-[#F57C00]" />
        <h1 className="font-headline-lg text-headline-lg text-[#191c1e]">Alerts</h1>
      </div>
      <p className="text-body-sm text-[#727780] mb-6">
        Factories currently flagged Medium or High by the composite risk score. This view reads
        directly from live factory data -- there is no separate real-time alerting system yet.
      </p>

      {error && (
        <div className="card p-6 flex items-center gap-3 border-[#D32F2F]/30 mb-4">
          <ShieldAlert size={20} className="text-[#D32F2F]" />
          <p className="text-body-sm text-[#42474f]">
            Couldn't reach the backend. Confirm the API is running and reachable at the configured URL.
          </p>
        </div>
      )}

      {!error && factories.length === 0 && (
        <div className="card p-6 text-body-sm text-[#42474f]">
          No factories are currently flagged Medium or High risk.
        </div>
      )}

      <div className="space-y-3">
        {factories.map((f) => {
          const c = tierColor(f.risk_tier);
          return (
            <div
              key={f.factory_id}
              className={`card p-4 flex items-center justify-between cursor-pointer hover:shadow-md transition-shadow ${c.border}`}
              onClick={() => onNavigate('factory-detail', f.factory_id)}
            >
              <div className="flex items-center gap-4">
                <div className={`w-2 h-10 rounded-full ${c.bg.replace('bg-', 'bg-')}`} style={{ backgroundColor: f.risk_tier === 'High' ? '#D32F2F' : '#F57C00' }} />
                <div>
                  <div className="font-bold text-body-md text-[#191c1e]">{f.factory_name}</div>
                  <div className="text-body-sm text-[#727780]">{f.region || f.district}</div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span className={`px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wide ${c.bg} ${c.text}`}>
                  {f.risk_tier} risk
                </span>
                <span className="text-body-sm font-bold text-[#191c1e] w-16 text-right">
                  {f.tsi_score ? f.tsi_score.toFixed(1) : '-'}
                </span>
                <ChevronRight size={16} className="text-[#727780]" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
