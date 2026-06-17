import { apiRequest } from './apiClient';

// AI "Ask the org" assistant: a natural-language question over the org's data.
export const assistantApi = {
  query: (question) => apiRequest('POST', '/assistant/query', { body: { question } }),
};
