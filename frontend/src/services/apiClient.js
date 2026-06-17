// Central API client: targets the backend through the dev proxy (VITE_API_URL,
// e.g. http://localhost:3001) or CloudFront in the cloud. Injects the JWT,
// transparently refreshes on 401 and retries once, and normalizes our error
// envelope ({ error: { code, message, details } }) into an ApiError.

const BASE = import.meta.env.VITE_API_URL || '';
const ACCESS_KEY = 'tm_access_token';
const REFRESH_KEY = 'tm_refresh_token';

export const tokenStore = {
  get access() {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  set({ access_token, refresh_token }) {
    if (access_token) localStorage.setItem(ACCESS_KEY, access_token);
    if (refresh_token) localStorage.setItem(REFRESH_KEY, refresh_token);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

// Called when refresh fails so the AuthContext can drop the session.
let onUnauthorized = () => {};
export function setOnUnauthorized(handler) {
  onUnauthorized = handler;
}

// Build a query string from a params object, skipping empty/null values.
export function toQuery(params) {
  const search = new URLSearchParams();
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.append(key, value);
  });
  const str = search.toString();
  return str ? `?${str}` : '';
}

export class ApiError extends Error {
  constructor(status, payload) {
    super(payload?.error?.message || 'Request failed');
    this.name = 'ApiError';
    this.status = status;
    this.code = payload?.error?.code;
    this.details = payload?.error?.details || [];
  }
}

async function rawRequest(method, url, { body, token } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(url, {
    method,
    headers,
    body: body != null ? JSON.stringify(body) : undefined,
  });
  const text = await response.text();
  return { response, data: text ? JSON.parse(text) : null };
}

async function tryRefresh() {
  const refresh = tokenStore.refresh;
  if (!refresh) return false;
  const { response, data } = await rawRequest('POST', `${BASE}/api/auth/refresh`, {
    body: { refresh_token: refresh },
  });
  if (response.ok && data?.access_token) {
    tokenStore.set({ access_token: data.access_token });
    return true;
  }
  return false;
}

export async function apiRequest(method, path, { body, auth = true } = {}) {
  const url = `${BASE}/api${path}`;
  let { response, data } = await rawRequest(method, url, {
    body,
    token: auth ? tokenStore.access : null,
  });

  if (response.status === 401 && auth) {
    if (await tryRefresh()) {
      ({ response, data } = await rawRequest(method, url, { body, token: tokenStore.access }));
    }
    if (response.status === 401) {
      tokenStore.clear();
      onUnauthorized();
    }
  }

  if (!response.ok) throw new ApiError(response.status, data);
  return data;
}
