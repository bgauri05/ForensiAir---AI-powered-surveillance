import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { TopHeader } from './components/TopHeader';
import { LoginPage } from './components/LoginPage';
import { ExecutiveDashboardPage } from './components/ExecutiveDashboardPage';
import { AIAnalysisPage } from './components/AIAnalysisPage';
import { FactoryDetailDossierPage } from './components/FactoryDetailDossierPage';
import { ReportsCenterPage } from './components/ReportsCenterPage';
import { DatasetQualityPage } from './components/DatasetQualityPage';
import { AdminPortalPage } from './components/AdminPortalPage';
import { InstitutionalOversightPage } from './components/InstitutionalOversightPage';
import { AlertsPage } from './components/AlertsPage';
import { SettingsPage } from './components/SettingsPage';
import { ShieldAlert } from 'lucide-react';
import { apiFetch, getAuthToken, clearAuthToken, UNAUTHORIZED_EVENT } from './config';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  // Real logged-in session, hydrated from GET /api/me. null until resolved;
  // 'checking' while validating a stored token on mount; the previous demo
  // "Role: Admin/Inspector" dropdown (client-side only, no real session
  // behind it) is gone -- role now comes only from the authenticated JWT.
  const [currentUser, setCurrentUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  // Which factory "View Details" / a table row click should open. Previously
  // onNavigate only ever took a tab name, so FactoryDetailDossierPage had no
  // idea which factory was clicked and always defaulted to the first one in
  // the list. handleNavigate carries an optional factory id alongside the
  // tab switch; pages that don't pass one (most of them) are unaffected.
  const [selectedFactoryId, setSelectedFactoryId] = useState(null);

  useEffect(() => {
    validateSession();
  }, []);

  // apiFetch() dispatches this on any 401 from any request, anywhere in the
  // app -- a dead/expired session, not a role restriction (403s are left
  // alone; those are legitimate responses from require_role(), not auth
  // failures). This is what actually ends the session: clearing currentUser
  // makes the render below fall through to <LoginPage>, since no router
  // exists to redirect through. Previously nothing listened for this at
  // all, so an expired token just made every page quietly show its
  // demo-fallback data instead.
  useEffect(() => {
    const handleUnauthorized = () => handleLogout();
    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
  }, []);

  const validateSession = async () => {
    const token = getAuthToken();
    if (!token) {
      setAuthChecked(true);
      return;
    }
    try {
      const res = await apiFetch('/api/me');
      if (res.ok) {
        setCurrentUser(await res.json());
      } else {
        clearAuthToken();
      }
    } catch (err) {
      clearAuthToken();
    } finally {
      setAuthChecked(true);
    }
  };

  const handleLoginSuccess = () => {
    validateSession();
  };

  const handleLogout = () => {
    clearAuthToken();
    setCurrentUser(null);
    setActiveTab('dashboard');
  };

  const handleNavigate = (tab, factoryId) => {
    if (factoryId) setSelectedFactoryId(factoryId);
    setActiveTab(tab);
  };

  if (!authChecked) {
    return (
      <div className="min-h-screen bg-[#f8f9fb] flex items-center justify-center">
        <span className="material-symbols-outlined animate-spin text-3xl text-[#00355f]">progress_activity</span>
      </div>
    );
  }

  if (!currentUser) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  const userRole = currentUser.role;

  const renderActiveModule = () => {
    // Role-based gating check -- client-side convenience only; the real
    // enforcement is server-side via require_role() on the protected
    // endpoints themselves.
    if (userRole === 'inspector' && (activeTab === 'dataset-quality' || activeTab === 'administration')) {
      return (
        <div style={{ padding: 40, textAlign: 'center', background: '#fff', margin: 24, borderRadius: 8, border: '1px solid #fee2e2' }}>
          <ShieldAlert size={48} color="#ef4444" style={{ margin: '0 auto 16px auto' }} />
          <h2 style={{ fontSize: 20, fontWeight: 700, color: '#991b1b', marginBottom: 8 }}>Access Restricted (403 Forbidden)</h2>
          <p style={{ color: '#64748b', maxWidth: 500, margin: '0 auto 20px auto', fontSize: 14 }}>
            You're logged in as <strong>{currentUser.username}</strong> (Field Inspector). Access to Dataset Quality audits and Administration controls requires <strong>System Controller / Admin</strong> privileges. Log out and sign back in with an admin account to access this section.
          </p>
          <button className="btn btn-primary" onClick={handleLogout}>
            Log Out
          </button>
        </div>
      );
    }

    switch (activeTab) {
      case 'dashboard':
        return <ExecutiveDashboardPage onNavigate={handleNavigate} />;
      case 'ai-analysis':
        return <AIAnalysisPage onNavigate={handleNavigate} selectedFactoryId={selectedFactoryId} />;
      case 'institutional-oversight':
        return <InstitutionalOversightPage onNavigate={handleNavigate} />;
      case 'factories':
      case 'factory-detail':
        return <FactoryDetailDossierPage onNavigate={handleNavigate} selectedFactoryId={selectedFactoryId} />;
      case 'reports':
        return <ReportsCenterPage onNavigate={handleNavigate} />;
      case 'dataset-quality':
        return <DatasetQualityPage onNavigate={handleNavigate} />;
      case 'administration':
        return <AdminPortalPage onNavigate={handleNavigate} />;
      case 'alerts':
        return <AlertsPage onNavigate={handleNavigate} />;
      case 'settings':
        return <SettingsPage currentUser={currentUser} onLogout={handleLogout} />;
      default:
        return <ExecutiveDashboardPage onNavigate={handleNavigate} />;
    }
  };

  return (
    <div className="min-h-screen bg-[#f8f9fb]">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} userRole={userRole} currentUser={currentUser} />
      <TopHeader currentUser={currentUser} onLogout={handleLogout} onNavigate={handleNavigate} />
      <main className="ml-16 md:ml-[280px] pt-16 min-h-screen bg-[#f8f9fb] text-[#191c1e]">
        {renderActiveModule()}
      </main>
    </div>
  );
}
