import api from './api';
import { Ontology } from '../types';

export const ontologyService = {
  async validate(config_yaml: string): Promise<{
    valid: boolean;
    errors: string[];
    warnings: string[];
  }> {
    const response = await api.post('/ontology/validate', { config_yaml });
    return response.data;
  },

  async build(config_yaml: string): Promise<{
    valid: boolean;
    ontology?: Ontology;
    errors?: string[];
  }> {
    const response = await api.post('/ontology/build', { config_yaml });
    return response.data;
  },
};
