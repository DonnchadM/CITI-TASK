import { apiRequest, toQuery } from './apiClient';

export const teamsApi = {
  list: (params) => apiRequest('GET', `/teams${toQuery(params)}`),
  get: (id) => apiRequest('GET', `/teams/${id}`),
  create: (body) => apiRequest('POST', '/teams', { body }),
  update: (id, body) => apiRequest('PUT', `/teams/${id}`, { body }),
  remove: (id) => apiRequest('DELETE', `/teams/${id}`),
  members: (id) => apiRequest('GET', `/teams/${id}/members`),
  addMember: (id, body) => apiRequest('POST', `/teams/${id}/members`, { body }),
  removeMember: (id, personId) => apiRequest('DELETE', `/teams/${id}/members/${personId}`),
};
