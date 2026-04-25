import DatasourceManager from '../DatasourceManager';
import { useProject } from '@/contexts/ProjectContext';

export default function DatasourcePage() {
  const { currentProject } = useProject();
  if (!currentProject) return null;
  return <DatasourceManager projectId={currentProject.id} />;
}
