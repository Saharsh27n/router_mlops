// Thin wrapper around the gateway's REST surface. Relative paths work in both dev
// (proxied by Vite, see vite.config.js) and prod (served by nginx alongside the SPA).
//
// A fixed demo key is fine for a viva dashboard talking to its own gateway; it is not
// how a real deployment would hand out credentials to a browser.
const API_KEY = 'demo-key-smartroute'

async function request(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: { 'X-API-Key': API_KEY, ...(options.headers ?? {}) },
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`${path} -> ${res.status} ${body}`.slice(0, 300))
  }
  return res.json()
}

export const api = {
  health: () => request('/health'),
  stats: () => request('/stats'),
  recent: (limit = 25) => request(`/requests/recent?limit=${limit}`),
  chat: (query, { threshold, noCascade, strategy = 'hybrid' } = {}) =>
    request('/v1/chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ query, threshold, no_cascade: noCascade, strategy }),
    }),
  drift: () => request('/drift'),
  simulateDrift: () => request('/admin/simulate-drift', { method: 'POST' }),
  retrain: () => request('/admin/retrain', { method: 'POST' }),
}
