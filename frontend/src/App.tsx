import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import Explorer from './pages/Explorer';
import ChatPage from './pages/ChatPage';
import Watchlist from './pages/Watchlist';
import OntologyMap from './pages/OntologyMap';
import QueryHistory from './pages/QueryHistory';
import Settings from './pages/Settings';
import MainLayout from './components/Layout/MainLayout';
import PrivateRoute from './components/PrivateRoute';
import { ProjectProvider } from './contexts/ProjectContext';
import AppLayout from './layouts/AppLayout';
import AssistantPage from './pages/v2/AssistantPage';
import OntologyBrowser from './pages/v2/OntologyBrowser';
import OntologyGraph from './pages/v2/OntologyGraph';
import DatasourcePage from './pages/v2/DatasourcePage';
import ModelingPage from './pages/v2/ModelingPage';
import DashboardPage from './pages/v2/DashboardPage';
import AppsPage from './pages/v2/AppsPage';
import SettingsPage from './pages/v2/SettingsPage';
import PipelinesPage from './pages/v2/PipelinesPage';
import ApiKeysPage from './pages/v2/ApiKeysPage';
import AuditPage from './pages/v2/AuditPage';

const PathDebug: React.FC = () => {
  const location = useLocation();
  return (
    <div style={{position:'fixed',top:0,right:0,zIndex:99999,background:'blue',color:'white',padding:'8px 12px',fontSize:'12px',fontWeight:'bold'}}>
      Path: {location.pathname}
    </div>
  );
};

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <PathDebug />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* New v2 layout */}
        <Route
          path="/app/*"
          element={
            <PrivateRoute>
              <ProjectProvider>
                <AppLayout />
              </ProjectProvider>
            </PrivateRoute>
          }
        >
          <Route index element={<Navigate to="/app/assistant" replace />} />
          <Route path="assistant" element={<AssistantPage />} />
          <Route path="assistant/history" element={<AssistantPage />} />
          <Route path="ontology" element={<OntologyBrowser />} />
          <Route path="ontology/graph" element={<OntologyGraph />} />
          <Route path="ontology/datasources" element={<DatasourcePage />} />
          <Route path="ontology/modeling" element={<ModelingPage />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="dashboard/templates" element={<DashboardPage />} />
          <Route path="apps" element={<AppsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="settings/pipelines" element={<PipelinesPage />} />
          <Route path="settings/api-keys" element={<ApiKeysPage />} />
          <Route path="settings/audit" element={<AuditPage />} />
        </Route>

        {/* Old layout */}
        <Route
          path="/"
          element={
            <PrivateRoute>
              <ProjectProvider>
                <MainLayout />
              </ProjectProvider>
            </PrivateRoute>
          }
        >
          <Route index element={<Navigate to="/explorer" replace />} />
          <Route path="explorer" element={<Explorer />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="watchlist" element={<Watchlist />} />
          <Route path="map" element={<OntologyMap />} />
          <Route path="history" element={<QueryHistory />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
