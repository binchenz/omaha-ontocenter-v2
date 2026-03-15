import api from './api';
import { QueryHistory } from '../types';

export const queryService = {
  async queryObjects(
    projectId: number,
    objectType: string,
    filters?: Record<string, any>,
    limit: number = 100
  ): Promise<{
    success: boolean;
    data?: any[];
    count?: number;
    error?: string;
  }> {
    const response = await api.post(`/query/${projectId}/query`, {
      object_type: objectType,
      filters,
      limit,
    });
    return response.data;
  },

  async listObjectTypes(projectId: number): Promise<{ objects: string[] }> {
    const response = await api.get(`/query/${projectId}/objects`);
    return response.data;
  },

  async getHistory(
    projectId: number,
    skip: number = 0,
    limit: number = 50
  ): Promise<QueryHistory[]> {
    const response = await api.get(`/query/${projectId}/history`, {
      params: { skip, limit },
    });
    return response.data;
  },
};
