import { useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { NAV_MODULES } from './navConfig';
import ProjectSwitcher from '@/components/Layout/ProjectSwitcher';

export default function TopNav() {
  const navigate = useNavigate();
  const location = useLocation();

  const activeModule = useMemo(
    () => NAV_MODULES.find((m) => location.pathname.startsWith(m.basePath)),
    [location.pathname]
  );

  return (
      <header className="h-12 bg-gray-900 border-b border-gray-800 flex items-center px-4 shrink-0">
        <div
          className="text-white font-semibold text-sm mr-8 cursor-pointer"
          onClick={() => navigate('/app/assistant')}
        >
          Omaha OntoCenter
        </div>

        <nav className="flex items-center gap-1 flex-1">
          {NAV_MODULES.map((mod) => {
            const isActive = activeModule?.key === mod.key;
            return (
              <button
                key={mod.key}
                onClick={() => navigate(mod.subPages[0].path)}
                className={`px-3 py-1.5 text-sm rounded transition-colors ${
                  isActive
                    ? 'text-white bg-gray-800'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
                }`}
              >
                {mod.label}
              </button>
            );
          })}
        </nav>

        <div className="flex items-center gap-3">
          <ProjectSwitcher />
        </div>
      </header>
  );
}
