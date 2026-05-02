"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ontologyApi } from "@/services/pythonApi";

export default function CreateOntologyPage() {
  const [yaml, setYaml] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleCreate = async () => {
    setLoading(true); setError("");
    try {
      const result = await ontologyApi.create(yaml);
      router.push(`/ontology/${result.id}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const exampleYaml = `name: 我的第一个本体
slug: my-first-ontology
description: 示例电商本体
objects:
  - name: Order
    slug: order
    table_name: orders
    properties:
      - name: id
        source_column: id
        semantic_type: id
      - name: amount
        source_column: amount
        semantic_type: currency
        unit: CNY`;

  return (
    <div>
      <h1 className="text-2xl font-bold text-text-primary mb-4">新建本体</h1>
      <div className="grid grid-cols-2 gap-6">
        <div>
          <textarea
            value={yaml}
            onChange={(e) => setYaml(e.target.value)}
            placeholder={exampleYaml}
            className="w-full h-[500px] p-4 bg-surface border border-gray-200 rounded-lg text-sm font-mono text-text-data resize-none focus:outline-none focus:border-accent"
          />
          <div className="flex gap-2 mt-3">
            <button onClick={handleCreate} disabled={loading || !yaml.trim()} className="px-6 py-2 bg-accent text-white rounded text-sm hover:bg-accent-hover disabled:opacity-50">
              {loading ? "创建中..." : "创建本体"}
            </button>
            <button onClick={() => setYaml(exampleYaml)} className="px-4 py-2 border border-gray-200 rounded text-sm text-text-secondary hover:bg-surface">
              填入示例
            </button>
          </div>
          {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
        </div>
        <div className="bg-data border border-gray-200 rounded-lg p-4">
          <h2 className="text-sm font-medium text-text-primary mb-2">YAML 格式说明</h2>
          <pre className="text-xs text-text-secondary whitespace-pre-wrap">
{`name: 本体名称
slug: 唯一标识 (字母数字连字符)
objects: 数据对象列表
  - name: 对象名 (支持中文)
    slug: 对象标识
    table_name: 对应数据表名
    properties: 属性列表
      - name: 属性名
        source_column: 数据库列名
        semantic_type: currency|percentage|date|text|enum|number|id`}
          </pre>
        </div>
      </div>
    </div>
  );
}
