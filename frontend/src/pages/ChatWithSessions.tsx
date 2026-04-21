import React, { useState, useEffect } from 'react';
import { Plus, Trash2, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { chatApi } from '@/services/chatApi';
import { ChatSession } from '@/types/chat';
import { ChatAgent } from './ChatAgent';
import { cn } from '@/lib/utils';

interface Props { projectId: number; }

const ChatWithSessions: React.FC<Props> = ({ projectId }) => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);

  useEffect(() => { loadSessions(); }, [projectId]);

  const loadSessions = async () => {
    const data = await chatApi.listSessions(projectId);
    setSessions(data);
    if (data.length > 0 && !activeSessionId) setActiveSessionId(data[0].id);
  };

  const handleNew = async () => {
    const session = await chatApi.createSession(projectId, { user_id: 0, title: `会话 ${sessions.length + 1}` });
    await loadSessions();
    setActiveSessionId(session.id);
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('删除此会话？')) return;
    await chatApi.deleteSession(projectId, id);
    if (activeSessionId === id) setActiveSessionId(null);
    await loadSessions();
  };

  return (
    <div className="flex h-[600px] border border-white/10 rounded-lg overflow-hidden">
      <div className="w-48 bg-background border-r border-white/10 flex flex-col">
        <div className="p-3 border-b border-white/10">
          <Button size="sm" onClick={handleNew} className="w-full bg-primary hover:bg-primary/90 text-xs">
            <Plus size={12} className="mr-1" /> 新建会话
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {sessions.map(s => (
            <div
              key={s.id}
              className={cn(
                'flex items-center gap-2 px-3 py-2 cursor-pointer text-xs group',
                activeSessionId === s.id
                  ? 'bg-primary/10 text-primary border-l-2 border-primary'
                  : 'text-slate-400 hover:bg-white/5 hover:text-white'
              )}
              onClick={() => setActiveSessionId(s.id)}
            >
              <MessageSquare size={12} className="shrink-0" />
              <span className="flex-1 truncate">{s.title || `会话 ${s.id}`}</span>
              <button
                onClick={e => { e.stopPropagation(); handleDelete(s.id); }}
                className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300"
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
          {sessions.length === 0 && (
            <p className="text-slate-500 text-xs text-center p-4">点击上方按钮创建会话</p>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        {activeSessionId ? (
          <ChatAgent projectId={projectId} sessionId={activeSessionId} />
        ) : (
          <div className="flex items-center justify-center h-full text-slate-500 text-sm">
            选择或创建一个会话
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatWithSessions;
