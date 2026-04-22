import api from './api';

export interface PropertyConfig {
  name: string;
  column?: string;
  type: string;
  semantic_type?: string;
  description?: string;
}

export interface RelationshipConfig {
  name: string;
  to_object: string;
  type: string;
  join_condition: { from_field: string; to_field: string };
}

export interface ObjectConfig {
  name: string;
  datasource: string;
  table?: string;
  api_name?: string;
  primary_key?: string;
  description?: string;
  properties: PropertyConfig[];
  relationships: RelationshipConfig[];
}

export interface DatasourceConfig {
  id: string;
  name?: string;
  type: string;
  connection: Record<string, string>;
}

export interface OntologyModel {
  datasources: DatasourceConfig[];
  objects: ObjectConfig[];
}

export const ontologyEditorService = {
  generateYaml: async (model: OntologyModel): Promise<{ yaml: string; valid: boolean }> => {
    const res = await api.post('/ontology/generate', { model });
    return res.data;
  },

  parseYaml: async (config_yaml: string): Promise<OntologyModel> => {
    const res = await api.post('/ontology/build', { config_yaml });
    const ontology = res.data.ontology;
    if (!ontology) return { datasources: [], objects: [] };
    const objects: ObjectConfig[] = Object.entries(ontology.objects || {}).map(([name, obj]: [string, any]) => ({
      name,
      datasource: obj.datasource || '',
      table: obj.table_name,
      properties: (obj.properties || []).map((p: any) => ({
        name: p.name,
        column: p.column_name,
        type: p.type || 'string',
      })),
      relationships: [],
    }));
    return { datasources: [], objects };
  },
};
