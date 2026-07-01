-- db/reports.sql — семь управленческих отчётов (ТермоСфера).
--
-- СГЕНЕРИРОВАНО из backend/app/reports/queries.py (не править вручную:
-- правки внесите в queries.py и выполните `make reports-sql`).
-- Тот же SQL исполняет API (/api/reports/*), поэтому файл и живые отчёты совпадают.
--
-- Считаем по core-слою (карантинные строки в core не попали). Бизнес-правила —
-- в ASSUMPTIONS.md. Все запросы read-only.


-- === 1. Воронка продаж ===
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
)
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
ORDER BY sort_order;


-- === 2. Продажи и маржа по менеджерам ===
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
)
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
ORDER BY revenue DESC, u.user_id;


-- === 2a. Отгружено, но не закрыто (доп. к отчёту 2) ===
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
)
SELECT da.deal_id, da.manager_id, u.name AS manager_name,
       da.amount, da.line_margin AS margin
FROM deal_amount da
LEFT JOIN users u ON u.user_id = da.manager_id
WHERE da.stage_id = 'SHIPPED'
ORDER BY da.deal_id;


-- === 3. Дебиторка ===
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
),
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
ORDER BY balance DESC, da.deal_id;


-- === 4. Задержка производства > 5 дней ===
WITH cutoff AS (SELECT GREATEST(
        (SELECT max(updated_at)::date   FROM deals),
        (SELECT max(payment_date)       FROM payments),
        (SELECT max(actual_date)        FROM shipments),
        (SELECT max(completed_at)::date FROM activities),
        (SELECT max(changed_at)::date   FROM stage_history),
        (SELECT max(actual_finish_at)   FROM production_orders)
    ) AS d)
SELECT po.production_order_id,
       po.deal_id,
       po.status,
       po.planned_finish_at,
       po.actual_finish_at,
       (COALESCE(po.actual_finish_at, (SELECT d FROM cutoff)) - po.planned_finish_at) AS delay_days
FROM production_orders po
WHERE po.planned_finish_at IS NOT NULL
  AND (COALESCE(po.actual_finish_at, (SELECT d FROM cutoff)) - po.planned_finish_at) > 5
ORDER BY delay_days DESC, po.production_order_id;


-- === 5. Сделки без активности N дней (N = 14) ===
WITH cutoff AS (SELECT GREATEST(
        (SELECT max(updated_at)::date   FROM deals),
        (SELECT max(payment_date)       FROM payments),
        (SELECT max(actual_date)        FROM shipments),
        (SELECT max(completed_at)::date FROM activities),
        (SELECT max(changed_at)::date   FROM stage_history),
        (SELECT max(actual_finish_at)   FROM production_orders)
    ) AS d),
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
  AND (t.last_touch IS NULL OR ((SELECT d FROM cutoff) - t.last_touch) > 14)
ORDER BY days_since DESC NULLS FIRST, d.deal_id;


-- === 6. Источники заявок: выручка/маржа + окупаемость ===
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
),
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
ORDER BY revenue DESC, s.code;


-- === 7. Проблемы данных (агрегат) ===
SELECT issue_type,
       action,
       count(*) AS count
FROM data_quality_issues
GROUP BY issue_type, action
ORDER BY issue_type, action;
