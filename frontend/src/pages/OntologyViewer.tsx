import React, { useState, useMemo } from 'react';
import { parse } from 'yaml';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { cn } from '@/lib/utils';

interface OntologyViewerProps {
  configYaml: string;
}

const TYPE_COLORS: Record<string, string> = {
  string: 'bg-blue-500/20 text-blue-300',
  integer: 'bg-green-500/20 text-green-300',
  float: 'bg-cyan-500/20 text-cyan-300',
  decimal: 'bg-cyan-500/20 text-cyan-300',
  currency: 'bg-yellow-500/20 text-yellow-300',
  date: 'bg-orange-500/20 text-orange-300',
  boolean: 'bg-purple-500/20 text-purple-300',
  computed: 'bg-pink-500/20 text-pink-300',
};

const OntologyViewer: React.FC<OntologyViewerProps> = ({ configYaml }) => {
  const [selectedObject, setSelectedObject] = useState<string | null>(null);
  const [selectedRelationship, setSelectedRelationship] = useState<string | null>(null);
  const [propSearch, setPropSearch] = useState('');

  const parsed = useMemo(() => {
    if (!configYaml?.trim()) return null;
    try { return parse(configYaml); } catch { return null; }
  }, [configYaml]);

  if (!parsed) {
    return <p className="text-slate-400 text-sm text-center py-12">暂无有效的 Ontology 配置，请先在 Configuration 中填写 YAML</p>;
  }

  const objects: any[] = parsed?.ontology?.objects ?? [];
  const relationships: any[] = parsed?.ontology?.relationships ?? [];
  const currentObj = objects.find(o => o.name === selectedObject);
  const currentRel = relationships.find(r => r.name === selectedRelationship);
  const relatedRels = currentObj
    ? relationships.filter(r => r.from_object === currentObj.name || r.to_object === currentObj.name)
    : [];
  const filteredProps = (currentObj?.properties ?? []).filter((p: any) =>
    !propSearch ||
    p.name?.toLowerCase().includes(propSearch.toLowerCase()) ||
    p.description?.toLowerCase().includes(propSearch.toLowerCase())
  );

  return (
    <div className="flex gap-4 min-h-[600px]">
      {/* Left panel */}
      <div className="w-56 shrink-0 space-y-3">
        <div className="border border-white/10 rounded-md overflow-hidden">
          <div className="px-3 py-2 bg-surface border-b border-white/10 text-xs text-slate-400 font-medium">
            Objects ({objects.length})
          </div>
          {objects.map((obj: any) => (
            <div
              key={obj.name}
              onClick={() => { setSelectedObject(obj.name); setSelectedRelationship(null); }}
              className={cn(
                'flex items-center justify-between px-3 py-2 cursor-pointer text-sm border-l-2 transition-colors',
                selectedObject === obj.name
                  ? 'bg-primary/10 text-primary border-primary'
                  : 'text-slate-400 hover:text-white hover:bg-white/5 border-transparent'
              )}
            >
              <span>{obj.name}</span>
              <span className="text-xs text-slate-500">{(obj.properties ?? []).length}</span>
            </div>
          ))}
        </div>

        {relationships.length > 0 && (
          <div className="border border-white/10 rounded-md overflow-hidden">
            <div className="px-3 py-2 bg-surface border-b border-white/10 text-xs text-slate-400 font-medium">
              Relationships ({relationships.length})
            </div>
            {relationships.map((rel: any) => (
              <div
                key={rel.name}
                onClick={() => { setSelectedRelationship(rel.name); setSelectedObject(null); }}
                className={cn(
                  'px-3 py-2 cursor-pointer border-l-2 transition-colors',
                  selectedRelationship === rel.name
                    ? 'bg-primary/10 text-primary border-primary'
                    : 'text-slate-400 hover:text-white hover:bg-white/5 border-transparent'
                )}
              >
                <div className="text-sm">{rel.name}</div>
                <div className="text-xs text-slate-500">{rel.from_object} → {rel.to_object}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Right panel */}
      <div className="flex-1 space-y-3 overflow-auto">
        {!currentObj && !currentRel && (
          <p className="text-slate-500 text-sm text-center mt-20">从左侧选择一个 Object 或 Relationship 查看详情</p>
        )}

        {currentObj && (
          <>
            <div className="border border-white/10 rounded-md p-4 bg-surface space-y-2">
              <h3 className="text-white font-semibold text-base">{currentObj.name}</h3>
              <div className="flex gap-4 text-sm">
                <span className="text-slate-400">表名：<code className="text-slate-300 font-mono">{currentObj.table}</code></span>
                <span className="text-slate-400">数据源：<span className="text-slate-300">{currentObj.datasource || '-'}</span></span>
              </div>
              {currentObj.description && <p className="text-slate-400 text-sm">{currentObj.description}</p>}
              {currentObj.business_context && (
                <div className="bg-blue-500/10 border border-blue-500/20 rounded p-3 text-xs text-slate-300">
                  <p className="text-blue-400 font-medium mb-1">业务背景</p>
                  <pre className="whitespace-pre-wrap">{currentObj.business_context}</pre>
                </div>
              )}
            </div>

            {currentObj.default_filters?.length > 0 && (
              <div className="border border-white/10 rounded-md p-3 bg-surface">
                <p className="text-xs text-slate-400 mb-2">默认过滤条件（自动应用）</p>
                <div className="flex flex-wrap gap-2">
                  {currentObj.default_filters.map((f: any, i: number) => (
                    <Badge key={i} variant="outline" className="text-orange-300 border-orange-500/30 font-mono text-xs">
                      {f.field} {f.operator} {f.value !== undefined ? `'${f.value}'` : ''}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {currentObj.computed_properties?.length > 0 && (
              <div className="border border-white/10 rounded-md p-3 bg-surface">
                <p className="text-xs text-slate-400 mb-2">计算属性 ({currentObj.computed_properties.length})</p>
                <div className="space-y-2">
                  {currentObj.computed_properties.map((cp: any) => (
                    <div key={cp.name} className="text-sm">
                      <code className="text-slate-300 font-mono">{cp.name}</code>
                      <Badge className="ml-2 bg-pink-500/20 text-pink-300 text-xs">{cp.type}</Badge>
                      {cp.description && <span className="text-slate-500 ml-2 text-xs">{cp.description}</span>}
                      <div className="text-xs text-slate-500 mt-1">formula: <code className="text-slate-400">{cp.formula}</code></div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="border border-white/10 rounded-md bg-surface">
              <div className="flex items-center justify-between px-4 py-2 border-b border-white/10">
                <span className="text-xs text-slate-400">Properties ({(currentObj.properties ?? []).length})</span>
                <Input value={propSearch} onChange={e => setPropSearch(e.target.value)}
                  placeholder="搜索属性" className="bg-background border-white/10 text-white h-7 text-xs w-40" />
              </div>
              <Table>
                <TableHeader>
                  <TableRow className="border-white/10">
                    <TableHead className="text-slate-400 text-xs">属性名</TableHead>
                    <TableHead className="text-slate-400 text-xs">类型</TableHead>
                    <TableHead className="text-slate-400 text-xs">列名</TableHead>
                    <TableHead className="text-slate-400 text-xs">描述</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredProps.map((p: any) => (
                    <TableRow key={p.name} className="border-white/10 hover:bg-white/5">
                      <TableCell className="font-mono text-xs text-slate-300">{p.name}</TableCell>
                      <TableCell>
                        <span className={cn('text-xs px-1.5 py-0.5 rounded font-mono', TYPE_COLORS[p.type] ?? 'bg-white/10 text-slate-300')}>
                          {p.type}
                        </span>
                      </TableCell>
                      <TableCell className="text-xs text-slate-500 font-mono">{p.column || p.column_name || '-'}</TableCell>
                      <TableCell className="text-xs text-slate-400">{p.description || '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {relatedRels.length > 0 && (
              <div className="border border-white/10 rounded-md p-3 bg-surface">
                <p className="text-xs text-slate-400 mb-2">参与的关联关系 ({relatedRels.length})</p>
                <div className="space-y-2">
                  {relatedRels.map((rel: any) => (
                    <div key={rel.name} className="text-sm flex items-center gap-2 flex-wrap">
                      <Badge variant="outline" className={rel.from_object === currentObj.name ? 'text-blue-300 border-blue-500/30' : 'text-green-300 border-green-500/30'}>
                        {rel.from_object === currentObj.name ? 'FROM' : 'TO'}
                      </Badge>
                      <span className="text-white font-medium">{rel.name}</span>
                      <span className="text-slate-500 text-xs">{rel.from_object} → {rel.to_object}</span>
                      <Badge variant="outline" className="text-slate-400 text-xs">{rel.join_type || 'LEFT'} JOIN</Badge>
                      {rel.join_condition && (
                        <code className="text-xs text-slate-500 font-mono">ON {rel.join_condition.from_field} = {rel.join_condition.to_field}</code>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {currentRel && (
          <div className="border border-white/10 rounded-md p-4 bg-surface space-y-4">
            <h3 className="text-white font-semibold">{currentRel.name}</h3>
            <div className="flex gap-4 text-sm">
              <span className="text-slate-400">类型：<Badge variant="secondary">{currentRel.type || 'many_to_one'}</Badge></span>
              <span className="text-slate-400">JOIN：<Badge variant="secondary">{currentRel.join_type || 'LEFT'} JOIN</Badge></span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="border border-white/10 rounded p-3 text-center">
                <p className="text-xs text-slate-400 mb-1">From</p>
                <p className="text-white font-semibold">{currentRel.from_object}</p>
                {currentRel.join_condition && <code className="text-xs text-slate-400 font-mono">{currentRel.join_condition.from_field}</code>}
              </div>
              <div className="border border-white/10 rounded p-3 text-center">
                <p className="text-xs text-slate-400 mb-1">To</p>
                <p className="text-white font-semibold">{currentRel.to_object}</p>
                {currentRel.join_condition && <code className="text-xs text-slate-400 font-mono">{currentRel.join_condition.to_field}</code>}
              </div>
            </div>
            {currentRel.description && <p className="text-slate-400 text-sm">{currentRel.description}</p>}
          </div>
        )}
      </div>
    </div>
  );
};

export default OntologyViewer;
