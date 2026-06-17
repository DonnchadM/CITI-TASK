import { apiRequest } from './apiClient';

// Read-only analytics: org-wide KPI summary and per-team drill-down.
export const analyticsApi = {
  summary: () => apiRequest('GET', '/analytics/summary'),
  teams: () => apiRequest('GET', '/analytics/teams'),
};
