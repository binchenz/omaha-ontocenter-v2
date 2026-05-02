import { pythonFetch } from "@/services/pythonApi";
import type { OntologySchema } from "@/types/api";

export interface Tool {
  name: string;
  description: string;
  execute: (params: Record<string, any>) => Promise<any>;
}

export async function loadTools(ontologyId: string): Promise<Record<string, Tool>> {
  try {
    const schema: OntologySchema = await pythonFetch(`/ontology/${ontologyId}/schema`);
    return buildToolsFromSchema(ontologyId, schema);
  } catch {
    return {};
  }
}

export function buildToolsFromSchema(ontologyId: string, schema: OntologySchema): Record<string, Tool> {
  const tools: Record<string, Tool> = {};
  for (const obj of schema.objects) {
    const qualifier = `${obj.slug}_${schema.slug}`;
    tools[`search_${qualifier}`] = {
      name: `search_${qualifier}`,
      description: `搜索 ${obj.name}（本体: ${schema.name}）。${obj.description || ""}`,
      execute: async (params: Record<string, any>) =>
        pythonFetch(`/ontology/${ontologyId}/query`, {
          method: "POST",
          body: JSON.stringify({
            operation: "search",
            object: obj.slug,
            filters: params.filters,
            limit: params.limit || 10,
          }),
        }),
    };

    tools[`aggregate_${qualifier}`] = {
      name: `aggregate_${qualifier}`,
      description: `按维度聚合统计 ${obj.name}（本体: ${schema.name}）`,
      execute: async (params: Record<string, any>) =>
        pythonFetch(`/ontology/${ontologyId}/query`, {
          method: "POST",
          body: JSON.stringify({
            operation: "aggregate",
            object: obj.slug,
            measures: params.measures || ["COUNT(*)"],
            group_by: params.group_by || [],
          }),
        }),
    };
  }
  return tools;
}

/**
 * Load tools from multiple ontologies — all names qualified by ontology slug
 * so the LLM can never confuse cross-ontology objects with the same name.
 */
export async function loadAllTools(ontologies: OntologySchema[]): Promise<Record<string, Tool>> {
  const merged: Record<string, Tool> = {};
  for (const schema of ontologies) {
    Object.assign(merged, buildToolsFromSchema(schema.id, schema));
  }
  return merged;
}

export function buildIngestTools(): Record<string, Tool> {
  return {
    ingest_file: {
      name: "ingest_file",
      description: "上传并解析用户的数据文件（CSV/Excel），返回列名和类型推断结果",
      execute: async (params: Record<string, any>) => {
        const fd = new FormData();
        fd.append("type", params.file_type || "csv");
        if (params.file_path) fd.append("path", params.file_path);
        return pythonFetch("/ingest", { method: "POST", body: fd });
      },
    },
    create_ontology: {
      name: "create_ontology",
      description: "根据数据 schema 自动生成本体并注册，用户不需要看到 YAML",
      execute: async (params: Record<string, any>) => {
        const columns = params.columns as Array<{ name: string; semantic_type: string }>;
        const tableName = params.table_name || "data";
        const props = columns
          .map((c) => `      - name: ${c.name}\n        source_column: ${c.name}\n        semantic_type: ${c.semantic_type}`)
          .join("\n");
        const yaml = `name: ${tableName}-auto\nslug: ${tableName}-auto\nobjects:\n  - name: ${tableName.charAt(0).toUpperCase() + tableName.slice(1)}\n    slug: ${tableName}\n    table_name: ${tableName}\n    properties:\n${props}`;
        return pythonFetch("/ontology", {
          method: "POST",
          body: JSON.stringify({ yaml_source: yaml }),
        });
      },
    },
    list_my_data: {
      name: "list_my_data",
      description: "列出用户已有的所有数据集和本体，用于判断用户问的数据是否已存在",
      execute: async () => {
        const [ontologies, datasources] = await Promise.all([
          pythonFetch("/ontology").catch(() => []),
          pythonFetch("/datasources").catch(() => []),
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
