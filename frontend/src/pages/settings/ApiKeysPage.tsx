import ApiKeyManager from '@/components/shared/ApiKeyManager';
import { useProject } from '@/contexts/ProjectContext';

export default function ApiKeysPage() {
  const { currentProject } = useProject();
  if (!currentProject) return null;
  return <ApiKeyManager projectId={currentProject.id} />;
}
