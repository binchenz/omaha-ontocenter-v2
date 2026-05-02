"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ontologyApi, mcpApi, pythonFetch } from "@/services/pythonApi";
import { downloadJson } from "@/lib/download";
import type { OntologySchema } from "@/types/api";

export default function OntologyDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const [schema, setSchema] = useState<OntologySchema | null>(null);
  const [yaml, setYaml] = useState("");
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [mcpResult, setMcpResult] = useState<any>(null);

  const refresh = async () => {
    setLoading(true);
    try {
      const s = await ontologyApi.getSchema(id);
      setSchema(s);
      const y = await pythonFetch(`/ontology/${id}/yaml`);
      setYaml(y.yaml);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, [id]);

  const handleSaveYaml = async () => {
    setSaving(true);
    try {
      const result = await ontologyApi.update(id, yaml);
      router.replace(`/ontology/${result.id}`);
      setEditing(false);
      await refresh();
    } catch (e: any) {
      alert(`保存失败: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleGenerate = async () => {
    const r = await mcpApi.generate(id);
    setMcpResult(r);
  };

  if (loading) return <div className="text-text-secondary">加载中...</div>;
  if (!schema) return <div className="text-text-secondary">本体未找到</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">{schema.name}</h1>
          <p className="text-sm text-text-secondary mt-1">v{schema.version} · {schema.objects.length} 个对象</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setEditing(!editing)}
            className="px-4 py-2 border border-gray-200 rounded text-sm text-text-secondary hover:bg-surface"
          >
            {editing ? "取消编辑" : "编辑 YAML"}
          </button>
          <button onClick={handleGenerate} className="px-4 py-2 bg-accent text-white rounded text-sm hover:bg-accent-hover">
            生成 MCP
          </button>
        </div>
      </div>

      {editing ? (
        <div className="bg-surface border border-gray-200 rounded-lg p-4 mb-6">
          <h2 className="font-medium text-text-primary mb-2">编辑 YAML</h2>
          <textarea
            value={yaml}
            onChange={(e) => setYaml(e.target.value)}
            className="w-full h-96 p-3 bg-data border border-gray-200 rounded text-xs font-mono text-text-data resize-none focus:outline-none focus:border-accent"
          />
          <div className="flex gap-2 mt-3">
            <button onClick={handleSaveYaml} disabled={saving} className="px-4 py-2 bg-accent text-white rounded text-sm hover:bg-accent-hover disabled:opacity-50">
              {saving ? "保存中..." : "保存"}
            </button>
            <button onClick={() => setEditing(false)} className="px-4 py-2 border border-gray-200 rounded text-sm text-text-secondary">
              取消
            </button>
          </div>
          <p className="text-xs text-text-secondary mt-2">
            注意：保存会重建本体，对象 ID 会变化。
          </p>
        </div>
      ) : (
        <>
          <h2 className="text-lg font-semibold text-text-primary mb-3">对象</h2>
          {schema.objects.map((obj) => (
            <div key={obj.id} className="bg-surface border border-gray-200 rounded-lg p-4 mb-3">
              <h3 className="font-medium text-text-primary">
                {obj.name} <code className="text-xs text-text-secondary bg-data px-1 py-0.5 rounded">{obj.slug}</code>
              </h3>
              <p className="text-sm text-text-secondary mt-1">{obj.description || `数据表: ${obj.table_name}`}</p>
              <div className="mt-3">
                <p className="text-xs font-medium text-text-secondary mb-1">属性</p>
                <div className="grid grid-cols-4 gap-1 text-xs">
                  {obj.properties.map((prop) => (
                    <div key={prop.slug} className="p-2 bg-data rounded">
                      <span className="font-medium text-text-data">{prop.name}</span>
                      <span className="text-cool ml-1">{prop.semantic_type}</span>
                      {prop.unit && <span className="text-text-secondary ml-1">({prop.unit})</span>}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}

          {schema.links.length > 0 && (
            <>
              <h2 className="text-lg font-semibold text-text-primary mb-3 mt-6">链接</h2>
              {schema.links.map((link: any, i: number) => (
                <div key={i} className="text-sm bg-surface border border-gray-200 rounded p-3 mb-2">
                  <span className="font-medium">{link.from_object}</span>
                  <span className="text-cool mx-2">→</span>
                  <span className="font-medium">{link.to_object}</span>
                  <span className="text-text-secondary ml-2">({link.type})</span>
                </div>
              ))}
            </>
          )}
        </>
      )}

      {mcpResult && (
        <div className="mt-6 bg-surface border border-accent rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-lg font-semibold text-text-primary">MCP Server 已生成</h2>
            <button
              onClick={() => downloadJson(`${schema.slug}-mcp.json`, mcpResult.mcp_config)}
              className="px-3 py-1.5 bg-accent text-white rounded text-xs hover:bg-accent-hover"
            >
              下载 MCP 配置
            </button>
          </div>
          <p className="text-sm text-text-secondary mb-2">共 {mcpResult.tools_count} 个工具 · 端点: <code className="bg-data px-1 rounded text-xs">{mcpResult.endpoint}</code></p>
          <details className="text-xs">
            <summary className="cursor-pointer text-accent">MCP 配置</summary>
            <pre className="mt-2 p-3 bg-data rounded overflow-auto max-h-64">{JSON.stringify(mcpResult.mcp_config, null, 2)}</pre>
          </details>
        </div>
      )}
    </div>
  );
}
