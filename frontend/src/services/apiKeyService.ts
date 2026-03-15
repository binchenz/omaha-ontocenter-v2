import api from './api';

export interface ApiKey {
  id: number;
  name: string;
  key_prefix: string;
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
}

export interface ApiKeyCreated extends ApiKey {
  key: string; // only returned once
}

export const apiKeyService = {
  list: (projectId: number): Promise<ApiKey[]> =>
    api.get(`/projects/${projectId}/api-keys`).then(r => r.data),

  create: (projectId: number, name: string): Promise<ApiKeyCreated> =>
    api.post(`/projects/${projectId}/api-keys`, { name }).then(r => r.data),

  revoke: (projectId: number, keyId: number): Promise<void> =>
    api.delete(`/projects/${projectId}/api-keys/${keyId}`).then(r => r.data),
};
