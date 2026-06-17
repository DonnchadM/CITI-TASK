import { apiRequest, toQuery } from './apiClient';

// Admin user management (auth service). All require the manage_users permission.
export const usersApi = {
  list: (params) => apiRequest('GET', `/auth/users${toQuery(params)}`),
  create: (body) => apiRequest('POST', '/auth/users', { body }),
  update: (id, body) => apiRequest('PUT', `/auth/users/${id}`, { body }),
  remove: (id) => apiRequest('DELETE', `/auth/users/${id}`),
};

export const ROLES = ['ADMIN', 'MANAGER', 'CONTRIBUTOR', 'VIEWER'];
