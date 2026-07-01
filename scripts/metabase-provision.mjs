#!/usr/bin/env node
// Идемпотентный провижининг Metabase через его REST API.
// Запуск: node --env-file=.env scripts/metabase-provision.mjs  (make bi-provision)
//
// Делает: ждёт /api/health → создаёт админа (или логинится, если уже настроен) →
// подключает боевую БД termosphere как источник → синкает схему → создаёт 7 вопросов
// из канонического SQL отчётов (совпадает с db/reports.sql) → собирает дашборд.
// Повторный запуск ничего не дублирует (ищет по имени и переиспользует).

const BASE = `http://127.0.0.1:${process.env.MB_DIRECT_PORT || '3010'}`
const ADMIN_EMAIL = process.env.MB_ADMIN_EMAIL || 'admin@termosphere.local'
const ADMIN_PASSWORD = process.env.MB_ADMIN_PASSWORD
const SITE_NAME = process.env.MB_SITE_NAME || 'ТермоСфера BI'
// Реквизиты подключения источника (боевая CRM-БД в сети compose — host `db`)
const SRC = {
  host: 'db',
  port: 5432,
  dbname: process.env.POSTGRES_DB || 'termosphere',
  user: process.env.POSTGRES_USER || 'termosphere',
  password: process.env.POSTGRES_PASSWORD || 'termosphere',
}
const SRC_NAME = 'ТермоСфера (core)'
const DASH_NAME = 'ТермоСфера — обзор'

if (!ADMIN_PASSWORD) {
  console.error('MB_ADMIN_PASSWORD не задан (см. .env). Прерываю.')
  process.exit(1)
}

let SESSION = null
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function mb(method, path, body) {
  const headers = { 'Content-Type': 'application/json' }
  if (SESSION) headers['X-Metabase-Session'] = SESSION
  const res = await fetch(BASE + path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const text = await res.text()
  let json = null
  try { json = text ? JSON.parse(text) : null } catch { /* not json */ }
  if (!res.ok) {
    const err = new Error(`${method} ${path} → ${res.status}: ${text.slice(0, 400)}`)
    err.status = res.status
    throw err
  }
  return json
}

async function waitHealth(timeoutMs = 240000) {
  const t0 = Date.now()
  process.stdout.write('Жду /api/health ')
  while (Date.now() - t0 < timeoutMs) {
    try {
      const r = await fetch(BASE + '/api/health')
      if (r.ok) { const j = await r.json(); if (j.status === 'ok') { console.log('→ ok'); return } }
    } catch { /* ещё не поднялся */ }
    process.stdout.write('.')
    await sleep(3000)
  }
  throw new Error('Metabase не поднялся за отведённое время')
}

async function ensureSession() {
  const props = await mb('GET', '/api/session/properties')
  const token = props['setup-token']
  if (token) {
    console.log('Первичная настройка (setup) — создаю администратора…')
    const out = await mb('POST', '/api/setup', {
      token,
      user: {
        first_name: 'Admin', last_name: 'ТермоСфера',
        email: ADMIN_EMAIL, password: ADMIN_PASSWORD, site_name: SITE_NAME,
      },
      prefs: { site_name: SITE_NAME, site_locale: 'ru', allow_tracking: false },
    })
    SESSION = out.id
    console.log('  админ создан, сессия получена')
  } else {
    console.log('Metabase уже настроен — логинюсь…')
    const out = await mb('POST', '/api/session', { username: ADMIN_EMAIL, password: ADMIN_PASSWORD })
    SESSION = out.id
    console.log('  сессия получена')
  }
}

async function ensureDatabase() {
  const list = await mb('GET', '/api/database')
  const arr = Array.isArray(list) ? list : (list.data || [])
  const found = arr.find((d) => d.name === SRC_NAME)
  if (found) {
    console.log(`Источник «${SRC_NAME}» уже есть (id=${found.id}) — переиспользую`)
    return found.id
  }
  console.log(`Подключаю источник «${SRC_NAME}» (${SRC.host}:${SRC.port}/${SRC.dbname})…`)
  const created = await mb('POST', '/api/database', {
    engine: 'postgres',
    name: SRC_NAME,
    details: { host: SRC.host, port: SRC.port, dbname: SRC.dbname, user: SRC.user, password: SRC.password, ssl: false, 'tunnel-enabled': false },
    is_full_sync: true,
  })
  console.log(`  подключено (id=${created.id})`)
  return created.id
}

async function waitTables(dbId, timeoutMs = 120000) {
  await mb('POST', `/api/database/${dbId}/sync_schema`).catch(() => {})
  const t0 = Date.now()
  process.stdout.write('Синк схемы ')
  while (Date.now() - t0 < timeoutMs) {
    const meta = await mb('GET', `/api/database/${dbId}/metadata`).catch(() => null)
    const tables = (meta && meta.tables) || []
    const names = tables.map((t) => t.name)
    if (names.includes('deals') && names.includes('data_quality_issues')) {
      console.log(`→ ${tables.length} таблиц (deals найдена)`) ; return tables
    }
    process.stdout.write('.')
    await sleep(3000)
  }
  throw new Error('Схема не засинкалась (таблица deals не появилась)')
}

// Канонический SQL отчётов (совпадает с db/reports.sql / queries.py).
const Q = {
  funnel: `WITH lines AS (SELECT dp.deal_id, SUM(dp.quantity*dp.unit_price-dp.discount) AS revenue, SUM(dp.quantity*p.cost_price) AS cost FROM deal_products dp JOIN products p ON p.product_id=dp.product_id GROUP BY dp.deal_id),
deal_amount AS (SELECT d.deal_id,d.stage_id,d.manager_id,d.source_id,d.expected_amount, l.revenue::numeric(14,2) AS line_revenue,(l.revenue-l.cost)::numeric(14,2) AS line_margin, COALESCE(l.revenue,d.expected_amount)::numeric(14,2) AS amount FROM deals d LEFT JOIN lines l ON l.deal_id=d.deal_id)
SELECT ps.sort_order, ps.stage_id, ps.stage_name, ps.is_success, count(da.deal_id) AS deals, COALESCE(SUM(da.amount),0)::numeric(14,2) AS amount
FROM pipeline_stages ps LEFT JOIN deal_amount da ON da.stage_id=ps.stage_id
GROUP BY ps.sort_order,ps.stage_id,ps.stage_name,ps.is_success
UNION ALL SELECT 999,NULL,'Без стадии',NULL,count(*),COALESCE(SUM(amount),0)::numeric(14,2) FROM deal_amount WHERE stage_id IS NULL HAVING count(*)>0
ORDER BY sort_order`,

  managers: `WITH lines AS (SELECT dp.deal_id, SUM(dp.quantity*dp.unit_price-dp.discount) AS revenue, SUM(dp.quantity*p.cost_price) AS cost FROM deal_products dp JOIN products p ON p.product_id=dp.product_id GROUP BY dp.deal_id),
deal_amount AS (SELECT d.deal_id,d.stage_id,d.manager_id,d.source_id,d.expected_amount, l.revenue::numeric(14,2) AS line_revenue,(l.revenue-l.cost)::numeric(14,2) AS line_margin, COALESCE(l.revenue,d.expected_amount)::numeric(14,2) AS amount FROM deals d LEFT JOIN lines l ON l.deal_id=d.deal_id)
SELECT u.user_id,u.name,u.active,
 count(da.deal_id) FILTER (WHERE da.stage_id='WON') AS won_deals,
 COALESCE(SUM(da.amount) FILTER (WHERE da.stage_id='WON'),0)::numeric(14,2) AS revenue,
 SUM(da.line_margin) FILTER (WHERE da.stage_id='WON') AS margin,
 count(*) FILTER (WHERE da.stage_id='WON' AND da.line_margin IS NULL) AS won_without_margin
FROM users u LEFT JOIN deal_amount da ON da.manager_id=u.user_id
WHERE u.role='sales_manager' GROUP BY u.user_id,u.name,u.active ORDER BY revenue DESC,u.user_id`,

  receivables: `WITH lines AS (SELECT dp.deal_id, SUM(dp.quantity*dp.unit_price-dp.discount) AS revenue, SUM(dp.quantity*p.cost_price) AS cost FROM deal_products dp JOIN products p ON p.product_id=dp.product_id GROUP BY dp.deal_id),
deal_amount AS (SELECT d.deal_id,d.stage_id,d.manager_id,d.source_id,d.expected_amount, l.revenue::numeric(14,2) AS line_revenue,(l.revenue-l.cost)::numeric(14,2) AS line_margin, COALESCE(l.revenue,d.expected_amount)::numeric(14,2) AS amount FROM deals d LEFT JOIN lines l ON l.deal_id=d.deal_id),
pay AS (SELECT deal_id, SUM(amount) FILTER (WHERE status='paid' AND payment_type IN ('prepayment','full')) AS paid, SUM(amount) FILTER (WHERE status='pending') AS pending, SUM(amount) FILTER (WHERE payment_type='correction') AS correction FROM payments GROUP BY deal_id)
SELECT da.deal_id,da.stage_id,da.amount,
 COALESCE(p.paid,0)::numeric(14,2) AS paid, COALESCE(p.pending,0)::numeric(14,2) AS pending, COALESCE(p.correction,0)::numeric(14,2) AS correction,
 (da.amount-COALESCE(p.paid,0)+COALESCE(p.correction,0))::numeric(14,2) AS balance
FROM deal_amount da LEFT JOIN pay p ON p.deal_id=da.deal_id
WHERE da.stage_id IS DISTINCT FROM 'LOST' AND (da.stage_id IN ('CONTRACT','PRODUCTION','SHIPPED','WON') OR p.deal_id IS NOT NULL)
ORDER BY balance DESC,da.deal_id`,

  production: `WITH cutoff AS (SELECT GREATEST((SELECT max(updated_at)::date FROM deals),(SELECT max(payment_date) FROM payments),(SELECT max(actual_date) FROM shipments),(SELECT max(completed_at)::date FROM activities),(SELECT max(changed_at)::date FROM stage_history),(SELECT max(actual_finish_at) FROM production_orders)) AS d)
SELECT po.production_order_id,po.deal_id,po.status,po.planned_finish_at,po.actual_finish_at,
 (COALESCE(po.actual_finish_at,(SELECT d FROM cutoff))-po.planned_finish_at) AS delay_days
FROM production_orders po
WHERE po.planned_finish_at IS NOT NULL AND (COALESCE(po.actual_finish_at,(SELECT d FROM cutoff))-po.planned_finish_at)>5
ORDER BY delay_days DESC,po.production_order_id`,

  stale: `WITH cutoff AS (SELECT GREATEST((SELECT max(updated_at)::date FROM deals),(SELECT max(payment_date) FROM payments),(SELECT max(actual_date) FROM shipments),(SELECT max(completed_at)::date FROM activities),(SELECT max(changed_at)::date FROM stage_history),(SELECT max(actual_finish_at) FROM production_orders)) AS d),
touch AS (SELECT deal_id, max(GREATEST(deadline_at,completed_at))::date AS last_touch FROM activities GROUP BY deal_id)
SELECT d.deal_id,d.stage_id,t.last_touch,((SELECT d FROM cutoff)-t.last_touch) AS days_since
FROM deals d LEFT JOIN touch t ON t.deal_id=d.deal_id
WHERE d.stage_id IS DISTINCT FROM 'WON' AND d.stage_id IS DISTINCT FROM 'LOST'
 AND (t.last_touch IS NULL OR ((SELECT d FROM cutoff)-t.last_touch)>14)
ORDER BY days_since DESC NULLS FIRST,d.deal_id`,

  sources: `WITH lines AS (SELECT dp.deal_id, SUM(dp.quantity*dp.unit_price-dp.discount) AS revenue, SUM(dp.quantity*p.cost_price) AS cost FROM deal_products dp JOIN products p ON p.product_id=dp.product_id GROUP BY dp.deal_id),
deal_amount AS (SELECT d.deal_id,d.stage_id,d.manager_id,d.source_id,d.expected_amount, l.revenue::numeric(14,2) AS line_revenue,(l.revenue-l.cost)::numeric(14,2) AS line_margin, COALESCE(l.revenue,d.expected_amount)::numeric(14,2) AS amount FROM deals d LEFT JOIN lines l ON l.deal_id=d.deal_id),
mc AS (SELECT source_id, SUM(cost_amount) AS costs, count(*) AS cost_rows FROM marketing_costs GROUP BY source_id)
SELECT s.id,s.code,s.name,count(da.deal_id) AS deals,
 count(da.deal_id) FILTER (WHERE da.stage_id='WON') AS won_deals,
 COALESCE(SUM(da.amount) FILTER (WHERE da.stage_id='WON'),0)::numeric(14,2) AS revenue,
 SUM(da.line_margin) FILTER (WHERE da.stage_id='WON') AS margin,
 COALESCE(mc.costs,0)::numeric(14,2) AS costs, COALESCE(mc.cost_rows,0) AS cost_rows
FROM sources s LEFT JOIN deal_amount da ON da.source_id=s.id LEFT JOIN mc ON mc.source_id=s.id
GROUP BY s.id,s.code,s.name,mc.costs,mc.cost_rows ORDER BY revenue DESC,s.code`,

  quality: `SELECT issue_type,action,count(*) AS count FROM data_quality_issues GROUP BY issue_type,action ORDER BY issue_type,action`,
}

// Определения карточек: имя, SQL, тип визуализации и настройки.
const CARDS = [
  { name: 'Воронка продаж', sql: Q.funnel, display: 'bar', viz: { 'graph.dimensions': ['stage_name'], 'graph.metrics': ['amount'] } },
  { name: 'Источники: выручка и затраты', sql: Q.sources, display: 'bar', viz: { 'graph.dimensions': ['name'], 'graph.metrics': ['revenue', 'costs'] } },
  { name: 'Продажи и маржа по менеджерам', sql: Q.managers, display: 'table', viz: {} },
  { name: 'Дебиторка (остатки)', sql: Q.receivables, display: 'table', viz: {} },
  { name: 'Задержка производства > 5 дней', sql: Q.production, display: 'table', viz: {} },
  { name: 'Сделки без активности (N=14)', sql: Q.stale, display: 'table', viz: {} },
  { name: 'Проблемы данных (по типам)', sql: Q.quality, display: 'table', viz: {} },
]

async function ensureCards(dbId) {
  // Учитываем и архивные карточки: дефолтный GET их не отдаёт, иначе POST создал бы дубль.
  const active = await mb('GET', '/api/card')
  const archived = await mb('GET', '/api/card?f=archived').catch(() => [])
  const byName = new Map([...(active || []), ...(archived || [])].map((c) => [c.name, c]))
  const result = []
  for (const c of CARDS) {
    const found = byName.get(c.name)
    const payload = {
      name: c.name,
      dataset_query: { type: 'native', native: { query: c.sql }, database: dbId },
      display: c.display,
      visualization_settings: c.viz,
    }
    if (found) {
      // При дрейфе SQL (Q.* поменялся) — обновляем карточку, а не переиспользуем старую;
      // архивную — разархивируем. Иначе повторный прогон закрепил бы устаревший SQL.
      const curSql = found.dataset_query?.native?.query
      if (found.archived) {
        await mb('PUT', `/api/card/${found.id}`, { ...payload, archived: false })
        console.log(`  разархивирован+обновлён вопрос «${c.name}» (id=${found.id})`)
      } else if (curSql !== c.sql) {
        await mb('PUT', `/api/card/${found.id}`, payload)
        console.log(`  обновлён SQL вопроса «${c.name}» (id=${found.id})`)
      } else {
        console.log(`  вопрос «${c.name}» уже есть (id=${found.id})`)
      }
      result.push(found.id)
      continue
    }
    const card = await mb('POST', '/api/card', payload)
    console.log(`  создан вопрос «${c.name}» (id=${card.id})`)
    result.push(card.id)
  }
  return result
}

async function ensureDashboard(cardIds) {
  // Учитываем архивные дашборды (дефолтный GET их не отдаёт → иначе POST плодил бы дубль).
  const active = await mb('GET', '/api/dashboard')
  const archived = await mb('GET', '/api/dashboard?f=archived').catch(() => [])
  const found = [...(active || []), ...(archived || [])].find((d) => d.name === DASH_NAME)
  let dashId
  if (found) {
    dashId = found.id
    if (found.archived) {
      await mb('PUT', `/api/dashboard/${dashId}`, { archived: false })
      console.log(`Дашборд «${DASH_NAME}» был архивным — разархивирован (id=${dashId})`)
    } else {
      console.log(`Дашборд «${DASH_NAME}» уже есть (id=${dashId}) — пересобираю карточки`)
    }
  } else {
    const dash = await mb('POST', '/api/dashboard', { name: DASH_NAME, description: 'Семь управленческих отчётов на core-слое (BI поверх той же БД).' })
    dashId = dash.id
    console.log(`Создан дашборд «${DASH_NAME}» (id=${dashId})`)
  }
  // Раскладка пересобирается каждый прогон (PUT заменяет набор dashcards целиком —
  // без дублей, всегда ровно len(cardIds) карточек). По одной в ряд, полуширокая (сетка 24).
  const dashcards = cardIds.map((cardId, i) => ({
    id: -(i + 1), card_id: cardId, row: i * 6, col: 0, size_x: 12, size_y: 6,
    parameter_mappings: [], visualization_settings: {},
  }))
  await mb('PUT', `/api/dashboard/${dashId}`, { dashcards })
  console.log(`  карточек на дашборде: ${dashcards.length}`)
  return dashId
}

async function main() {
  console.log(`Metabase provisioning → ${BASE}`)
  await waitHealth()
  await ensureSession()
  const dbId = await ensureDatabase()
  await waitTables(dbId)
  const cardIds = await ensureCards(dbId)
  const dashId = await ensureDashboard(cardIds)
  console.log('\nГОТОВО:')
  console.log(`  источник id=${dbId}, вопросов=${cardIds.length}, дашборд id=${dashId}`)
  console.log(`  дашборд (внутр.): ${BASE}/dashboard/${dashId}`)
}

main().catch((e) => { console.error('\nОШИБКА:', e.message); process.exit(1) })
