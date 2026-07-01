# API-образ: FastAPI + uvicorn поверх core-слоя. Контекст сборки — ./backend.
FROM python:3.12-slim

WORKDIR /app

# Сначала зависимости — слой кэшируется, пока requirements не менялись.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Затем код приложения (app/, alembic/ и т.п.). .venv/кэши исключены .dockerignore.
COPY . .

# В контейнере слушаем 0.0.0.0:8000; наружу порт публикует docker-compose.
# DATABASE_URL приходит из окружения (compose указывает на сервис db).
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
