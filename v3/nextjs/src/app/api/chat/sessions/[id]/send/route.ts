import { NextRequest, NextResponse } from "next/server";
import { routeToSkill } from "@/app/agent/skill-router";
import { loadAllTools, buildIngestTools, type Tool } from "@/app/agent/tool-registry";
import { executeReactStream } from "@/app/agent/react";
import { DATA_SKILLS, SKILL_STATUS } from "@/app/agent/skills";
import { ingestApi, ontologyApi } from "@/services/pythonApi";
import type { OntologySchema } from "@/types/api";

export async function POST(req: NextRequest, { params }: { params: { id: string } }) {
  const formData = await req.formData();
  const message = formData.get("message") as string || "";
  const file = formData.get("file") as File | null;

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      let closed = false;
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

        // Route + ontology fetch run concurrently — they have no data dependency.
        const fullMessage = message + fileContext;
        const [routeResult, ontList] = await Promise.all([
          routeToSkill(fullMessage, !!file),
          ontologyApi.list().catch((e) => {
            console.warn("[chat/send] ontology list failed:", e);
            return [] as OntologySchema[];
          }),
        ]);
        const { skill, reasoning } = routeResult;
        send("skill", { name: skill.frontmatter.name, reasoning });

        if (closed) return;

        const tools: Record<string, Tool> = { ...buildIngestTools() };

        // Only load ontology-derived tools when the active skill needs them.
        if (DATA_SKILLS.has(skill.frontmatter.name) && ontList.length > 0) {
          const schemas = await Promise.all(
            ontList.map((o: { id: string }) =>
              ontologyApi.getSchema(o.id).catch((e) => {
                console.warn(`[chat/send] schema fetch failed for ${o.id}:`, e);
                return null;
              })
            )
          );
          Object.assign(tools, await loadAllTools(schemas.filter(Boolean) as OntologySchema[]));
        }

        if (closed) return;

        send("status", { text: SKILL_STATUS[skill.frontmatter.name] || "处理中..." });

        await executeReactStream(
          fullMessage,
          skill.body,
          tools,
          (toolCall) => send("tool", toolCall),
          (token) => send("token", { text: token }),
        );

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
