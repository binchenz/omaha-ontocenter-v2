import api from './api';

export interface ColumnInfo {
  name: string;
  type: string;
  nullable: boolean;
}

export interface TableSummary {
  name: string;
  row_count: number;
  columns: ColumnInfo[];
  sample_values: Record<string, string[]>;
}

export interface InferredProperty {
  name: string;
  data_type: string;
  semantic_type: string | null;
  description: string;
}

export interface InferredObject {
  name: string;
  source_entity: string;
  description: string;
  business_context: string;
  domain: string;
  datasource_id: string;
  datasource_type: string;
  properties: InferredProperty[];
}

export interface InferredRelationship {
  name: string;
  from_object: string;
  to_object: string;
  relationship_type: string;
  from_field: string;
  to_field: string;
}

export const modelingService = {
  async scan(projectId: number, datasourceId: string) {
    const resp = await api.post(`/ontology-store/${projectId}/scan`, {
      datasource_id: datasourceId,
    });
    return resp.data as { tables: TableSummary[] };
  },

  async infer(projectId: number, datasourceId: string, tables: string[]) {
    const resp = await api.post(`/ontology-store/${projectId}/infer`, {
      datasource_id: datasourceId,
      tables,
    });
    return resp.data as {
      objects: InferredObject[];
      relationships: InferredRelationship[];
      warnings: string[];
    };
  },

  async confirm(projectId: number, objects: InferredObject[], relationships: InferredRelationship[]) {
    const resp = await api.post(`/ontology-store/${projectId}/confirm`, {
      objects,
      relationships,
    });
    return resp.data as {
      objects_created: number;
      objects_updated: number;
      relationships_created: number;
    };
  },
};
