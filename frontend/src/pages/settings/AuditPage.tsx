import AuditLogViewer from '../legacy/AuditLogViewer';
import { useProject } from '@/contexts/ProjectContext';

export default function AuditPage() {
  const { currentProject } = useProject();
  if (!currentProject) return null;
  return <AuditLogViewer projectId={currentProject.id} />;
}
