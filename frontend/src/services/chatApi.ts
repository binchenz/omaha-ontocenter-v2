/**
 * Chat API service.
 */
import api from './api';
import type {
  ChatSession,
  ChatSessionCreate,
  SendMessageRequest,
  SendMessageResponse,
} from '@/types/chat';

export const chatApi = {
  async createSession(projectId: number, data: ChatSessionCreate): Promise<ChatSession> {
    const response = await api.post(`/chat/${projectId}/sessions`, data);
    return response.data;
  },

  async listSessions(projectId: number): Promise<ChatSession[]> {
    const response = await api.get(`/chat/${projectId}/sessions`);
    return response.data;
  },

  async sendMessage(
    projectId: number,
    sessionId: number,
    data: SendMessageRequest
  ): Promise<SendMessageResponse> {
    const response = await api.post(`/chat/${projectId}/sessions/${sessionId}/message`, data);
    return response.data;
  },

  async deleteSession(projectId: number, sessionId: number): Promise<void> {
    await api.delete(`/chat/${projectId}/sessions/${sessionId}`);
  },

  async uploadFile(
    projectId: number,
    sessionId: number,
    file: File
  ): Promise<{
    success: boolean;
    file_path: string;
    filename: string;
    table_name?: string;
    row_count?: number;
    column_count?: number;
    columns?: { name: string; type: string }[];
    quality_report?: { score: number; issues: any[] };
    error?: string;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post(
      `/chat/${projectId}/sessions/${sessionId}/upload`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  },
};
