import { NextRequest, NextResponse } from "next/server";
import type { CoreMessage } from "ai";
import { routeToSkill } from "@/app/agent/skill-router";
import { loadAllTools, buildIngestTools, type Tool } from "@/app/agent/tool-registry";
import { executeReactStream } from "@/app/agent/react";
import { DATA_SKILLS, SKILL_STATUS, SKILLS } from "@/app/agent/skills";
import { ingestApi, ontologyApi } from "@/services/pythonApi";
import type { OntologySchema } from "@/types/api";
import { prisma } from "@/lib/prisma";
import { getSessionContext, ownedSessionWhere } from "@/lib/session";
import { DEFAULT_SESSION_TITLE, MAX_HISTORY_MESSAGES } from "@/lib/constants";

export async function POST(req: NextRequest, { params }: { params: { id: string } }) {
  const ctx = await getSessionContext();
  if (!ctx) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { tenantId } = ctx;
  const sessionId = params.id;

  const formData = await req.formData();
  const message = String(formData.get("message") ?? "");
  const file = formData.get("file") as File | null;

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      let closed = false;
      let fullResponse = "";
      const allToolCalls: unknown[] = [];
      const send = (event: string, data: unknown) => {
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
          send("status", { text: SKILL_STATUS[SKILLS.DATA_INGEST] });
          const fd = new FormData();
          fd.append("type", file.name.endsWith(".csv") ? "csv" : "excel");
          fd.append("file", file);
          fd.append("tenant_id", tenantId);
          try {
            const ingestResult = await ingestApi.ingest(fd);
            const cols = ingestResult.columns
              .map((c) => `${c.name}(${c.semantic_type})`)
              .join(", ");
            fileContext = `\n\n[文件已上传] 表名: ${ingestResult.table_name}, ${ingestResult.rows_count} 行, 列: ${cols}, dataset_id: ${ingestResult.dataset_id}`;
          } catch (err: any) {
            send("error", { message: `文件解析失败: ${err.message}` });
            controller.close();
            return;
          }
        }

        if (closed) return;

        const fullMessage = message + fileContext;
        const [routeResult, historyRows] = await Promise.all([
          routeToSkill(fullMessage, !!file),
          prisma.chatMessage.findMany({
            where: { sessionId },
            orderBy: { createdAt: "desc" },
            take: MAX_HISTORY_MESSAGES,
            select: { role: true, content: true },
          }).catch((e) => {
            console.warn("[chat/send] history fetch failed:", e);
            return [] as Array<{ role: string; content: string }>;
          }),
        ]);
        const { skill, reasoning } = routeResult;
        const isFirstTurn = historyRows.length === 0;
        send("skill", { name: skill.frontmatter.name, reasoning });

        // listSchemas only matters for data-query/data-explore — general-chat
        // and data-ingest never consume ontology search/aggregate tools.
        // Skipping the fetch on ~80% of turns (greetings + ingest) saves a
        // 40-80KB HTTP roundtrip. The sequential cost for data-* skills
        // (~20-50ms) is a worthwhile trade for the dominant case.
        let schemas: OntologySchema[] = [];
        if (DATA_SKILLS.has(skill.frontmatter.name)) {
          schemas = await ontologyApi
            .listSchemas(tenantId, { limit: 500, order: "desc" })
            .catch((e) => {
              console.warn("[chat/send] listSchemas failed:", e);
              return [] as OntologySchema[];
            });
        }

        // ai-sdk rejects roles other than user/assistant in CoreMessage[].
        const history: CoreMessage[] = [...historyRows]
          .reverse()
          .filter((m): m is { role: "user" | "assistant"; content: string } =>
            m.role === "user" || m.role === "assistant")
          .map((m) => ({ role: m.role, content: m.content }));

        if (closed) return;

        const tools: Record<string, Tool> = {
          ...buildIngestTools(tenantId, {
            includeCreate: skill.frontmatter.name === SKILLS.DATA_INGEST,
          }),
        };

        if (DATA_SKILLS.has(skill.frontmatter.name) && schemas.length > 0) {
          Object.assign(tools, loadAllTools(schemas, tenantId));
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

        // Persist after stream — best-effort, never fail the response.
        // Store the CLEAN user message (not fullMessage); the "[文件已上传]…"
        // context was only for the LLM's single-turn input, and persisting
        // it would leak dataset_id / schema hints into the user bubble on
        // page reload.
        try {
          await prisma.chatMessage.createMany({
            data: [
              { sessionId, role: "user", content: message },
              {
                sessionId,
                role: "assistant",
                content: fullResponse,
                toolCalls: allToolCalls.length > 0 ? JSON.stringify(allToolCalls) : null,
              },
            ],
          });
          const trimmed = message.trim();
          // Auto-rename only on the first turn to preserve user-edited titles.
          // Scope by tenant+user so one user cannot rename another's session
          // if the session id is guessed.
          if (isFirstTurn && trimmed) {
            await prisma.chatSession.updateMany({
              where: { ...ownedSessionWhere(ctx, sessionId), title: DEFAULT_SESSION_TITLE },
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
