import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import type { CoreMessage } from "ai";
import { authOptions } from "@/lib/auth";
import { routeToSkill } from "@/app/agent/skill-router";
import { loadAllTools, buildIngestTools, type Tool } from "@/app/agent/tool-registry";
import { executeReactStream } from "@/app/agent/react";
import { DATA_SKILLS, SKILL_STATUS } from "@/app/agent/skills";
import { ingestApi, ontologyApi } from "@/services/pythonApi";
import type { OntologySchema } from "@/types/api";
import { prisma } from "@/lib/prisma";

// Cap prior-turn history sent to the LLM. Too long → cost + context pollution.
const MAX_HISTORY_TURNS = 12;

export async function POST(req: NextRequest, { params }: { params: { id: string } }) {
  const session = await getServerSession(authOptions);
  if (!session?.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const tenantId = (session.user as any).tenantId || "default";
  const sessionId = params.id;

  const formData = await req.formData();
  const message = formData.get("message") as string || "";
  const file = formData.get("file") as File | null;

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      let closed = false;
      let fullResponse = "";
      const allToolCalls: any[] = [];
      const send = (event: string, data: any) => {
        if (closed) return;
        try {
          controller.enqueue(encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`));
        } catch {
          closed = true;
        }
      };

      const abort = () => { closed = true; };
      req.signal.addEventListener("abort", abort);

      try {
        let fileContext = "";
        if (file) {
          send("status", { text: SKILL_STATUS["data-ingest"] });
          const fd = new FormData();
          fd.append("type", file.name.endsWith(".csv") ? "csv" : "excel");
          fd.append("file", file);
          fd.append("tenant_id", tenantId);
          try {
            const ingestResult = await ingestApi.ingest(fd);
            const cols = ingestResult.columns.map((c: any) => `${c.name}(${c.semantic_type})`).join(", ");
            fileContext = `\n\n[文件已上传] 表名: ${ingestResult.table_name}, ${ingestResult.rows_count} 行, 列: ${cols}, dataset_id: ${ingestResult.dataset_id}`;
          } catch (err: any) {
            send("error", { message: `文件解析失败: ${err.message}` });
            controller.close();
            return;
          }
        }

        if (closed) return;

        // Route + ontology fetch + chat history run concurrently — no data dependency.
        const fullMessage = message + fileContext;
        const [routeResult, ontList, historyRows] = await Promise.all([
          routeToSkill(fullMessage, !!file),
          ontologyApi.list(tenantId).catch((e) => {
            console.warn("[chat/send] ontology list failed:", e);
            return [] as OntologySchema[];
          }),
          prisma.chatMessage.findMany({
            where: { sessionId },
            orderBy: { createdAt: "desc" },
            take: MAX_HISTORY_TURNS,
            select: { role: true, content: true },
          }).catch((e) => {
            console.warn("[chat/send] history fetch failed:", e);
            return [] as Array<{ role: string; content: string }>;
          }),
        ]);
        const { skill, reasoning } = routeResult;
        send("skill", { name: skill.frontmatter.name, reasoning });

        // Oldest-first, filter to user/assistant only (ai-sdk rejects other roles).
        const history: CoreMessage[] = historyRows
          .reverse()
          .filter((m) => m.role === "user" || m.role === "assistant")
          .map((m) => ({ role: m.role as "user" | "assistant", content: m.content }));

        if (closed) return;

        const tools: Record<string, Tool> = {
          ...buildIngestTools(tenantId, { includeCreate: skill.frontmatter.name === "data-ingest" }),
        };

        // Only load ontology-derived tools when the active skill needs them.
        if (DATA_SKILLS.has(skill.frontmatter.name) && ontList.length > 0) {
          const schemas = await Promise.all(
            ontList.map((o: { id: string }) =>
              ontologyApi.getSchema(o.id, tenantId).catch((e) => {
                console.warn(`[chat/send] schema fetch failed for ${o.id}:`, e);
                return null;
              })
            )
          );
          Object.assign(tools, await loadAllTools(schemas.filter(Boolean) as OntologySchema[], tenantId));
        }

        if (closed) return;

        send("status", { text: SKILL_STATUS[skill.frontmatter.name] || "处理中..." });

        await executeReactStream(
          fullMessage,
          skill.body,
          tools,
          (toolCall) => {
            allToolCalls.push(toolCall);
            send("tool", toolCall);
          },
          (token) => {
            fullResponse += token;
            send("token", { text: token });
          },
          history,
        );

        // Persist messages after stream completes — best-effort, never fail the response.
        try {
          await prisma.chatMessage.createMany({
            data: [
              { sessionId, role: "user", content: fullMessage },
              {
                sessionId,
                role: "assistant",
                content: fullResponse,
                toolCalls: allToolCalls.length > 0 ? JSON.stringify(allToolCalls) : null,
              },
            ],
          });
          const trimmed = message.trim();
          if (trimmed) {
            // Only rename the default placeholder — preserve user-edited titles.
            await prisma.chatSession.updateMany({
              where: { id: sessionId, title: "新对话" },
              data: { title: trimmed.slice(0, 30) },
            });
          }
        } catch (e) {
          console.warn("[chat/send] Failed to persist messages:", e);
        }

        send("done", {});
      } catch (err: any) {
        send("error", { message: err.message || "处理请求时出错" });
      } finally {
        req.signal.removeEventListener("abort", abort);
        if (!closed) controller.close();
      }
    },
  });

  return new NextResponse(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
