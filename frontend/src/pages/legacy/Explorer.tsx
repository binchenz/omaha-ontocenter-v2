import React from 'react';
import RequireProject from '@/components/shared/RequireProject';
import ObjectExplorer from './ObjectExplorer';

const Explorer: React.FC = () => (
  <RequireProject emptyMessage="请在顶部创建一个项目后开始探索数据">
    {(projectId) => <ObjectExplorer projectId={projectId} />}
  </RequireProject>
);

export default Explorer;
