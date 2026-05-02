"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { createOntologyFromColumns } from "@/features/ontology/createOntologyFromColumns";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [step, setStep] = useState<"upload" | "preview" | "creating">("upload");
  const [ingestResult, setIngestResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true); setError("");
    try {
      const fd = new FormData();
      fd.append("type", file.name.endsWith(".csv") ? "csv" : "excel");
      fd.append("file", file);
      const res = await fetch("/api/python/ingest", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "上传失败");
      setIngestResult(data);
      setStep("preview");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!ingestResult || !file) return;
    setLoading(true); setError("");
    try {
      const result = await createOntologyFromColumns({
        source: file.name,
        tableName: ingestResult.table_name,
        columns: ingestResult.columns,
      });
      router.push(`/ontology/${result.id}`);
    } catch (e: any) {
      setError(e.message);
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold text-text-primary mb-6">上传 CSV / Excel</h1>

      {step === "upload" && (
        <div className="bg-surface border border-gray-200 rounded-lg p-8">
          <input
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="block w-full text-sm text-text-primary file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-accent file:text-white hover:file:bg-accent-hover"
          />
          {file && <p className="mt-3 text-sm text-text-secondary">已选择: {file.name} ({(file.size / 1024).toFixed(1)} KB)</p>}
          <button
            onClick={handleUpload}
            disabled={!file || loading}
            className="mt-4 px-4 py-2 bg-accent text-white rounded text-sm hover:bg-accent-hover disabled:opacity-50"
          >
            {loading ? "上传中..." : "上传并解析"}
          </button>
          {error && <p className="text-red-500 text-sm mt-3">{error}</p>}
        </div>
      )}

      {step === "preview" && ingestResult && (
        <div className="space-y-4">
          <div className="bg-surface border border-gray-200 rounded-lg p-4">
            <h2 className="font-medium text-text-primary mb-2">解析结果</h2>
            <p className="text-sm text-text-secondary mb-3">
              已导入 <span className="text-accent font-medium">{ingestResult.rows_count}</span> 行数据
              · 数据集 ID: <code className="bg-data px-1 rounded">{ingestResult.dataset_id}</code>
            </p>
            <div className="grid grid-cols-3 gap-2 text-xs">
              {ingestResult.columns.map((c: any) => (
                <div key={c.name} className="bg-data rounded p-2">
                  <div className="font-medium text-text-data">{c.name}</div>
                  <div className="text-cool">{c.semantic_type}</div>
                  <div className="text-text-secondary mt-1">样例: {String(c.sample_values?.[0] || '').slice(0, 20)}</div>
                </div>
              ))}
            </div>
            <div className="flex gap-2 mt-4">
              <button onClick={handleCreate} disabled={loading} className="px-4 py-2 bg-accent text-white rounded text-sm hover:bg-accent-hover disabled:opacity-50">
                {loading ? "创建中..." : "创建本体"}
              </button>
              <button onClick={() => setStep("upload")} className="px-4 py-2 border border-gray-200 rounded text-sm text-text-secondary hover:bg-data">
                重新上传
              </button>
            </div>
            {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
          </div>
        </div>
      )}
    </div>
  );
}
