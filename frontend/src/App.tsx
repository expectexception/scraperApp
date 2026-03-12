import { useEffect, useState } from 'react';
import { useAuth } from './hooks/useAuth';
import { Layout } from './layouts/Layout';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { JobsPage } from './pages/JobsPage';
import { ScrapedJobsPage } from './pages/ScrapedJobsPage';
import { HistoryPage } from './pages/HistoryPage';
import { ConfigsPage } from './pages/ConfigsPage';
import { CatalogPage } from './pages/CatalogPage';

import type { View } from './types';

function App() {
  const { isLoggedIn } = useAuth();
  const savedView = localStorage.getItem('aeroops_active_view');
  const initialView: View = savedView === 'jobs' || savedView === 'scraped' || savedView === 'history' || savedView === 'configs' || savedView === 'catalog'
    ? savedView
    : 'dashboard';
  const [activeView, setActiveView] = useState(initialView);

  useEffect(() => {
    localStorage.setItem('aeroops_active_view', activeView);
  }, [activeView]);

  if (!isLoggedIn) {
    return <LoginPage />;
  }

  const renderView = () => {
    switch (activeView) {
      case 'dashboard':
        return <DashboardPage />;
      case 'jobs':
        return <JobsPage />;
      case 'scraped':
        return <ScrapedJobsPage />;
      case 'history':
        return <HistoryPage />;
      case 'configs':
        return <ConfigsPage />;
      case 'catalog':
        return <CatalogPage />;
      default:
        return <DashboardPage />;
    }
  };

  return (
    <Layout activeView={activeView} setActiveView={setActiveView}>
      {renderView()}
    </Layout>
  );
}

export default App;
