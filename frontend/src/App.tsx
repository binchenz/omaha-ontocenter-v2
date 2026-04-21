import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
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

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
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
