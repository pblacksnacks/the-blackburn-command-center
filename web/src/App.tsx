import { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import LeadDetailPage from './pages/LeadDetailPage';
import ResearchPage from './pages/ResearchPage';
import BriefingsPage from './pages/BriefingsPage';
import { fetchConfig } from './api';
import { ModeContext, type AppMode } from './modeContext';

export default function App() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [mode, setMode] = useState<AppMode>('anthropic');
  const handlePipelineComplete = useCallback(() => setRefreshKey((k) => k + 1), []);

  useEffect(() => {
    fetchConfig()
      .then((cfg) => {
        setMode(cfg.mode);
        document.documentElement.dataset.theme = cfg.mode;
      })
      .catch(() => {});
  }, []);

  return (
    <ModeContext.Provider value={mode}>
      <BrowserRouter>
        <Layout onPipelineComplete={handlePipelineComplete}>
          <Routes>
            <Route path="/" element={<Dashboard refreshKey={refreshKey} />} />
            <Route path="/leads/:email" element={<LeadDetailPage />} />
            <Route path="/research" element={<ResearchPage refreshKey={refreshKey} />} />
            <Route path="/briefings" element={<BriefingsPage refreshKey={refreshKey} />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </ModeContext.Provider>
  );
}
