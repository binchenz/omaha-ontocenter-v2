/**
 * Chat API service.
 */
import axios from 'axios';
import type {
  ChatSession,
  ChatSessionCreate,
  SendMessageRequest,
  SendMessageResponse,
} from '@/types/chat';

const API_BASE = '/api/v1';

export const chatApi = {
  /**
   * Create a new chat session.
   */
  async createSession(
    projectId: number,
    data: ChatSessionCreate
  ): Promise<ChatSession> {
    const response = await axios.post(
      `${API_BASE}/chat/${projectId}/sessions`,
      data
    );
    return response.data;
  },

  /**
   * List all chat sessions for a project.
   */
  async listSessions(projectId: number): Promise<ChatSession[]> {
    const response = await axios.get(`${API_BASE}/chat/${projectId}/sessions`);
    return response.data;
  },

  /**
   * Send a message in a chat session.
   */
  async sendMessage(
    projectId: number,
    sessionId: number,
    data: SendMessageRequest
  ): Promise<SendMessageResponse> {
    const response = await axios.post(
      `${API_BASE}/chat/${projectId}/sessions/${sessionId}/message`,
      data
    );
    return response.data;
  },

  /**
   * Delete a chat session.
   */
  async deleteSession(projectId: number, sessionId: number): Promise<void> {
    await axios.delete(`${API_BASE}/chat/${projectId}/sessions/${sessionId}`);
  },
};
