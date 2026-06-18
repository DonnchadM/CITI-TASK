import { apiRequest } from './apiClient';

// Read-only analytics: org-wide KPI summary, per-team drill-down, achievement
// trend, and the illustrative promotion-readiness view.
export const analyticsApi = {
  summary: () => apiRequest('GET', '/analytics/summary'),
  teams: () => apiRequest('GET', '/analytics/teams'),
  achievementsByMonth: () => apiRequest('GET', '/analytics/achievements-by-month'),
  promotions: () => apiRequest('GET', '/analytics/promotions'),
};
