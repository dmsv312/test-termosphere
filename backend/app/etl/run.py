"""Оркестратор загрузки: CSV → raw → core (нормализация, дедуп, лог качества)."""

from sqlalchemy import func

from app.db.session import SessionLocal
from app.etl.load_raw import load_all as load_raw
from app.etl.transform import run_transform
from app.models import core as c

# Таблицы для печати сводки после прохода.
_SUMMARY = [
    ("users", c.User),
    ("companies", c.Company),
    ("contacts", c.Contact),
    ("products", c.Product),
    ("pipeline_stages", c.PipelineStage),
    ("deals", c.Deal),
    ("deal_products", c.DealProduct),
    ("payments", c.Payment),
    ("stage_history", c.StageHistory),
    ("activities", c.Activity),
    ("production_orders", c.ProductionOrder),
    ("shipments", c.Shipment),
    ("marketing_costs", c.MarketingCost),
]


def main() -> None:
    print("Загрузка raw:")
    load_raw()

    print("Transform raw → core:")
    with SessionLocal() as session:
        issues = run_transform(session)
        for name, model in _SUMMARY:
            print(f"  core.{name}: {session.query(func.count()).select_from(model).scalar()}")
        by_action = dict(
            session.query(c.DataQualityIssue.action, func.count())
            .group_by(c.DataQualityIssue.action)
            .all()
        )
    total = sum(by_action.values())
    parts = ", ".join(f"{a}={by_action.get(a, 0)}" for a in ("fixed", "quarantined", "flagged"))
    print(f"  data_quality_issues: {total} ({parts})")


if __name__ == "__main__":
    main()
