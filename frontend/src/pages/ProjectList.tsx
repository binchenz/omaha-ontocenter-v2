import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Pencil, Trash2, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { projectService } from '@/services/project';
import { Project } from '@/types';

const ProjectList: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const navigate = useNavigate();

  useEffect(() => { loadProjects(); }, []);

  const loadProjects = async () => {
    setLoading(true);
    try { setProjects(await projectService.list()); }
    catch { /* error handled silently */ }
    finally { setLoading(false); }
  };

  const openCreate = () => { setEditing(null); setName(''); setDescription(''); setModalOpen(true); };
  const openEdit = (p: Project) => { setEditing(p); setName(p.name); setDescription(p.description || ''); setModalOpen(true); };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Delete this project?')) return;
    await projectService.delete(id);
    loadProjects();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (editing) {
      await projectService.update(editing.id, { name, description });
    } else {
      await projectService.create({ name, description });
    }
    setModalOpen(false);
    loadProjects();
  };

  return (
    <Card className="bg-surface border-white/10">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-white">Projects</CardTitle>
        <Button onClick={openCreate} size="sm" className="bg-primary hover:bg-primary/90">
          <Plus size={16} className="mr-2" /> New Project
        </Button>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-slate-400 text-sm">Loading...</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="border-white/10">
                <TableHead className="text-slate-400">Name</TableHead>
                <TableHead className="text-slate-400">Description</TableHead>
                <TableHead className="text-slate-400">Created</TableHead>
                <TableHead className="text-slate-400">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {projects.map(p => (
                <TableRow key={p.id} className="border-white/10 hover:bg-white/5">
                  <TableCell className="text-white font-medium">{p.name}</TableCell>
                  <TableCell className="text-slate-400">{p.description}</TableCell>
                  <TableCell className="text-slate-400 font-mono text-xs">
                    {new Date(p.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm" onClick={() => navigate(`/projects/${p.id}`)}>
                        <Settings size={14} />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => openEdit(p)}>
                        <Pencil size={14} />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(p.id)}
                        className="text-red-400 hover:text-red-300">
                        <Trash2 size={14} />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="bg-surface border-white/10 text-white">
          <DialogHeader>
            <DialogTitle>{editing ? 'Edit Project' : 'Create Project'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <Label className="text-slate-300">Name *</Label>
              <Input value={name} onChange={e => setName(e.target.value)} required
                className="bg-background border-white/10 text-white" />
            </div>
            <div className="space-y-1">
              <Label className="text-slate-300">Description</Label>
              <textarea value={description} onChange={e => setDescription(e.target.value)}
                rows={3}
                className="w-full rounded-md border border-white/10 bg-background px-3 py-2 text-sm text-white resize-none focus:outline-none focus:ring-2 focus:ring-primary" />
            </div>
            <div className="flex gap-2 justify-end">
              <Button type="button" variant="ghost" onClick={() => setModalOpen(false)}>Cancel</Button>
              <Button type="submit" className="bg-primary hover:bg-primary/90">
                {editing ? 'Update' : 'Create'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </Card>
  );
};

export default ProjectList;
