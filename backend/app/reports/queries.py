"""Канонический SQL семи управленческих отчётов — единый источник правды.

Эти же строки: (1) исполняет API (`app/api/routes/reports.py` через `text()`),
(2) выгружаются в человекочитаемый `db/reports.sql` (`app/reports/dump_sql.py`).
Так отчёт в API и отчёт в файле-дампе не расходятся по определению.

Считаем ТОЛЬКО по core (карантинные строки в core не попали — см. transform).
Ключевые бизнес-правила зафиксированы в ASSUMPTIONS.md и вплетены сюда:

- `amount` сделки = ГИБРИД: `COALESCE(Σ позиций, expected_amount)` (реш. 1).
- Маржа — ТОЛЬКО по позициям: `Σ(qty·price − discount) − Σ(qty·cost)`; где позиций
  нет — маржа NULL («неизвестна»).
- Дата среза («сегодня») = максимум по ФАКТИЧЕСКИМ событиям (без плановых будущих
  дат). На этой выгрузке = 2026-06-15. Общая для отчётов 4 и 5 (реш. 3).
- Продажи/маржа по менеджерам и источникам — по выигранным (stage = WON) (реш. §Прочее).
- Дебиторка — по обязующим стадиям ИЛИ сделкам с оплатами, кроме LOST; `pending`
  не гасит долг; `correction` со знаком уменьшает остаток (реш. 2).
"""

# --- Переиспользуемые фрагменты ----------------------------------------------

# Позиции сделки → выручка/себестоимость; и гибрид-сумма на уровне сделки.
# amount = позиции, если они есть, иначе оценка из карточки (expected_amount).
# line_margin = NULL там, где позиций нет (маржу не выдумываем).
_BASE_CTE = """\
WITH lines AS (
    SELECT dp.deal_id,
           SUM(dp.quantity * dp.unit_price - dp.discount) AS revenue,
           SUM(dp.quantity * p.cost_price)                AS cost
    FROM deal_products dp
    JOIN products p ON p.product_id = dp.product_id
    GROUP BY dp.deal_id
),
deal_amount AS (
    -- позиции считаются со scale 4 (qty·price); деньги приводим к 2 знакам единообразно
    SELECT d.deal_id, d.stage_id, d.manager_id, d.source_id, d.expected_amount,
           l.revenue::numeric(14, 2)                              AS line_revenue,
           (l.revenue - l.cost)::numeric(14, 2)                   AS line_margin,
           COALESCE(l.revenue, d.expected_amount)::numeric(14, 2) AS amount
    FROM deals d
    LEFT JOIN lines l ON l.deal_id = d.deal_id
)"""

# Дата среза = максимум по фактическим событиям (updated_at/оплаты/отгрузки/
# завершённые активности/переходы стадий/факт. финиш производства). Плановые
# будущие даты (custom_deadline, planned_finish) НЕ берём — иначе «задержка» и
# «без активности» считались бы от несуществующего будущего.
CUTOFF_EXPR = """GREATEST(
        (SELECT max(updated_at)::date   FROM deals),
        (SELECT max(payment_date)       FROM payments),
        (SELECT max(actual_date)        FROM shipments),
        (SELECT max(completed_at)::date FROM activities),
        (SELECT max(changed_at)::date   FROM stage_history),
        (SELECT max(actual_finish_at)   FROM production_orders)
    )"""

CUTOFF_SQL = f"SELECT {CUTOFF_EXPR} AS cutoff_date"


# --- Отчёт 1. Воронка ---------------------------------------------------------
# Количество сделок и сумма (гибрид) по стадиям, в порядке воронки. Сделки без
# распознанной стадии (напр. WAIT_CLIENT → NULL) — отдельной строкой «Без стадии».
FUNNEL_SQL = f"""\
{_BASE_CTE}
SELECT ps.sort_order,
       ps.stage_id,
       ps.stage_name,
       ps.is_success,
       count(da.deal_id)                        AS deals,
       COALESCE(SUM(da.amount), 0)::numeric(14, 2) AS amount
FROM pipeline_stages ps
LEFT JOIN deal_amount da ON da.stage_id = ps.stage_id
GROUP BY ps.sort_order, ps.stage_id, ps.stage_name, ps.is_success
UNION ALL
SELECT 999, NULL, 'Без стадии', NULL,
       count(*), COALESCE(SUM(amount), 0)::numeric(14, 2)
FROM deal_amount
WHERE stage_id IS NULL
HAVING count(*) > 0
ORDER BY sort_order
"""


# --- Отчёт 2. Продажи и маржа по менеджерам -----------------------------------
# По выигранным (WON): выручка = Σ amount, маржа = Σ маржи по позициям. Менеджеры
# с 0 продаж тоже в списке (в т.ч. неактивные). `won_without_margin` — сколько
# выигранных сделок без позиций (их маржа неизвестна и в Σ маржи не входит).
MANAGERS_SQL = f"""\
{_BASE_CTE}
SELECT u.user_id,
       u.name,
       u.active,
       count(da.deal_id) FILTER (WHERE da.stage_id = 'WON')                 AS won_deals,
       COALESCE(SUM(da.amount) FILTER (WHERE da.stage_id = 'WON'), 0)::numeric(14, 2) AS revenue,
       SUM(da.line_margin) FILTER (WHERE da.stage_id = 'WON')               AS margin,
       count(*) FILTER (WHERE da.stage_id = 'WON' AND da.line_margin IS NULL) AS won_without_margin
FROM users u
LEFT JOIN deal_amount da ON da.manager_id = u.user_id
WHERE u.role = 'sales_manager'
GROUP BY u.user_id, u.name, u.active
ORDER BY revenue DESC, u.user_id
"""

# Отгружено, но не закрыто (SHIPPED): фактическая продажа, которую не смешиваем с
# закрытыми (WON), но и не теряем — показываем отдельной пометкой к отчёту 2.
SHIPPED_NOT_CLOSED_SQL = f"""\
{_BASE_CTE}
SELECT da.deal_id, da.manager_id, u.name AS manager_name,
       da.amount, da.line_margin AS margin
FROM deal_amount da
LEFT JOIN users u ON u.user_id = da.manager_id
WHERE da.stage_id = 'SHIPPED'
ORDER BY da.deal_id
"""


# --- Отчёт 3. Дебиторка -------------------------------------------------------
# Сделки в обязующих стадиях (CONTRACT/PRODUCTION/SHIPPED/WON) ИЛИ имеющие оплаты,
# кроме LOST. paid = обычные оплаты (prepayment/full, status=paid); pending —
# отдельно (в остаток не входит); correction — со знаком. Остаток может быть
# отрицательным (переплата).
RECEIVABLES_SQL = f"""\
{_BASE_CTE},
pay AS (
    SELECT deal_id,
           SUM(amount) FILTER (WHERE status = 'paid'
                               AND payment_type IN ('prepayment', 'full')) AS paid,
           SUM(amount) FILTER (WHERE status = 'pending')                   AS pending,
           SUM(amount) FILTER (WHERE payment_type = 'correction')          AS correction
    FROM payments
    GROUP BY deal_id
)
SELECT da.deal_id,
       da.stage_id,
       da.amount,
       COALESCE(p.paid, 0)::numeric(14, 2)       AS paid,
       COALESCE(p.pending, 0)::numeric(14, 2)    AS pending,
       COALESCE(p.correction, 0)::numeric(14, 2) AS correction,
       (da.amount - COALESCE(p.paid, 0) + COALESCE(p.correction, 0))::numeric(14, 2) AS balance
FROM deal_amount da
LEFT JOIN pay p ON p.deal_id = da.deal_id
WHERE da.stage_id IS DISTINCT FROM 'LOST'
  AND (da.stage_id IN ('CONTRACT', 'PRODUCTION', 'SHIPPED', 'WON')
       OR p.deal_id IS NOT NULL)
ORDER BY balance DESC, da.deal_id
"""


# --- Отчёт 4. Задержка производства > 5 дней ----------------------------------
# Задержка = COALESCE(факт. финиш, дата среза) − плановый финиш. Готовые заказы
# считаем по факту, незавершённые — по дате среза.
PRODUCTION_DELAYS_SQL = f"""\
WITH cutoff AS (SELECT {CUTOFF_EXPR} AS d)
SELECT po.production_order_id,
       po.deal_id,
       po.status,
       po.planned_finish_at,
       po.actual_finish_at,
       (COALESCE(po.actual_finish_at, (SELECT d FROM cutoff)) - po.planned_finish_at) AS delay_days
FROM production_orders po
WHERE po.planned_finish_at IS NOT NULL
  AND (COALESCE(po.actual_finish_at, (SELECT d FROM cutoff)) - po.planned_finish_at) > 5
ORDER BY delay_days DESC, po.production_order_id
"""


# --- Отчёт 5. Сделки без активности N дней ------------------------------------
# Живые сделки (не WON/LOST), где дата среза − последнее касание > N ИЛИ касаний
# не было. Касание = только записи activities (deadline/completed), не stage_history.
STALE_DEALS_SQL = f"""\
WITH cutoff AS (SELECT {CUTOFF_EXPR} AS d),
touch AS (
    SELECT deal_id, max(GREATEST(deadline_at, completed_at))::date AS last_touch
    FROM activities
    GROUP BY deal_id
)
SELECT d.deal_id,
       d.stage_id,
       t.last_touch,
       ((SELECT d FROM cutoff) - t.last_touch) AS days_since
FROM deals d
LEFT JOIN touch t ON t.deal_id = d.deal_id
WHERE d.stage_id IS DISTINCT FROM 'WON'
  AND d.stage_id IS DISTINCT FROM 'LOST'
  AND (t.last_touch IS NULL OR ((SELECT d FROM cutoff) - t.last_touch) > :n_days)
ORDER BY days_since DESC NULLS FIRST, d.deal_id
"""


# --- Отчёт 6. Источники заявок: выручка/маржа + окупаемость --------------------
# По каналу: всего сделок, выигранных, выручка/маржа по WON, затраты из
# marketing_costs. ROMI = (выручка − затраты)/затраты; при нулевых затратах
# (нет строк расходов ИЛИ сумма 0) деления не делаем — считаем «нет затрат».
SOURCES_SQL = f"""\
{_BASE_CTE},
mc AS (
    SELECT source_id, SUM(cost_amount) AS costs, count(*) AS cost_rows
    FROM marketing_costs
    GROUP BY source_id
)
SELECT s.id,
       s.code,
       s.name,
       count(da.deal_id)                                              AS deals,
       count(da.deal_id) FILTER (WHERE da.stage_id = 'WON')           AS won_deals,
       COALESCE(SUM(da.amount) FILTER (WHERE da.stage_id = 'WON'), 0)::numeric(14, 2) AS revenue,
       SUM(da.line_margin) FILTER (WHERE da.stage_id = 'WON')         AS margin,
       COALESCE(mc.costs, 0)::numeric(14, 2)                          AS costs,
       COALESCE(mc.cost_rows, 0)                                      AS cost_rows
FROM sources s
LEFT JOIN deal_amount da ON da.source_id = s.id
LEFT JOIN mc ON mc.source_id = s.id
GROUP BY s.id, s.code, s.name, mc.costs, mc.cost_rows
ORDER BY revenue DESC, s.code
"""


# --- Отчёт 7. Проблемы данных -------------------------------------------------
# Агрегат лога качества по типу × реакция (детальную таблицу отдаёт /api/data-quality).
DATA_QUALITY_SQL = """\
SELECT issue_type,
       action,
       count(*) AS count
FROM data_quality_issues
GROUP BY issue_type, action
ORDER BY issue_type, action
"""


# Значение N по умолчанию для отчёта 5 (дни без активности).
DEFAULT_STALE_DAYS = 14

# Реестр отчётов для дампа в db/reports.sql (порядок = порядок в файле/меню).
# API-обёртки живут в routes/reports.py; здесь — только SQL и заголовки.
REPORTS = [
    ("1. Воронка продаж", FUNNEL_SQL),
    ("2. Продажи и маржа по менеджерам", MANAGERS_SQL),
    ("2a. Отгружено, но не закрыто (доп. к отчёту 2)", SHIPPED_NOT_CLOSED_SQL),
    ("3. Дебиторка", RECEIVABLES_SQL),
    ("4. Задержка производства > 5 дней", PRODUCTION_DELAYS_SQL),
    ("5. Сделки без активности N дней (N = %d)" % DEFAULT_STALE_DAYS, STALE_DEALS_SQL),
    ("6. Источники заявок: выручка/маржа + окупаемость", SOURCES_SQL),
    ("7. Проблемы данных (агрегат)", DATA_QUALITY_SQL),
]
