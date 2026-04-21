import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Star } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { watchlistService, WatchlistItem } from '@/services/watchlist';

const Watchlist: React.FC = () => {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [tsCode, setTsCode] = useState('');
  const [note, setNote] = useState('');
  const [error, setError] = useState('');

  useEffect(() => { loadItems(); }, []);

  const loadItems = async () => {
    setLoading(true);
    setError('');
    try {
      setItems(await watchlistService.list());
    } catch {
      setError('加载自选股失败');
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    await watchlistService.add(tsCode, note || undefined);
    setAddOpen(false);
    setTsCode(''); setNote('');
    loadItems();
  };

  const handleRemove = async (id: number) => {
    if (!window.confirm('确认从自选股中移除？')) return;
    await watchlistService.remove(id);
    loadItems();
  };

  return (
    <Card className="bg-surface border-white/10">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-white flex items-center gap-2">
          <Star size={18} /> 自选股
        </CardTitle>
        <Button onClick={() => setAddOpen(true)} size="sm" className="bg-primary hover:bg-primary/90">
          <Plus size={16} className="mr-2" /> 添加股票
        </Button>
      </CardHeader>
      <CardContent>
        {error && <p className="text-red-400 text-sm mb-4">{error}</p>}
        {loading ? (
          <p className="text-slate-400 text-sm">加载中...</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="border-white/10">
                <TableHead className="text-slate-400">代码</TableHead>
                <TableHead className="text-slate-400">备注</TableHead>
                <TableHead className="text-slate-400">添加时间</TableHead>
                <TableHead className="text-slate-400"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.length === 0 && (
                <TableRow><TableCell colSpan={4} className="text-slate-400 text-center">暂无自选股</TableCell></TableRow>
              )}
              {items.map(item => (
                <TableRow key={item.id} className="border-white/10 hover:bg-white/5">
                  <TableCell className="text-white font-mono">{item.ts_code}</TableCell>
                  <TableCell className="text-slate-400">{item.note || '—'}</TableCell>
                  <TableCell className="text-slate-400 text-xs font-mono">
                    {new Date(item.added_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" onClick={() => handleRemove(item.id)}
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
          <DialogHeader><DialogTitle>添加自选股</DialogTitle></DialogHeader>
          <form onSubmit={handleAdd} className="space-y-4">
            <div className="space-y-1">
              <Label className="text-slate-300">股票代码 *</Label>
              <Input value={tsCode} onChange={e => setTsCode(e.target.value)} required
                placeholder="000001.SZ" className="bg-background border-white/10 text-white font-mono" />
            </div>
            <div className="space-y-1">
              <Label className="text-slate-300">备注</Label>
              <Input value={note} onChange={e => setNote(e.target.value)}
                placeholder="可选备注" className="bg-background border-white/10 text-white" />
            </div>
            <div className="flex gap-2 justify-end">
              <Button type="button" variant="ghost" onClick={() => setAddOpen(false)}>取消</Button>
              <Button type="submit" className="bg-primary hover:bg-primary/90">添加</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </Card>
  );
};

export default Watchlist;
