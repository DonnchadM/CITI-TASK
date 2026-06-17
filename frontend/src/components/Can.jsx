import { usePermissions } from '../hooks/usePermissions';

// Renders children only if the current user may perform `action`; otherwise the
// optional fallback. UX-only guard (the backend enforces the real check).
export function Can({ action, children, fallback = null }) {
  const { can } = usePermissions();
  return can(action) ? children : fallback;
}
