import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import { AuthContext } from '../context/auth-context';
import { usePermissions } from './usePermissions';

const wrapperFor = (role) =>
  function Wrapper({ children }) {
    return <AuthContext.Provider value={{ user: role ? { role } : null }}>{children}</AuthContext.Provider>;
  };

describe('usePermissions (client RBAC mirror)', () => {
  it('viewer can read but not create/delete', () => {
    const { result } = renderHook(() => usePermissions(), { wrapper: wrapperFor('VIEWER') });
    expect(result.current.can('read')).toBe(true);
    expect(result.current.can('create')).toBe(false);
    expect(result.current.can('delete')).toBe(false);
  });

  it('contributor can create/update but not delete or manage users', () => {
    const { result } = renderHook(() => usePermissions(), { wrapper: wrapperFor('CONTRIBUTOR') });
    expect(result.current.can('update')).toBe(true);
    expect(result.current.can('delete')).toBe(false);
    expect(result.current.can('manage_users')).toBe(false);
  });

  it('admin can manage users', () => {
    const { result } = renderHook(() => usePermissions(), { wrapper: wrapperFor('ADMIN') });
    expect(result.current.can('manage_users')).toBe(true);
  });

  it('an unauthenticated user can do nothing', () => {
    const { result } = renderHook(() => usePermissions(), { wrapper: wrapperFor(null) });
    expect(result.current.can('read')).toBe(false);
  });
});
