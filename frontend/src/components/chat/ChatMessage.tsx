import React from 'react';
import { ChatMessage as ChatMessageType } from '@/types/chat';
import { cn } from '@/lib/utils';

interface ChatMessageProps {
  message: ChatMessageType;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div className={cn('flex mb-3', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[70%] rounded-lg px-4 py-2.5',
          isUser
            ? 'bg-primary text-white'
            : 'bg-white/5 text-slate-200 border border-white/10'
        )}
      >
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        <span className="block text-[10px] mt-1 opacity-50">
          {new Date(message.created_at).toLocaleTimeString()}
        </span>
      </div>
    </div>
  );
};
