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
  links: any[]; functions: any[];
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
