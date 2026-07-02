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
| [docs/api-contract.md](docs/api-contract.md) | Контракт REST API: эндпоинты, параметры, форма ответа, примеры (+ машинная схема [openapi.json](docs/openapi.json)) |
| [docs/architecture.md](docs/architecture.md) | Модель данных: ERD (с атрибутами), BPM/FSM, словарь таблиц |
| [docs/worklog.md](docs/worklog.md) | Живой журнал: решения, задачи AI, проверки, проблемы |

## Быстрый старт (с нуля)

Что нужно на машине: **Docker + Docker Compose, Python 3.12+, Node 18+ / npm, make** (для шага B полного контура ещё `openssl` — генерация хеша пароля).

**ОС:** Linux и macOS — нативно; Windows — только через **WSL2** (или Git Bash). Нативные PowerShell/cmd не подойдут: Makefile и команды рассчитаны на unix-shell (`make`, пути `.venv/bin`, `openssl`, `printf`). Само приложение работает в linux-контейнерах, поэтому хостовая ОС на него не влияет — ограничение только в обвязке запуска.

### 1. Данные

Исходные CSV в репозиторий намеренно не входят (`data/*.csv` в `.gitignore`) — это тестовая выгрузка, после загрузки она живёт в БД. Возьми 13 листов из Google-таблицы, указанной в `Тестовое задание .pdf`, выгрузи каждый в CSV и положи в `data/` под именем `Таблица выгрузки Битрикс - <таблица>.csv` — загрузчик ищет файлы строго по этому шаблону. Нужны все 13:

```
users · companies · contacts · products · pipeline_stages · deals · deal_products
payments · stage_history · activities · production_orders · shipments · marketing_costs
```

### 2. Окружение

```bash
cp .env.example .env      # значения по умолчанию годятся для локального запуска
```

### 3. Развернуть и загрузить данные

```bash
make venv       # создать backend/.venv и поставить зависимости (Python)
make up         # docker: поднять только postgres (порт 5435)
make migrate    # alembic upgrade head — создать raw + core (типы, PK/FK/CHECK)
make load       # CSV из data/ → raw, затем нормализация raw → core
```

`make load` в конце печатает сводку — на эталонной выгрузке это `core.deals: 11` и `data_quality_issues: 29 (fixed=9, quarantined=8, flagged=12)` (всего 80 строк в raw). Если увидел эти числа — пайплайн отработал верно.

### 4. Открыть

Есть два пути.

**A. Дев-режим (быстрее всего посмотреть, без пароля):**

```bash
make api        # FastAPI + Swagger на http://localhost:8010/docs
make web        # дашборд на http://localhost:5173 (проксирует /api на :8010)
```

**B. Полный контур в Docker (как в проде, за basic-auth):**

```bash
# basic-auth обязателен (nginx). Создай файл логина/пароля ОДИН раз:
mkdir -p deploy && printf '%s:%s\n' "termosphere" "$(openssl passwd -apr1 'ВАШ_ПАРОЛЬ')" > deploy/htpasswd
make up-full    # docker: собрать и поднять api + web (nginx) поверх наполненной БД
# дашборд на http://localhost:8090 (логин termosphere / ВАШ_ПАРОЛЬ)
# Swagger UI — там же на /docs (ReDoc на /redoc, схема на /openapi.json), за тем же basic-auth
```

Порядок важен: `make up-full` на пустой БД поднимет контейнеры, но ручки вернут 500 — сперва `migrate` + `load` (том `pgdata` наполняется один раз и переживает пересборку образов). Без файла `deploy/htpasswd` контейнер `web` стартует, но nginx не может прочитать файл паролей и отдаёт 500 на запросы — поэтому создай его до `up-full` (шаг B выше).

Файл `deploy/htpasswd` должен остаться **читаемым** (по умолчанию создаётся читаемым — `644`/`664`, подходит). Не ставь `chmod 600`: nginx-воркер в контейнере (uid 101) не владелец файла и не сможет его прочитать — тогда запросы вернут 500.

**Доступ снаружи.** Порты привязаны к `127.0.0.1` (db 5435, api 8010, web 8090) — намеренно, ради безопасности: из коробки контур доступен только с той же машины (`localhost`). Cloudflare-туннель и публичный домен к репозиторию не относятся (cloudflared живёт на хосте, не в git) — `make up-full` работает и без них. Чтобы открыть контур с другой машины (подняли на сервере): либо SSH-проброс порта (`ssh -L 8090:127.0.0.1:8090 сервер`), либо свой обратный прокси/туннель перед `web`, либо поменять привязку на `0.0.0.0` в `docker-compose.yml` (снимает изоляцию — только осознанно и обязательно за basic-auth).

### Прочее

`make help` — все команды. Артефакты: `make schema` (дамп схемы БД), `make reports-sql` (перегенерировать `db/reports.sql` из `queries.py`), `make openapi` (перегенерировать `docs/openapi.json`), `make test` (юнит-тесты чистилок).

Опциональный BI-бонус (Metabase поверх той же БД, docker-профиль `bi`, по умолчанию не поднимается):

```bash
make bi-up          # metabase_db + metabase + nginx-прокси (reverse-proxy)
make bi-provision   # авто-настройка: admin + источник termosphere + 7 вопросов + дашборд
```

Публикация — за собственным Cloudflare-туннелем. Авторизация различается по хостнейму: витрина (`termosphere.dm312sv.online`) закрыта basic-auth на nginx (креды/хеш вне git: `.env` / `deploy/htpasswd`); BI (`bi.dm312sv.online`) — за собственным логином Metabase (email+пароль), без отдельного basic-auth, то есть один запрос авторизации. Сам Metabase напрямую наружу не торчит.

## Статус

Реализованы шаги 0–7 из плана [AGENTS.md](AGENTS.md): каркас → raw → core → transform → живой контур с деплоем → 7 отчётов вертикальными срезами → BI-бонус Metabase. Числа отчётов сверены с эталонными расчётами (Приложение B), живой контур проверен Playwright (0 JS-ошибок) и опубликован за basic-auth. Финальные документы (этот README, [AI_USAGE.md](AI_USAGE.md), [dashboard_plan.md](dashboard_plan.md), ERD/BPM/FSM в [docs/architecture.md](docs/architecture.md)) — на месте. Шаг 7: Metabase (v0.62.3.5) поднят отдельным docker-профилем `bi` поверх той же БД, автопровижининг создаёт источник + 7 вопросов + дашборд (числа сверены), опубликован за тем же basic-auth.
