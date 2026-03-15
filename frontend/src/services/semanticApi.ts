import api from './api';
import { SemanticConfig, FormulaTestResult } from '../types/semantic';

export const semanticApi = {
  get: (projectId: number): Promise<SemanticConfig> =>
    api.get(`/projects/${projectId}/semantic`).then(r => r.data),

  save: (projectId: number, config: string): Promise<{ success: boolean }> =>
    api.put(`/projects/${projectId}/semantic`, { config }).then(r => r.data),

  testFormula: (projectId: number, objectType: string, formula: string): Promise<FormulaTestResult> =>
    api.post(`/projects/${projectId}/semantic/test-formula`, {
      object_type: objectType,
      formula,
    }).then(r => r.data),
};
