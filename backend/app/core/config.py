from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения. Читаются из .env в корне репозитория (или из env)."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),  # запуск из корня или из backend/
        extra="ignore",
    )

    database_url: str = (
        "postgresql+psycopg://termosphere:termosphere@localhost:5435/termosphere"
    )
    # Часовой пояс данных выгрузки — фиксируем как справочную константу (см. ASSUMPTIONS).
    data_tz: str = "+05:00"
    # CORS: в проде фронт ходит через nginx (тот же origin), в dev — через Vite-прокси.
    # По умолчанию разрешаем всё: контур read-only, только GET.
    cors_origins: list[str] = ["*"]


settings = Settings()
