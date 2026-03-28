import React, { useState } from 'react';
import { Plus, Edit2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { SemanticObject } from '../../types/semantic';
import FormulaBuilder from './FormulaBuilder';

interface PropertyEditorProps {
  objectName: string;
  objectMeta: SemanticObject | null;
  projectId: number;
  onTestFormula: (formula: string) => Promise<{ sql: string | null; error: string | null }>;
  onChange: (updated: SemanticObject) => void;
}

const SEMANTIC_TYPES = ['', 'currency', 'percentage', 'enum', 'date', 'id', 'text'];
const SEMANTIC_LABELS: Record<string, string> = { '': '默认', currency: '货币', percentage: '百分比', enum: '枚举', date: '日期', id: 'ID', text: '文本' };
const GRANULARITY_LEVELS = [
  { value: 'master_data', label: '主数据' },
  { value: 'city_level', label: '城市级' },
  { value: 'store_level', label: '门店级' },
  { value: 'transaction', label: '交易级' },
];

const PropertyEditor: React.FC<PropertyEditorProps> = ({
  objectName, objectMeta, projectId: _projectId, onTestFormula, onChange
}) => {
  const [formulaBuilderOpen, setFormulaBuilderOpen] = useState(false);
  const [editingComputed, setEditingComputed] = useState<string | null>(null);
  const [addingDimension, setAddingDimension] = useState(false);
  const [newDimension, setNewDimension] = useState('');

  if (!objectMeta) {
    return (
      <div className="p-4 text-slate-400 text-sm">请从左侧选择一个对象</div>
    );
  }

  const granularity = objectMeta.granularity || { dimensions: [], level: '', description: '' };

  const updateObjectInfo = (field: string, value: any) => onChange({ ...objectMeta, [field]: value });
  const updateGranularity = (field: string, value: any) =>
    onChange({ ...objectMeta, granularity: { ...granularity, [field]: value } });

  const addDimension = () => {
    if (newDimension.trim()) {
      updateGranularity('dimensions', [...granularity.dimensions, newDimension.trim()]);
      setNewDimension('');
      setAddingDimension(false);
    }
  };

  const removeDimension = (dim: string) =>
    updateGranularity('dimensions', granularity.dimensions.filter(d => d !== dim));

  const updateBaseProperty = (propName: string, field: string, value: any) =>
    onChange({
      ...objectMeta,
      base_properties: {
        ...objectMeta.base_properties,
        [propName]: { ...objectMeta.base_properties[propName], [field]: value },
      },
    });

  const handleFormulaSave = (formula: string) => {
    if (!editingComputed) return;
    onChange({
      ...objectMeta,
      computed_properties: {
        ...objectMeta.computed_properties,
        [editingComputed]: { ...objectMeta.computed_properties[editingComputed], formula },
      },
    });
    setFormulaBuilderOpen(false);
    setEditingComputed(null);
  };

  const addComputedField = () => {
    const name = `new_field_${Date.now()}`;
    onChange({
      ...objectMeta,
      computed_properties: {
        ...objectMeta.computed_properties,
        [name]: { name, semantic_type: 'computed' as const, formula: '', description: '' },
      },
    });
    setEditingComputed(name);
    setFormulaBuilderOpen(true);
  };

  return (
    <div className="p-4 space-y-4 text-sm">
      {/* Object Info */}
      <div className="border border-white/10 rounded-md bg-surface p-4 space-y-3">
        <p className="text-white font-medium text-xs">对象信息</p>
        <div>
          <label className="text-slate-400 text-xs">描述</label>
          <Input value={objectMeta.description || ''} placeholder="对象描述"
            onChange={e => updateObjectInfo('description', e.target.value)}
            className="mt-1 bg-background border-white/10 text-white text-xs h-8" />
        </div>
        <div>
          <label className="text-slate-400 text-xs">业务上下文</label>
          <textarea value={objectMeta.business_context || ''} placeholder="业务上下文说明" rows={3}
            onChange={e => updateObjectInfo('business_context', e.target.value)}
            className="mt-1 w-full rounded-md border border-white/10 bg-background px-3 py-2 text-xs text-white resize-none focus:outline-none focus:ring-2 focus:ring-primary" />
        </div>
      </div>

      {/* Granularity */}
      <div className="border border-white/10 rounded-md bg-surface p-4 space-y-3">
        <p className="text-white font-medium text-xs">粒度信息</p>
        <div>
          <label className="text-slate-400 text-xs">维度</label>
          <div className="mt-1 flex flex-wrap gap-1">
            {granularity.dimensions.map(dim => (
              <Badge key={dim} variant="secondary" className="text-xs gap-1">
                {dim}
                <X size={10} className="cursor-pointer" onClick={() => removeDimension(dim)} />
              </Badge>
            ))}
            {addingDimension ? (
              <Input autoFocus value={newDimension} onChange={e => setNewDimension(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addDimension()}
                onBlur={() => { addDimension(); setAddingDimension(false); }}
                className="w-24 h-6 text-xs bg-background border-white/10 text-white" />
            ) : (
              <Badge variant="outline" className="text-xs cursor-pointer border-dashed hover:bg-white/5"
                onClick={() => setAddingDimension(true)}>
                <Plus size={10} className="mr-1" /> 添加维度
              </Badge>
            )}
          </div>
        </div>
        <div>
          <label className="text-slate-400 text-xs">级别</label>
          <select value={granularity.level || ''} onChange={e => updateGranularity('level', e.target.value)}
            className="mt-1 w-full rounded-md border border-white/10 bg-background px-3 py-1.5 text-xs text-white">
            <option value="">选择粒度级别</option>
            {GRANULARITY_LEVELS.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
          </select>
        </div>
        <div>
          <label className="text-slate-400 text-xs">描述</label>
          <Input value={granularity.description || ''} placeholder="粒度描述"
            onChange={e => updateGranularity('description', e.target.value)}
            className="mt-1 bg-background border-white/10 text-white text-xs h-8" />
        </div>
      </div>

      {/* Base Properties */}
      <div className="border border-white/10 rounded-md bg-surface overflow-hidden">
        <div className="px-4 py-2 border-b border-white/10 text-xs text-white font-medium">
          {objectName} — 基础字段
        </div>
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-white/10">
              <th className="px-3 py-2 text-left text-slate-400">字段名</th>
              <th className="px-3 py-2 text-left text-slate-400">列名</th>
              <th className="px-3 py-2 text-left text-slate-400">语义类型</th>
              <th className="px-3 py-2 text-left text-slate-400">描述</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(objectMeta.base_properties).map(([name, prop]) => (
              <tr key={name} className="border-b border-white/5">
                <td className="px-3 py-2"><code className="text-slate-300 font-mono">{name}</code></td>
                <td className="px-3 py-2 text-slate-500">{(prop as any).column || ''}</td>
                <td className="px-3 py-2">
                  <select value={prop.semantic_type || ''} onChange={e => updateBaseProperty(name, 'semantic_type', e.target.value || undefined)}
                    className="rounded border border-white/10 bg-background px-1 py-0.5 text-xs text-white">
                    {SEMANTIC_TYPES.map(t => <option key={t} value={t}>{SEMANTIC_LABELS[t]}</option>)}
                  </select>
                </td>
                <td className="px-3 py-2">
                  <input value={prop.description || ''} placeholder="业务描述"
                    onChange={e => updateBaseProperty(name, 'description', e.target.value)}
                    className="w-full bg-transparent border-b border-white/10 text-slate-300 text-xs focus:outline-none focus:border-primary" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Computed Properties */}
      <div className="border border-white/10 rounded-md bg-surface overflow-hidden">
        <div className="px-4 py-2 border-b border-white/10 text-xs text-white font-medium flex items-center justify-between">
          <span>{objectName} — 计算字段</span>
          <Button variant="ghost" size="sm" className="h-6 text-xs text-primary" onClick={addComputedField}>
            <Plus size={11} className="mr-1" /> 添加计算字段
          </Button>
        </div>
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-white/10">
              <th className="px-3 py-2 text-left text-slate-400">字段名</th>
              <th className="px-3 py-2 text-left text-slate-400">公式</th>
              <th className="px-3 py-2 text-left text-slate-400">描述</th>
              <th className="px-3 py-2 text-left text-slate-400">操作</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(objectMeta.computed_properties).map(([name, prop]) => (
              <tr key={name} className="border-b border-white/5">
                <td className="px-3 py-2"><code className="text-slate-300 font-mono">{name}</code></td>
                <td className="px-3 py-2 text-slate-500 font-mono">{prop.formula}</td>
                <td className="px-3 py-2 text-slate-500">{prop.description}</td>
                <td className="px-3 py-2">
                  <Button variant="ghost" size="sm" className="h-6 text-xs text-slate-400"
                    onClick={() => { setEditingComputed(name); setFormulaBuilderOpen(true); }}>
                    <Edit2 size={11} className="mr-1" /> 编辑
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <FormulaBuilder
        open={formulaBuilderOpen}
        objectName={objectName}
        objectMeta={objectMeta}
        initialFormula={editingComputed ? objectMeta.computed_properties[editingComputed]?.formula : ''}
        onSave={handleFormulaSave}
        onCancel={() => { setFormulaBuilderOpen(false); setEditingComputed(null); }}
        onTest={onTestFormula}
      />
    </div>
  );
};

export default PropertyEditor;
