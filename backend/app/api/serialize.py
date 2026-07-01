"""Сериализация core-строк в JSON-безопасные словари.

Деньги/количества (`Decimal`) отдаём строкой — не теряем точность и ведущие нули;
даты/время — ISO-8601. Имена ключей = имена колонок (в этой схеме совпадают с
атрибутами модели), порядок — как в определении таблицы.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any


def _jsonify(val: Any) -> Any:
    """Одно значение → JSON-безопасное (Decimal→str, дата/время→ISO)."""
    if isinstance(val, Decimal):
        return str(val)
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    return val


def row_to_dict(obj: Any) -> dict:
    """ORM-строка → dict с JSON-безопасными значениями (Decimal→str, дата→ISO)."""
    return {col.name: _jsonify(getattr(obj, col.name)) for col in obj.__table__.columns}


def mapping_to_dict(mapping: Any) -> dict:
    """Строка сырого SQL-результата (RowMapping) → JSON-безопасный dict.

    Для отчётов (raw SQL через text()): деньги (Decimal) отдаём строкой — точность;
    даты — ISO; целые (count/разница дат) остаются числами.
    """
    return {key: _jsonify(value) for key, value in mapping.items()}
