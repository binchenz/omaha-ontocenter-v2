import { NextRequest, NextResponse } from "next/server";
import { getBearerContext } from "@/lib/bearerAuth";
import { ontologyApi } from "@/services/pythonApi";
import { loadAllTools } from "@/app/agent/tool-registry";
import { toolToMcpDescriptor } from "@/app/agent/mcp-adapter";
import type { OntologySchema } from "@/types/api";
import type { SessionContext } from "@/lib/session";

interface JsonRpcReq {
  jsonrpc: "2.0";
  id?: string | number | null;
  method: string;
  params?: any;
}

const PROTOCOL_VERSION = "2024-11-05";

export async function POST(req: NextRequest) {
  const body = (await req.json().catch(() => null)) as JsonRpcReq | null;

  if (!body || body.jsonrpc !== "2.0" || typeof body.method !== "string") {
    return jsonRpcError(null, -32600, "Invalid Request", 400);
  }

  // Notifications (no id) skip auth + just ack 204.
  // For now we treat any incoming notification as a no-op acknowledged with 204.
  if (body.id === undefined) {
    return new NextResponse(null, { status: 204 });
  }

  const ctx = await getBearerContext(req);
  if (!ctx) {
    return jsonRpcError(body.id, -32001, "Unauthorized", 401);
  }

  try {
    const result = await dispatch(body.method, body.params || {}, ctx);
    return NextResponse.json({ jsonrpc: "2.0", id: body.id, result });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return jsonRpcError(body.id, -32000, msg, 200);
  }
}

function jsonRpcError(
  id: string | number | null | undefined,
  code: number,
  message: string,
  httpStatus: number,
) {
  return NextResponse.json(
    { jsonrpc: "2.0", id: id ?? null, error: { code, message } },
    { status: httpStatus },
  );
}

async function dispatch(
  method: string,
  params: any,
  ctx: SessionContext,
): Promise<unknown> {
  if (method === "initialize") {
    return {
      protocolVersion: PROTOCOL_VERSION,
      capabilities: { tools: {} },
      serverInfo: { name: "ontocenter-v3", version: "0.1.0" },
    };
  }

  if (method === "tools/list") {
    const schemas = (await ontologyApi.listSchemas(ctx.tenantId, { limit: 500 })) as OntologySchema[];
    const tools = loadAllTools(schemas, ctx.tenantId);
    return {
      tools: Object.entries(tools).map(([name, t]) => toolToMcpDescriptor(name, t)),
    };
  }

  if (method === "tools/call") {
    const toolName = String(params?.name || "");
    const args = params?.arguments || {};
    if (!toolName) throw new Error("tools/call requires `name`");

    const schemas = (await ontologyApi.listSchemas(ctx.tenantId, { limit: 500 })) as OntologySchema[];
    const tools = loadAllTools(schemas, ctx.tenantId);
    const tool = tools[toolName];
    if (!tool) throw new Error(`Unknown tool: ${toolName}`);

    const result = await tool.execute(args);
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  }

  throw new Error(`Method not found: ${method}`);
}
