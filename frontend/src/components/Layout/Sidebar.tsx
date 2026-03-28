import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { FolderOpen, Star, LogOut, User } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/lib/utils';

const navItems = [
  { to: '/projects', icon: FolderOpen, label: 'Projects' },
  { to: '/watchlist', icon: Star, label: 'Watchlist' },
];

const Sidebar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className="fixed left-0 top-0 h-screen w-60 bg-surface border-r border-white/10 flex flex-col z-40">
      <div className="px-6 py-5 border-b border-white/10">
        <span className="text-white font-semibold text-sm tracking-wide font-mono">
          Omaha OntoCenter
        </span>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors',
                isActive
                  ? 'bg-primary/10 text-primary border-l-2 border-primary pl-[10px]'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              )
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-3 py-4 border-t border-white/10">
        <div className="flex items-center gap-3 px-3 py-2 text-sm text-slate-400">
          <User size={16} />
          <span className="flex-1 truncate">{user?.username}</span>
          <button
            onClick={handleLogout}
            className="hover:text-white transition-colors"
            title="Logout"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
