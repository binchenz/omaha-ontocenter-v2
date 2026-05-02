"use client";
import { useState, useRef, useEffect } from "react";
import { useSession } from "next-auth/react";
import { redirect } from "next/navigation";
import { Plus, Trash2 } from "lucide-react";
import { ChartView, detectChartable } from "@/components/chat/ChartView";
import { downloadCsv, oagToCsvRows } from "@/lib/download";

type ToolCall = { toolName: string; args: any; result: any; status: "success" | "error" };
type Message = {
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCall[];
  skill?: { name: string; reasoning: string };
  status?: string;
};
type Session = {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
};

export default function ChatPage() {
  const { status } = useSession();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeId, setActiveId] = useState<string>("");
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const loadedSessionsRef = useRef<Set<string>>(new Set());

  const active = sessions.find((s) => s.id === activeId);
  const messages = active?.messages || [];

  // Initial sessions load — fetch from server once authenticated.
  useEffect(() => {
    if (status !== "authenticated") return;
    let cancelled = false;
    fetch("/api/chat/sessions")
      .then((r) => (r.ok ? r.json() : []))
      .then((rows: Array<{ id: string; title: string | null; createdAt: string }>) => {
        if (cancelled) return;
        setSessions(
          rows.map((s) => ({
            id: s.id,
            title: s.title || "新对话",
            messages: [],
            createdAt: new Date(s.createdAt).getTime(),
          }))
        );
        if (rows.length > 0) setActiveId(rows[0].id);
      })
      .catch((err) => console.warn("[chat] failed to load sessions list:", err));
    return () => {
      cancelled = true;
    };
  }, [status]);

  // Lazy-load messages when a session becomes active.
  useEffect(() => {
    if (!activeId) return;
    if (loadedSessionsRef.current.has(activeId)) return;
    loadedSessionsRef.current.add(activeId);
    fetch(`/api/chat/sessions/${activeId}/messages`)
      .then((r) => (r.ok ? r.json() : []))
      .then((msgs: Array<{ role: string; content: string; toolCalls: ToolCall[] }>) => {
        setSessions((prev) =>
          prev.map((s) =>
            s.id === activeId
              ? {
                  ...s,
                  messages: msgs
                    .filter((m) => m.role === "user" || m.role === "assistant")
                    .map((m) => ({
                      role: m.role as "user" | "assistant",
                      content: m.content,
                      toolCalls: m.toolCalls || [],
                    })),
                }
              : s
          )
        );
      })
      .catch(() => {
        // Permit retry on transient failure.
        loadedSessionsRef.current.delete(activeId);
      });
  }, [activeId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auth guard — declared after hooks to respect rules-of-hooks.
  if (status === "unauthenticated") redirect("/login");
  if (status === "loading") return <div className="flex h-full items-center justify-center text-text-secondary">加载中...</div>;

  const createSession = async () => {
    try {
      const created: { id: string; title: string | null; createdAt: string } = await fetch("/api/chat/sessions", {
        method: "POST",
      }).then((r) => r.json());
      const newSession: Session = {
        id: created.id,
        title: created.title || "新对话",
        messages: [],
        createdAt: new Date(created.createdAt).getTime(),
      };
      loadedSessionsRef.current.add(created.id); // nothing to fetch for brand-new session
      setSessions((prev) => [newSession, ...prev]);
      setActiveId(created.id);
    } catch (err) {
      console.error("Failed to create session:", err);
    }
  };

  const deleteSession = async (id: string) => {
    if (!confirm("删除此对话？")) return;
    try {
      const res = await fetch(`/api/chat/sessions/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("delete failed");
      loadedSessionsRef.current.delete(id);
      setSessions((prev) => {
        const remaining = prev.filter((s) => s.id !== id);
        if (activeId === id) setActiveId(remaining[0]?.id || "");
        return remaining;
      });
    } catch (err) {
      console.error("Failed to delete session:", err);
    }
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || streaming) return;

    // Ensure we have a real server-backed session before sending.
    let sessionId = activeId;
    if (!sessionId) {
      try {
        const created: { id: string; title: string | null; createdAt: string } = await fetch("/api/chat/sessions", {
          method: "POST",
        }).then((r) => r.json());
        sessionId = created.id;
        loadedSessionsRef.current.add(created.id);
        setSessions((prev) => [
          {
            id: created.id,
            title: text.slice(0, 20),
            messages: [],
            createdAt: new Date(created.createdAt).getTime(),
          },
          ...prev,
        ]);
        setActiveId(created.id);
      } catch (err: any) {
        console.error("Failed to create session:", err);
        return;
      }
    }

    const userMsg: Message = { role: "user", content: text };
    const assistantMsg: Message = { role: "assistant", content: "", toolCalls: [] };

    setSessions((prev) => prev.map((s) =>
      s.id === sessionId ? {
        ...s,
        title: s.messages.length === 0 ? text.slice(0, 20) : s.title,
        messages: [...s.messages, userMsg, assistantMsg],
      } : s
    ));

    setInput("");
    setStreaming(true);

    try {
      const fd = new FormData();
      fd.append("message", text);
      if (pendingFile) {
        fd.append("file", pendingFile);
        setPendingFile(null);
      }
      const res = await fetch(`/api/chat/sessions/${sessionId}/send`, {
        method: "POST",
        body: fd,
        // No Content-Type header — browser sets multipart boundary
      });

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response stream");
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
          let event = "";
          let data = "";
          for (const line of part.split("\n")) {
            if (line.startsWith("event: ")) event = line.slice(7).trim();
            else if (line.startsWith("data: ")) data += line.slice(6);
          }
          if (!data) continue;

          try {
            const payload = JSON.parse(data);
            setSessions((prev) => prev.map((s) => {
              if (s.id !== sessionId) return s;
              const msgs = [...s.messages];
              const last = { ...msgs[msgs.length - 1] };
              if (event === "skill") last.skill = payload;
              else if (event === "status") last.status = payload.text;
              else if (event === "tool") last.toolCalls = [...(last.toolCalls || []), payload];
              else if (event === "token") last.content = (last.content || "") + (payload.text || "");
              else if (event === "done" && payload.message) last.content = payload.message;
              else if (event === "error") last.content = `错误: ${payload.message}`;
              msgs[msgs.length - 1] = last;
              return { ...s, messages: msgs };
            }));
          } catch (e) {
            console.warn("[chat] SSE parse failed", { event, data, error: e });
          }
        }
      }
    } catch (err: any) {
      setSessions((prev) => prev.map((s) => {
        if (s.id !== sessionId) return s;
        const msgs = [...s.messages];
        const last = { ...msgs[msgs.length - 1] };
        // Append error rather than replace — preserves streamed tokens + tool calls
        const suffix = `\n\n[连接中断: ${err.message}]`;
        last.content = (last.content || "") + suffix;
        msgs[msgs.length - 1] = last;
        return { ...s, messages: msgs };
      }));
    } finally {
      setStreaming(false);
    }
  };

  return (
    <div className="flex h-full">
      <div className="w-56 border-r border-gray-200 p-3 hidden lg:flex flex-col">
        <button
          onClick={createSession}
          className="flex items-center gap-2 px-3 py-2 bg-accent text-white rounded text-sm hover:bg-accent-hover mb-3"
        >
          <Plus size={14} />
          新对话
        </button>
        <h3 className="text-xs font-medium text-text-secondary uppercase mb-2">历史对话</h3>
        <div className="flex-1 overflow-auto space-y-1">
          {sessions.length === 0 && (
            <p className="text-xs text-text-secondary">还没有对话</p>
          )}
          {sessions.map((s) => (
            <div
              key={s.id}
              onClick={() => setActiveId(s.id)}
              className={`group flex items-center justify-between px-2 py-1.5 rounded text-xs cursor-pointer ${
                activeId === s.id ? "bg-accent-glow text-accent" : "text-text-secondary hover:bg-data"
              }`}
            >
              <span className="truncate flex-1">{s.title}</span>
              <button
                onClick={(e) => { e.stopPropagation(); deleteSession(s.id); }}
                className="opacity-0 group-hover:opacity-100 text-text-secondary hover:text-red-500"
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col">
        <div className="flex-1 overflow-auto p-6">
          {messages.length === 0 && (
            <div className="text-center mt-24 text-text-secondary max-w-md mx-auto">
              <h2 className="text-2xl font-bold text-text-primary mb-3">有什么可以帮你的？</h2>
              <p className="text-sm mb-6">关于你的业务数据，问我任何问题</p>
              <div className="text-left bg-surface border border-gray-200 rounded-lg p-4">
                <p className="text-xs font-medium text-text-secondary mb-2">试试这些问题：</p>
                <div className="space-y-1 text-xs">
                  <button onClick={() => setInput("帮我看看最近的订单情况")} className="block text-left text-accent hover:underline">
                    · 帮我看看最近的订单情况
                  </button>
                  <button onClick={() => setInput("各类别的销售数据对比")} className="block text-left text-accent hover:underline">
                    · 各类别的销售数据对比
                  </button>
                  <button onClick={() => setInput("有哪些异常的数据值得关注？")} className="block text-left text-accent hover:underline">
                    · 有哪些异常的数据值得关注？
                  </button>
                </div>
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className="mb-6">
              {msg.role === "user" ? (
                <div className="flex justify-end">
                  <div className="bg-accent text-white rounded-lg px-4 py-2 text-sm max-w-[70%]">
                    {msg.content}
                  </div>
                </div>
              ) : (
                <div className="space-y-2 max-w-[85%]">
                  {msg.skill && (
                    <div className="text-xs text-text-secondary">
                      <span className="text-cool">▸</span> 技能: <code className="text-accent">{msg.skill.name}</code>
                      <span className="ml-2 text-text-secondary">{msg.skill.reasoning}</span>
                    </div>
                  )}

                  {msg.toolCalls?.map((tc, j) => {
                    const chartable = tc.status === "success" && detectChartable(tc.result);
                    const rows = tc.result?.matched ? oagToCsvRows(tc.result) : [];
                    return (
                      <div key={j}>
                        <details className="bg-surface border border-gray-200 rounded text-xs">
                          <summary className="cursor-pointer p-2 text-text-secondary flex items-center">
                            <span className={tc.status === "success" ? "text-cool" : "text-red-500"}>
                              {tc.status === "success" ? "✓" : "✗"}
                            </span>
                            <span className="ml-1">调用 <code className="text-accent">{tc.toolName}</code></span>
                            {tc.result?.matched && (
                              <span className="text-text-secondary ml-2">
                                → {tc.result.matched.length} 条结果
                              </span>
                            )}
                            {rows.length > 0 && (
                              <button
                                onClick={(e) => {
                                  e.preventDefault();
                                  downloadCsv(`${tc.toolName}-${Date.now()}.csv`, rows);
                                }}
                                className="ml-auto px-2 py-0.5 border border-gray-200 rounded text-xs text-text-secondary hover:bg-data"
                              >
                                导出 CSV
                              </button>
                            )}
                          </summary>
                          <pre className="p-2 bg-data overflow-auto max-h-48 text-text-data">
                            {JSON.stringify({ args: tc.args, result: tc.result }, null, 2)}
                          </pre>
                        </details>
                        {chartable && <ChartView result={tc.result} />}
                      </div>
                    );
                  })}

                  {streaming && i === messages.length - 1 && msg.status && (
                    <div className="text-xs text-text-secondary italic animate-pulse">
                      {msg.status}
                    </div>
                  )}

                  {msg.content && (
                    <div className="bg-surface border border-gray-200 rounded-lg px-4 py-3 text-sm whitespace-pre-wrap text-text-primary">
                      {msg.content}
                      {streaming && i === messages.length - 1 && <span className="inline-block w-2 h-4 bg-accent ml-1 animate-pulse" />}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        <div className="border-t border-gray-200 p-4">
          <div className="flex gap-2 items-center">
            <label className="cursor-pointer px-3 py-2 border border-gray-200 rounded-lg text-text-secondary hover:bg-data text-sm">
              📎
              <input
                type="file"
                accept=".csv,.xlsx,.xls"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) setPendingFile(f);
                  e.target.value = "";
                }}
              />
            </label>
            {pendingFile && (
              <span className="text-xs text-accent truncate max-w-32">
                {pendingFile.name}
              </span>
            )}
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="输入问题..."
              disabled={streaming}
              className="flex-1 px-4 py-2 border border-gray-200 rounded-lg bg-root text-sm text-text-primary focus:outline-none focus:border-accent"
            />
            <button
              onClick={handleSend}
              disabled={streaming || !input.trim()}
              className="px-6 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent-hover transition-colors disabled:opacity-50"
            >
              {streaming ? "分析中..." : "发送"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
