import api from './api';

export interface Asset {
  id: number;
  project_id: number;
  name: string;
  description?: string;
  query_config: {
    object_type: string;
    selected_columns?: string[];
    filters?: Array<{ field: string; operator: string; value: string }>;
    joins?: Array<{ relationship_name: string; join_type: string }>;
  };
  row_count?: number;
  created_by: number;
  created_at: string;
  updated_at?: string;
}

export interface SaveAssetRequest {
  name: string;
  description?: string;
  query_config: {
    object_type: string;
    selected_columns?: string[];
    filters?: Array<{ field: string; operator: string; value: string }>;
    joins?: Array<{ relationship_name: string; join_type: string }>;
  };
  row_count?: number;
}

export interface AssetLineage {
  upstream: Array<{
    urn: string;
    type: string;
    name: string;
  }>;
  downstream: Array<{
    urn: string;
    type: string;
    name: string;
  }>;
}

export const assetService = {
  async saveAsset(projectId: number, data: SaveAssetRequest): Promise<Asset> {
    const response = await api.post(`/assets/${projectId}`, data);
    return response.data;
  },

  async listAssets(
    projectId: number,
    skip: number = 0,
    limit: number = 50
  ): Promise<Asset[]> {
    const response = await api.get(`/assets/${projectId}`, {
      params: { skip, limit },
    });
    return response.data;
  },

  async getAsset(projectId: number, assetId: number): Promise<Asset> {
    const response = await api.get(`/assets/${projectId}/${assetId}`);
    return response.data;
  },

  async deleteAsset(projectId: number, assetId: number): Promise<void> {
    await api.delete(`/assets/${projectId}/${assetId}`);
  },

  async getLineage(projectId: number, assetId: number): Promise<AssetLineage> {
    const response = await api.get(`/assets/${projectId}/${assetId}/lineage`);
    return response.data;
  },
};
