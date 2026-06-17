import { apiRequest, toQuery } from './apiClient';

export const achievementsApi = {
  list: (params) => apiRequest('GET', `/achievements${toQuery(params)}`),
  create: (body) => apiRequest('POST', '/achievements', { body }),
  update: (id, body) => apiRequest('PUT', `/achievements/${id}`, { body }),
  remove: (id) => apiRequest('DELETE', `/achievements/${id}`),
};
