import { useLocation, useNavigate } from 'react-router-dom';
import { findModuleByPath } from './navConfig';

export default function ModuleSidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const currentModule = findModuleByPath(location.pathname);

  if (!currentModule) return null;

  return (
    <aside className="w-50 bg-gray-900/50 border-r border-gray-800 shrink-0 overflow-y-auto">
      <div className="p-3">
        <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2 px-2">
          {currentModule.label}
        </h2>
        <nav className="flex flex-col gap-0.5">
          {currentModule.subPages.map((page) => {
            const isActive =
              location.pathname === page.path ||
              (page.path !== currentModule.basePath &&
                location.pathname.startsWith(page.path));
            const exactMatch =
              page.path === currentModule.basePath &&
              location.pathname === page.path;
            const active = isActive || exactMatch;

            const Icon = page.icon;
            return (
              <button
                key={page.path}
                onClick={() => navigate(page.path)}
                className={`flex items-center gap-2 px-2 py-1.5 rounded text-sm transition-colors w-full text-left ${
                  active
                    ? 'text-white bg-gray-800'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
                }`}
              >
                <Icon size={16} />
                {page.label}
              </button>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
