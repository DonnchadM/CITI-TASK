import { apiRequest } from './apiClient';

// Auth + current-user API. login is public (no token); the rest require auth.
export const authApi = {
  login: (email, password) =>
    apiRequest('POST', '/auth/login', { body: { email, password }, auth: false }),
  logout: () => apiRequest('POST', '/auth/logout'),
  me: () => apiRequest('GET', '/auth/me'),
  changePassword: (current_password, new_password) =>
    apiRequest('PUT', '/auth/me/password', { body: { current_password, new_password } }),
};
