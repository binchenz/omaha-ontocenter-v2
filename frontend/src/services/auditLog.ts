import api from './api';

export interface AuditLogEntry {
  id: number;
  user_id: number | null;
  username: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  detail: Record<string, any> | null;
  ip_address: string | null;
  created_at: string | null;
}

export const auditService = {
  list: async (projectId: number, action?: string, limit = 100): Promise<AuditLogEntry[]> => {
    const params: Record<string, any> = { limit };
    if (action) params.action = action;
    const res = await api.get(`/projects/${projectId}/audit-logs`, { params });
    return res.data.logs;
  },
};
