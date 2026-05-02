"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ontologyApi } from "@/services/pythonApi";
import { buildOntologyYaml } from "@/lib/yaml-builder";

const PRESETS: Record<string, { port: number; user: string }> = {
  postgres: { port: 5432, user: "postgres" },
  mysql: { port: 3306, user: "root" },
  sqlite: { port: 0, user: "" },
};

export default function ConnectPage() {
  const router = useRouter();
  const [type, setType] = useState<"postgres" | "mysql" | "sqlite">("postgres");
  const [host, setHost] = useState("localhost");
  const [port, setPort] = useState(5432);
  const [database, setDatabase] = useState("");
  const [user, setUser] = useState("postgres");
  const [password, setPassword] = useState("");
  const [path, setPath] = useState("");
  const [step, setStep] = useState<"connect" | "preview" | "creating">("connect");
  const [discoverResult, setDiscoverResult] = useState<any>(null);
  const [selectedTable, setSelectedTable] = useState<string>("");
  const [yamlDraft, setYamlDraft] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const updateType = (t: typeof type) => {
    setType(t);
    const p = PRESETS[t];
    setPort(p.port);
    setUser(p.user);
  };

  const buildFormData = () => {
    const fd = new FormData();
    fd.append("type", type);
    if (type === "sqlite") {
      fd.append("path", path);
    } else {
      fd.append("host", host);
      fd.append("port", String(port));
      fd.append("database", database);
      fd.append("user", user);
      fd.append("password", password);
    }
    return fd;
  };

  const handleDiscover = async () => {
    setLoading(true); setError("");
    try {
      const res = await fetch("/api/python/ingest/discover", {
        method: "POST",
        body: buildFormData(),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "连接失败");
      setDiscoverResult(data);
      if (data.tables.length > 0) setSelectedTable(data.tables[0]);
      setStep("preview");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleIngest = async () => {
    setLoading(true); setError("");
    try {
      const res = await fetch("/api/python/ingest", {
        method: "POST",
        body: buildFormData(),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "导入失败");

      setYamlDraft(buildOntologyYaml({
        source: `${type} 数据源`,
        tableName: data.table_name,
        columns: data.columns,
      }));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    setLoading(true);
    try {
      const result = await ontologyApi.create(yamlDraft);
      router.push(`/ontology/${result.id}`);
    } catch (e: any) {
      setError(e.message);
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold text-text-primary mb-6">连接数据库</h1>

      {step === "connect" && (
        <div className="bg-surface border border-gray-200 rounded-lg p-6 space-y-4">
          <div>
            <label className="block text-sm text-text-secondary mb-1">数据库类型</label>
            <div className="flex gap-2">
              {(["postgres", "mysql", "sqlite"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => updateType(t)}
                  className={`px-3 py-1.5 rounded text-sm border ${type === t ? "border-accent bg-accent-glow text-accent" : "border-gray-200 text-text-secondary"}`}
                >
                  {t === "postgres" ? "PostgreSQL" : t === "mysql" ? "MySQL" : "SQLite"}
                </button>
              ))}
            </div>
          </div>

          {type === "sqlite" ? (
            <div>
              <label className="block text-sm text-text-secondary mb-1">数据库文件路径</label>
              <input
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder="/path/to/database.db"
                className="w-full px-3 py-2 border border-gray-200 rounded bg-root text-sm"
              />
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm text-text-secondary mb-1">主机</label>
                  <input value={host} onChange={(e) => setHost(e.target.value)} className="w-full px-3 py-2 border border-gray-200 rounded bg-root text-sm" />
                </div>
                <div>
                  <label className="block text-sm text-text-secondary mb-1">端口</label>
                  <input type="number" value={port} onChange={(e) => setPort(parseInt(e.target.value) || 0)} className="w-full px-3 py-2 border border-gray-200 rounded bg-root text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">数据库名</label>
                <input value={database} onChange={(e) => setDatabase(e.target.value)} className="w-full px-3 py-2 border border-gray-200 rounded bg-root text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm text-text-secondary mb-1">用户名</label>
                  <input value={user} onChange={(e) => setUser(e.target.value)} className="w-full px-3 py-2 border border-gray-200 rounded bg-root text-sm" />
                </div>
                <div>
                  <label className="block text-sm text-text-secondary mb-1">密码</label>
                  <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full px-3 py-2 border border-gray-200 rounded bg-root text-sm" />
                </div>
              </div>
            </>
          )}

          <button onClick={handleDiscover} disabled={loading} className="px-4 py-2 bg-accent text-white rounded text-sm hover:bg-accent-hover disabled:opacity-50">
            {loading ? "连接中..." : "连接并扫描"}
          </button>
          {error && <p className="text-red-500 text-sm">{error}</p>}
        </div>
      )}

      {step === "preview" && discoverResult && !yamlDraft && (
        <div className="bg-surface border border-gray-200 rounded-lg p-4 space-y-3">
          <h2 className="font-medium text-text-primary">发现 {discoverResult.tables.length} 个表</h2>
          <div className="space-y-2">
            {discoverResult.tables.map((t: string) => (
              <label key={t} className="flex items-center gap-2 p-2 bg-data rounded cursor-pointer hover:border-accent border border-transparent">
                <input type="radio" checked={selectedTable === t} onChange={() => setSelectedTable(t)} />
                <span className="text-sm font-medium">{t}</span>
                <span className="text-xs text-text-secondary ml-auto">
                  {discoverResult.columns?.[t]?.length || 0} 列
                </span>
              </label>
            ))}
          </div>
          <div className="flex gap-2 mt-3">
            <button onClick={handleIngest} disabled={!selectedTable || loading} className="px-4 py-2 bg-accent text-white rounded text-sm hover:bg-accent-hover disabled:opacity-50">
              {loading ? "导入中..." : "导入并生成本体"}
            </button>
            <button onClick={() => setStep("connect")} className="px-4 py-2 border border-gray-200 rounded text-sm text-text-secondary">
              返回
            </button>
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
        </div>
      )}

      {yamlDraft && (
        <div className="bg-surface border border-gray-200 rounded-lg p-4">
          <h2 className="font-medium text-text-primary mb-2">建议的本体 YAML</h2>
          <textarea
            value={yamlDraft}
            onChange={(e) => setYamlDraft(e.target.value)}
            className="w-full h-72 p-3 bg-data border border-gray-200 rounded text-xs font-mono text-text-data resize-none"
          />
          <button onClick={handleCreate} disabled={loading} className="mt-3 px-4 py-2 bg-accent text-white rounded text-sm hover:bg-accent-hover disabled:opacity-50">
            {loading ? "创建中..." : "创建本体"}
          </button>
          {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
        </div>
      )}
    </div>
  );
}
