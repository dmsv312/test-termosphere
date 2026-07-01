"""Семь управленческих отчётов (шаг 5). Read-only.

Каждый эндпоинт исполняет канонический SQL из `app/reports/queries.py` (тот же,
что выгружается в db/reports.sql) через `text()` и отдаёт JSON. Деньги — строкой
(точность), даты — ISO. Никакой бизнес-логики в Python: все формулы — в SQL,
чтобы отчёт в API и в db/reports.sql не расходились.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.serialize import mapping_to_dict
from app.db.session import get_session
from app.reports import queries as q

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _run(session: Session, sql: str, params: dict | None = None) -> list:
    """Исполнить отчётный SQL → список RowMapping (сырые значения, до сериализации)."""
    return session.execute(text(sql), params or {}).mappings().all()


def _sum(rows: list, key: str) -> str:
    """Сумма денежной колонки по строкам (Decimal, NULL пропускаем) → строкой."""
    total = Decimal(0)
    for row in rows:
        value = row[key]
        if value is not None:
            total += value
    return str(total)


def _cutoff(session: Session) -> str:
    """Дата среза («сегодня» выгрузки) = max по фактическим событиям (ISO-строкой)."""
    return _run(session, q.CUTOFF_SQL)[0]["cutoff_date"].isoformat()


@router.get("/funnel")
def funnel(session: Session = Depends(get_session)) -> dict:
    """Отчёт 1. Воронка: сделки и сумма (гибрид) по стадиям."""
    rows = _run(session, q.FUNNEL_SQL)
    return {
        "report": "funnel",
        "title": "Воронка продаж",
        "rows": [mapping_to_dict(r) for r in rows],
        "totals": {
            "deals": sum(r["deals"] for r in rows),
            "amount": _sum(rows, "amount"),
        },
    }


@router.get("/managers")
def managers(session: Session = Depends(get_session)) -> dict:
    """Отчёт 2. Продажи и маржа по менеджерам (по WON) + SHIPPED отдельной пометкой."""
    rows = _run(session, q.MANAGERS_SQL)
    shipped = _run(session, q.SHIPPED_NOT_CLOSED_SQL)
    return {
        "report": "managers",
        "title": "Продажи и маржа по менеджерам",
        "rows": [mapping_to_dict(r) for r in rows],
        "shipped_not_closed": [mapping_to_dict(r) for r in shipped],
    }


@router.get("/receivables")
def receivables(session: Session = Depends(get_session)) -> dict:
    """Отчёт 3. Дебиторка: сумма / оплачено / в ожидании / корректировка / остаток."""
    rows = _run(session, q.RECEIVABLES_SQL)
    return {
        "report": "receivables",
        "title": "Дебиторка",
        "rows": [mapping_to_dict(r) for r in rows],
        "totals": {
            key: _sum(rows, key)
            for key in ("amount", "paid", "pending", "correction", "balance")
        },
    }


@router.get("/production-delays")
def production_delays(session: Session = Depends(get_session)) -> dict:
    """Отчёт 4. Производственные заказы с задержкой > 5 дней."""
    rows = _run(session, q.PRODUCTION_DELAYS_SQL)
    return {
        "report": "production-delays",
        "title": "Задержка производства > 5 дней",
        "cutoff_date": _cutoff(session),
        "threshold_days": 5,
        "rows": [mapping_to_dict(r) for r in rows],
    }


@router.get("/stale-deals")
def stale_deals(
    n_days: int = Query(q.DEFAULT_STALE_DAYS, ge=0, le=3650),
    session: Session = Depends(get_session),
) -> dict:
    """Отчёт 5. Живые сделки без активности более N дней (по умолчанию N=14)."""
    rows = _run(session, q.STALE_DEALS_SQL, {"n_days": n_days})
    return {
        "report": "stale-deals",
        "title": "Сделки без активности N дней",
        "cutoff_date": _cutoff(session),
        "n_days": n_days,
        "rows": [mapping_to_dict(r) for r in rows],
    }


@router.get("/sources")
def sources(session: Session = Depends(get_session)) -> dict:
    """Отчёт 6. Источники: выручка/маржа по WON, затраты и ROMI (или «нет затрат»)."""
    rows = _run(session, q.SOURCES_SQL)
    out = []
    for row in rows:
        item = mapping_to_dict(row)
        costs, revenue, cost_rows = row["costs"], row["revenue"], row["cost_rows"]
        # ROMI считаем только при реальных затратах; иначе — «нет затрат» (не делим на 0).
        has_costs = cost_rows > 0 and costs is not None and costs > 0
        item["has_costs"] = has_costs
        item["romi"] = round(float((revenue - costs) / costs), 4) if has_costs else None
        out.append(item)
    return {"report": "sources", "title": "Источники заявок", "rows": out}
