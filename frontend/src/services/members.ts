import api from './api';

export interface ProjectMember {
  user_id: number;
  username: string;
  email: string;
  role: string;
  joined_at: string | null;
}

export const membersService = {
  list: async (projectId: number): Promise<ProjectMember[]> => {
    const res = await api.get(`/projects/${projectId}/members`);
    return res.data.members;
  },

  add: async (projectId: number, username: string, role: string): Promise<ProjectMember> => {
    const res = await api.post(`/projects/${projectId}/members`, { username, role });
    return res.data;
  },

  updateRole: async (projectId: number, userId: number, role: string): Promise<void> => {
    await api.put(`/projects/${projectId}/members/${userId}`, { role });
  },

  remove: async (projectId: number, userId: number): Promise<void> => {
    await api.delete(`/projects/${projectId}/members/${userId}`);
  },
};
