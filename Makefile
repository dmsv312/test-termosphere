# ТермоСфера — команды разработки. Каркас: venv + postgres в Docker.
PY := backend/.venv/bin/python
PIP := backend/.venv/bin/pip

.PHONY: help venv up down psql logs migrate revision load transform test api web schema reports-sql build up-full down-full logs-app bi-up bi-provision bi-down bi-logs

help:            ## список команд
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-12s %s\n", $$1, $$2}'

venv:            ## создать venv и поставить зависимости
	python3 -m venv backend/.venv
	$(PIP) install -U pip
	$(PIP) install -r backend/requirements.txt

up:              ## поднять postgres (порт 5435)
	docker compose up -d db

down:            ## остановить контейнеры
	docker compose down

psql:            ## psql в контейнер
	docker compose exec db psql -U termosphere -d termosphere

logs:            ## логи postgres
	docker compose logs -f db

migrate:         ## применить миграции (alembic upgrade head)
	cd backend && .venv/bin/alembic upgrade head

revision:        ## autogenerate ревизию: make revision m="описание"
	cd backend && .venv/bin/alembic revision --autogenerate -m "$(m)"

load:            ## CSV из data/ -> raw -> core (полный проход)
	cd backend && .venv/bin/python -m app.etl.run

transform:       ## raw -> core (нормализация, дедуп, лог качества)
	cd backend && .venv/bin/python -m app.etl.transform

test:            ## юнит-тесты чистилок (pytest)
	cd backend && .venv/bin/pytest -q

api:             ## FastAPI локально (Swagger на /docs); 8000 занят → 8010
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8010

web:             ## фронт (Vite dev, :5173, проксирует /api на :8010)
	cd frontend && npm run dev

schema:          ## снять схему БД в db/schema.sql
	docker compose exec -T db pg_dump -U termosphere -d termosphere --schema-only > db/schema.sql

reports-sql:     ## сгенерировать db/reports.sql из канонического SQL (queries.py)
	cd backend && .venv/bin/python -m app.reports.dump_sql

build:           ## собрать образы api + web
	docker compose build api web

up-full:         ## поднять весь контур (db + api + web) в docker
	docker compose up -d --build

down-full:       ## остановить весь контур (включая bi, если поднят) + удалить сеть
	docker compose --profile bi down

logs-app:        ## логи api + web
	docker compose logs -f api web

# --- Шаг 7: Metabase (BI, профиль bi) ---
bi-up:           ## поднять Metabase-контур (metabase_db + metabase + прокси)
	docker compose --profile bi up -d metabase_db metabase metabase_proxy

bi-provision:    ## авто-настройка Metabase (admin + источник + вопросы + дашборд); идемпотентно
	node --env-file=.env scripts/metabase-provision.mjs

bi-down:         ## остановить Metabase-контур
	docker compose --profile bi rm -sf metabase_proxy metabase metabase_db

bi-logs:         ## логи Metabase
	docker compose --profile bi logs -f metabase
