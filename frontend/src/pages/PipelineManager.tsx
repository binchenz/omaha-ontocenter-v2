import React, { useState, useEffect } from 'react';
import { Plus, Play, Pause, Trash2, CheckCircle, XCircle, Loader2, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { pipelineService, PipelineData, PipelineCreate } from '@/services/pipeline';

const STATUS_ICON: Record<string, React.ReactNode> = {
  success: <CheckCircle size={12} className="text-green-400" />,
  error: <XCircle size={12} className="text-red-400" />,
  running: <Loader2 size={12} className="text-blue-400 animate-spin" />,
};

interface Props { projectId: number; }

const PipelineManager: React.FC<Props> = ({ projectId }) => {
  const [pipelines, setPipelines] = useState<PipelineData[]>([]);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState<number | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState<PipelineCreate>({
    name: '', datasource_id: '', object_type: '', target_table: '', schedule: '0 * * * *',
  });

  useEffect(() => { loadPipelines(); }, [projectId]);

  const loadPipelines = async () => {
    setLoading(true);
    try { setPipelines(await pipelineService.list(projectId)); }
    catch { setError('加载 Pipeline 失败'); }
    finally { setLoading(false); }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await pipelineService.create(projectId, form);
      setCreateOpen(false);
      setForm({ name: '', datasource_id: '', object_type: '', target_table: '', schedule: '0 * * * *' });
      loadPipelines();
    } catch (err: any) {
      setError(err.response?.data?.detail || '创建失败');
    }
  };

  const handleRun = async (p: PipelineData) => {
    setRunning(p.id);
    try {
      const result = await pipelineService.run(projectId, p.id);
      if (!result.success) setError(`运行失败: ${result.error}`);
      loadPipelines();
    } finally {
      setRunning(null);
    }
  };

  const handleToggle = async (p: PipelineData) => {
    await pipelineService.update(projectId, p.id, { status: p.status === 'active' ? 'paused' : 'active' });
    loadPipelines();
  };

  const handleDelete = async (p: PipelineData) => {
    if (!window.confirm(`确认删除 Pipeline "${p.name}"？`)) return;
    await pipelineService.delete(projectId, p.id);
    loadPipelines();
  };

  const statusBadge = (p: PipelineData) => (
    <span className={`text-xs px-1.5 py-0.5 rounded font-mono ${p.status === 'active' ? 'bg-green-500/10 text-green-400' : 'bg-slate-500/10 text-slate-400'}`}>
      {p.status}
    </span>
  );

  return (
    <Card className="bg-surface border-white/10">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-white flex items-center gap-2">
          <Clock size={16} /> 数据 Pipeline
        </CardTitle>
        <Button size="sm" onClick={() => setCreateOpen(true)} className="bg-primary hover:bg-primary/90">
          <Plus size={14} className="mr-2" /> 新建
        </Button>
      </CardHeader>
      <CardContent>
        {error && <p className="text-red-400 text-sm mb-3">{error}</p>}
        {loading ? (
          <p className="text-slate-400 text-sm">加载中...</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="border-white/10">
                {['名称', '对象', '目标表', '调度', '状态', '上次运行', ''].map(h => (
                  <TableHead key={h} className="text-slate-400 text-xs">{h}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {pipelines.length === 0 && (
                <TableRow><TableCell colSpan={7} className="text-slate-400 text-center text-sm">暂无 Pipeline</TableCell></TableRow>
              )}
              {pipelines.map(p => (
                <TableRow key={p.id} className="border-white/10 hover:bg-white/5">
                  <TableCell className="text-white text-sm">{p.name}</TableCell>
                  <TableCell className="text-slate-400 text-xs font-mono">{p.object_type}</TableCell>
                  <TableCell className="text-slate-400 text-xs font-mono">{p.target_table}</TableCell>
                  <TableCell className="text-slate-400 text-xs font-mono">{p.schedule}</TableCell>
                  <TableCell>{statusBadge(p)}</TableCell>
                  <TableCell className="text-xs">
                    <div className="flex items-center gap-1">
                      {p.last_run_status && STATUS_ICON[p.last_run_status]}
                      <span className="text-slate-400 font-mono">
                        {p.last_run_at ? new Date(p.last_run_at).toLocaleString() : '—'}
                      </span>
                      {p.last_run_rows != null && (
                        <span className="text-slate-500">({p.last_run_rows} 行)</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="sm" onClick={() => handleRun(p)}
                        disabled={running === p.id} className="text-primary h-7 px-2">
                        {running === p.id ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleToggle(p)}
                        className="text-slate-400 h-7 px-2">
                        <Pause size={12} />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(p)}
                        className="text-red-400 hover:text-red-300 h-7 px-2">
                        <Trash2 size={12} />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="bg-surface border-white/10 text-white">
          <DialogHeader><DialogTitle>新建 Pipeline</DialogTitle></DialogHeader>
          <form onSubmit={handleCreate} className="space-y-3">
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <div className="grid grid-cols-2 gap-3">
              {([
                ['名称 *', 'name', '如: 每日股票同步'],
                ['数据源 ID *', 'datasource_id', '如: tushare_pro'],
                ['对象类型 *', 'object_type', '如: Stock'],
                ['目标表名 *', 'target_table', '如: synced_stocks'],
                ['调度 (Cron)', 'schedule', '如: 0 * * * *'],
              ] as const).map(([label, field, placeholder]) => (
                <div key={field} className="space-y-1">
                  <Label className="text-slate-300 text-xs">{label}</Label>
                  <Input
                    value={(form as any)[field]}
                    onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
                    placeholder={placeholder}
                    required={field !== 'schedule'}
                    className="bg-background border-white/10 text-white text-xs h-7"
                  />
                </div>
              ))}
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <Button type="button" variant="ghost" onClick={() => { setCreateOpen(false); setError(''); }}>取消</Button>
              <Button type="submit" className="bg-primary hover:bg-primary/90">创建</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </Card>
  );
};

export default PipelineManager;
