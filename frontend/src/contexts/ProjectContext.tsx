import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { projectService } from '../services/project';
import { Project } from '../types';

interface ProjectContextType {
  projects: Project[];
  currentProject: Project | null;
  loading: boolean;
  switchProject: (id: number) => void;
  refreshProjects: () => Promise<void>;
}

const ProjectContext = createContext<ProjectContextType>({
  projects: [],
  currentProject: null,
  loading: true,
  switchProject: () => {},
  refreshProjects: async () => {},
});

const STORAGE_KEY = 'current_project_id';

export const ProjectProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);

  const loadProjects = useCallback(async () => {
    try {
      const list = await projectService.list();
      setProjects(list);

      const savedId = localStorage.getItem(STORAGE_KEY);
      const saved = savedId ? list.find(p => p.id === Number(savedId)) : null;
      const target = saved || list[0] || null;
      setCurrentProject(target);
      if (target) localStorage.setItem(STORAGE_KEY, String(target.id));
    } catch {
      // auth error handled by axios interceptor
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadProjects(); }, [loadProjects]);

  const switchProject = useCallback((id: number) => {
    const target = projects.find(proj => proj.id === id);
    if (target) {
      setCurrentProject(target);
      localStorage.setItem(STORAGE_KEY, String(id));
    }
  }, [projects]);

  return (
    <ProjectContext.Provider value={{ projects, currentProject, loading, switchProject, refreshProjects: loadProjects }}>
      {children}
    </ProjectContext.Provider>
  );
};

export const useProject = () => useContext(ProjectContext);
