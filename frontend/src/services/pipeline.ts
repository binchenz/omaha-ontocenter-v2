import api from './api';

export interface PipelineData {
  id: number;
  name: string;
  description: string | null;
  datasource_id: string;
  object_type: string;
  filters: any[];
  target_table: string;
  schedule: string;
  status: string;
  last_run_at: string | null;
  last_run_status: string | null;
  last_run_rows: number | null;
  last_error: string | null;
  created_at: string | null;
}

export interface PipelineCreate {
  name: string;
  description?: string;
  datasource_id: string;
  object_type: string;
  filters?: any[];
  target_table: string;
  schedule?: string;
}

export interface PipelineRunData {
  id: number;
  status: string;
  rows_synced: number | null;
  duration_seconds: number | null;
  error_message: string | null;
  triggered_by: string;
  created_at: string | null;
}

export const pipelineService = {
  list: async (projectId: number): Promise<PipelineData[]> => {
    const res = await api.get(`/projects/${projectId}/pipelines`);
    return res.data.pipelines;
  },

  create: async (projectId: number, data: PipelineCreate): Promise<PipelineData> => {
    const res = await api.post(`/projects/${projectId}/pipelines`, data);
    return res.data;
  },

  update: async (projectId: number, pipelineId: number, data: Partial<PipelineCreate & { status: string }>): Promise<PipelineData> => {
    const res = await api.put(`/projects/${projectId}/pipelines/${pipelineId}`, data);
    return res.data;
  },

  delete: async (projectId: number, pipelineId: number): Promise<void> => {
    await api.delete(`/projects/${projectId}/pipelines/${pipelineId}`);
  },

  run: async (projectId: number, pipelineId: number): Promise<{ success: boolean; rows?: number; error?: string }> => {
    const res = await api.post(`/projects/${projectId}/pipelines/${pipelineId}/run`);
    return res.data;
  },

  listRuns: async (projectId: number, pipelineId: number, limit = 20): Promise<PipelineRunData[]> => {
    const res = await api.get(`/projects/${projectId}/pipelines/${pipelineId}/runs`, { params: { limit } });
    return res.data.runs;
  },
};
