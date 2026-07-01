"""CORE-слой: нормализованные данные с настоящими типами и ограничениями.

В отличие от raw (всё TEXT, без ограничений) здесь — целевая схема:
натуральные PK (после дедупа), FK между сущностями, CHECK на доменах статусов,
деньги/ИНН — Decimal/строка. Ограничения БД тут — страховка целостности;
активное решение fix/quarantine/flag принимает Python-transform (шаг 3) и пишет
в `data_quality_issues`. Строки, где остался бизнес-сигнал (отриц. сумма, WON без
даты, неактивный менеджер и т.п.), помечаются `has_quality_issue=true`.

Наши добавления сверх исходных 13 таблиц:
- `sources` — справочник нормализованных каналов (к нему приводим deals.source и
  marketing_costs.source, иначе «выручка по каналу» не сойдётся с «затратами»);
- `data_quality_issues` — лог всех найденных проблем (три реакции).
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)

from app.db.session import Base

# Часовой пояс данных — +05:00; храним как timestamptz.
TS = DateTime(timezone=True)
# Деньги/себестоимость/цены — Decimal, не float.
MONEY = Numeric(14, 2)


# --- Наши справочники / служебные таблицы ------------------------------------


class Source(Base):
    """Справочник нормализованных каналов (наш, сидируется миграцией)."""

    __tablename__ = "sources"
    id = Column(Integer, primary_key=True)
    code = Column(String, nullable=False, unique=True)  # avito, website, ...
    name = Column(String)  # человекочитаемое имя


class DataQualityIssue(Base):
    """Лог всех найденных проблем качества (поля — по BRIEF §4)."""

    __tablename__ = "data_quality_issues"
    __table_args__ = (
        CheckConstraint(
            "action in ('fixed','quarantined','flagged')",
            name="ck_dqi_action",
        ),
    )
    id = Column(Integer, primary_key=True)
    entity = Column(String, nullable=False)  # deal, deal_product, payment, ...
    entity_id = Column(String)  # натуральный ключ проблемной строки (может быть NULL)
    issue_type = Column(String, nullable=False)  # negative_amount, duplicate, orphan_deal, ...
    action = Column(String, nullable=False)  # fixed | quarantined | flagged
    details = Column(Text)  # пояснение + исходное значение (напр. "14.06.2026 → 2026-06-14")
    detected_at = Column(TS, server_default=func.now(), nullable=False)


# --- Справочники из выгрузки --------------------------------------------------


class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True)
    name = Column(Text)
    role = Column(Text)
    active = Column(Boolean)
    department = Column(Text)
    email = Column(Text)
    has_quality_issue = Column(Boolean, nullable=False, server_default="false")


class Company(Base):
    __tablename__ = "companies"
    company_id = Column(String, primary_key=True)
    name = Column(Text)
    inn = Column(String)  # строка: ведущие нули значимы
    city = Column(Text)
    industry = Column(Text)
    created_at = Column(TS)
    has_quality_issue = Column(Boolean, nullable=False, server_default="false")


class Contact(Base):
    __tablename__ = "contacts"
    contact_id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.company_id"))  # nullable: сирота → NULL+флаг
    name = Column(Text)
    phone = Column(String)  # нормализованный +7XXXXXXXXXX
    email = Column(Text)
    created_at = Column(TS)
    has_quality_issue = Column(Boolean, nullable=False, server_default="false")


class Product(Base):
    __tablename__ = "products"
    product_id = Column(String, primary_key=True)
    sku = Column(String)
    name = Column(Text)
    category = Column(Text)
    cost_price = Column(MONEY)
    is_active = Column(Boolean)
    # дубль по SKU: строку оставляем, но помечаем и связываем с каноническим товаром
    canonical_id = Column(String, ForeignKey("products.product_id"))
    has_quality_issue = Column(Boolean, nullable=False, server_default="false")


class PipelineStage(Base):
    """Справочник стадий воронки (грузится из CSV на шаге transform)."""

    __tablename__ = "pipeline_stages"
    stage_id = Column(String, primary_key=True)  # NEW, QUALIFICATION, ... WON, LOST
    pipeline_id = Column(String)
    stage_name = Column(Text)
    sort_order = Column(Integer)
    is_final = Column(Boolean)
    is_success = Column(Boolean)


# --- Сделки и их дети ---------------------------------------------------------


class Deal(Base):
    __tablename__ = "deals"
    deal_id = Column(String, primary_key=True)  # после дедупа (max updated_at)
    title = Column(Text)
    created_at = Column(TS)
    updated_at = Column(TS)
    closed_at = Column(TS)  # WON без даты → NULL + флаг (не выдумываем)
    custom_deadline = Column(Date)  # в данных — дата без времени
    stage_id = Column(String, ForeignKey("pipeline_stages.stage_id"))  # WAIT_CLIENT → NULL+флаг
    manager_id = Column(String, ForeignKey("users.user_id"))  # nullable: без менеджера/сирота
    company_id = Column(String, ForeignKey("companies.company_id"))  # nullable
    contact_id = Column(String, ForeignKey("contacts.contact_id"))  # nullable
    source_id = Column(Integer, ForeignKey("sources.id"))  # нормализованный канал
    expected_amount = Column(MONEY)  # оценка из карточки; гибрид-сумма считается в отчётах
    currency = Column(String, nullable=False, server_default="RUB")  # пусто → RUB + флаг
    lost_reason = Column(Text)
    has_quality_issue = Column(Boolean, nullable=False, server_default="false")


class DealProduct(Base):
    __tablename__ = "deal_products"
    id = Column(Integer, primary_key=True)  # суррогат: натурального ключа нет
    deal_id = Column(String, ForeignKey("deals.deal_id"), nullable=False)  # сирота → карантин
    product_id = Column(String, ForeignKey("products.product_id"), nullable=False)  # PR999 → карантин
    quantity = Column(Numeric(14, 2))
    unit_price = Column(MONEY)
    discount = Column(MONEY, nullable=False, server_default="0")  # абсолютные рубли
    has_quality_issue = Column(Boolean, nullable=False, server_default="false")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "payment_type in ('prepayment','full','correction','unknown')",
            name="ck_payment_type",
        ),
        CheckConstraint("status in ('paid','pending')", name="ck_payment_status"),
    )
    payment_id = Column(String, primary_key=True)
    deal_id = Column(String, ForeignKey("deals.deal_id"), nullable=False)  # PAY005/D9999 → карантин
    payment_date = Column(Date)  # в данных — дата без времени
    amount = Column(MONEY)  # correction может быть отрицательным (легально)
    payment_type = Column(String)  # prepayment | full | correction | unknown(флаг)
    status = Column(String)  # paid | pending
    has_quality_issue = Column(Boolean, nullable=False, server_default="false")


class StageHistory(Base):
    __tablename__ = "stage_history"
    event_id = Column(String, primary_key=True)
    deal_id = Column(String, ForeignKey("deals.deal_id"), nullable=False)  # EVT005/D1012 → карантин
    old_stage_id = Column(String, ForeignKey("pipeline_stages.stage_id"))
    new_stage_id = Column(String, ForeignKey("pipeline_stages.stage_id"))
    changed_at = Column(TS)
    changed_by_id = Column(String, ForeignKey("users.user_id"))
    has_quality_issue = Column(Boolean, nullable=False, server_default="false")  # illegal_transition


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        CheckConstraint(
            "activity_type in ('call','email','task')", name="ck_activity_type"
        ),
    )
    activity_id = Column(String, primary_key=True)
    deal_id = Column(String, ForeignKey("deals.deal_id"), nullable=False)  # A903/D9999 → карантин
    activity_type = Column(String)  # call | email | task
    direction = Column(String)  # inbound | outbound | NULL
    subject = Column(Text)
    responsible_user_id = Column(String, ForeignKey("users.user_id"))
    completed = Column(Boolean)
    deadline_at = Column(TS)
    completed_at = Column(TS)
    has_quality_issue = Column(Boolean, nullable=False, server_default="false")


class ProductionOrder(Base):
    __tablename__ = "production_orders"
    __table_args__ = (
        CheckConstraint(
            "status in ('planned','in_progress','done')", name="ck_production_status"
        ),
    )
    production_order_id = Column(String, primary_key=True)
    deal_id = Column(String, ForeignKey("deals.deal_id"), nullable=False)  # PO004/D9999 → карантин
    created_at = Column(TS)  # PO003 создан раньше сделки → флаг temporal_inconsistency
    planned_finish_at = Column(Date)  # в данных — дата без времени
    actual_finish_at = Column(Date)
    status = Column(String)  # planned | in_progress | done
    workshop = Column(Text)
    has_quality_issue = Column(Boolean, nullable=False, server_default="false")


class Shipment(Base):
    __tablename__ = "shipments"
    __table_args__ = (
        CheckConstraint("status in ('planned','shipped')", name="ck_shipment_status"),
    )
    shipment_id = Column(String, primary_key=True)
    deal_id = Column(String, ForeignKey("deals.deal_id"), nullable=False)
    planned_date = Column(Date)
    actual_date = Column(Date)
    status = Column(String)  # planned | shipped
    has_quality_issue = Column(Boolean, nullable=False, server_default="false")


class MarketingCost(Base):
    __tablename__ = "marketing_costs"
    id = Column(Integer, primary_key=True)  # суррогат: натурального ключа нет
    cost_date = Column(Date)
    source_id = Column(Integer, ForeignKey("sources.id"))  # нормализованный канал
    campaign = Column(Text)
    cost_amount = Column(MONEY)
    currency = Column(String, nullable=False, server_default="RUB")
    has_quality_issue = Column(Boolean, nullable=False, server_default="false")


# Канонический набор каналов (нижний регистр) — сид справочника `sources`.
# Проверено по данным: deals.source/marketing_costs.source после нормализации.
SOURCE_SEED = [
    {"code": "avito", "name": "Avito"},
    {"code": "website", "name": "Сайт"},
    {"code": "yandex_direct", "name": "Яндекс.Директ"},
    {"code": "phone", "name": "Телефон"},
    {"code": "referral", "name": "Рекомендации"},
    {"code": "telegram", "name": "Telegram"},
]
