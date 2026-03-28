import React from 'react';
import { BarChart2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { SemanticObject } from '../../types/semantic';

interface AgentPreviewProps {
  objectName: string;
  objectMeta: SemanticObject | null;
}

const levelMap: Record<string, string> = {
  master_data: '主数据', city_level: '城市级', store_level: '门店级', transaction: '交易级',
};

const AgentPreview: React.FC<AgentPreviewProps> = ({ objectName, objectMeta }) => {
  if (!objectMeta) {
    return (
      <div className="border border-white/10 rounded-md p-4 bg-surface">
        <p className="text-slate-400 text-sm">请选择一个对象</p>
      </div>
    );
  }

  return (
    <div className="border border-white/10 rounded-md bg-surface">
      <div className="px-4 py-3 border-b border-white/10 text-xs text-slate-400 font-medium">Agent 上下文预览</div>
      <div className="p-4 space-y-4 text-sm">
        <div>
          <span className="text-white font-semibold">{objectName}</span>
          {objectMeta.description && <span className="text-slate-400 ml-2">（{objectMeta.description}）</span>}
        </div>

        {objectMeta.granularity && (
          <div className="bg-background rounded p-3 space-y-2">
            <p className="text-slate-300 text-xs font-medium flex items-center gap-1">
              <BarChart2 size={12} /> 数据粒度
            </p>
            {objectMeta.granularity.dimensions?.length > 0 && (
              <div className="flex flex-wrap gap-1">
                <span className="text-slate-500 text-xs">维度：</span>
                {objectMeta.granularity.dimensions.map((dim, i) => (
                  <Badge key={i} variant="secondary" className="text-xs">{dim}</Badge>
                ))}
              </div>
            )}
            {objectMeta.granularity.level && (
              <div className="flex items-center gap-1">
                <span className="text-slate-500 text-xs">级别：</span>
                <Badge variant="secondary" className="text-xs">{levelMap[objectMeta.granularity.level] || objectMeta.granularity.level}</Badge>
              </div>
            )}
            {objectMeta.granularity.description && (
              <p className="text-slate-400 text-xs">说明：{objectMeta.granularity.description}</p>
            )}
          </div>
        )}

        <div>
          <p className="text-slate-300 text-xs font-medium mb-2">字段：</p>
          <div className="space-y-1">
            {Object.entries(objectMeta.base_properties).map(([name, prop]) => (
              <div key={name} className="flex items-center gap-2 ml-3 text-xs">
                <code className="text-slate-300 font-mono">{name}</code>
                {prop.semantic_type === 'currency' && <Badge className="bg-yellow-500/20 text-yellow-300 text-xs">货币 {prop.currency}</Badge>}
                {prop.semantic_type === 'percentage' && <Badge className="bg-blue-500/20 text-blue-300 text-xs">百分比</Badge>}
                {prop.semantic_type === 'enum' && <Badge className="bg-purple-500/20 text-purple-300 text-xs">枚举</Badge>}
                {prop.description && <span className="text-slate-500">: {prop.description}</span>}
              </div>
            ))}
            {Object.entries(objectMeta.computed_properties).map(([name, prop]) => (
              <div key={name} className="ml-3 text-xs space-y-0.5">
                <div className="flex items-center gap-2">
                  <code className="text-slate-300 font-mono">{name}</code>
                  <Badge className="bg-green-500/20 text-green-300 text-xs">计算</Badge>
                  {prop.description && <span className="text-slate-500">: {prop.description}</span>}
                </div>
                <p className="text-slate-500 ml-4">公式: {prop.formula}</p>
              </div>
            ))}
          </div>
        </div>

        {objectMeta.relationships.length > 0 && (
          <div>
            <p className="text-slate-300 text-xs font-medium mb-2">关系：</p>
            {objectMeta.relationships
              .filter(r => r.from_object === objectName || r.to_object === objectName)
              .map((rel, i) => (
                <div key={i} className="ml-3 text-xs flex items-center gap-2">
                  <code className="text-slate-300 font-mono">{rel.name}</code>
                  {rel.description && <span className="text-slate-500">: {rel.description}</span>}
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentPreview;
