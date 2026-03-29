import React, { useState, useEffect } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { Search, Plus, Trash2, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { queryService } from '@/services/query';
import { assetService } from '@/services/asset';

interface ObjectExplorerProps {
  projectId?: number;
}

interface Filter { field: string; operator: string; value: string; }
interface Column { name: string; type: string; description: string; }
interface Relationship {
  name: string; description: string; from_object: string; to_object: string;
  type: string; join_condition: { from_field: string; to_field: string }; direction: string;
}
interface JoinConfig { relationship_name: string; join_type: string; relationship: Relationship; }

const OPERATORS = ['=', '>', '<', '>=', '<=', '!=', 'LIKE', 'IN'];

const ObjectExplorer: React.FC<ObjectExplorerProps> = ({ projectId: propProjectId }) => {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const projectId = propProjectId || (id ? parseInt(id) : undefined);

  const [objectTypes, setObjectTypes] = useState<string[]>([]);
  const [selectedType, setSelectedType] = useState<string>('');
  const [allColumns, setAllColumns] = useState<Column[]>([]);
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  const [filters, setFilters] = useState<Filter[]>([]);
  const [availableRelationships, setAvailableRelationships] = useState<Relationship[]>([]);
  const [joins, setJoins] = useState<JoinConfig[]>([]);
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [selectedRelationship, setSelectedRelationship] = useState<string>('');
  const [selectedJoinType, setSelectedJoinType] = useState<string>('LEFT');
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [saveDesc, setSaveDesc] = useState('');

  useEffect(() => { loadObjectTypes(); }, [projectId]);
  useEffect(() => { if (selectedType) { loadObjectSchema(); loadRelationships(); } }, [selectedType]);
  useEffect(() => {
    const state = location.state as { assetConfig?: any; preselect?: string };
    if (state?.assetConfig) {
      const config = state.assetConfig;
      setSelectedType(config.object_type);
      if (config.selected_columns) setSelectedColumns(config.selected_columns);
      if (config.filters) setFilters(config.filters);
      if (config.joins) setJoins(config.joins.map((j: any) => ({ ...j, relationship: {} as Relationship })));
    } else if (state?.preselect) {
      setSelectedType(state.preselect);
    }
  }, [location.state]);

  const loadObjectTypes = async () => {
    if (!projectId) return;
    try {
      const result = await queryService.listObjectTypes(projectId);
      setObjectTypes(result.objects || []);
    } catch {}
  };

  const loadRelationships = async () => {
    if (!projectId || !selectedType) return;
    try {
      const result = await queryService.getRelationships(projectId, selectedType);
      setAvailableRelationships(result.relationships || []);
    } catch {}
  };

  const loadObjectSchema = async () => {
    if (!projectId || !selectedType) return;
    try {
      const result = await queryService.getObjectSchema(projectId, selectedType);
      if (result.success && result.columns) {
        setAllColumns(result.columns);
        setSelectedColumns(result.columns.map((col: Column) => col.name));
      }
    } catch {}
  };

  const getValidFilters = () => filters.filter(f => f.field && f.operator && f.value);
  const getJoinPayload = () => joins.length > 0
    ? joins.map(j => ({ relationship_name: j.relationship_name, join_type: j.join_type }))
    : undefined;

  const handleQuery = async () => {
    if (!projectId || !selectedType || selectedColumns.length === 0) return;
    setLoading(true);
    try {
      const result = await queryService.queryObjects(projectId, selectedType, selectedColumns, getValidFilters(), getJoinPayload(), 100);
      if (result.success && result.data) setData(result.data);
    } finally {
      setLoading(false);
    }
  };

  const addFilter = () => setFilters(f => [...f, { field: '', operator: '=', value: '' }]);
  const removeFilter = (i: number) => setFilters(f => f.filter((_, idx) => idx !== i));
  const updateFilter = (i: number, key: keyof Filter, value: string) =>
    setFilters(f => f.map((item, idx) => idx === i ? { ...item, [key]: value } : item));

  const confirmJoin = () => {
    if (!selectedRelationship) return;
    const relationship = availableRelationships.find(r => r.name === selectedRelationship);
    if (!relationship) return;
    setJoins(j => [...j, { relationship_name: selectedRelationship, join_type: selectedJoinType, relationship }]);
    setShowJoinModal(false);
  };

  const handleSaveAsset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId || !selectedType || !saveName) return;
    await assetService.saveAsset(projectId, {
      name: saveName, description: saveDesc,
      query_config: {
        object_type: selectedType, selected_columns: selectedColumns,
        filters: getValidFilters(), joins: joins.map(j => ({ relationship_name: j.relationship_name, join_type: j.join_type })),
      },
      row_count: data.length,
    });
    setShowSaveModal(false); setSaveName(''); setSaveDesc('');
  };

  const columns = data.length > 0 ? Object.keys(data[0]) : selectedColumns;

  if (objectTypes.length === 0) {
    return (
      <Card className="bg-surface border-white/10">
        <CardContent className="py-12 text-center text-slate-400 text-sm">
          Object Explorer will be available after configuration is saved.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card className="bg-surface border-white/10">
        <CardHeader><CardTitle className="text-white text-base">Object Explorer</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-3">
            <select value={selectedType} onChange={e => setSelectedType(e.target.value)}
              className="flex-1 rounded-md border border-white/10 bg-background px-3 py-2 text-sm text-white">
              <option value="">Select object type</option>
              {objectTypes.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <Button onClick={handleQuery} disabled={!selectedType || selectedColumns.length === 0 || loading}
              className="bg-primary hover:bg-primary/90">
              <Search size={14} className="mr-2" /> {loading ? 'Querying...' : 'Query'}
            </Button>
            <Button variant="ghost" onClick={() => setShowSaveModal(true)}
              disabled={!selectedType || data.length === 0} className="text-slate-400">
              <Save size={14} className="mr-2" /> Save Asset
            </Button>
          </div>

          {selectedType && (
            <>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <Label className="text-slate-300 text-xs">Columns</Label>
                  <div className="flex gap-2">
                    <Button variant="ghost" size="sm" className="text-xs h-6 text-primary"
                      onClick={() => setSelectedColumns(allColumns.map(c => c.name))}>All</Button>
                    <Button variant="ghost" size="sm" className="text-xs h-6 text-slate-400"
                      onClick={() => setSelectedColumns([])}>None</Button>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  {allColumns.map(col => (
                    <label key={col.name} className="flex items-center gap-1 text-xs text-slate-300 cursor-pointer">
                      <input type="checkbox" checked={selectedColumns.includes(col.name)}
                        onChange={e => setSelectedColumns(prev =>
                          e.target.checked ? [...prev, col.name] : prev.filter(c => c !== col.name)
                        )} />
                      {col.name}
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <Label className="text-slate-300 text-xs">Joins</Label>
                  <Button variant="ghost" size="sm" className="text-xs h-6 text-primary"
                    onClick={() => setShowJoinModal(true)} disabled={availableRelationships.length === 0}>
                    <Plus size={12} className="mr-1" /> Add JOIN
                  </Button>
                </div>
                {joins.map((j, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-slate-400 mb-1">
                    <span className="text-slate-300">{j.relationship.to_object}</span>
                    <span>{j.join_type} JOIN</span>
                    <Button variant="ghost" size="sm" className="h-5 text-red-400 ml-auto"
                      onClick={() => setJoins(jj => jj.filter((_, idx) => idx !== i))}>
                      <Trash2 size={11} />
                    </Button>
                  </div>
                ))}
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <Label className="text-slate-300 text-xs">Filters</Label>
                  <Button variant="ghost" size="sm" className="text-xs h-6 text-primary" onClick={addFilter}>
                    <Plus size={12} className="mr-1" /> Add Filter
                  </Button>
                </div>
                {filters.map((f, i) => (
                  <div key={i} className="flex gap-2 mb-2">
                    <select value={f.field} onChange={e => updateFilter(i, 'field', e.target.value)}
                      className="rounded border border-white/10 bg-background px-2 py-1 text-xs text-white flex-1">
                      <option value="">Field</option>
                      {allColumns.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                    </select>
                    <select value={f.operator} onChange={e => updateFilter(i, 'operator', e.target.value)}
                      className="rounded border border-white/10 bg-background px-2 py-1 text-xs text-white w-20">
                      {OPERATORS.map(op => <option key={op} value={op}>{op}</option>)}
                    </select>
                    <Input value={f.value} onChange={e => updateFilter(i, 'value', e.target.value)}
                      placeholder="value" className="bg-background border-white/10 text-white text-xs h-7 flex-1" />
                    <Button variant="ghost" size="sm" className="h-7 text-red-400" onClick={() => removeFilter(i)}>
                      <Trash2 size={12} />
                    </Button>
                  </div>
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {data.length > 0 && (
        <Card className="bg-surface border-white/10 overflow-auto">
          <CardHeader><CardTitle className="text-white text-sm">Results ({data.length} rows)</CardTitle></CardHeader>
          <CardContent className="p-0">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b border-white/10">
                  {columns.map(c => <th key={c} className="px-3 py-2 text-left text-slate-400">{c}</th>)}
                </tr>
              </thead>
              <tbody>
                {data.map((row, i) => (
                  <tr key={i} className="border-b border-white/5 hover:bg-white/5">
                    {columns.map(c => <td key={c} className="px-3 py-2 text-slate-300">{String(row[c] ?? '')}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      <Dialog open={showJoinModal} onOpenChange={setShowJoinModal}>
        <DialogContent className="bg-surface border-white/10 text-white">
          <DialogHeader><DialogTitle>Add JOIN</DialogTitle></DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1">
              <Label className="text-slate-300">Relationship</Label>
              <select value={selectedRelationship} onChange={e => setSelectedRelationship(e.target.value)}
                className="w-full rounded-md border border-white/10 bg-background px-3 py-2 text-sm text-white">
                <option value="">Select relationship</option>
                {availableRelationships.map(r => <option key={r.name} value={r.name}>{r.to_object} - {r.description}</option>)}
              </select>
            </div>
            <div className="space-y-1">
              <Label className="text-slate-300">Join Type</Label>
              <select value={selectedJoinType} onChange={e => setSelectedJoinType(e.target.value)}
                className="w-full rounded-md border border-white/10 bg-background px-3 py-2 text-sm text-white">
                <option value="LEFT">LEFT JOIN</option>
                <option value="INNER">INNER JOIN</option>
                <option value="RIGHT">RIGHT JOIN</option>
              </select>
            </div>
            <div className="flex gap-2 justify-end">
              <Button variant="ghost" onClick={() => setShowJoinModal(false)}>Cancel</Button>
              <Button onClick={confirmJoin} className="bg-primary hover:bg-primary/90">Add</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={showSaveModal} onOpenChange={setShowSaveModal}>
        <DialogContent className="bg-surface border-white/10 text-white">
          <DialogHeader><DialogTitle>Save as Asset</DialogTitle></DialogHeader>
          <form onSubmit={handleSaveAsset} className="space-y-4">
            <div className="space-y-1">
              <Label className="text-slate-300">Asset Name *</Label>
              <Input value={saveName} onChange={e => setSaveName(e.target.value)} required
                className="bg-background border-white/10 text-white" />
            </div>
            <div className="space-y-1">
              <Label className="text-slate-300">Description</Label>
              <textarea value={saveDesc} onChange={e => setSaveDesc(e.target.value)} rows={3}
                className="w-full rounded-md border border-white/10 bg-background px-3 py-2 text-sm text-white resize-none focus:outline-none focus:ring-2 focus:ring-primary" />
            </div>
            <div className="flex gap-2 justify-end">
              <Button type="button" variant="ghost" onClick={() => setShowSaveModal(false)}>Cancel</Button>
              <Button type="submit" className="bg-primary hover:bg-primary/90">Save</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ObjectExplorer;
