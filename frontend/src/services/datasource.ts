import api from './api';

export interface DatasourceInfo {
  id: string;
  type: string;
  name: string;
}

export interface ColumnInfo {
  name: string;
  type: string;
  nullable: boolean;
}

export const datasourceService = {
  list: async (projectId: number): Promise<DatasourceInfo[]> => {
    const res = await api.get(`/datasources/${projectId}/list`);
    return res.data.datasources;
  },

  testConnection: async (projectId: number, type: string, connection: Record<string, any>): Promise<{ connected: boolean; error?: string }> => {
    const res = await api.post(`/datasources/${projectId}/test`, { type, connection });
    return res.data;
  },

  upload: async (projectId: number, file: File, tableName: string): Promise<{ success: boolean; columns: ColumnInfo[] }> => {
    const form = new FormData();
    form.append('file', file);
    form.append('table_name', tableName);
    const res = await api.post(`/datasources/${projectId}/upload`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
};
