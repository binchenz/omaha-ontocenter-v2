import React from 'react';
import { ChatMessage as ChatMessageType } from '@/types/chat';
import { cn } from '@/lib/utils';
import { StructuredMessage } from './StructuredMessage';

interface ChatMessageProps {
  message: ChatMessageType;
  onOptionSelect?: (value: string) => void;
  onFileUpload?: (files: FileList) => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  onOptionSelect,
  onFileUpload,
}) => {
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
        {message.structured && message.structured.length > 0 ? (
          <StructuredMessage
            items={message.structured}
            onOptionSelect={onOptionSelect}
            onFileUpload={onFileUpload}
          />
        ) : (
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        )}
        <span className="block text-[10px] mt-1 opacity-50">
          {new Date(message.created_at).toLocaleTimeString()}
        </span>
      </div>
    </div>
  );
};
