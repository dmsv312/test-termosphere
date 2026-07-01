# test-termosphere

Первый аналитический контур над выгрузкой из CRM (Bitrix24-подобной) и связанных производственных таблиц: приведение сырых данных в порядок, нормализация и управленческие отчёты.

**Пайплайн:** `CSV/Excel → PostgreSQL → нормализация (raw → core) → SQL-отчёты → API / дашборд`

## Задача

Дана выгрузка из CRM (13 таблиц: сделки, товары, оплаты, компании, контакты, стадии воронки, история стадий, активности, производственные заказы, отгрузки, маркетинговые затраты и др.). Нужно:

1. Развернуть PostgreSQL.
2. Загрузить данные.
3. Спроектировать staging/raw-слой и нормализованный слой.
4. Найти и описать проблемы качества данных.
5. Сделать SQL-отчёты (воронка, маржа по менеджерам, дебиторка, задержки производства, сделки без активности, источники).
6. Подготовить ER-модель и BPM/FSM-модель процесса сделки.
7. Описать план API/дашборда и использование AI.

Полное ТЗ — в `Тестовое задание .pdf`.

## Архитектура

Многослойный подход (medallion):

```
CSV  →  RAW (всё TEXT, без ограничений)  →  transform (Python)  →  CORE (типы, PK/FK/CHECK)
                                                  │
                                                  ├──→  data_quality_issues (лог: что нашли, что сделали)
                                                  └──→  sources (справочник нормализованных каналов)

CORE  →  вьюхи/запросы  →  7 отчётов  →  FastAPI (JSON)  →  React-дашборд
```

- **raw** — сырьё «как есть», строками, без ограничений (кривая дата/сумма не должна ронять импорт; нужен оригинал для сверки).
- **core** — нормализованный слой: типы, ключи, дефолты, справочники.
- **transform** — Python читает raw, чистит/дедуплицирует/проверяет связи и пишет core, попутно логируя все проблемы качества.

Подробно — в [docs/architecture.md](docs/architecture.md) (ERD, BPM/FSM, словарь таблиц).

## Стек

FastAPI · SQLAlchemy · Alembic · PostgreSQL (Docker) · React (Vite) · Recharts · Mermaid (ERD/BPM/FSM). Опционально Metabase поверх той же БД.

## Структура репозитория

```
test-termosphere/
├── README.md  AGENTS.md  ASSUMPTIONS.md  DATA_QUALITY.md  AI_USAGE.md  dashboard_plan.md
├── docs/
│   ├── architecture.md     # ERD, BPM/FSM, словарь таблиц
│   └── worklog.md          # живой журнал работы (см. AGENTS.md)
├── data/                   # исходные CSV (в git не входят, см. «Быстрый старт»)
├── db/
│   ├── schema.sql          # дамп схемы (make schema)
│   └── reports.sql         # 7 отчётов, генерируется из queries.py (make reports-sql)
├── backend/                # FastAPI + SQLAlchemy + Alembic + ETL + reports
│   └── app/{db,core,models,etl,reports,api}/
└── frontend/               # React (Vite) + Recharts (pages/reports/*, CoreViewer, DataQuality)
```

## Отчёты

1. Воронка — количество и сумма сделок по стадиям.
2. Продажи и маржа по менеджерам.
3. Дебиторка — сумма сделки, оплаты, остаток.
4. Сделки с задержкой производства > 5 дней.
5. Сделки без активности последние N дней.
6. Источники заявок — выручка/маржа и окупаемость.
7. Список проблем данных.

## Документация

| Файл | О чём |
|---|---|
| [AGENTS.md](AGENTS.md) | Правила разработки и документирования (в т.ч. для AI-агента) |
| [ASSUMPTIONS.md](ASSUMPTIONS.md) | Принятые бизнес-допущения и решения |
| [DATA_QUALITY.md](DATA_QUALITY.md) | Каталог проблем качества данных и реакция на них |
| [AI_USAGE.md](AI_USAGE.md) | Как использовали AI: задачи, ручные проверки, где AI ошибался, решения человека |
| [dashboard_plan.md](dashboard_plan.md) | API и дашборд: эндпоинты, экраны, деплой |
| [docs/architecture.md](docs/architecture.md) | Модель данных: ERD, BPM/FSM, словарь таблиц |
| [docs/worklog.md](docs/worklog.md) | Живой журнал: решения, задачи AI, проверки, проблемы |

## Быстрый старт

Исходные CSV в репозиторий не входят — положи 13 файлов выгрузки в `data/` (см. список таблиц выше). Схема и загрузка данных выполняются с хоста (миграции/ETL), затем поднимается контур в Docker:

```bash
make up        # docker: поднять только postgres (порт 5435)
make migrate   # alembic upgrade head — создать raw + core (таблицы средствами Python)
make load      # CSV из data/ → raw, затем transform raw → core
make up-full   # docker: поднять api + web (nginx) поверх наполненной БД
```

Порядок важен: `make up-full` на пустой БД поднимет контейнеры, но ручки вернут 500 — сперва `migrate` + `load` (том `pgdata` наполняется один раз и переживает пересборку образов).

Для разработки фронта/бэка без Docker: `make api` (uvicorn, :8010) + `make web` (Vite dev, :5173, проксирует `/api`). Прочее — `make help`; артефакты: `make schema` (дамп схемы), `make reports-sql` (перегенерировать `db/reports.sql`), `make test` (юнит-тесты чистилок).

Опциональный BI-бонус (Metabase поверх той же БД, docker-профиль `bi`, по умолчанию не поднимается):

```bash
make bi-up          # metabase_db + metabase + nginx-прокси с basic-auth
make bi-provision   # авто-настройка: admin + источник termosphere + 7 вопросов + дашборд
```

Публичный стенд закрыт basic-auth (nginx), опубликован за собственным Cloudflare-туннелем; креды и хеш — вне git (`.env` / `deploy/htpasswd`).

## Статус

Реализованы шаги 0–7 из плана [AGENTS.md](AGENTS.md): каркас → raw → core → transform → живой контур с деплоем → 7 отчётов вертикальными срезами → BI-бонус Metabase. Числа отчётов сверены с эталонными расчётами (Приложение B), живой контур проверен Playwright (0 JS-ошибок) и опубликован за basic-auth. Финальные документы (этот README, [AI_USAGE.md](AI_USAGE.md), [dashboard_plan.md](dashboard_plan.md), ERD/BPM/FSM в [docs/architecture.md](docs/architecture.md)) — на месте. Шаг 7: Metabase (v0.62.3.5) поднят отдельным docker-профилем `bi` поверх той же БД, автопровижининг создаёт источник + 7 вопросов + дашборд (числа сверены), опубликован за тем же basic-auth.
