"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { datasourceApi } from "@/services/pythonApi";

interface Dataset {
  id: string;
  table_name: string;
  rows_count: number;
  last_synced_at: string | null;
  status: string;
}

interface Datasource {
  id: string;
  name: string;
  type: string;
  status: string;
  datasets_count: number;
  datasets: Dataset[];
  created_at: string;
}

const TYPE_LABELS: Record<string, string> = {
  csv: "CSV", excel: "Excel", mysql: "MySQL", postgres: "PostgreSQL", sqlite: "SQLite",
};

export default function DatasourcesPage() {
  const [items, setItems] = useState<Datasource[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = () => {
    setLoading(true);
    datasourceApi.list().then(setItems).catch(() => setItems([])).finally(() => setLoading(false));
  };

  useEffect(() => { refresh(); }, []);

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`删除数据源 "${name}"？关联的 Delta 数据集也会被删除。`)) return;
    try {
      await datasourceApi.delete(id);
      refresh();
    } catch (e: any) {
      alert(`删除失败: ${e.message}`);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-text-primary">数据源</h1>
        <div className="flex gap-2">
          <Link href="/datasources/connect" className="px-4 py-2 border border-gray-200 rounded text-sm text-text-secondary hover:bg-surface">
            连接数据库
          </Link>
          <Link href="/datasources/upload" className="px-4 py-2 bg-accent text-white rounded text-sm hover:bg-accent-hover">
            上传 CSV
          </Link>
        </div>
      </div>

      {loading ? (
        <p className="text-text-secondary text-sm">加载中...</p>
      ) : items.length === 0 ? (
        <div className="text-center py-16 text-text-secondary">
          <p className="mb-2">暂无数据源</p>
          <p className="text-sm">上传 CSV 或连接 MySQL/PostgreSQL 开始使用</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {items.map((item) => (
            <div key={item.id} className="bg-surface border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <h3 className="font-medium text-text-primary">{item.name}</h3>
                  <p className="text-xs text-text-secondary mt-1">
                    <span className="bg-data px-2 py-0.5 rounded">{TYPE_LABELS[item.type] || item.type}</span>
                    <span className="mx-2">·</span>
                    {item.datasets_count} 个数据集
                    <span className="mx-2">·</span>
                    {item.status}
                  </p>
                </div>
                <button
                  onClick={() => handleDelete(item.id, item.name)}
                  className="text-xs text-text-secondary hover:text-red-500 px-3 py-1 hover:bg-red-50 rounded"
                >
                  删除
                </button>
              </div>
              {item.datasets.length > 0 && (
                <div className="mt-3 space-y-1 border-t border-gray-100 pt-2">
                  {item.datasets.map((ds) => (
                    <div key={ds.id} className="flex items-center text-xs text-text-secondary py-1">
                      <span className="text-cool">▸</span>
                      <span className="ml-2 font-medium text-text-data">{ds.table_name}</span>
                      <span className="ml-3">{ds.rows_count} 行</span>
                      {ds.last_synced_at && (
                        <span className="ml-3 text-text-secondary">
                          同步于 {new Date(ds.last_synced_at).toLocaleString("zh-CN")}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
