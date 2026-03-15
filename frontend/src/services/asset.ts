import api from './api';
import { Asset } from '../types';

export type { Asset };

export type SaveAssetRequest = Pick<Asset, 'name' | 'description' | 'query_config' | 'row_count'>;

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
