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
    deals          ||--o{ payments          : "оплаты"
    deals          ||--o{ stage_history     : "переходы"
    deals          ||--o{ activities        : "активности"
    deals          ||--o{ production_orders : "производство"
    deals          ||--o{ shipments         : "отгрузки"
    sources        ||--o{ marketing_costs   : "затраты"
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
