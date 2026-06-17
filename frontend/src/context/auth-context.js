import { createContext } from 'react';

// The auth context object lives in its own module so the provider file can
// export only its component (keeps React Fast Refresh happy).
export const AuthContext = createContext(null);
