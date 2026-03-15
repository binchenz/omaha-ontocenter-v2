import api from './api';
import { QueryHistory } from '../types';

export const queryService = {
  async queryObjects(
    projectId: number,
    objectType: string,
    selectedColumns?: string[],
    filters?: Array<{ field: string; operator: string; value: string }>,
    limit: number = 100
  ): Promise<{
    success: boolean;
    data?: any[];
    count?: number;
    error?: string;
  }> {
    const response = await api.post(`/query/${projectId}/query`, {
      object_type: objectType,
      selected_columns: selectedColumns,
      filters,
      limit,
    });
    return response.data;
  },

  async listObjectTypes(projectId: number): Promise<{ objects: string[] }> {
    const response = await api.get(`/query/${projectId}/objects`);
    return response.data;
  },

  async getObjectSchema(
    projectId: number,
    objectType: string
  ): Promise<{
    success: boolean;
    columns?: Array<{ name: string; type: string; description: string }>;
    error?: string;
  }> {
    const response = await api.get(`/query/${projectId}/schema/${objectType}`);
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
