export interface OAGProperty {
  value: any;
  semantic_type: string;
  unit?: string | null;
  format?: string | null;
  source?: string | null;
  last_updated?: string | null;
}

export interface OAGLink { object_type: string; id: string; label: string; }

export interface OAGMatch {
  id: string;
  label?: string | null;
  properties: Record<string, OAGProperty>;
  links?: Record<string, OAGLink>;
  available_functions?: string[];
}

export interface OAGQueryResponse {
  object_type: string;
  matched: OAGMatch[];
  context: { total: number; related_objects?: string[]; suggested_queries?: string[]; };
}

export interface OntologySchema {
  id: string; name: string; slug: string; version: number;
  objects: OntologyObjectSchema[];
  links: OntologyLinkSchema[];
  functions: OntologyFunctionSchema[];
}

export interface OntologyObjectSchema {
  id: string; name: string; slug: string; description: string;
  table_name: string; datasource_id: string;
  properties: OntologyPropertySchema[];
}

export interface OntologyPropertySchema {
  name: string; slug: string; semantic_type: string;
  source_column: string; is_computed: boolean;
  function_ref?: string | null; unit: string;
}

export interface OntologyLinkSchema {
  name: string; from_object: string; to_object: string; type: string;
}

export interface OntologyFunctionSchema {
  name: string; handler: string; description: string;
}

// List-endpoint projections — lighter than OntologySchema and returned by
// /ontology (id+name+slug+version+status only, no objects).
export interface OntologyListItem {
  id: string;
  name: string;
  slug: string;
  version?: number;
  status?: string;
}

export interface DatasetInfo {
  id: string;
  table_name: string;
  rows_count: number;
  last_synced_at: string | null;
  status: string;
}

export interface DatasourceListItem {
  id: string;
  name: string;
  type: string;
  status: string;
  datasets_count: number;
  datasets: DatasetInfo[];
  created_at: string;
}

export interface IngestColumn {
  name: string;
  semantic_type: string;
}

export interface IngestResult {
  table_name: string;
  rows_count: number;
  dataset_id: string;
  columns: IngestColumn[];
}
