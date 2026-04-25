import MembersManager from '../MembersManager';
import { useProject } from '@/contexts/ProjectContext';

export default function SettingsPage() {
  const { currentProject } = useProject();
  if (!currentProject) return null;
  return <MembersManager projectId={currentProject.id} />;
}
