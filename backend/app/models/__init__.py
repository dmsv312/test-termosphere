# Импортируем модели, чтобы Alembic видел их в Base.metadata для autogenerate.
from app.models import raw  # noqa: F401
from app.models import core  # noqa: F401
