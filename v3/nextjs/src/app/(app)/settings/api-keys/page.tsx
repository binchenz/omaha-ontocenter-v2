"use client";
import { useState } from "react";

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<Array<{ label: string; created: string; scopes: string }>>([]);
  const [generated, setGenerated] = useState("");

  const handleGenerate = () => {
    const label = prompt("密钥标签 (如 'Claude Code 访问'):") || "未命名";
    const newKey = { label, created: new Date().toISOString(), scopes: "read, mcp" };
    setKeys((prev) => [newKey, ...prev]);
    setGenerated(`ocv3_${Math.random().toString(36).slice(2, 18)}`);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-text-primary">API Keys</h1>
        <button onClick={handleGenerate} className="px-4 py-2 bg-accent text-white rounded text-sm hover:bg-accent-hover">
          生成新密钥
        </button>
      </div>

      {generated && (
        <div className="bg-accent-glow border border-accent rounded-lg p-4 mb-4">
          <p className="text-sm font-medium text-text-primary mb-2">新密钥已生成 (仅显示一次)</p>
          <code className="text-xs bg-data px-3 py-1 rounded block break-all text-cool">{generated}</code>
          <button onClick={() => navigator.clipboard.writeText(generated)} className="text-xs text-accent mt-2 hover:underline">
            复制到剪贴板
          </button>
        </div>
      )}

      {keys.length === 0 ? (
        <p className="text-text-secondary text-sm">暂无 API Key。生成后可配置到 Claude Code 等 Agent 中访问 MCP Server。</p>
      ) : (
        <div className="grid gap-3">
          {keys.map((k, i) => (
            <div key={i} className="bg-surface border border-gray-200 rounded-lg p-4 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-text-primary">{k.label}</h3>
                <p className="text-xs text-text-secondary mt-1">权限: {k.scopes} · 创建于 {new Date(k.created).toLocaleDateString()}</p>
              </div>
              <button className="text-xs text-red-400 hover:text-red-500">撤销</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
