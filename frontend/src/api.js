// Тонкий клиент к FastAPI. Всегда относительные пути /api/* — в dev их проксирует
// Vite на uvicorn, в проде nginx на контейнер api (один origin, без CORS-возни).

async function getJSON(path) {
  const res = await fetch(path)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${path} → HTTP ${res.status}${text ? `: ${text}` : ''}`)
  }
  return res.json()
}

export const api = {
  coreTables: () => getJSON('/api/core/tables'),
  coreTable: (name) => getJSON(`/api/core/${name}`),
  dqSummary: () => getJSON('/api/data-quality/summary'),
  dqIssues: () => getJSON('/api/data-quality/issues'),
  // Отчёты (шаг 5)
  reportFunnel: () => getJSON('/api/reports/funnel'),
  reportManagers: () => getJSON('/api/reports/managers'),
  reportReceivables: () => getJSON('/api/reports/receivables'),
  reportProduction: () => getJSON('/api/reports/production-delays'),
  reportStale: (nDays) => getJSON(`/api/reports/stale-deals?n_days=${nDays}`),
  reportSources: () => getJSON('/api/reports/sources'),
}
