import { useState } from 'react';
import { useAuth } from './hooks/useAuth';
import { Layout } from './layouts/Layout';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { HistoryPage } from './pages/HistoryPage';
import { ConfigsPage } from './pages/ConfigsPage';
import { CatalogPage } from './pages/CatalogPage';

import type { View } from './types';

function App() {
  const { isLoggedIn } = useAuth();
  const [activeView, setActiveView] = useState<View>('dashboard');

  if (!isLoggedIn) {
    return <LoginPage />;
  }

  const renderView = () => {
    switch (activeView) {
      case 'dashboard':
        return <DashboardPage />;
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
