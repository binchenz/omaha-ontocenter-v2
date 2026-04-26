import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import Explorer from './pages/legacy/Explorer';
import ChatPage from './pages/ChatPage';
import Watchlist from './pages/legacy/Watchlist';
import OntologyMap from './pages/legacy/OntologyMap';
import QueryHistory from './pages/legacy/QueryHistory';
import Settings from './pages/Settings';
import MainLayout from './components/layout/MainLayout';
import PrivateRoute from './components/shared/PrivateRoute';
import { ProjectProvider } from './contexts/ProjectContext';
import AppLayout from './layouts/AppLayout';
import AssistantPage from './pages/assistant/AssistantPage';
import OntologyBrowser from './pages/ontology/OntologyBrowser';
import OntologyGraph from './pages/ontology/OntologyGraph';
import DatasourcePage from './pages/apps/DatasourcePage';
import ModelingPage from './pages/ontology/ModelingPage';
import DashboardPage from './pages/dashboard/DashboardPage';
import AppsPage from './pages/apps/AppsPage';
import SettingsPage from './pages/settings/SettingsPage';
import PipelinesPage from './pages/apps/PipelinesPage';
import ApiKeysPage from './pages/settings/ApiKeysPage';
import AuditPage from './pages/settings/AuditPage';

const App: React.FC = () => {
  return (
    <BrowserRouter>
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
