"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ontologyApi } from "@/services/pythonApi";

export default function OntologyPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = () => {
    setLoading(true);
    ontologyApi.list().then(setItems).finally(() => setLoading(false));
  };

  useEffect(() => { refresh(); }, []);

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`确定删除本体 "${name}"？此操作不可撤销。`)) return;
    try {
      await ontologyApi.delete(id);
      refresh();
    } catch (e: any) {
      alert(`删除失败: ${e.message}`);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-text-primary">我的本体</h1>
        <div className="flex gap-2">
          <Link href="/datasources/upload" className="px-4 py-2 border border-gray-200 rounded text-sm text-text-secondary hover:bg-surface">
            上传 CSV
          </Link>
          <Link href="/ontology/create" className="px-4 py-2 bg-accent text-white rounded text-sm hover:bg-accent-hover">
            新建本体
          </Link>
        </div>
      </div>
      {loading ? (
        <p className="text-text-secondary text-sm">加载中...</p>
      ) : items.length === 0 ? (
        <div className="text-center py-16 text-text-secondary">
          <p className="mb-2">暂无本体</p>
          <p className="text-sm mb-4">上传 CSV 自动生成，或直接编写 YAML 定义</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {items.map((item: any) => (
            <div key={item.id} className="bg-surface border border-gray-200 rounded-lg p-4 flex items-center justify-between hover:border-accent transition-colors">
              <Link href={`/ontology/${item.id}`} className="flex-1">
                <h3 className="font-medium text-text-primary">{item.name}</h3>
                <p className="text-xs text-text-secondary mt-1">{item.slug} · v{item.version} · {item.status}</p>
              </Link>
              <button
                onClick={() => handleDelete(item.id, item.name)}
                className="text-xs text-text-secondary hover:text-red-500 px-3 py-1 hover:bg-red-50 rounded"
              >
                删除
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
