export interface User {
  id: number;
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at?: string;
}

export interface Project {
  id: number;
  name: string;
  description?: string;
  owner_id: number;
  datahub_dataset_urn?: string;
  omaha_config?: string;
  metadata: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

export interface QueryHistory {
  id: number;
  natural_language_query: string;
  object_type?: string;
  result_count?: number;
  status: string;
  error_message?: string;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface OntologyObject {
  name: string;
  table_name?: string;
  properties: Array<{
    name: string;
    type: string;
    column_name?: string;
  }>;
}

export interface Ontology {
  objects: Record<string, OntologyObject>;
  relationships: Array<{
    name: string;
    type: string;
    from_object: string;
    to_object: string;
  }>;
}
