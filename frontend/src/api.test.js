// @vitest-environment jsdom
import { afterEach, expect, it, vi } from 'vitest';
import { listAll, request, setToken } from './api';

afterEach(() => { setToken(null); vi.unstubAllGlobals(); });

it('includes the session bearer token on paginated notification requests', async () => {
  const fetch = vi.fn().mockResolvedValueOnce({ ok: true, status: 200, json: async () => Array.from({ length: 100 }, (_, id) => ({ id })) })
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => [{ id: 100 }] });
  vi.stubGlobal('fetch', fetch);
  setToken('test-session');
  expect(await listAll('/notifications?unread_only=true')).toHaveLength(101);
  expect(fetch.mock.calls.map(([url]) => url)).toEqual([
    '/api/v1/notifications?unread_only=true&offset=0&limit=100',
    '/api/v1/notifications?unread_only=true&offset=100&limit=100',
  ]);
  expect(fetch.mock.calls[1][1].headers.Authorization).toBe('Bearer test-session');
});

it('expires the session on a notification 401 and preserves the API message', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({ detail: 'Session expired' }) }));
  setToken('expired-session');
  const expired = vi.fn();
  window.addEventListener('session-expired', expired);
  try {
    await expect(request('/notifications')).rejects.toThrow('Session expired');
    expect(expired).toHaveBeenCalledOnce();
  } finally { window.removeEventListener('session-expired', expired); }
});

it('surfaces forbidden administrative requests without ending a valid session', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 403, json: async () => ({ detail: 'Administrator access required' }) }));
  setToken('student-session');
  const expired = vi.fn();
  window.addEventListener('session-expired', expired);
  try {
    await expect(request('/admin/reports/summary')).rejects.toThrow('Administrator access required');
    expect(expired).not.toHaveBeenCalled();
  } finally { window.removeEventListener('session-expired', expired); }
});
