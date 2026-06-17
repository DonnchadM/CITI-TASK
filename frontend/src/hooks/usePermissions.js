import { useAuth } from '../hooks/useAuth';

// Client-side mirror of the backend RBAC matrix (docs/DESIGN.md). This is for UX
// only — hiding/disabling actions the user cannot perform. The backend remains
// the real enforcement point.
export const PERMISSIONS = {
  ADMIN: ['read', 'create', 'update', 'delete', 'manage_users'],
  MANAGER: ['read', 'create', 'update', 'delete'],
  CONTRIBUTOR: ['read', 'create', 'update'],
  VIEWER: ['read'],
};

export function usePermissions() {
  const { user } = useAuth();
  const role = user?.role;
  const can = (action) => (PERMISSIONS[role] || []).includes(action);
  return { role, can };
}
