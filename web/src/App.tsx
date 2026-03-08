import { useState, useCallback } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import LeadDetailPage from './pages/LeadDetailPage';
import ResearchPage from './pages/ResearchPage';
import BriefingsPage from './pages/BriefingsPage';

export default function App() {
  const [refreshKey, setRefreshKey] = useState(0);
  const handlePipelineComplete = useCallback(() => setRefreshKey((k) => k + 1), []);

  return (
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
  );
}
