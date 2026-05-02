import type { Tool } from "./tool-registry";

/**
 * MCP tools/list descriptor: name + description + JSON Schema input.
 * Mirrors the zod schemas in react.ts:schemaForTool, translated to JSON Schema
 * because MCP clients (the assistant Desktop, Cursor) expect plain JSON Schema.
 */
export interface McpToolDescriptor {
  name: string;
  description: string;
  inputSchema: object;
}

export function toolToMcpDescriptor(name: string, tool: Tool): McpToolDescriptor {
  return {
    name,
    description: tool.description,
    inputSchema: schemaForToolName(name),
  };
}

/** Different tool families accept different parameter shapes.
 *  JSON Schema for MCP tools/list. MUST stay in sync with
 *  react.ts:schemaForTool (which uses zod for the same constraints).
 *  When adding a new tool family, edit BOTH files.
 */
function schemaForToolName(name: string): object {
  if (name.startsWith("search_")) {
    return {
      type: "object",
      properties: {
        filters: {
          type: "object",
          description: "按列过滤，如 {status: 'shipped'}",
          additionalProperties: true,
        },
        limit: {
          type: "integer",
          description: "返回数量上限，默认 10",
          default: 10,
        },
      },
      additionalProperties: false,
    };
  }
  if (name.startsWith("aggregate_")) {
    return {
      type: "object",
      properties: {
        measures: {
          type: "array",
          items: { type: "string" },
          description: "聚合表达式，如 SUM(amount) 或 COUNT(*) AS cnt",
        },
        group_by: {
          type: "array",
          items: { type: "string" },
          description: "分组字段",
        },
        filters: { type: "object", additionalProperties: true },
      },
      required: ["measures"],
      additionalProperties: false,
    };
  }
  if (name.startsWith("count_")) {
    return {
      type: "object",
      properties: {
        filters: { type: "object", additionalProperties: true },
      },
      additionalProperties: false,
    };
  }
  if (name === "navigate_path") {
    return {
      type: "object",
      properties: {
        start_object: { type: "string", description: "起始对象 slug" },
        start_id: { type: "string", description: "起始对象主键值" },
        path: {
          type: "array",
          items: { type: "string" },
          description: "依次经过的对象 slug 列表",
        },
      },
      required: ["start_object", "start_id", "path"],
      additionalProperties: false,
    };
  }
  if (name === "call_function") {
    return {
      type: "object",
      properties: {
        function_name: { type: "string" },
        kwargs: { type: "object", additionalProperties: true },
      },
      required: ["function_name"],
      additionalProperties: false,
    };
  }
  if (name === "list_my_data") {
    return { type: "object", additionalProperties: false };
  }
  if (name === "create_ontology") {
    return {
      type: "object",
      properties: {
        table_name: { type: "string", description: "数据表名（英文）" },
        display_name: { type: "string", description: "业务名（中文）" },
        columns: {
          type: "array",
          items: {
            type: "object",
            properties: {
              name: { type: "string" },
              semantic_type: { type: "string" },
            },
            required: ["name", "semantic_type"],
          },
        },
      },
      required: ["table_name", "display_name", "columns"],
    };
  }
  // Permissive fallback for unknown tools.
  return { type: "object", additionalProperties: true };
}
