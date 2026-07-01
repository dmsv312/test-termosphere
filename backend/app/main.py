from fastapi import FastAPI
from sqlalchemy import text

from app.db.session import engine

app = FastAPI(
    title="ТермоСфера — аналитический контур",
    description="CSV → PostgreSQL → нормализация (raw→core) → отчёты → API/дашборд",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict:
    """Живость API и соединение с БД (используется для проверки каркаса)."""
    with engine.connect() as conn:
        db_ok = conn.execute(text("select 1")).scalar() == 1
    return {"status": "ok", "db_reachable": db_ok}
