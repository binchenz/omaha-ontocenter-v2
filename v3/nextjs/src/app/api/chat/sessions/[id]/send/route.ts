import { NextRequest, NextResponse } from "next/server";
import type { CoreMessage } from "ai";
import { routeToSkill } from "@/app/agent/skill-router";
import { executeReactStream } from "@/app/agent/react";
import { SKILL_STATUS, SKILLS } from "@/app/agent/skills";
import { prisma } from "@/lib/prisma";
import { getSessionContext, ownedSessionWhere } from "@/lib/session";
import { DEFAULT_SESSION_TITLE, MAX_HISTORY_MESSAGES } from "@/lib/constants";
import { ingestUploadedFile } from "./ingestFile";
import { applyStickyDataIngest } from "./resolveSkill";
import { buildToolset } from "./buildToolset";

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
          try {
            fileContext = await ingestUploadedFile(file, tenantId);
          } catch (err: any) {
            send("error", { message: `文件解析失败: ${err.message}` });
            controller.close();
            return;
          }
        }
        if (closed) return;

        const fullMessage = message + fileContext;
        const [routed, historyRows] = await Promise.all([
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
        const isFirstTurn = historyRows.length === 0;

        const { skill, reasoning } = applyStickyDataIngest(routed, !!file, historyRows);
        send("skill", { name: skill.frontmatter.name, reasoning });

        if (closed) return;
        const tools = await buildToolset(tenantId, skill.frontmatter.name);

        // ai-sdk rejects roles other than user/assistant in CoreMessage[].
        const history: CoreMessage[] = [...historyRows]
          .reverse()
          .filter((m): m is { role: "user" | "assistant"; content: string } =>
            m.role === "user" || m.role === "assistant")
          .map((m) => ({ role: m.role, content: m.content }));

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
        // For upload turns, persist the FULL message (with the `[文件已上传]`
        // marker) so the next turn's router can detect "post-upload" state and
        // keep data-ingest sticky for one more turn.
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
