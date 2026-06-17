import { Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

// Route guard for role-restricted pages (e.g. admin). Sends users without an
// allowed role back to the dashboard. UX-only; the backend enforces RBAC.
export function RequireRole({ roles, children }) {
  const { user } = useAuth();
  if (!user || !roles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }
  return children;
}
