import React from 'react';
import { useProject } from '@/contexts/ProjectContext';

interface Props {
  emptyMessage: string;
  children: (projectId: number) => React.ReactNode;
}

const RequireProject: React.FC<Props> = ({ emptyMessage, children }) => {
  const { currentProject, loading } = useProject();

  if (loading) {
    return <div className="text-slate-400 text-sm">加载中...</div>;
  }

  if (!currentProject) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-slate-400">
        <p className="text-sm mb-2">还没有项目</p>
        <p className="text-xs">{emptyMessage}</p>
      </div>
    );
  }

  return <>{children(currentProject.id)}</>;
};

export default RequireProject;
