import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { chatApi } from '@/services/chatApi';
import { ChatMessage } from '@/components/chat/ChatMessage';
import { DataTable } from '@/components/chat/DataTable';
import { ChartRenderer } from '@/components/chat/ChartRenderer';
import type { ChatMessage as ChatMessageType, SendMessageResponse } from '@/types/chat';

interface Props {
  projectId: number;
  sessionId: number;
}

export const ChatAgent: React.FC<Props> = ({ projectId, sessionId }) => {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResponse, setLastResponse] = useState<SendMessageResponse | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    setMessages([]);
    setLastResponse(null);
    setError(null);
  }, [sessionId]);

  const handleSend = useCallback(async (overrideMessage?: string) => {
    const userMessage = overrideMessage ?? input.trim();
    if (!userMessage || loading) return;
    if (!overrideMessage) setInput('');
    setLoading(true);
    setError(null);

    const tempUserMsg: ChatMessageType = {
      id: Date.now(), session_id: sessionId, role: 'user',
      content: userMessage, tool_calls: null, chart_config: null,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      const response = await chatApi.sendMessage(projectId, sessionId, { message: userMessage });
      const assistantMsg: ChatMessageType = {
        id: Date.now() + 1, session_id: sessionId, role: 'assistant',
        content: response.message, tool_calls: null,
        chart_config: response.chart_config ? JSON.stringify(response.chart_config) : null,
        structured: response.structured,
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, assistantMsg]);
      setLastResponse(response);
    } catch {
      setError('发送消息失败');
    } finally {
      setLoading(false);
    }
  }, [input, loading, projectId, sessionId]);

  const handleOptionSelect = useCallback(async (value: string) => {
    await handleSend(value);
  }, [handleSend]);

  const handleFileUpload = useCallback(async (files: FileList) => {
    if (!sessionId) return;
    for (const file of Array.from(files)) {
      try {
        const result = await chatApi.uploadFile(projectId, sessionId, file);
        if (result.success) {
          await handleSend(`我上传了文件：${result.filename}`);
        }
      } catch (err) {
        console.error('Upload failed:', err);
      }
    }
  }, [projectId, sessionId, handleSend]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 && (
          <p className="text-slate-500 text-sm text-center mt-8">输入消息开始对话</p>
        )}
        {messages.map(msg => (
          <ChatMessage
            key={msg.id}
            message={msg}
            onOptionSelect={handleOptionSelect}
            onFileUpload={handleFileUpload}
          />
        ))}
        {loading && (
          <div className="flex justify-center mt-2">
            <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {lastResponse?.data_table && (
        <div className="px-4 pb-2">
          <DataTable data={lastResponse.data_table} />
        </div>
      )}

      {lastResponse?.chart_config && (
        <div className="px-4 pb-2">
          <ChartRenderer config={lastResponse.chart_config} />
        </div>
      )}

      {lastResponse?.sql && (
        <div className="mx-4 mb-2 px-3 py-2 bg-white/5 border border-white/10 rounded">
          <p className="text-slate-400 text-xs mb-1">生成的 SQL</p>
          <pre className="text-slate-300 text-xs font-mono overflow-auto">{lastResponse.sql}</pre>
        </div>
      )}

      {error && (
        <div className="mx-4 mb-2 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded text-red-400 text-sm flex items-center justify-between">
          {error}
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300 ml-2">×</button>
        </div>
      )}

      <div className="border-t border-white/10 p-3 flex gap-2">
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入消息..."
          disabled={loading}
          rows={1}
          className="flex-1 resize-none rounded-md border border-white/10 bg-background px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
        />
        <Button onClick={() => handleSend()} disabled={loading || !input.trim()} className="bg-primary hover:bg-primary/90 shrink-0">
          <Send size={16} />
        </Button>
      </div>
    </div>
  );
};
