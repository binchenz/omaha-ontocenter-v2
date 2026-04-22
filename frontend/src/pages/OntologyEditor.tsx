import React, { useState } from 'react';
import { Plus, Download, Upload, Save, ChevronDown, ChevronRight, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ontologyEditorService, OntologyModel, DatasourceConfig, ObjectConfig, PropertyConfig } from '@/services/ontologyEditor';
import { projectService } from '@/services/project';
import { useProject } from '@/contexts/ProjectContext';
import CodeMirror from '@uiw/react-codemirror';
import { yaml } from '@codemirror/lang-yaml';

const CONNECTOR_TYPES = ['tushare', 'sqlite', 'mysql', 'postgresql', 'csv', 'excel', 'rest_api'];
const FIELD_TYPES = ['string', 'integer', 'decimal', 'date', 'datetime', 'boolean'];
const SEMANTIC_TYPES = ['', 'text', 'number', 'percentage', 'currency_cny', 'date', 'stock_code', 'ratio'];

const emptyDs = (): DatasourceConfig => ({ id: '', type: 'sqlite', connection: {} });
const emptyObj = (): ObjectConfig => ({ name: '', datasource: '', properties: [], relationships: [] });
const emptyProp = (): PropertyConfig => ({ name: '', type: 'string' });

interface Props { projectId: number; }

const OntologyEditor: React.FC<Props> = ({ projectId }) => {
  const { currentProject, refreshProjects } = useProject();
  const [model, setModel] = useState<OntologyModel>({ datasources: [], objects: [] });
  const [yamlPreview, setYamlPreview] = useState('');
  const [selectedDs, setSelectedDs] = useState<number | null>(null);
  const [selectedObj, setSelectedObj] = useState<number | null>(null);
  const [status, setStatus] = useState('');
  const [addPropOpen, setAddPropOpen] = useState(false);
  const [newProp, setNewProp] = useState<PropertyConfig>(emptyProp());

  const showStatus = (msg: string) => {
    setStatus(msg);
    setTimeout(() => setStatus(''), 2500);
  };

  const handleGenerateYaml = async () => {
    const result = await ontologyEditorService.generateYaml(model);
    setYamlPreview(result.yaml);
    showStatus('YAML 已生成');
  };

  const handleSave = async () => {
    if (!currentProject || !yamlPreview) return;
    await projectService.update(projectId, { omaha_config: yamlPreview });
    await refreshProjects();
    showStatus('已保存到项目');
  };

  const handleImport = async () => {
    if (!currentProject?.omaha_config) return;
    const config = typeof currentProject.omaha_config === 'string'
      ? currentProject.omaha_config
      : new TextDecoder().decode(currentProject.omaha_config as unknown as Uint8Array);
    const imported = await ontologyEditorService.parseYaml(config);
    setModel(imported);
    showStatus('已从 YAML 导入');
  };

  const updateDs = (i: number, patch: Partial<DatasourceConfig>) =>
    setModel(m => ({ ...m, datasources: m.datasources.map((d, idx) => idx === i ? { ...d, ...patch } : d) }));

  const updateObj = (i: number, patch: Partial<ObjectConfig>) =>
    setModel(m => ({ ...m, objects: m.objects.map((o, idx) => idx === i ? { ...o, ...patch } : o) }));

  const addProp = () => {
    if (selectedObj === null || !newProp.name) return;
    updateObj(selectedObj, { properties: [...model.objects[selectedObj].properties, { ...newProp }] });
    setNewProp(emptyProp());
    setAddPropOpen(false);
  };

  const removeProp = (objIdx: number, propIdx: number) =>
    updateObj(objIdx, { properties: model.objects[objIdx].properties.filter((_, i) => i !== propIdx) });

  return (
    <div className="flex gap-4 h-[700px]">
      <div className="w-1/2 flex flex-col gap-3 overflow-y-auto pr-2">
        <Card className="bg-surface border-white/10">
          <CardHeader className="py-3 flex flex-row items-center justify-between">
            <CardTitle className="text-white text-sm">数据源</CardTitle>
            <Button size="sm" variant="ghost" className="text-primary text-xs h-6"
              onClick={() => setModel(m => ({ ...m, datasources: [...m.datasources, emptyDs()] }))}>
              <Plus size={12} className="mr-1" /> 添加
            </Button>
          </CardHeader>
          <CardContent className="py-0 pb-3 space-y-2">
            {model.datasources.map((ds, i) => (
              <div key={i} className="border border-white/10 rounded p-2">
                <div className="flex items-center gap-2 cursor-pointer"
                  onClick={() => setSelectedDs(selectedDs === i ? null : i)}>
                  {selectedDs === i ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                  <span className="text-white text-xs font-mono flex-1">{ds.id || '(未命名)'}</span>
                  <span className="text-slate-500 text-xs">{ds.type}</span>
                  <button onClick={e => { e.stopPropagation(); setModel(m => ({ ...m, datasources: m.datasources.filter((_, idx) => idx !== i) })); }}
                    className="text-red-400 hover:text-red-300"><Trash2 size={11} /></button>
                </div>
                {selectedDs === i && (
                  <div className="mt-2 space-y-2 pl-4">
                    <div className="flex gap-2">
                      <div className="flex-1 space-y-1">
                        <Label className="text-slate-400 text-xs">ID</Label>
                        <Input value={ds.id} onChange={e => updateDs(i, { id: e.target.value })}
                          className="bg-background border-white/10 text-white text-xs h-7" />
                      </div>
                      <div className="flex-1 space-y-1">
                        <Label className="text-slate-400 text-xs">类型</Label>
                        <select value={ds.type} onChange={e => updateDs(i, { type: e.target.value })}
                          className="w-full rounded border border-white/10 bg-background px-2 py-1 text-xs text-white h-7">
                          {CONNECTOR_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                        </select>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
            {model.datasources.length === 0 && <p className="text-slate-500 text-xs">暂无数据源</p>}
          </CardContent>
        </Card>

        <Card className="bg-surface border-white/10">
          <CardHeader className="py-3 flex flex-row items-center justify-between">
            <CardTitle className="text-white text-sm">对象类型</CardTitle>
            <Button size="sm" variant="ghost" className="text-primary text-xs h-6"
              onClick={() => setModel(m => ({ ...m, objects: [...m.objects, emptyObj()] }))}>
              <Plus size={12} className="mr-1" /> 添加
            </Button>
          </CardHeader>
          <CardContent className="py-0 pb-3 space-y-2">
            {model.objects.map((obj, i) => (
              <div key={i} className="border border-white/10 rounded p-2">
                <div className="flex items-center gap-2 cursor-pointer"
                  onClick={() => setSelectedObj(selectedObj === i ? null : i)}>
                  {selectedObj === i ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                  <span className="text-white text-xs font-mono flex-1">{obj.name || '(未命名)'}</span>
                  <span className="text-slate-500 text-xs">{obj.properties.length} 字段</span>
                  <button onClick={e => { e.stopPropagation(); setModel(m => ({ ...m, objects: m.objects.filter((_, idx) => idx !== i) })); }}
                    className="text-red-400 hover:text-red-300"><Trash2 size={11} /></button>
                </div>
                {selectedObj === i && (
                  <div className="mt-2 space-y-2 pl-4">
                    <div className="grid grid-cols-2 gap-2">
                      {(['name', 'datasource', 'table', 'primary_key'] as const).map(field => (
                        <div key={field} className="space-y-1">
                          <Label className="text-slate-400 text-xs">
                            {field === 'name' ? '名称' : field === 'datasource' ? '数据源' : field === 'table' ? '表名' : '主键'}
                          </Label>
                          <Input value={obj[field] || ''} onChange={e => updateObj(i, { [field]: e.target.value })}
                            className="bg-background border-white/10 text-white text-xs h-7" />
                        </div>
                      ))}
                    </div>
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-slate-400 text-xs">字段</span>
                        <Button size="sm" variant="ghost" className="text-primary text-xs h-5"
                          onClick={() => setAddPropOpen(true)}>
                          <Plus size={10} className="mr-1" /> 添加字段
                        </Button>
                      </div>
                      {obj.properties.length > 0 && (
                        <Table>
                          <TableHeader>
                            <TableRow className="border-white/10">
                              {['名称', '类型', '语义类型', ''].map(h => (
                                <TableHead key={h} className="text-slate-400 text-xs py-1">{h}</TableHead>
                              ))}
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {obj.properties.map((prop, pi) => (
                              <TableRow key={pi} className="border-white/5">
                                <TableCell className="text-white text-xs py-1 font-mono">{prop.name}</TableCell>
                                <TableCell className="text-slate-400 text-xs py-1">{prop.type}</TableCell>
                                <TableCell className="text-slate-400 text-xs py-1">{prop.semantic_type || '—'}</TableCell>
                                <TableCell className="py-1">
                                  <button onClick={() => removeProp(i, pi)} className="text-red-400 hover:text-red-300">
                                    <Trash2 size={10} />
                                  </button>
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
            {model.objects.length === 0 && <p className="text-slate-500 text-xs">暂无对象类型</p>}
          </CardContent>
        </Card>

        <Button variant="ghost" size="sm" onClick={handleImport} className="text-slate-400 self-start">
          <Upload size={14} className="mr-2" /> 从 YAML 导入
        </Button>
      </div>

      <div className="w-1/2 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-slate-400 text-sm">YAML 预览</span>
          <div className="flex items-center gap-2">
            {status && <span className="text-green-400 text-xs">{status}</span>}
            <Button size="sm" variant="ghost" onClick={handleGenerateYaml} className="text-slate-400 text-xs">
              <Download size={12} className="mr-1" /> 生成 YAML
            </Button>
            <Button size="sm" onClick={handleSave} disabled={!yamlPreview}
              className="bg-primary hover:bg-primary/90 text-xs">
              <Save size={12} className="mr-1" /> 保存到项目
            </Button>
          </div>
        </div>
        <div className="flex-1 border border-white/10 rounded overflow-hidden">
          <CodeMirror value={yamlPreview} height="100%" extensions={[yaml()]} editable={false} theme="dark" />
        </div>
      </div>

      <Dialog open={addPropOpen} onOpenChange={setAddPropOpen}>
        <DialogContent className="bg-surface border-white/10 text-white">
          <DialogHeader><DialogTitle>添加字段</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-slate-300">字段名 *</Label>
                <Input value={newProp.name} onChange={e => setNewProp(p => ({ ...p, name: e.target.value }))}
                  className="bg-background border-white/10 text-white" />
              </div>
              <div className="space-y-1">
                <Label className="text-slate-300">列名</Label>
                <Input value={newProp.column || ''} onChange={e => setNewProp(p => ({ ...p, column: e.target.value }))}
                  className="bg-background border-white/10 text-white" />
              </div>
              <div className="space-y-1">
                <Label className="text-slate-300">类型</Label>
                <select value={newProp.type} onChange={e => setNewProp(p => ({ ...p, type: e.target.value }))}
                  className="w-full rounded border border-white/10 bg-background px-3 py-2 text-sm text-white">
                  {FIELD_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="space-y-1">
                <Label className="text-slate-300">语义类型</Label>
                <select value={newProp.semantic_type || ''} onChange={e => setNewProp(p => ({ ...p, semantic_type: e.target.value || undefined }))}
                  className="w-full rounded border border-white/10 bg-background px-3 py-2 text-sm text-white">
                  {SEMANTIC_TYPES.map(t => <option key={t} value={t}>{t || '(无)'}</option>)}
                </select>
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <Button variant="ghost" onClick={() => setAddPropOpen(false)}>取消</Button>
              <Button onClick={addProp} disabled={!newProp.name} className="bg-primary hover:bg-primary/90">添加</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default OntologyEditor;
