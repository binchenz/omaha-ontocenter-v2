import { streamText, type CoreMessage } from "ai";
import { z } from "zod";
import { Tool } from "./tool-registry";
import { llmModel } from "./llm";
import { UPLOAD_MARKER } from "@/lib/constants";

export interface ToolCallEvent {
  toolName: string;
  args: any;
  result: any;
  status: "success" | "error";
}

export async function executeReactStream(
  question: string,
  skillInstructions: string,
  tools: Record<string, Tool>,
  onToolCall: (call: ToolCallEvent) => void,
  onToken: (token: string) => void,
  history: CoreMessage[] = [],
): Promise<void> {
  const system = `你是中小企业数据分析助手。

${skillInstructions}

用中文清晰回答用户问题。
- 数据用具体数字说话
- 给出业务洞察，不仅是数字
- 严格基于对话历史中的真实信息回答，绝不编造表名/列名/数值`;

  const aiTools: Record<string, any> = {};
  for (const [name, t] of Object.entries(tools)) {
    aiTools[name] = {
      description: t.description,
      parameters: schemaForTool(name),
      execute: async (args: any) => {
        try {
          const result = await t.execute(args);
          onToolCall({ toolName: name, args, result, status: "success" });
          return result;
        } catch (err: any) {
          const errResult = { error: err.message };
          onToolCall({ toolName: name, args, result: errResult, status: "error" });
          return errResult;
        }
      },
    };
  }

  const messages: CoreMessage[] = [
    ...history,
    { role: "user", content: question },
  ];

  try {
    const result = streamText({
      model: llmModel,
      system,
      messages,
      maxSteps: 5,
      tools: aiTools,
    });

    for await (const chunk of result.textStream) {
      onToken(chunk);
    }
  } catch (err: any) {
    onToken(`\n\n[错误] ${err.message}`);
  }
}


/** Different tools accept different parameter shapes — pick the right zod schema.
 *  MUST stay in sync with mcp-adapter.ts:schemaForToolName (which encodes the
 *  same constraints as JSON Schema for MCP clients). When adding a new tool
 *  family, edit BOTH files.
 */
function schemaForTool(name: string) {
  if (name.startsWith("search_")) {
    return z.object({
      filters: z.record(z.any()).optional().describe("按列过滤，如 {status: 'shipped'}"),
      limit: z.number().int().optional().describe("返回数量上限，默认 10"),
    });
  }
  if (name.startsWith("aggregate_")) {
    return z.object({
      measures: z.array(z.string()).describe("聚合表达式，如 SUM(amount) 或 COUNT(*) AS cnt"),
      group_by: z.array(z.string()).optional().describe("分组字段"),
      filters: z.record(z.any()).optional(),
    });
  }
  if (name.startsWith("count_")) {
    return z.object({
      filters: z.record(z.any()).optional(),
    });
  }
  if (name === "navigate_path") {
    return z.object({
      start_object: z.string().describe("起始对象 slug"),
      start_id: z.string().describe("起始对象主键值"),
      path: z.array(z.string()).describe("依次经过的对象 slug 列表"),
    });
  }
  if (name === "call_function") {
    return z.object({
      function_name: z.string(),
      kwargs: z.record(z.any()).optional(),
    });
  }
  if (name === "create_ontology") {
    return z.object({
      table_name: z.string().describe(`数据表名（英文，来自 ${UPLOAD_MARKER} 段）`),
      display_name: z.string().describe("业务名（中文，从列名推断，如 '订单''客户''商品'，绝不能是 'Data' 或 '数据'）"),
      columns: z.array(z.object({
        name: z.string(),
        semantic_type: z.string(),
      })).describe("列定义"),
    });
  }
  if (name === "list_my_data") {
    return z.object({});
  }
  // Safe fallback
  return z.object({}).passthrough();
}
