import { ontologyApi, datasourceApi } from "@/services/pythonApi";
import { buildOntologyYaml } from "@/lib/yaml-builder";
import type { OntologySchema } from "@/types/api";

export interface Tool {
  name: string;
  description: string;
  execute: (params: Record<string, any>) => Promise<any>;
}

export async function loadTools(ontologyId: string, tenantId = "default"): Promise<Record<string, Tool>> {
  try {
    const schema: OntologySchema = await ontologyApi.getSchema(ontologyId, tenantId);
    return buildToolsFromSchema(ontologyId, schema, tenantId);
  } catch {
    return {};
  }
}

export function buildToolsFromSchema(
  ontologyId: string,
  schema: OntologySchema,
  tenantId = "default",
): Record<string, Tool> {
  const tools: Record<string, Tool> = {};
  for (const obj of schema.objects) {
    const qualifier = `${obj.slug}_${schema.slug}`;
    tools[`search_${qualifier}`] = {
      name: `search_${qualifier}`,
      description: `搜索 ${obj.name}（本体: ${schema.name}）。${obj.description || ""}`,
      execute: async (params: Record<string, any>) =>
        ontologyApi.query(
          ontologyId,
          {
            operation: "search",
            object: obj.slug,
            filters: params.filters,
            limit: params.limit || 10,
          },
          tenantId,
        ),
    };

    tools[`aggregate_${qualifier}`] = {
      name: `aggregate_${qualifier}`,
      description: `按维度聚合统计 ${obj.name}（本体: ${schema.name}）`,
      execute: async (params: Record<string, any>) =>
        ontologyApi.query(
          ontologyId,
          {
            operation: "aggregate",
            object: obj.slug,
            measures: params.measures || ["COUNT(*)"],
            group_by: params.group_by || [],
          },
          tenantId,
        ),
    };
  }
  return tools;
}

/**
 * Load tools from multiple ontologies — all names qualified by ontology slug
 * so the LLM can never confuse cross-ontology objects with the same name.
 */
export async function loadAllTools(
  ontologies: OntologySchema[],
  tenantId = "default",
): Promise<Record<string, Tool>> {
  const merged: Record<string, Tool> = {};
  for (const schema of ontologies) {
    Object.assign(merged, buildToolsFromSchema(schema.id, schema, tenantId));
  }
  return merged;
}

export function buildIngestTools(tenantId = "default"): Record<string, Tool> {
  return {
    create_ontology: {
      name: "create_ontology",
      description: "根据数据 schema 自动生成本体并注册，用户不需要看到 YAML。必须传 display_name（业务名，如'订单''客户'），LLM 从列名推断",
      execute: async (params: Record<string, any>) => {
        const columns = params.columns as Array<{ name: string; semantic_type: string }>;
        const tableName = params.table_name || "data";
        const displayName = params.display_name?.trim() || undefined;
        const yaml = buildOntologyYaml({ source: "upload", tableName, columns, displayName });
        return ontologyApi.create(yaml, tenantId);
      },
    },
    list_my_data: {
      name: "list_my_data",
      description: "列出用户已有的所有数据集和本体，用于判断用户问的数据是否已存在",
      execute: async () => {
        const [ontologies, datasources] = await Promise.all([
          ontologyApi.list(tenantId).catch(() => []),
          datasourceApi.list(tenantId).catch(() => []),
        ]);
        return {
          ontologies: ontologies.map((o: any) => ({ id: o.id, name: o.name, slug: o.slug })),
          datasources: datasources.map((d: any) => ({
            id: d.id, name: d.name, type: d.type,
            datasets: d.datasets?.map((ds: any) => ({ table: ds.table_name, rows: ds.rows_count })),
          })),
        };
      },
    },
  };
}
