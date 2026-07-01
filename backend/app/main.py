from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import core as core_routes
from app.api.routes import quality as quality_routes
from app.core.config import settings
from app.db.session import engine

app = FastAPI(
    title="ТермоСфера — аналитический контур",
    description="CSV → PostgreSQL → нормализация (raw→core) → отчёты → API/дашборд",
    version="0.1.0",
)

# Dev: фронт на Vite (другой origin) ходит в API напрямую; в проде — тот же origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(core_routes.router)
app.include_router(quality_routes.router)


@app.get("/health")
def health() -> dict:
    """Живость API и соединение с БД (используется для проверки каркаса)."""
    with engine.connect() as conn:
        db_ok = conn.execute(text("select 1")).scalar() == 1
    return {"status": "ok", "db_reachable": db_ok}
