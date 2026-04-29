import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import MainLayout from './components/layout/MainLayout';
import PrivateRoute from './components/shared/PrivateRoute';
import { ProjectProvider } from './contexts/ProjectContext';
import AppLayout from './layouts/AppLayout';
import AssistantPage from './pages/assistant/AssistantPage';
import DashboardPage from './pages/dashboard/DashboardPage';
import AppsPage from './pages/apps/AppsPage';
import SettingsPage from './pages/settings/SettingsPage';
import ApiKeysPage from './pages/settings/ApiKeysPage';
import AuditPage from './pages/settings/AuditPage';

const ChatPage = React.lazy(() => import('./pages/ChatPage'));
const Settings = React.lazy(() => import('./pages/Settings'));
const OntologyBrowser = React.lazy(() => import('./pages/ontology/OntologyBrowser'));
const OntologyGraph = React.lazy(() => import('./pages/ontology/OntologyGraph'));
const ModelingPage = React.lazy(() => import('./pages/ontology/ModelingPage'));
const DatasourcePage = React.lazy(() => import('./pages/apps/DatasourcePage'));
const PipelinesPage = React.lazy(() => import('./pages/apps/PipelinesPage'));

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className="p-8 text-center text-gray-500">加载中...</div>}>
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
            <Route index element={<Navigate to="/app/assistant" replace />} />
            <Route path="chat" element={<ChatPage />} />
            <Route path="map" element={<Navigate to="/app/ontology/graph" replace />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
};

export default App;
