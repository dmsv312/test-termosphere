# API-контракт — ТермоСфера

Контракт REST API аналитического контура. Дополняет машинную схему
[`openapi.json`](openapi.json) (её же отдаёт живой сервер на `/openapi.json` и
рисует Swagger UI на `/docs`): здесь — форма ответа каждого эндпоинта с типами
полей и примерами, чего в авто-схеме нет (ответы отдаются как `application/json`
без Pydantic-моделей).

- **Версия:** 0.1.0
- **База:** все пути относительные (`/api/*`, `/health`). В dev их проксирует
  Vite на `:8010`, в проде — nginx на контейнер API. Один origin, CORS не нужен.
- **Метод:** только `GET`. Контур **read-only** — ни один эндпоинт не меняет данные.
- **Аутентификация:** на уровне API её нет; публичный доступ закрыт basic-auth
  на nginx (см. README). Локально API доступен на `127.0.0.1:8010` без пароля.

## Соглашения по типам

| В JSON | Тип | Почему |
|---|---|---|
| Деньги, цены, количества | **строка** (`"126000.00"`) | `Decimal` сериализуем строкой — не теряем копейки и точность |
| ИНН | **строка** (`"0278123456"`) | значимы ведущие нули |
| Даты и время | **строка ISO-8601** (`"2026-06-08T16:45:00+00:00"`, `"2026-06-15"`) | однозначный разбор |
| Счётчики, разницы дат, `sort_order` | **число** | это целые, не деньги |
| Отсутствующее значение | `null` | напр. маржа неизвестна, нет даты закрытия |

Денежное поле всегда строка, поэтому на клиенте перед арифметикой/форматированием
его приводят к числу (`Number(v)`); `null` рендерим как «—».

---

## Служебное

### `GET /health`
Живость приложения и доступность БД (для проверки контейнера/каркаса).

```json
{ "status": "ok", "db_reachable": true }
```

---

## Витрина core

### `GET /api/core/tables`
Список core-таблиц по белому списку: системное имя, человекочитаемая подпись,
число строк. Порядок — как в модели данных.

```json
[
  { "name": "sources", "label": "Источники (каналы)", "count": 6 },
  { "name": "deals",   "label": "Сделки",             "count": 11 }
]
```

### `GET /api/core/{table}`
Строки одной core-таблицы. `{table}` — только из белого списка (см. `/tables`);
неизвестное имя → **404**.

**Параметр запроса:** `limit` (int, диапазон `1…5000`, по умолчанию 500) — ограничение
числа строк; вне диапазона → **422**.

| Поле | Тип | Описание |
|---|---|---|
| `table` | string | системное имя таблицы |
| `label` | string | человекочитаемая подпись |
| `columns` | string[] | имена колонок в порядке схемы |
| `rows` | object[] | строки; ключи = `columns`; денежные/датовые поля — по соглашениям выше |

У строк с бизнес-сигналом поле `has_quality_issue = true` (клиент их подсвечивает).

Пример сокращён: у `deals` 15 колонок; ниже показаны несколько (в порядке схемы).

```json
{
  "table": "deals",
  "label": "Сделки",
  "columns": ["deal_id", "title", "created_at", "stage_id", "expected_amount", "currency", "has_quality_issue"],
  "rows": [
    { "deal_id": "D1001", "title": "Панели для склада Альфа", "created_at": "2026-06-01T04:14:58+00:00",
      "stage_id": "PRODUCTION", "expected_amount": "150000.00", "currency": "RUB", "has_quality_issue": false }
  ]
}
```

---

## Отчёты

Все отчёты считаются каноническим SQL из `backend/app/reports/queries.py` — тем же,
что выгружается в [`db/reports.sql`](../db/reports.sql). Бизнес-правила (гибрид-сумма,
дата среза, дебиторка) — в [ASSUMPTIONS.md](../ASSUMPTIONS.md).

### `GET /api/reports/funnel` — воронка
Количество сделок и сумма по стадиям, в порядке воронки. Сделки с нераспознанной
стадией — отдельной строкой «Без стадии» (`stage_id: null`).

Строка `rows[]`: `sort_order` (int), `stage_id` (string|null), `stage_name` (string),
`is_success` (bool|null), `deals` (int), `amount` (string). Плюс `totals: {deals, amount}`.

```json
{
  "report": "funnel", "title": "Воронка продаж",
  "rows": [
    { "sort_order": 10, "stage_id": "NEW", "stage_name": "Новая заявка",
      "is_success": false, "deals": 1, "amount": "35000.00" }
  ],
  "totals": { "deals": 11, "amount": "1040000.00" }
}
```

### `GET /api/reports/managers` — продажи и маржа по менеджерам
По выигранным сделкам (стадия WON). Плюс отдельный блок «отгружено, но не закрыто».

Строка `rows[]`: `user_id` (string), `name` (string), `active` (bool),
`won_deals` (int), `revenue` (string), `margin` (string|**null** — если у всех
выигранных сделок нет позиций), `won_without_margin` (int — сколько выигранных
без позиций).
Блок `shipped_not_closed[]`: `deal_id`, `manager_id`, `manager_name`, `amount`, `margin`.

```json
{
  "report": "managers", "title": "Продажи и маржа по менеджерам",
  "rows": [
    { "user_id": "U10", "name": "Иван Петров", "active": true,
      "won_deals": 2, "revenue": "361000.00", "margin": "85600.00", "won_without_margin": 1 }
  ],
  "shipped_not_closed": [
    { "deal_id": "D1005", "manager_id": "U11", "manager_name": "Анна Соколова",
      "amount": "92000.00", "margin": "48500.00" }
  ]
}
```

### `GET /api/reports/receivables` — дебиторка
Сделки в обязующих стадиях (CONTRACT/PRODUCTION/SHIPPED/WON) или с любыми оплатами,
кроме LOST. Остаток = `amount − paid + correction`; `pending` в остаток не входит.

Строка `rows[]`: `deal_id`, `stage_id`, `amount`, `paid`, `pending`, `correction`,
`balance` (все деньги — строкой; `balance` может быть отрицательным — переплата).
Плюс `totals` по тем же денежным колонкам.

```json
{
  "report": "receivables", "title": "Дебиторка",
  "rows": [
    { "deal_id": "D1005", "stage_id": "SHIPPED", "amount": "92000.00",
      "paid": "100000.00", "pending": "0.00", "correction": "0.00", "balance": "-8000.00" }
  ],
  "totals": { "amount": "837000.00", "paid": "396000.00", "pending": "30000.00",
              "correction": "-5000.00", "balance": "436000.00" }
}
```

### `GET /api/reports/production-delays` — задержка производства > 5 дней
Заказы, где `COALESCE(actual_finish, дата_среза) − planned_finish > 5`.

Верхний уровень: `cutoff_date` (ISO date — дата среза), `threshold_days` (int, = 5).
Строка `rows[]`: `production_order_id`, `deal_id`, `status`, `planned_finish_at`
(date), `actual_finish_at` (date|null), `delay_days` (int).

```json
{
  "report": "production-delays", "title": "Задержка производства > 5 дней",
  "cutoff_date": "2026-06-15", "threshold_days": 5,
  "rows": [
    { "production_order_id": "PO003", "deal_id": "D1005", "status": "done",
      "planned_finish_at": "2026-06-08", "actual_finish_at": "2026-06-14", "delay_days": 6 }
  ]
}
```

### `GET /api/reports/stale-deals` — сделки без активности N дней
Живые сделки (не WON/LOST), где от даты среза до последнего касания прошло больше N
дней либо активностей не было вовсе.

**Параметр запроса:** `n_days` (int, по умолчанию **14**, диапазон `0…3650`;
вне диапазона → **422**).
Верхний уровень: `cutoff_date` (ISO date), `n_days` (int — эхо параметра).
Строка `rows[]`: `deal_id`, `stage_id` (string|null), `last_touch` (date|null —
`null`, если активностей не было), `days_since` (int|null).

```json
{
  "report": "stale-deals", "title": "Сделки без активности N дней",
  "cutoff_date": "2026-06-15", "n_days": 14,
  "rows": [
    { "deal_id": "D1006", "stage_id": "NEW", "last_touch": null, "days_since": null }
  ]
}
```

### `GET /api/reports/sources` — источники: выручка/маржа + окупаемость
По каналам. ROMI считаем только при реальных затратах, иначе `has_costs=false`,
`romi=null` («нет затрат»).

Строка `rows[]`: `id` (int), `code` (string), `name` (string), `deals` (int),
`won_deals` (int), `revenue` (string), `margin` (string|null), `costs` (string),
`cost_rows` (int), `has_costs` (bool), `romi` (number|null — отношение прибыли к затратам; напр. `27.7805` = +2778 %, на клиенте умножается на 100).

```json
{
  "report": "sources", "title": "Источники заявок",
  "rows": [
    { "id": 3, "code": "yandex_direct", "name": "Яндекс.Директ", "deals": 2,
      "won_deals": 1, "revenue": "236000.00", "margin": "85600.00", "costs": "8200.00",
      "cost_rows": 1, "has_costs": true, "romi": 27.7805 },
    { "id": 5, "code": "referral", "name": "Рекомендации", "deals": 1, "won_deals": 1,
      "revenue": "125000.00", "margin": null, "costs": "0.00", "cost_rows": 0,
      "has_costs": false, "romi": null }
  ]
}
```

---

## Качество данных (отчёт №7)

### `GET /api/data-quality/summary`
Агрегат журнала `data_quality_issues`.

`total` (int); `by_action` (объект `{fixed, quarantined, flagged}` — int);
`by_type` (массив `{issue_type, action, count}`).

```json
{
  "total": 29,
  "by_action": { "fixed": 9, "quarantined": 8, "flagged": 12 },
  "by_type": [ { "issue_type": "duplicate_deal", "action": "quarantined", "count": 1 } ]
}
```

### `GET /api/data-quality/issues`
Полный список проблем (для детальной таблицы). Массив объектов:
`id` (int), `entity` (string), `entity_id` (string|null), `issue_type` (string),
`action` (`fixed`|`quarantined`|`flagged`), `details` (string|null),
`detected_at` (ISO datetime).

```json
[
  { "id": 26, "entity": "activity", "entity_id": "A903", "issue_type": "orphan_deal",
    "action": "quarantined", "details": "активность на отсутствующую сделку D9999",
    "detected_at": "2026-07-01T09:09:52.337710+00:00" }
]
```

---

## Коды ответов

| Код | Когда |
|---|---|
| `200` | успешный ответ |
| `404` | `GET /api/core/{table}` с именем вне белого списка |
| `422` | `n_days` вне `0…3650` или `limit` (`/api/core/{table}`) вне `1…5000` |
| `500` | БД не наполнена (`migrate`+`load` не выполнены) — см. README |

## Как обновлять контракт

`openapi.json` генерируется из живого приложения: `make openapi`. Формулы отчётов
меняются в `queries.py` → `make reports-sql`. Этот файл (`api-contract.md`) правится
руками при изменении формы ответа.
