"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { mcpApi } from "@/services/pythonApi";
import { downloadJson } from "@/utils/download";

interface Skill {
  id: string;
  ontology_id: string;
  name: string;
  version: string;
  description: string;
  ontology_name: string;
}

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [generated, setGenerated] = useState<Record<string, any>>({});

  useEffect(() => {
    mcpApi.skills().then((d) => setSkills(d.skills || [])).finally(() => setLoading(false));
  }, []);

  const handleGenerate = async (skill: Skill) => {
    const result = await mcpApi.generate(skill.ontology_id);
    setGenerated((prev) => ({ ...prev, [skill.id]: result }));
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-text-primary">能力中心</h1>
        <Link href="/ontology" className="px-4 py-2 bg-accent text-white rounded text-sm hover:bg-accent-hover">
          管理本体
        </Link>
      </div>

      {loading ? (
        <p className="text-text-secondary text-sm">加载中...</p>
      ) : skills.length === 0 ? (
        <div className="text-center py-16 text-text-secondary">
          <p className="mb-2">暂无可用 Skill</p>
          <p className="text-sm mb-4">先创建本体，每个本体自动对应一个 Skill 包供下游 Agent 安装</p>
          <Link href="/ontology/create" className="text-accent text-sm hover:underline">
            创建第一个本体
          </Link>
        </div>
      ) : (
        <div className="grid gap-3">
          {skills.map((s) => (
            <div key={s.id} className="bg-surface border border-gray-200 rounded-lg p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-medium text-text-primary">{s.name}</h3>
                  <p className="text-sm text-text-secondary mt-1">{s.description}</p>
                  <div className="flex gap-3 mt-2 text-xs text-text-secondary">
                    <span>v{s.version}</span>
                    <span>·</span>
                    <span>本体: {s.ontology_name}</span>
                  </div>
                </div>
                <button
                  onClick={() => handleGenerate(s)}
                  className="px-3 py-1.5 bg-accent text-white rounded text-xs hover:bg-accent-hover"
                >
                  {generated[s.id] ? "重新生成" : "生成 MCP"}
                </button>
              </div>

              {generated[s.id] && (
                <div className="mt-3 text-xs space-y-2 border-t border-gray-100 pt-3">
                  <div className="flex items-center justify-between">
                    <span className="text-text-secondary">已生成 {generated[s.id].tools_count} 个工具</span>
                    <button
                      onClick={() => downloadJson(`${s.name}-mcp.json`, generated[s.id].mcp_config)}
                      className="px-2 py-1 bg-accent text-white rounded text-xs hover:bg-accent-hover"
                    >
                      下载 MCP 配置
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {generated[s.id].tools.map((t: any) => (
                      <code key={t.name} className="bg-data px-2 py-0.5 rounded text-text-data">
                        {t.name}
                      </code>
                    ))}
                  </div>
                  <details>
                    <summary className="cursor-pointer text-accent">查看 MCP 配置 (可直接复制)</summary>
                    <pre className="bg-data p-2 rounded overflow-auto text-text-data mt-1">
                      {JSON.stringify(generated[s.id].mcp_config, null, 2)}
                    </pre>
                  </details>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
