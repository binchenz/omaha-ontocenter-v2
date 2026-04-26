import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import ProjectSwitcher from './ProjectSwitcher';

const MainLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-background text-white">
      <Sidebar />
      <div className="ml-60 flex flex-col min-h-screen">
        <header className="h-12 border-b border-white/10 bg-surface/50 backdrop-blur flex items-center px-6 shrink-0">
          <ProjectSwitcher />
        </header>
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default MainLayout;
