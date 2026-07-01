"""Отчёт №7 «Проблемы данных» — поверх лога `data_quality_issues`.

Первый отчёт контура: он валидирует весь пайплайн raw→core (что нашли и как
отреагировали: fixed / quarantined / flagged). Read-only.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.serialize import row_to_dict
from app.db.session import get_session
from app.models import core as c

router = APIRouter(prefix="/api/data-quality", tags=["data-quality"])

# Три реакции — фиксированный порядок для стабильного вывода.
_ACTIONS = ("fixed", "quarantined", "flagged")


@router.get("/summary")
def summary(session: Session = Depends(get_session)) -> dict:
    """Агрегат: всего проблем, разбивка по реакции и по типу × реакции."""
    by_type_rows = (
        session.query(
            c.DataQualityIssue.issue_type,
            c.DataQualityIssue.action,
            func.count(),
        )
        .group_by(c.DataQualityIssue.issue_type, c.DataQualityIssue.action)
        .order_by(c.DataQualityIssue.issue_type, c.DataQualityIssue.action)
        .all()
    )
    by_type = [
        {"issue_type": t, "action": a, "count": n} for t, a, n in by_type_rows
    ]
    counts = dict(
        session.query(c.DataQualityIssue.action, func.count())
        .group_by(c.DataQualityIssue.action)
        .all()
    )
    by_action = {a: counts.get(a, 0) for a in _ACTIONS}
    return {
        "total": sum(by_action.values()),
        "by_action": by_action,
        "by_type": by_type,
    }


@router.get("/issues")
def issues(session: Session = Depends(get_session)) -> list[dict]:
    """Полный список проблем (все строки лога) — для детальной таблицы."""
    rows = (
        session.query(c.DataQualityIssue)
        .order_by(
            c.DataQualityIssue.entity,
            c.DataQualityIssue.entity_id,
            c.DataQualityIssue.id,
        )
        .all()
    )
    return [row_to_dict(r) for r in rows]
