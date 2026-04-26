import { useState } from 'react';

interface InferredProperty {
  name: string;
  data_type: string;
  semantic_type?: string | null;
  description?: string | null;
}

interface InferredObject {
  name: string;
  source_entity?: string;
  description?: string | null;
  business_context?: string | null;
  properties: InferredProperty[];
}

interface InferredRelationship {
  name?: string;
  from_object: string;
  to_object: string;
  from_field: string;
  to_field: string;
}

interface OntologyPreviewData {
  template_name?: string | null;
  objects: InferredObject[];
  relationships: InferredRelationship[];
  warnings?: string[];
}

interface Props {
  data: OntologyPreviewData;
  onConfirm?: () => void;
  onRetry?: () => void;
}

export function OntologyConfirmPanel({ data, onConfirm, onRetry }: Props) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const toggle = (name: string) =>
    setExpanded((prev) => ({ ...prev, [name]: !prev[name] }));

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800/50 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-300">建模结果</span>
        {data.template_name && (
          <span className="text-xs text-blue-400">已套用：{data.template_name}</span>
        )}
      </div>

      <div>
        <p className="text-sm text-gray-400 mb-2">
          业务对象 ({data.objects?.length ?? 0})
        </p>
        <div className="space-y-1.5">
          {(data.objects || []).map((obj) => (
            <div key={obj.name} className="border-l-2 border-blue-500 pl-3">
              <button
                onClick={() => toggle(obj.name)}
                className="text-left w-full text-sm text-gray-200 hover:text-white"
              >
                <span className="font-medium">📦 {obj.name}</span>
                {obj.description && (
                  <span className="text-gray-500 ml-2">— {obj.description}</span>
                )}
                <span className="text-gray-500 ml-2 text-xs">
                  ({obj.properties.length} 个字段)
                </span>
              </button>
              {expanded[obj.name] && (
                <div className="mt-1 ml-2 space-y-0.5 text-xs">
                  {obj.properties.map((p) => (
                    <div key={p.name} className="text-gray-400">
                      <span className="text-gray-200">{p.name}</span>
                      <span className="ml-2">{p.data_type}</span>
                      {p.semantic_type && (
                        <span className="ml-2 text-blue-400">
                          ({p.semantic_type})
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {data.relationships && data.relationships.length > 0 && (
        <div>
          <p className="text-sm text-gray-400 mb-2">
            关系 ({data.relationships.length})
          </p>
          <div className="space-y-1 text-xs text-gray-300">
            {data.relationships.map((r, i) => (
              <div key={i}>
                🔗 {r.from_object} → {r.to_object}
                <span className="text-gray-500 ml-2">
                  按 {r.from_field} 关联
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.warnings && data.warnings.length > 0 && (
        <div className="border-l-2 border-yellow-500 pl-3 text-xs text-yellow-400">
          {data.warnings.map((w, i) => (
            <p key={i}>⚠ {w}</p>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={onConfirm}
          className="flex-1 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm text-white transition-colors"
        >
          ✓ 确认建模
        </button>
        <button
          onClick={onRetry}
          className="flex-1 py-2 rounded-lg border border-gray-600 hover:bg-gray-700 text-sm text-gray-200 transition-colors"
        >
          ↻ 重新分析
        </button>
      </div>
    </div>
  );
}
