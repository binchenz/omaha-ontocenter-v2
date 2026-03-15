export interface SemanticProperty {
  name: string;
  column?: string;
  type?: string;
  semantic_type?: 'currency' | 'percentage' | 'enum' | 'computed' | 'date' | 'id' | 'text';
  description?: string;
  business_context?: string;
  formula?: string;
  return_type?: string;
  currency?: string;
  enum_values?: Array<{ value: string; label: string }>;
}

export interface SemanticObject {
  description?: string;
  base_properties: Record<string, SemanticProperty>;
  computed_properties: Record<string, SemanticProperty>;
  property_map: Record<string, string>;
  relationships: any[];
}

export interface SemanticConfig {
  config: string;
  parsed: {
    valid: boolean;
    objects: Record<string, SemanticObject>;
    metrics: any[];
  };
}

export interface FormulaTestResult {
  sql: string | null;
  sample: any[];
  error: string | null;
}
