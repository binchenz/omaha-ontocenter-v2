import { ontologyApi, datasourceApi } from "@/services/pythonApi";
import { createOntologyFromColumns } from "@/features/ontology/createOntologyFromColumns";
import type { OntologySchema } from "@/types/api";

export interface Tool {
  name: string;
  description: string;
  execute: (params: Record<string, any>) => Promise<any>;
}

function buildToolsFromSchema(
  ontologyId: string,
  schema: OntologySchema,
  tenantId: string,
): Record<string, Tool> {
  const tools: Record<string, Tool> = {};
  for (const obj of schema.objects) {
    const qualifier = `${obj.slug}_${schema.slug}`;
    const descSuffix = obj.description ? ` ${obj.description}` : "";
    const OPS: Array<{
      op: "search" | "aggregate" | "count";
      description: string;
      body: (p: any) => Record<string, unknown>;
    }> = [
      {
        op: "search",
        description: `搜索 ${obj.name}（本体: ${schema.name}）。${descSuffix}`,
        body: (p) => ({ filters: p.filters, limit: p.limit || 10 }),
      },
      {
        op: "aggregate",
        description: `按维度聚合统计 ${obj.name}（本体: ${schema.name}）`,
        body: (p) => ({ measures: p.measures || ["COUNT(*)"], group_by: p.group_by || [] }),
      },
      {
        op: "count",
        description: `统计 ${obj.name} 数量（本体: ${schema.name}）。比 search_* 更轻量 — 只返回行数，不返回行数据`,
        body: (p) => ({ filters: p.filters }),
      },
    ];
    for (const opDef of OPS) {
      const name = `${opDef.op}_${qualifier}`;
      tools[name] = {
        name,
        description: opDef.description,
        execute: async (params) =>
          ontologyApi.query(
            ontologyId,
            { operation: opDef.op, object: obj.slug, ...opDef.body(params) },
            tenantId,
          ),
      };
    }
  }
  return tools;
}

/**
 * Load tools from multiple ontologies. Names are qualified by ontology slug
 * so the LLM never confuses cross-ontology objects with the same name.
 */
export function loadAllTools(
  ontologies: OntologySchema[],
  tenantId: string,
): Record<string, Tool> {
  const merged: Record<string, Tool> = {};
  for (const schema of ontologies) {
    Object.assign(merged, buildToolsFromSchema(schema.id, schema, tenantId));
  }
  return merged;
}

/**
 * Load the full tool set for a tenant — schemas + ontology-derived tools.
 * Used by both /api/mcp/route.ts and chat send/route.ts. Does NOT include
 * ingest tools (those depend on skill context).
 */
export async function loadTenantToolSet(tenantId: string): Promise<{
  schemas: OntologySchema[];
  tools: Record<string, Tool>;
}> {
  const schemas = (await ontologyApi.listSchemas(tenantId, { limit: 500 })) as OntologySchema[];
  const tools = loadAllTools(schemas, tenantId);
  return { schemas, tools };
}

export function buildIngestTools(
  tenantId: string,
  options: { includeCreate?: boolean } = {},
): Record<string, Tool> {
  const { includeCreate = true } = options;
  const tools: Record<string, Tool> = {
    list_my_data: {
      name: "list_my_data",
      description: "列出用户最近的数据集和本体（按创建时间倒序），用于判断用户问的数据是否已存在",
      execute: async () => {
        // Backend already returns the 10 most-recent in desc order — no
        // client-side slice/reverse needed. Result stays ~2KB instead of 20KB
        // on tenants with thousands of items.
        const [ontologies, datasources] = await Promise.all([
          ontologyApi.list(tenantId, { limit: 10, order: "desc" }).catch(() => []),
          datasourceApi.list(tenantId, { limit: 10, order: "desc" }).catch(() => []),
        ]);
        return {
          ontologies: ontologies.map((o) => ({ id: o.id, name: o.name, slug: o.slug })),
          datasources: datasources.map((d) => ({
            id: d.id, name: d.name, type: d.type,
            datasets: d.datasets?.map((ds) => ({ table: ds.table_name, rows: ds.rows_count })),
          })),
        };
      },
    },
  };
  if (includeCreate) {
    tools.create_ontology = {
      name: "create_ontology",
      description: "根据数据 schema 自动生成本体并注册，用户不需要看到 YAML。必须传 display_name（业务名，如'订单''客户'），LLM 从列名推断",
      execute: async (params) => {
        const columns = params.columns as Array<{ name: string; semantic_type: string }>;
        const tableName = params.table_name || "data";
        const displayName = params.display_name?.trim() || undefined;
        return createOntologyFromColumns({
          source: "upload",
          tableName,
          columns,
          displayName,
          tenantId,
        });
      },
    };
  }
  return tools;
}
