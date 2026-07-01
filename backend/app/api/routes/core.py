"""Витрина core-слоя: просмотр нормализованных таблиц для верификации данных.

Read-only. Чтение — чистый SQLAlchemy к core, без бизнес-формул (формулы отчётов
придут на шаге 5). Доступ к таблицам — по белому списку (`TABLES`): пользователь
не может запросить произвольное имя.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.serialize import row_to_dict
from app.db.session import get_session
from app.models import core as c

router = APIRouter(prefix="/api/core", tags=["core"])

# Белый список core-таблиц: канонический порядок + человекочитаемые ярлыки.
TABLES = [
    ("sources", c.Source, "Источники (каналы)"),
    ("users", c.User, "Сотрудники"),
    ("companies", c.Company, "Компании"),
    ("contacts", c.Contact, "Контакты"),
    ("products", c.Product, "Товары"),
    ("pipeline_stages", c.PipelineStage, "Стадии воронки"),
    ("deals", c.Deal, "Сделки"),
    ("deal_products", c.DealProduct, "Позиции сделок"),
    ("payments", c.Payment, "Оплаты"),
    ("stage_history", c.StageHistory, "История стадий"),
    ("activities", c.Activity, "Активности"),
    ("production_orders", c.ProductionOrder, "Производственные заказы"),
    ("shipments", c.Shipment, "Отгрузки"),
    ("marketing_costs", c.MarketingCost, "Маркетинговые затраты"),
    ("data_quality_issues", c.DataQualityIssue, "Проблемы качества"),
]
_BY_NAME = {name: (model, label) for name, model, label in TABLES}


@router.get("/tables")
def list_tables(session: Session = Depends(get_session)) -> list[dict]:
    """Список core-таблиц с числом строк — для навигации по витрине."""
    out = []
    for name, model, label in TABLES:
        count = session.query(func.count()).select_from(model).scalar()
        out.append({"name": name, "label": label, "count": count})
    return out


@router.get("/{table}")
def get_table(
    table: str,
    limit: int = Query(500, ge=1, le=5000),
    session: Session = Depends(get_session),
) -> dict:
    """Строки одной core-таблицы (по белому списку), отсортированные по PK.

    Данных мало (десятки строк) — отдаём как есть; `limit` — страховка.
    """
    entry = _BY_NAME.get(table)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Неизвестная core-таблица: {table}")
    model, label = entry
    pk_cols = list(model.__table__.primary_key.columns)
    rows = session.query(model).order_by(*pk_cols).limit(limit).all()
    return {
        "table": table,
        "label": label,
        "columns": [col.name for col in model.__table__.columns],
        "rows": [row_to_dict(r) for r in rows],
    }
