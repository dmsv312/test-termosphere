# ТермоСфера — команды разработки. Каркас: venv + postgres в Docker.
PY := backend/.venv/bin/python
PIP := backend/.venv/bin/pip

.PHONY: help venv up down psql logs migrate revision load api web schema

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

load:            ## CSV из data/ -> raw -> core
	cd backend && .venv/bin/python -m app.etl.run

api:             ## FastAPI (Swagger на /docs)
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

web:             ## фронт (Vite) — появится на шаге 4
	cd frontend && npm run dev

schema:          ## снять схему БД в db/schema.sql
	docker compose exec -T db pg_dump -U termosphere -d termosphere --schema-only > db/schema.sql
