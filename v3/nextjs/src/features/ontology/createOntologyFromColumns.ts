import { buildOntologyYaml } from "./yaml-builder";
import { ontologyApi } from "@/services/pythonApi";
import { DEFAULT_TENANT_ID } from "@/lib/constants";

export interface CreateOntologyFromColumnsArgs {
  source: string;
  tableName: string;
  columns: Array<{ name: string; semantic_type: string }>;
  displayName?: string;
  tenantId?: string;
}

/**
 * Build a draft ontology YAML from a column schema and register it via the
 * Python API. Centralises the upload-page / connect-page / agent tool flow
 * so all three sites stay in sync (e.g. when displayName semantics change).
 */
export function createOntologyFromColumns(args: CreateOntologyFromColumnsArgs) {
  const yaml = buildOntologyYaml({
    source: args.source,
    tableName: args.tableName,
    columns: args.columns,
    displayName: args.displayName,
  });
  return ontologyApi.create(yaml, args.tenantId ?? DEFAULT_TENANT_ID);
}
