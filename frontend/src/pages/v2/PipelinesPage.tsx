import PipelineManager from '../PipelineManager';
import { useProject } from '@/contexts/ProjectContext';

export default function PipelinesPage() {
  const { currentProject } = useProject();
  if (!currentProject) return null;
  return <PipelineManager projectId={currentProject.id} />;
}
