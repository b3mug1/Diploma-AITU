const base = '/api/v1';

export async function request(path, { method = 'GET', body } = {}) {
  const response = await fetch(`${base}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(typeof error.detail === 'string' ? error.detail : `Ошибка запроса (${response.status}). Проверьте введённые данные.`);
  }
  return response.json();
}

export async function listAll(path) {
  const rows = [];
  for (let offset = 0; ; offset += 100) {
    const page = await request(`${path}${path.includes('?') ? '&' : '?'}offset=${offset}&limit=100`);
    rows.push(...page);
    if (page.length < 100) return rows;
  }
}
