import api from './api';
import { Project } from '../types';

export const projectService = {
  async list(): Promise<Project[]> {
    const response = await api.get<Project[]>('/projects/');
    return response.data;
  },

  async get(id: number): Promise<Project> {
    const response = await api.get<Project>(`/projects/${id}`);
    return response.data;
  },

  async create(data: {
    name: string;
    description?: string;
    datahub_dataset_urn?: string;
    omaha_config?: string;
  }): Promise<Project> {
    const response = await api.post<Project>('/projects/', data);
    return response.data;
  },

  async update(
    id: number,
    data: {
      name?: string;
      description?: string;
      datahub_dataset_urn?: string;
      omaha_config?: string;
    }
  ): Promise<Project> {
    const response = await api.put<Project>(`/projects/${id}`, data);
    return response.data;
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/projects/${id}`);
  },
};
