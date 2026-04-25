import { useCallback, useState } from 'react';
import { CheckCircle, Loader2, Database, Brain, Save } from 'lucide-react';
import { useProject } from '@/contexts/ProjectContext';
import { modelingService, InferredObject, InferredRelationship } from '@/services/modeling';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type Step = 'scan' | 'infer' | 'confirm' | 'done';

type TableOption = {
  name: string;
  row_count: number;
  column_count: number;
};

function getErrorMessage(error: any) {
  return error?.response?.data?.detail || error?.message || '操作失败';
}

export default function ModelingPage() {
  const { currentProject } = useProject();
  const [step, setStep] = useState<Step>('scan');
  const [datasourceId, setDatasourceId] = useState('');
  const [tables, setTables] = useState<TableOption[]>([]);
  const [selectedTables, setSelectedTables] = useState<string[]>([]);
  const [objects, setObjects] = useState<InferredObject[]>([]);
  const [relationships, setRelationships] = useState<InferredRelationship[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [result, setResult] = useState<{ objects_created: number; objects_updated: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const projectId = currentProject?.id;
  const selectedTableCount = selectedTables.length;

  const handleScan = useCallback(async () => {
    if (!projectId || !datasourceId) return;
    setLoading(true);
    setError('');
    try {
      const data = await modelingService.scan(projectId, datasourceId);
      const nextTables = data.tables.map((t) => ({
        name: t.name,
        row_count: t.row_count,
        column_count: t.columns.length,
      }));
      setTables(nextTables);
      setSelectedTables(nextTables.map((t) => t.name));
      setStep('infer');
    } catch (e: any) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [projectId, datasourceId]);

  const handleInfer = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError('');
    try {
      const data = await modelingService.infer(projectId, datasourceId, selectedTables);
      setObjects(data.objects);
      setRelationships(data.relationships);
      setWarnings(data.warnings);
      setStep('confirm');
    } catch (e: any) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [projectId, datasourceId, selectedTables]);

  const handleConfirm = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    setError('');
    try {
      const data = await modelingService.confirm(projectId, objects, relationships);
      setResult(data);
      setStep('done');
    } catch (e: any) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [projectId, objects, relationships]);

  const toggleTable = useCallback((name: string) => {
    setSelectedTables((current) =>
      current.includes(name)
        ? current.filter((item) => item !== name)
        : [...current, name]
    );
  }, []);

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-xl font-semibold text-white mb-6">AI 自动建模</h1>

      {error && (
        <div className="bg-red-900/30 border border-red-800 text-red-300 px-4 py-2 rounded mb-4 text-sm">
          {error}
        </div>
      )}

      {/* Step 1: Scan */}
      <div className={`rounded-lg border p-4 mb-4 ${step === 'scan' ? 'border-blue-600 bg-gray-900' : 'border-gray-800 bg-gray-900/50'}`}>
        <div className="flex items-center gap-2 mb-3">
          <Database size={18} className={step === 'scan' ? 'text-blue-400' : 'text-gray-500'} />
          <h2 className="text-sm font-medium text-gray-200">1. 扫描数据源</h2>
          {step !== 'scan' && <CheckCircle size={16} className="text-green-500 ml-auto" />}
        </div>
        {step === 'scan' && (
          <div className="flex gap-2">
            <Input
              className="flex-1"
              placeholder="数据源ID (如 mysql_erp)"
              value={datasourceId}
              onChange={(e) => setDatasourceId(e.target.value)}
            />
            <Button
              onClick={handleScan}
              disabled={loading || !datasourceId}
              className="flex items-center gap-1"
            >
              {loading && <Loader2 size={14} className="animate-spin" />}
              扫描
            </Button>
          </div>
        )}
      </div>

      {/* Step 2: Select & Infer */}
      <div className={`rounded-lg border p-4 mb-4 ${step === 'infer' ? 'border-blue-600 bg-gray-900' : 'border-gray-800 bg-gray-900/50'}`}>
        <div className="flex items-center gap-2 mb-3">
          <Brain size={18} className={step === 'infer' ? 'text-blue-400' : 'text-gray-500'} />
          <h2 className="text-sm font-medium text-gray-200">2. AI 推断</h2>
          {(step === 'confirm' || step === 'done') && <CheckCircle size={16} className="text-green-500 ml-auto" />}
        </div>
        {step === 'infer' && (
          <>
            <div className="max-h-60 overflow-y-auto mb-3">
              {tables.map((t) => (
                <label key={t.name} className="flex items-center gap-2 py-1 px-2 hover:bg-gray-800 rounded cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedTables.includes(t.name)}
                    onChange={() => toggleTable(t.name)}
                    className="rounded"
                  />
                  <span className="text-sm text-gray-300">{t.name}</span>
                  <span className="text-xs text-gray-500 ml-auto">{t.row_count} rows, {t.column_count} cols</span>
                </label>
              ))}
            </div>
            <Button
              onClick={handleInfer}
              disabled={loading || selectedTableCount === 0}
              className="flex items-center gap-1"
            >
              {loading && <Loader2 size={14} className="animate-spin" />}
              开始推断 ({selectedTableCount} 张表)
            </Button>
          </>
        )}
      </div>

      {/* Step 3: Confirm */}
      <div className={`rounded-lg border p-4 mb-4 ${step === 'confirm' ? 'border-blue-600 bg-gray-900' : 'border-gray-800 bg-gray-900/50'}`}>
        <div className="flex items-center gap-2 mb-3">
          <Save size={18} className={step === 'confirm' ? 'text-blue-400' : 'text-gray-500'} />
          <h2 className="text-sm font-medium text-gray-200">3. 确认并保存</h2>
          {step === 'done' && <CheckCircle size={16} className="text-green-500 ml-auto" />}
        </div>
        {step === 'confirm' && (
          <>
            {warnings.length > 0 && (
              <div className="text-yellow-400 text-xs mb-2">
                {warnings.map((w, i) => <div key={i}>{w}</div>)}
              </div>
            )}
            <div className="max-h-60 overflow-y-auto mb-3 space-y-2">
              {objects.map((obj) => (
                <div key={obj.source_entity} className="bg-gray-800 rounded p-3">
                  <div className="text-sm text-white font-medium">{obj.name} <span className="text-gray-500 font-normal">({obj.source_entity})</span></div>
                  <div className="text-xs text-gray-400 mt-1">{obj.description}</div>
                  <div className="text-xs text-gray-500 mt-1">{obj.properties.length} 个字段</div>
                </div>
              ))}
            </div>
            {relationships.length > 0 && (
              <div className="text-xs text-gray-400 mb-3">
                {relationships.length} 个关系已推断
              </div>
            )}
            <Button
              onClick={handleConfirm}
              disabled={loading}
              className="flex items-center gap-1 bg-green-600 hover:bg-green-700"
            >
              {loading && <Loader2 size={14} className="animate-spin" />}
              确认保存
            </Button>
          </>
        )}
      </div>

      {/* Done */}
      {step === 'done' && result && (
        <div className="bg-green-900/20 border border-green-800 rounded-lg p-4 text-center">
          <CheckCircle size={32} className="text-green-500 mx-auto mb-2" />
          <p className="text-green-300 text-sm">
            建模完成: 创建 {result.objects_created} 个对象，更新 {result.objects_updated} 个对象
          </p>
        </div>
      )}
    </div>
  );
}
