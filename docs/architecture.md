# Архитектура и модель данных

## Слои

```
CSV  →  RAW (все колонки TEXT, без ограничений, суррогатный PK)
             │  transform (Python): чистка, дедуп, проверка связей, лог
             ▼
        CORE (типы, PK / FK / CHECK, справочники)
             │
             ├─→ sources               (нормализованные каналы)
             ├─→ data_quality_issues   (журнал проблем: entity, issue_type, action)
             ▼
        Вьюхи / запросы  →  7 отчётов  →  FastAPI (JSON)  →  React-дашборд
```

- **raw** — оригинал «как есть»; ограничений нет.
- **core** — нормализованный слой; целостность гарантируют PK/FK/CHECK.
- Активная проверка и решения (fix/quarantine/flag) — в Python до вставки в core.

## Словарь таблиц

| Таблица | Что это | Ключ |
|---|---|---|
| `deals` | сделки | `deal_id` |
| `deal_products` | позиции сделки | (`deal_id`, `product_id`) |
| `products` | товары + себестоимость | `product_id` (и `sku`) |
| `payments` | оплаты | `payment_id` |
| `companies` | компании-клиенты | `company_id` |
| `contacts` | контактные лица | `contact_id` |
| `users` | сотрудники | `user_id` |
| `pipeline_stages` | стадии воронки (справочник) | `stage_id` |
| `stage_history` | журнал переходов по стадиям | `event_id` |
| `activities` | звонки/письма/задачи | `activity_id` |
| `production_orders` | производственные заказы | `production_order_id` |
| `shipments` | отгрузки | `shipment_id` |
| `marketing_costs` | затраты на рекламу по каналам | (дата/канал) |
| `sources` *(наша)* | нормализованные каналы | `id` |
| `data_quality_issues` *(наша)* | журнал проблем качества | `id` |

## ER-модель (ERD)

Диаграмма core-слоя с ключевыми атрибутами (PK/FK и значимые поля). Полная схема
со всеми колонками и ограничениями — в [db/schema.sql](../db/schema.sql). Деньги —
`decimal`, ИНН — `string` (ведущие нули), даты выгрузки — `date`/`datetime` (+05:00).

```mermaid
erDiagram
    companies      ||--o{ contacts          : "имеет"
    companies      ||--o{ deals             : "клиент"
    contacts       ||--o{ deals             : "контакт"
    users          ||--o{ deals             : "менеджер"
    pipeline_stages||--o{ deals             : "стадия"
    sources        ||--o{ deals             : "канал"
    deals          ||--o{ deal_products     : "позиции"
    products       ||--o{ deal_products     : "товар"
    products       ||--o{ products          : "дубль→канон"
    deals          ||--o{ payments          : "оплаты"
    deals          ||--o{ stage_history     : "переходы"
    deals          ||--o{ activities        : "активности"
    deals          ||--o{ production_orders : "производство"
    deals          ||--o{ shipments         : "отгрузки"
    sources        ||--o{ marketing_costs   : "затраты"

    sources {
        int    id           PK
        string code         UK "avito, website, ..."
        string name
    }
    users {
        string user_id      PK
        string name
        string role         "sales_manager / production_manager / director"
        bool   active
        string email
    }
    companies {
        string company_id   PK
        string name
        string inn          "строка: ведущие нули значимы"
        string city
        string industry
    }
    contacts {
        string contact_id   PK
        string company_id   FK "nullable: сирота → NULL + флаг"
        string name
        string phone        "нормализован +7XXXXXXXXXX"
        string email
    }
    products {
        string product_id   PK
        string sku
        string name
        decimal cost_price  "себестоимость → маржа"
        bool   is_active
        string canonical_id FK "дубль по SKU → канонический товар"
    }
    pipeline_stages {
        string stage_id     PK
        string stage_name
        int    sort_order
        bool   is_final
        bool   is_success
    }
    deals {
        string deal_id      PK "после дедупа (max updated_at)"
        string title
        datetime created_at
        datetime updated_at
        datetime closed_at  "WON без даты → NULL + флаг"
        date   custom_deadline
        string stage_id     FK "WAIT_CLIENT → NULL + флаг"
        string manager_id   FK "nullable"
        string company_id   FK "nullable"
        string contact_id   FK "nullable"
        int    source_id    FK "нормализованный канал"
        decimal expected_amount "оценка из карточки; гибрид-сумма — в отчётах"
        string currency     "пусто → RUB + флаг"
        bool   has_quality_issue
    }
    deal_products {
        int    id           PK "суррогат"
        string deal_id      FK "сирота → карантин"
        string product_id   FK "PR999 → карантин"
        decimal quantity
        decimal unit_price
        decimal discount    "абсолютные рубли"
    }
    payments {
        string payment_id   PK
        string deal_id      FK "D9999 → карантин"
        date   payment_date
        decimal amount      "correction может быть < 0 (легально)"
        string payment_type "prepayment / full / correction / unknown"
        string status       "paid / pending"
    }
    stage_history {
        string event_id     PK
        string deal_id      FK "D1012 → карантин"
        string old_stage_id FK
        string new_stage_id FK
        datetime changed_at
        string changed_by_id FK
    }
    activities {
        string activity_id  PK
        string deal_id      FK
        string activity_type "call / email / task"
        bool   completed
        datetime deadline_at
        datetime completed_at
    }
    production_orders {
        string production_order_id PK
        string deal_id      FK
        datetime created_at "раньше сделки → флаг temporal_inconsistency"
        date   planned_finish_at
        date   actual_finish_at
        string status       "planned / in_progress / done"
        string workshop
    }
    shipments {
        string shipment_id  PK
        string deal_id      FK
        date   planned_date
        date   actual_date
        string status       "planned / shipped"
    }
    marketing_costs {
        int    id           PK "суррогат"
        date   cost_date
        int    source_id    FK "нормализованный канал"
        string campaign
        decimal cost_amount
    }
    data_quality_issues {
        int    id           PK
        string entity       "deal, payment, ..."
        string entity_id    "натуральный ключ проблемной строки"
        string issue_type   "negative_amount, orphan_deal, ..."
        string action       "fixed / quarantined / flagged"
        string details
        datetime detected_at
    }
```

## FSM — автомат стадий сделки

```mermaid
stateDiagram-v2
    [*] --> NEW
    NEW --> QUALIFICATION
    QUALIFICATION --> CALCULATION
    CALCULATION --> PROPOSAL
    PROPOSAL --> CONTRACT
    CONTRACT --> PRODUCTION
    PRODUCTION --> SHIPPED
    SHIPPED --> WON
    NEW --> LOST
    QUALIFICATION --> LOST
    CALCULATION --> LOST
    PROPOSAL --> LOST
    CONTRACT --> LOST
    WON --> [*]
    LOST --> [*]
```

**Нарушения автомата в данных:** сделка D1001 в истории прыгнула `QUALIFICATION → PRODUCTION`, минуя `CALCULATION/PROPOSAL/CONTRACT` (нелегальный переход); сделка D1011 стоит на стадии `WAIT_CLIENT`, которой нет в справочнике.

## BPM — процесс сделки

```mermaid
flowchart TD
    A[Заявка из канала] --> B[Новая сделка + менеджер]
    B --> C{Квалифицирован?}
    C -- нет --> L[Проиграно]
    C -- да --> D[Расчёт спецификации]
    D --> E[КП отправлено]
    E --> F{Договор?}
    F -- нет --> L
    F -- да --> G[Договор + предоплата]
    G --> H[Производство: заказ в цех]
    H --> I[Отгрузка]
    I --> J[Полная оплата]
    J --> K[Успешно / закрыто]
```
