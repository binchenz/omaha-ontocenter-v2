import { Outlet } from 'react-router-dom';
import TopNav from './TopNav';
import ModuleSidebar from './ModuleSidebar';
import RequireProject from '@/components/RequireProject';

export default function AppLayout() {
  return (
    <div className="h-screen flex flex-col bg-gray-950" data-layout="app">
      <TopNav />
      <div className="flex flex-1 overflow-hidden">
        <ModuleSidebar />
        <main className="flex-1 overflow-auto">
          <RequireProject emptyMessage="请在左上角选择一个项目后开始">
            {() => <Outlet />}
          </RequireProject>
        </main>
      </div>
    </div>
  );
}
