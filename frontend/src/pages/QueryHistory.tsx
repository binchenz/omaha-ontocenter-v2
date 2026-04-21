import React, { useState, useEffect } from 'react';
import { Trash2, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { queryHistoryService, QueryHistoryEntry } from '@/services/queryHistory';
import { useProject } from '@/contexts/ProjectContext';

interface Props { projectId?: number; onRerun?: (entry: QueryHistoryEntry) => void; }

const QueryHistory: React.FC<Props> = ({ projectId: propProjectId, onRerun }) => {
  const projectCtx = useProject();
  const projectId = propProjectId ?? projectCtx.currentProject?.id;
  const [entries, setEntries] = useState<QueryHistoryEntry[]>([]);

  useEffect(() => {
    if (projectId) setEntries(queryHistoryService.list(projectId));
  }, [projectId]);

  const handleClear = () => {
    if (!projectId || !window.confirm('清除所有查询历史？')) return;
    queryHistoryService.clear(projectId);
    setEntries([]);
  };

  if (!projectId) {
    return <div className="text-slate-400 text-sm text-center py-8">请先选择项目</div>;
  }

  const content = (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button variant="ghost" size="sm" onClick={handleClear} className="text-red-400 hover:text-red-300">
          <Trash2 size={14} className="mr-2" /> 清除历史
        </Button>
      </div>
      {entries.length === 0 ? (
        <p className="text-slate-400 text-sm text-center py-8">暂无查询历史</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="border-white/10">
              <TableHead className="text-slate-400">时间</TableHead>
              <TableHead className="text-slate-400">对象类型</TableHead>
              <TableHead className="text-slate-400">过滤条件</TableHead>
              <TableHead className="text-slate-400">结果数</TableHead>
              <TableHead className="text-slate-400"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {entries.map(e => (
              <TableRow key={e.id} className="border-white/10 hover:bg-white/5">
                <TableCell className="text-slate-400 text-xs font-mono">
                  {new Date(e.timestamp).toLocaleString()}
                </TableCell>
                <TableCell className="text-white text-sm">{e.objectType}</TableCell>
                <TableCell className="text-slate-400 text-xs font-mono max-w-xs truncate">
                  {JSON.stringify(e.filters)}
                </TableCell>
                <TableCell className="text-slate-400 text-sm">{e.resultCount}</TableCell>
                <TableCell>
                  {onRerun && (
                    <Button variant="ghost" size="sm" onClick={() => onRerun(e)} className="text-primary">
                      <RotateCcw size={14} />
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );

  if (!propProjectId) {
    return (
      <Card className="bg-surface border-white/10">
        <CardHeader><CardTitle className="text-white text-base">查询历史</CardTitle></CardHeader>
        <CardContent>{content}</CardContent>
      </Card>
    );
  }

  return content;
};

export default QueryHistory;
