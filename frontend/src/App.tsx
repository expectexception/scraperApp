import { useEffect, useState } from 'react';
import { useAuth } from './hooks/useAuth';
import { useRealtimeEvents } from './hooks/useRealtimeEvents';
import { Layout } from './layouts/Layout';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { JobsPage } from './pages/JobsPage';
import { ScrapedJobsPage } from './pages/ScrapedJobsPage';
import { HistoryPage } from './pages/HistoryPage';
import { ConfigsPage } from './pages/ConfigsPage';
import { CatalogPage } from './pages/CatalogPage';
import { DatabasePage } from './pages/DatabasePage';


import type { View } from './types';

function App() {
  const { isLoggedIn, token } = useAuth();
  const savedView = localStorage.getItem('aeroops_active_view');
  const initialView: View = savedView === 'jobs' || savedView === 'scraped' || savedView === 'history' || savedView === 'configs' || savedView === 'catalog' || savedView === 'database'
    ? savedView
    : 'dashboard';
  const [activeView, setActiveView] = useState(initialView);

  useEffect(() => {
    localStorage.setItem('aeroops_active_view', activeView);
  }, [activeView]);

  useRealtimeEvents(isLoggedIn, token);

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
      case 'database':
        return <DatabasePage />;
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
