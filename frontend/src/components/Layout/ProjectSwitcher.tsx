import React from 'react';
import { ChevronDown, Plus } from 'lucide-react';
import { useProject } from '@/contexts/ProjectContext';
import { projectService } from '@/services/project';

const ProjectSwitcher: React.FC = () => {
  const { projects, currentProject, switchProject, refreshProjects } = useProject();
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKey);
    };
  }, []);

  const handleCreate = async () => {
    const name = window.prompt('项目名称');
    if (!name) return;
    const p = await projectService.create({ name });
    await refreshProjects();
    switchProject(p.id);
    setOpen(false);
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm text-slate-300 hover:text-white hover:bg-white/5 transition-colors"
      >
        <span className="font-medium truncate max-w-[180px]">
          {currentProject?.name || '选择项目'}
        </span>
        <ChevronDown size={14} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 w-56 bg-surface border border-white/10 rounded-md shadow-xl z-50 py-1">
          {projects.map(p => (
            <button
              key={p.id}
              onClick={() => { switchProject(p.id); setOpen(false); }}
              className={`w-full text-left px-3 py-2 text-sm transition-colors ${
                p.id === currentProject?.id
                  ? 'text-primary bg-primary/10'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              {p.name}
            </button>
          ))}
          <div className="border-t border-white/10 mt-1 pt-1">
            <button
              onClick={handleCreate}
              className="w-full text-left px-3 py-2 text-sm text-slate-400 hover:text-white hover:bg-white/5 flex items-center gap-2"
            >
              <Plus size={14} /> 新建项目
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectSwitcher;
