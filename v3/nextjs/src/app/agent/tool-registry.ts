import { ontologyApi, datasourceApi } from "@/services/pythonApi";
import { buildOntologyYaml } from "@/lib/yaml-builder";
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
    const desc = obj.description ? ` ${obj.description}` : "";
    tools[`search_${qualifier}`] = {
      name: `search_${qualifier}`,
      description: `搜索 ${obj.name}（本体: ${schema.name}）。${desc}`,
      execute: async (params) =>
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
      execute: async (params) =>
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
        const [ontologies, datasources] = await Promise.all([
          ontologyApi.list(tenantId).catch(() => []),
          datasourceApi.list(tenantId).catch(() => []),
        ]);
        // Backend returns oldest-first; cap to 10 most-recent so the LLM
        // sees recent items and the result stays ~2KB instead of 20KB.
        const recentOnt = ontologies.slice(-10).reverse();
        const recentDs = datasources.slice(-10).reverse();
        return {
          ontologies: recentOnt.map((o: OntologySchema) => ({ id: o.id, name: o.name, slug: o.slug })),
          datasources: recentDs.map((d: any) => ({
            id: d.id, name: d.name, type: d.type,
            datasets: d.datasets?.map((ds: any) => ({ table: ds.table_name, rows: ds.rows_count })),
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
        const yaml = buildOntologyYaml({ source: "upload", tableName, columns, displayName });
        return ontologyApi.create(yaml, tenantId);
      },
    };
  }
  return tools;
}
