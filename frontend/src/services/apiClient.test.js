import { describe, it, expect, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../test/server';
import { apiRequest, toQuery, tokenStore, ApiError, setOnUnauthorized } from './apiClient';

const URL = 'http://localhost/api';

describe('toQuery', () => {
  it('builds a query string and skips empty values', () => {
    expect(toQuery({ a: 1, b: '', c: null, d: 'x' })).toBe('?a=1&d=x');
    expect(toQuery({})).toBe('');
  });
});

describe('apiRequest', () => {
  it('returns parsed data on success', async () => {
    tokenStore.set({ access_token: 't1' });
    server.use(http.get(`${URL}/people`, () => HttpResponse.json({ data: [], pagination: { total: 0 } })));
    const result = await apiRequest('GET', '/people');
    expect(result.pagination.total).toBe(0);
  });

  it('throws ApiError carrying status and code from the error envelope', async () => {
    tokenStore.set({ access_token: 't1' });
    server.use(http.get(`${URL}/people`, () =>
      HttpResponse.json({ error: { code: 'forbidden', message: 'no', details: [] } }, { status: 403 })));
    await expect(apiRequest('GET', '/people')).rejects.toMatchObject({ status: 403, code: 'forbidden' });
  });

  it('refreshes on 401 then retries the original request', async () => {
    tokenStore.set({ access_token: 'old', refresh_token: 'r1' });
    let getCalls = 0;
    server.use(
      http.get(`${URL}/people`, ({ request }) => {
        getCalls += 1;
        if (request.headers.get('authorization') === 'Bearer old') {
          return HttpResponse.json({ error: { message: 'expired' } }, { status: 401 });
        }
        return HttpResponse.json({ data: ['ok'] });
      }),
      http.post(`${URL}/auth/refresh`, () => HttpResponse.json({ access_token: 'new' })),
    );
    const result = await apiRequest('GET', '/people');
    expect(result.data).toEqual(['ok']);
    expect(tokenStore.access).toBe('new'); // token rotated
    expect(getCalls).toBe(2);              // original + retry
  });

  it('clears the session and notifies on failed refresh', async () => {
    tokenStore.set({ access_token: 'old', refresh_token: 'bad' });
    const onUnauthorized = vi.fn();
    setOnUnauthorized(onUnauthorized);
    server.use(
      http.get(`${URL}/people`, () => HttpResponse.json({ error: { message: 'expired' } }, { status: 401 })),
      http.post(`${URL}/auth/refresh`, () => HttpResponse.json({ error: {} }, { status: 401 })),
    );
    await expect(apiRequest('GET', '/people')).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).toHaveBeenCalled();
    expect(tokenStore.access).toBeNull();
  });
});
