import React, { useState, useEffect } from 'react';
import { UserPlus, Trash2, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { membersService, ProjectMember } from '@/services/members';

const ROLES = ['owner', 'editor', 'viewer'];

interface Props { projectId: number; }

const MembersManager: React.FC<Props> = ({ projectId }) => {
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [loading, setLoading] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [username, setUsername] = useState('');
  const [role, setRole] = useState('viewer');
  const [error, setError] = useState('');

  useEffect(() => { loadMembers(); }, [projectId]);

  const loadMembers = async () => {
    setLoading(true);
    try { setMembers(await membersService.list(projectId)); }
    catch { setError('加载成员失败'); }
    finally { setLoading(false); }
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await membersService.add(projectId, username, role);
      setAddOpen(false);
      setUsername('');
      setRole('viewer');
      loadMembers();
    } catch (err: any) {
      setError(err.response?.data?.detail || '添加失败');
    }
  };

  const handleRoleChange = async (userId: number, newRole: string) => {
    try {
      await membersService.updateRole(projectId, userId, newRole);
      loadMembers();
    } catch { setError('更新角色失败'); }
  };

  const handleRemove = async (userId: number, uname: string) => {
    if (!window.confirm(`确认移除成员 ${uname}？`)) return;
    try {
      await membersService.remove(projectId, userId);
      loadMembers();
    } catch { setError('移除失败'); }
  };

  const roleColor = (r: string) =>
    r === 'owner' ? 'text-yellow-400' : r === 'editor' ? 'text-blue-400' : 'text-slate-400';

  return (
    <Card className="bg-surface border-white/10">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-white flex items-center gap-2">
          <Shield size={16} /> 成员管理
        </CardTitle>
        <Button size="sm" onClick={() => setAddOpen(true)} className="bg-primary hover:bg-primary/90">
          <UserPlus size={14} className="mr-2" /> 邀请成员
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
                <TableHead className="text-slate-400">用户名</TableHead>
                <TableHead className="text-slate-400">邮箱</TableHead>
                <TableHead className="text-slate-400">角色</TableHead>
                <TableHead className="text-slate-400">加入时间</TableHead>
                <TableHead className="text-slate-400"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {members.length === 0 && (
                <TableRow><TableCell colSpan={5} className="text-slate-400 text-center">暂无成员</TableCell></TableRow>
              )}
              {members.map(m => (
                <TableRow key={m.user_id} className="border-white/10 hover:bg-white/5">
                  <TableCell className="text-white font-mono text-sm">{m.username}</TableCell>
                  <TableCell className="text-slate-400 text-sm">{m.email}</TableCell>
                  <TableCell>
                    <select
                      value={m.role}
                      onChange={e => handleRoleChange(m.user_id, e.target.value)}
                      className={`rounded border border-white/10 bg-background px-2 py-1 text-xs ${roleColor(m.role)}`}
                    >
                      {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </TableCell>
                  <TableCell className="text-slate-400 text-xs font-mono">
                    {m.joined_at ? new Date(m.joined_at).toLocaleDateString() : '—'}
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" onClick={() => handleRemove(m.user_id, m.username)}
                      className="text-red-400 hover:text-red-300">
                      <Trash2 size={14} />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="bg-surface border-white/10 text-white">
          <DialogHeader><DialogTitle>邀请成员</DialogTitle></DialogHeader>
          <form onSubmit={handleAdd} className="space-y-4">
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <div className="space-y-1">
              <Label className="text-slate-300">用户名 *</Label>
              <Input value={username} onChange={e => setUsername(e.target.value)} required
                placeholder="输入用户名" className="bg-background border-white/10 text-white" />
            </div>
            <div className="space-y-1">
              <Label className="text-slate-300">角色</Label>
              <select value={role} onChange={e => setRole(e.target.value)}
                className="w-full rounded border border-white/10 bg-background px-3 py-2 text-sm text-white">
                {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div className="flex gap-2 justify-end">
              <Button type="button" variant="ghost" onClick={() => { setAddOpen(false); setError(''); }}>取消</Button>
              <Button type="submit" className="bg-primary hover:bg-primary/90">邀请</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </Card>
  );
};

export default MembersManager;
