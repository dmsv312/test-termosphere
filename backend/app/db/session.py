from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, future=True
)

# Единая декларативная база для raw- и core-моделей (добавляются на шагах 1–2).
Base = declarative_base()


def get_session():
    """FastAPI-зависимость: сессия на запрос, гарантированно закрывается."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
