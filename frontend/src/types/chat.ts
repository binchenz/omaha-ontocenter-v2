/**
 * Chat session and message types.
 */

export interface ChatSession {
  id: number;
  project_id: number;
  user_id: number;
  title: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface ChatMessage {
  id: number;
  session_id: number;
  role: 'user' | 'assistant' | 'tool';
  content: string;
  tool_calls: string | null;
  chart_config: string | null;
  created_at: string;
}

export interface SendMessageRequest {
  message: string;
}

export interface SendMessageResponse {
  message: string;
  data_table: Record<string, any>[] | null;
  chart_config: Record<string, any> | null;
  sql: string | null;
}

export interface ChatSessionCreate {
  user_id: number;
  title?: string;
}
