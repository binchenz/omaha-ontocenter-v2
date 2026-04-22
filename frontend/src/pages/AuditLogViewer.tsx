import React, { useState, useEffect } from 'react';
import { ClipboardList } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { auditService, AuditLogEntry } from '@/services/auditLog';

const ACTION_LABELS: Record<string, string> = {
  'query.run': '查询',
  'project.create': '创建项目',
  'config.save': '保存配置',
  'member.add': '添加成员',
  'member.remove': '移除成员',
};

interface Props { projectId: number; }

const AuditLogViewer: React.FC<Props> = ({ projectId }) => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionFilter, setActionFilter] = useState('');

  useEffect(() => { loadLogs(); }, [projectId, actionFilter]);

  const loadLogs = async () => {
    setLoading(true);
    try { setLogs(await auditService.list(projectId, actionFilter || undefined)); }
    finally { setLoading(false); }
  };

  const actionLabel = (action: string) => ACTION_LABELS[action] || action;

  const actionColor = (action: string) => {
    if (action.startsWith('query')) return 'text-blue-400';
    if (action.startsWith('config')) return 'text-yellow-400';
    if (action.startsWith('member')) return 'text-purple-400';
    return 'text-slate-400';
  };

  return (
    <Card className="bg-surface border-white/10">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-white flex items-center gap-2">
          <ClipboardList size={16} /> 审计日志
        </CardTitle>
        <select value={actionFilter} onChange={e => setActionFilter(e.target.value)}
          className="rounded border border-white/10 bg-background px-2 py-1 text-xs text-slate-300">
          <option value="">全部操作</option>
          {Object.entries(ACTION_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-slate-400 text-sm">加载中...</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="border-white/10">
                <TableHead className="text-slate-400">时间</TableHead>
                <TableHead className="text-slate-400">用户</TableHead>
                <TableHead className="text-slate-400">操作</TableHead>
                <TableHead className="text-slate-400">资源</TableHead>
                <TableHead className="text-slate-400">IP</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logs.length === 0 && (
                <TableRow><TableCell colSpan={5} className="text-slate-400 text-center">暂无日志</TableCell></TableRow>
              )}
              {logs.map(log => (
                <TableRow key={log.id} className="border-white/10 hover:bg-white/5">
                  <TableCell className="text-slate-400 text-xs font-mono">
                    {log.created_at ? new Date(log.created_at).toLocaleString() : '—'}
                  </TableCell>
                  <TableCell className="text-white text-sm">{log.username || '—'}</TableCell>
                  <TableCell className={`text-xs font-mono ${actionColor(log.action)}`}>
                    {actionLabel(log.action)}
                  </TableCell>
                  <TableCell className="text-slate-400 text-xs font-mono">
                    {log.resource_type ? `${log.resource_type}/${log.resource_id || ''}` : '—'}
                  </TableCell>
                  <TableCell className="text-slate-500 text-xs font-mono">{log.ip_address || '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
};

export default AuditLogViewer;
