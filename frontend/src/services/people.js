import { apiRequest, toQuery } from './apiClient';

export const peopleApi = {
  list: (params) => apiRequest('GET', `/people${toQuery(params)}`),
  get: (id) => apiRequest('GET', `/people/${id}`),
  create: (body) => apiRequest('POST', '/people', { body }),
  update: (id, body) => apiRequest('PUT', `/people/${id}`, { body }),
  remove: (id) => apiRequest('DELETE', `/people/${id}`),
};
