import React, { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { TopHeader } from './components/TopHeader';
import { ExecutiveDashboardPage } from './components/ExecutiveDashboardPage';
import { AIAnalysisPage } from './components/AIAnalysisPage';
import { ExplainabilityPage } from './components/ExplainabilityPage';
import { FactoryDetailDossierPage } from './components/FactoryDetailDossierPage';
import { ReportsCenterPage } from './components/ReportsCenterPage';
import { DatasetQualityPage } from './components/DatasetQualityPage';
import { AdminPortalPage } from './components/AdminPortalPage';
import { InstitutionalOversightPage } from './components/InstitutionalOversightPage';
import { ShieldAlert } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [userRole, setUserRole] = useState('admin'); // 'admin' or 'inspector'

  const renderActiveModule = () => {
    // Role-based gating check
    if (userRole === 'inspector' && (activeTab === 'dataset-quality' || activeTab === 'administration')) {
      return (
        <div style={{ padding: 40, textAlign: 'center', background: '#fff', margin: 24, borderRadius: 8, border: '1px solid #fee2e2' }}>
          <ShieldAlert size={48} color="#ef4444" style={{ margin: '0 auto 16px auto' }} />
          <h2 style={{ fontSize: 20, fontWeight: 700, color: '#991b1b', marginBottom: 8 }}>Access Restricted (403 Forbidden)</h2>
          <p style={{ color: '#64748b', maxWidth: 500, margin: '0 auto 20px auto', fontSize: 14 }}>
            Your current role is <strong>Field Inspector</strong>. Access to Dataset Quality audits and Administration controls requires <strong>System Controller / Admin</strong> privileges.
          </p>
          <button className="btn btn-primary" onClick={() => setUserRole('admin')}>
            Switch to Admin Role (Demo Mode)
          </button>
        </div>
      );
    }

    switch (activeTab) {
      case 'dashboard':
        return <ExecutiveDashboardPage onNavigate={setActiveTab} />;
      case 'ai-analysis':
        return <AIAnalysisPage onNavigate={setActiveTab} />;
      case 'explainability':
        return <ExplainabilityPage onNavigate={setActiveTab} />;
      case 'institutional-oversight':
        return <InstitutionalOversightPage onNavigate={setActiveTab} />;
      case 'factories':
      case 'factory-detail':
        return <FactoryDetailDossierPage onNavigate={setActiveTab} />;
      case 'reports':
        return <ReportsCenterPage onNavigate={setActiveTab} />;
      case 'dataset-quality':
        return <DatasetQualityPage onNavigate={setActiveTab} />;
      case 'administration':
        return <AdminPortalPage onNavigate={setActiveTab} />;
      case 'alerts':
      case 'settings':
      default:
        return <ExecutiveDashboardPage onNavigate={setActiveTab} />;
    }
  };

  return (
    <div className="min-h-screen bg-[#f8f9fb]">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} userRole={userRole} />
      <TopHeader activeTab={activeTab} userRole={userRole} setUserRole={setUserRole} />
      <main className="ml-[280px] pt-16 min-h-screen bg-[#f8f9fb] text-[#191c1e]">
        {renderActiveModule()}
      </main>
    </div>
  );
}
