import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { queryService } from '@/services/query';

interface NodeDetailDrawerProps {
  projectId: number;
  objectName: string | null;
  fieldCount: number;
  onClose: () => void;
}

const NodeDetailDrawer: React.FC<NodeDetailDrawerProps> = ({
  projectId, objectName, fieldCount, onClose
}) => {
  const navigate = useNavigate();
  const [sampleData, setSampleData] = useState<any[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  useEffect(() => {
    if (!objectName) return;
    setLoading(true);
    setSampleData([]);
    // First fetch schema to get column names (max 5 base properties)
    queryService.getObjectSchema(projectId, objectName)
      .then(res => {
        if (res.success && res.columns) {
          const cols = res.columns.slice(0, 5).map((c: any) => c.name);
          setColumns(cols);
          return queryService.queryObjects(projectId, objectName, cols, [], undefined, 3);
        }
      })
      .then(res => { if (res?.success && res.data) setSampleData(res.data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId, objectName]);

  const open = !!objectName;

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-50 bg-surface border-t border-white/10"
      style={{
        transform: open ? 'translateY(0)' : 'translateY(100%)',
        transition: 'transform 250ms cubic-bezier(0,0,0.2,1)',
        height: '280px',
      }}
      role="dialog"
      aria-modal="true"
      aria-label={objectName ? `${objectName} details` : 'Node details'}
    >
      {objectName && (
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 shrink-0">
            <span className="text-white font-medium text-sm">
              {objectName}
              <span className="text-slate-400 ml-2 text-xs">{fieldCount} 个字段</span>
            </span>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="ghost"
                className="text-primary text-xs h-7"
                onClick={() => navigate(`/projects/${projectId}/explorer`, { state: { preselect: objectName } })}
              >
                <ArrowRight size={13} className="mr-1" /> 前往 Explorer
              </Button>
              <button
                onClick={onClose}
                className="text-slate-400 hover:text-white p-1 rounded focus:outline-none focus:ring-2 focus:ring-primary"
                aria-label="关闭"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Sample data */}
          <div className="flex-1 overflow-auto p-4">
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-6 rounded bg-white/5 animate-pulse" />
                ))}
              </div>
            ) : sampleData.length > 0 ? (
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="border-b border-white/10">
                    {columns.map(c => (
                      <th key={c} className="px-3 py-1.5 text-left text-slate-400">{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sampleData.map((row, i) => (
                    <tr key={i} className="border-b border-white/5">
                      {columns.map(c => (
                        <td key={c} className="px-3 py-1.5 text-slate-300">{String(row[c] ?? '')}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-slate-500 text-xs">暂无样本数据</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default NodeDetailDrawer;
