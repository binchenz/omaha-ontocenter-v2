import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Copy, Key } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { apiKeyService, ApiKey, ApiKeyCreated } from '../services/apiKeyService';

interface ApiKeyManagerProps {
  projectId: number;
}

const ApiKeyManager: React.FC<ApiKeyManagerProps> = ({ projectId }) => {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [createdKey, setCreatedKey] = useState<ApiKeyCreated | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => { loadKeys(); }, [projectId]);

  const loadKeys = async () => {
    setLoading(true);
    try {
      const data = await apiKeyService.list(projectId);
      setKeys(data);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newKeyName.trim()) return;
    setCreating(true);
    try {
      const created = await apiKeyService.create(projectId, newKeyName.trim());
      setCreatedKey(created);
      setNewKeyName('');
      loadKeys();
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (keyId: number) => {
    if (!window.confirm('撤销此 API Key？')) return;
    await apiKeyService.revoke(projectId, keyId);
    loadKeys();
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const closeModal = () => { setCreateModalOpen(false); setCreatedKey(null); setNewKeyName(''); };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <Button size="sm" onClick={() => setCreateModalOpen(true)} className="bg-primary hover:bg-primary/90">
          <Plus size={14} className="mr-2" /> 生成 API Key
        </Button>
      </div>

      <div className="rounded-md border border-white/10 bg-background p-3 text-xs text-slate-400 space-y-1">
        <p>API Key 用于连接外部 Agent（如 Claude Desktop）。在 <code className="font-mono text-slate-300">claude_desktop_config.json</code> 中添加：</p>
        <pre className="bg-surface rounded p-2 text-slate-300 overflow-auto">{`{
  "mcpServers": {
    "omaha": {
      "command": "/opt/homebrew/bin/python3.11",
      "args": ["-m", "app.mcp.server"],
      "env": { "OMAHA_API_KEY": "your_key_here" }
    }
  }
}`}</pre>
      </div>

      {loading ? (
        <p className="text-slate-400 text-sm">Loading...</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="border-white/10">
              <TableHead className="text-slate-400">名称</TableHead>
              <TableHead className="text-slate-400">前缀</TableHead>
              <TableHead className="text-slate-400">状态</TableHead>
              <TableHead className="text-slate-400">创建时间</TableHead>
              <TableHead className="text-slate-400"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {keys.map(k => (
              <TableRow key={k.id} className="border-white/10 hover:bg-white/5">
                <TableCell className="text-white">{k.name}</TableCell>
                <TableCell className="text-slate-400 font-mono text-xs">omaha_*_{k.key_prefix}...</TableCell>
                <TableCell>
                  <Badge variant={k.is_active ? 'default' : 'destructive'}>
                    {k.is_active ? '有效' : '已撤销'}
                  </Badge>
                </TableCell>
                <TableCell className="text-slate-400 text-xs">{new Date(k.created_at).toLocaleString('zh-CN')}</TableCell>
                <TableCell>
                  {k.is_active && (
                    <Button variant="ghost" size="sm" onClick={() => handleRevoke(k.id)} className="text-red-400 hover:text-red-300">
                      <Trash2 size={14} />
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <Dialog open={createModalOpen} onOpenChange={closeModal}>
        <DialogContent className="bg-surface border-white/10 text-white">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2"><Key size={16} /> 生成新 API Key</DialogTitle>
          </DialogHeader>
          {!createdKey ? (
            <div className="space-y-4">
              <div className="space-y-1">
                <Label className="text-slate-300">Key 名称（如 "claude-desktop"）</Label>
                <Input value={newKeyName} onChange={e => setNewKeyName(e.target.value)}
                  placeholder="Key 名称" onKeyDown={e => e.key === 'Enter' && handleCreate()}
                  className="bg-background border-white/10 text-white" />
              </div>
              <Button onClick={handleCreate} disabled={creating || !newKeyName.trim()} className="bg-primary hover:bg-primary/90">
                {creating ? '生成中...' : '生成'}
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-yellow-400 text-sm">请立即复制此 Key，关闭后将无法再次查看！</p>
              <div className="flex gap-2 items-center">
                <code className="flex-1 text-xs font-mono bg-background border border-white/10 rounded px-3 py-2 text-slate-300 break-all">
                  {createdKey.key}
                </code>
                <Button variant="ghost" size="sm" onClick={() => copyToClipboard(createdKey.key)} className="text-primary">
                  <Copy size={14} />
                </Button>
              </div>
              <Button onClick={closeModal} variant="ghost" className="text-slate-300">我已保存，关闭</Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ApiKeyManager;
