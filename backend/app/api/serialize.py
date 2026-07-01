"""Сериализация core-строк в JSON-безопасные словари.

Деньги/количества (`Decimal`) отдаём строкой — не теряем точность и ведущие нули;
даты/время — ISO-8601. Имена ключей = имена колонок (в этой схеме совпадают с
атрибутами модели), порядок — как в определении таблицы.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any


def row_to_dict(obj: Any) -> dict:
    """ORM-строка → dict с JSON-безопасными значениями (Decimal→str, дата→ISO)."""
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if isinstance(val, Decimal):
            val = str(val)
        elif isinstance(val, (datetime, date)):
            val = val.isoformat()
        result[col.name] = val
    return result
