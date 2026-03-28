import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { semanticApi } from '../services/semanticApi';
import { SemanticConfig, SemanticObject } from '../types/semantic';
import ObjectList from '../components/semantic/ObjectList';
import PropertyEditor from '../components/semantic/PropertyEditor';
import AgentPreview from '../components/semantic/AgentPreview';

const SemanticEditor: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const projectId = id ? parseInt(id) : 0;

  const [semanticConfig, setSemanticConfig] = useState<SemanticConfig | null>(null);
  const [selectedObject, setSelectedObject] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [localObjects, setLocalObjects] = useState<Record<string, SemanticObject>>({});

  useEffect(() => { loadConfig(); }, [projectId]);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const data = await semanticApi.get(projectId);
      setSemanticConfig(data);
      setLocalObjects(data.parsed.objects || {});
      const names = Object.keys(data.parsed.objects || {});
      if (names.length > 0) setSelectedObject(names[0]);
    } catch {
      setSaveMsg({ type: 'error', text: '加载语义配置失败' });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!semanticConfig) return;
    setSaving(true);
    setSaveMsg(null);
    try {
      await semanticApi.save(projectId, semanticConfig.config);
      setSaveMsg({ type: 'success', text: '语义配置已保存' });
      setTimeout(() => setSaveMsg(null), 3000);
    } catch {
      setSaveMsg({ type: 'error', text: '保存失败' });
    } finally {
      setSaving(false);
    }
  };

  const handleTestFormula = async (formula: string) => {
    if (!selectedObject) return { sql: null, error: '未选择对象', sample: [] };
    try {
      return await semanticApi.testFormula(projectId, selectedObject, formula);
    } catch {
      return { sql: null, error: '测试失败', sample: [] };
    }
  };

  const handleObjectChange = (updated: SemanticObject) => {
    if (!selectedObject) return;
    setLocalObjects(prev => ({ ...prev, [selectedObject]: updated }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const objectNames = Object.keys(localObjects);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-surface">
        <span className="text-white font-medium text-sm">语义层编辑器</span>
        <div className="flex items-center gap-3">
          {saveMsg && (
            <span className={`text-xs ${saveMsg.type === 'success' ? 'text-green-400' : 'text-red-400'}`}>
              {saveMsg.text}
            </span>
          )}
          <Button onClick={handleSave} disabled={saving} className="bg-primary hover:bg-primary/90 h-8 text-xs">
            <Save size={13} className="mr-1.5" /> {saving ? '保存中...' : '保存'}
          </Button>
        </div>
      </div>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: object list */}
        <div className="w-52 border-r border-white/10 overflow-y-auto shrink-0">
          <ObjectList objects={objectNames} selected={selectedObject} onSelect={setSelectedObject} />
        </div>

        {/* Center: property editor */}
        <div className="flex-1 overflow-y-auto">
          <PropertyEditor
            objectName={selectedObject || ''}
            objectMeta={selectedObject ? localObjects[selectedObject] : null}
            projectId={projectId}
            onTestFormula={handleTestFormula}
            onChange={handleObjectChange}
          />
        </div>

        {/* Right: agent preview */}
        <div className="w-72 border-l border-white/10 overflow-y-auto shrink-0 p-3">
          <AgentPreview
            objectName={selectedObject || ''}
            objectMeta={selectedObject ? localObjects[selectedObject] : null}
          />
        </div>
      </div>
    </div>
  );
};

export default SemanticEditor;
