import React from 'react';
import RequireProject from '@/components/RequireProject';
import ChatWithSessions from './ChatWithSessions';

const ChatPage: React.FC = () => (
  <RequireProject emptyMessage="请在顶部创建一个项目后开始使用 AI 助手">
    {(projectId) => <ChatWithSessions projectId={projectId} />}
  </RequireProject>
);

export default ChatPage;
