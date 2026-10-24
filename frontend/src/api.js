const base = '/api/v1';
let token = null;
export function setToken(value) { token = value; }

export async function request(path, { method = 'GET', body } = {}) {
  const response = await fetch(`${base}${path}`, {
    method,
    headers: { ...(body ? { 'Content-Type': 'application/json' } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) {
    if (response.status === 401 && token) window.dispatchEvent(new Event('session-expired'));
    const error = await response.json().catch(() => ({}));
    throw new Error(typeof error.detail === 'string' ? error.detail : `Ошибка запроса (${response.status}). Проверьте введённые данные.`);
  }
  return response.status === 204 ? null : response.json();
}

export async function listAll(path) {
  const rows = [];
  for (let offset = 0; ; offset += 100) {
    const page = await request(`${path}${path.includes('?') ? '&' : '?'}offset=${offset}&limit=100`);
    rows.push(...page);
    if (page.length < 100) return rows;
  }
}
