"use client";
import { useEffect, useState } from "react";

interface ApiKeyRow {
  id: string;
  label: string;
  scopes: string;
  createdAt: string;
  expiresAt: string | null;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKeyRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");
  const [newPlaintext, setNewPlaintext] = useState<string>("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/keys")
      .then(async (r) => {
        if (!r.ok) throw new Error(`加载失败: HTTP ${r.status}`);
        return (await r.json()) as ApiKeyRow[];
      })
      .then((rows) => {
        if (!cancelled) setKeys(Array.isArray(rows) ? rows : []);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleGenerate = async () => {
    const label = prompt("密钥标签 (如 'the assistant Desktop'):")?.trim() || "未命名";
    setError("");
    try {
      const r = await fetch("/api/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ label, scopes: "mcp:read" }),
      });
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw new Error(body?.error || `HTTP ${r.status}`);
      }
      const created = await r.json();
      setNewPlaintext(created.plaintext);
      setCopied(false);
      setKeys((prev) => [
        {
          id: created.id,
          label: created.label,
          scopes: created.scopes,
          createdAt: created.createdAt,
          expiresAt: created.expiresAt ?? null,
        },
        ...prev,
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("删除这个密钥？通过它访问的工具将立即失效。")) return;
    setError("");
    try {
      const r = await fetch(`/api/keys/${id}`, { method: "DELETE" });
      if (!r.ok && r.status !== 204) throw new Error(`删除失败: HTTP ${r.status}`);
      setKeys((prev) => prev.filter((k) => k.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const handleCopy = async () => {
    if (!newPlaintext) return;
    try {
      await navigator.clipboard.writeText(newPlaintext);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-text-primary">API Keys</h1>
        <button
          onClick={handleGenerate}
          className="px-4 py-2 bg-accent text-white rounded text-sm hover:bg-accent-hover"
        >
          生成新密钥
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-300 rounded-lg p-3 mb-4">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {newPlaintext && (
        <div className="bg-accent-glow border border-accent rounded-lg p-4 mb-4">
          <div className="flex items-start justify-between mb-2">
            <p className="text-sm font-medium text-text-primary">
              新密钥已生成 — <span className="text-red-600">仅此一次显示，请立即保存</span>
            </p>
            <button
              onClick={() => {
                setNewPlaintext("");
                setCopied(false);
              }}
              className="text-xs text-text-secondary hover:text-text-primary ml-4"
            >
              关闭
            </button>
          </div>
          <code className="text-xs bg-data px-3 py-2 rounded block break-all text-cool">
            {newPlaintext}
          </code>
          <button
            onClick={handleCopy}
            className="text-xs text-accent mt-2 hover:underline"
          >
            {copied ? "已复制 ✓" : "复制到剪贴板"}
          </button>
        </div>
      )}

      {loading ? (
        <p className="text-text-secondary text-sm">加载中…</p>
      ) : keys.length === 0 ? (
        <p className="text-text-secondary text-sm">
          暂无 API Key。生成后可配置到 the assistant 等 Agent 中访问 MCP Server。
        </p>
      ) : (
        <div className="grid gap-3">
          {keys.map((k) => (
            <div
              key={k.id}
              className="bg-surface border border-gray-200 rounded-lg p-4 flex items-center justify-between"
            >
              <div>
                <h3 className="text-sm font-medium text-text-primary">{k.label}</h3>
                <p className="text-xs text-text-secondary mt-1">
                  权限: {k.scopes} · 创建于 {formatDate(k.createdAt)} · 过期:{" "}
                  {k.expiresAt ? formatDate(k.expiresAt) : "永久"}
                </p>
              </div>
              <button
                onClick={() => handleDelete(k.id)}
                className="text-xs text-red-400 hover:text-red-500"
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
