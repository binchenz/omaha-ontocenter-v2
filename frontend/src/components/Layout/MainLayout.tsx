import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

const MainLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-background text-white">
      <Sidebar />
      <main className="ml-60 p-6 min-h-screen">
        <Outlet />
      </main>
    </div>
  );
};

export default MainLayout;
