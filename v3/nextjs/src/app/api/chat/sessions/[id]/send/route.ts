import { NextRequest, NextResponse } from "next/server";
import { routeToSkill } from "@/app/agent/skill-router";
import { loadAllTools, buildIngestTools } from "@/app/agent/tool-registry";
import { executeReactStream } from "@/app/agent/react";
import { pythonFetch } from "@/services/pythonApi";

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
        // Step 1: Handle file upload if present
        let fileContext = "";
        if (file) {
          send("status", { text: "正在解析文件..." });
          const fd = new FormData();
          fd.append("type", file.name.endsWith(".csv") ? "csv" : "excel");
          fd.append("file", file);
          try {
            const ingestResult = await pythonFetch("/ingest", { method: "POST", body: fd });
            fileContext = `\n\n[文件已上传] 表名: ${ingestResult.table_name}, ${ingestResult.rows_count} 行, 列: ${ingestResult.columns.map((c: any) => `${c.name}(${c.semantic_type})`).join(", ")}, dataset_id: ${ingestResult.dataset_id}`;
          } catch (err: any) {
            send("done", { message: `文件解析失败: ${err.message}` });
            controller.close();
            return;
          }
        }

        if (closed) return;

        // Step 2: Route to skill
        const { skill, reasoning } = await routeToSkill(message + fileContext, !!file);
        send("skill", { name: skill.frontmatter.name, reasoning });

        if (closed) return;

        // Step 3: Load tools
        let tools: Record<string, any> = {};

        // Always include ingest tools (for data-ingest skill)
        Object.assign(tools, buildIngestTools());

        // Load ontology-based tools (for data-query skill)
        try {
          const ontList = await pythonFetch("/ontology");
          if (ontList.length > 0) {
            const schemas = await Promise.all(
              ontList.map((o: any) => pythonFetch(`/ontology/${o.id}/schema`).catch(() => null))
            );
            Object.assign(tools, await loadAllTools(schemas.filter(Boolean)));
          }
        } catch {}

        if (closed) return;

        // Step 4: Execute with skill instructions
        const fullMessage = message + fileContext;
        const statusMap: Record<string, string> = {
          "data-ingest": "正在解析文件...",
          "data-query": "正在查询数据...",
          "data-explore": "正在查看数据...",
          "general-chat": "思考中...",
        };
        send("status", { text: statusMap[skill.frontmatter.name] || "处理中..." });

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
