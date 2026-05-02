/**
 * Build YAML draft for an ontology from an ingest result.
 * Used by /datasources/upload, /datasources/connect, and agent's create_ontology tool.
 *
 * `displayName` (optional) — business-friendly name the LLM infers from column
 * context (e.g. "订单", "客户"). Falls back to capitalized tableName. This feeds
 * both the ontology `name` and object `name`, making tools like `search_*`,
 * `aggregate_*` semantically clearer to downstream LLM calls.
 */
export function buildOntologyYaml(opts: {
  source: string;
  tableName: string;
  columns: Array<{ name: string; semantic_type: string }>;
  displayName?: string;
}): string {
  const { source, tableName, columns, displayName } = opts;
  const props = columns
    .map((c) => `      - name: ${c.name}
        source_column: ${c.name}
        semantic_type: ${c.semantic_type}${c.semantic_type === "currency" ? "\n        unit: CNY" : ""}`)
    .join("\n");

  const objectName = displayName || (tableName.charAt(0).toUpperCase() + tableName.slice(1));
  const ontologyName = displayName ? `${displayName}-${tableName}` : `${tableName}-ontology`;

  return `name: ${ontologyName}
slug: ${ontologyName}
description: 从 ${source} 自动生成
objects:
  - name: ${objectName}
    slug: ${tableName}
    table_name: ${tableName}
    properties:
${props}`;
}
