"""RAW-слой: данные «как есть» из CSV.

Все прикладные колонки — TEXT, без FK/CHECK/NOT NULL: кривой формат даты/суммы
не должен ронять загрузку, и нужен оригинал для сверки. Ключ — суррогатный `id`
(натуральные ключи в выгрузке содержат дубли, напр. D1008). Типизация, проверки
связей и решения fix/quarantine/flag — на шаге transform (raw → core).
"""

from sqlalchemy import Column, Integer, Text

from app.db.session import Base


class RawUser(Base):
    __tablename__ = "raw_users"
    id = Column(Integer, primary_key=True)
    user_id = Column(Text)
    name = Column(Text)
    role = Column(Text)
    active = Column(Text)
    department = Column(Text)
    email = Column(Text)


class RawCompany(Base):
    __tablename__ = "raw_companies"
    id = Column(Integer, primary_key=True)
    company_id = Column(Text)
    name = Column(Text)
    inn = Column(Text)
    city = Column(Text)
    industry = Column(Text)
    created_at = Column(Text)


class RawContact(Base):
    __tablename__ = "raw_contacts"
    id = Column(Integer, primary_key=True)
    contact_id = Column(Text)
    company_id = Column(Text)
    name = Column(Text)
    phone = Column(Text)
    email = Column(Text)
    created_at = Column(Text)


class RawProduct(Base):
    __tablename__ = "raw_products"
    id = Column(Integer, primary_key=True)
    product_id = Column(Text)
    sku = Column(Text)
    name = Column(Text)
    category = Column(Text)
    cost_price = Column(Text)
    is_active = Column(Text)


class RawPipelineStage(Base):
    __tablename__ = "raw_pipeline_stages"
    id = Column(Integer, primary_key=True)
    pipeline_id = Column(Text)
    stage_id = Column(Text)
    stage_name = Column(Text)
    sort_order = Column(Text)
    is_final = Column(Text)
    is_success = Column(Text)


class RawDeal(Base):
    __tablename__ = "raw_deals"
    id = Column(Integer, primary_key=True)
    deal_id = Column(Text)
    title = Column(Text)
    created_at = Column(Text)
    updated_at = Column(Text)
    stage_id = Column(Text)
    manager_id = Column(Text)
    company_id = Column(Text)
    contact_id = Column(Text)
    source = Column(Text)
    expected_amount = Column(Text)
    currency = Column(Text)
    closed_at = Column(Text)
    lost_reason = Column(Text)
    custom_deadline = Column(Text)


class RawDealProduct(Base):
    __tablename__ = "raw_deal_products"
    id = Column(Integer, primary_key=True)
    deal_id = Column(Text)
    product_id = Column(Text)
    quantity = Column(Text)
    unit_price = Column(Text)
    discount = Column(Text)


class RawPayment(Base):
    __tablename__ = "raw_payments"
    id = Column(Integer, primary_key=True)
    payment_id = Column(Text)
    deal_id = Column(Text)
    payment_date = Column(Text)
    amount = Column(Text)
    payment_type = Column(Text)
    status = Column(Text)


class RawStageHistory(Base):
    __tablename__ = "raw_stage_history"
    id = Column(Integer, primary_key=True)
    event_id = Column(Text)
    deal_id = Column(Text)
    old_stage_id = Column(Text)
    new_stage_id = Column(Text)
    changed_at = Column(Text)
    changed_by_id = Column(Text)


class RawActivity(Base):
    __tablename__ = "raw_activities"
    id = Column(Integer, primary_key=True)
    activity_id = Column(Text)
    deal_id = Column(Text)
    activity_type = Column(Text)
    direction = Column(Text)
    subject = Column(Text)
    responsible_user_id = Column(Text)
    completed = Column(Text)
    deadline_at = Column(Text)
    completed_at = Column(Text)


class RawProductionOrder(Base):
    __tablename__ = "raw_production_orders"
    id = Column(Integer, primary_key=True)
    production_order_id = Column(Text)
    deal_id = Column(Text)
    created_at = Column(Text)
    planned_finish_at = Column(Text)
    actual_finish_at = Column(Text)
    status = Column(Text)
    workshop = Column(Text)


class RawShipment(Base):
    __tablename__ = "raw_shipments"
    id = Column(Integer, primary_key=True)
    shipment_id = Column(Text)
    deal_id = Column(Text)
    planned_date = Column(Text)
    actual_date = Column(Text)
    status = Column(Text)


class RawMarketingCost(Base):
    __tablename__ = "raw_marketing_costs"
    id = Column(Integer, primary_key=True)
    cost_date = Column(Text)
    source = Column(Text)
    campaign = Column(Text)
    cost_amount = Column(Text)
    currency = Column(Text)


# (модель, логическое имя = имя CSV-таблицы). Порядок для raw не важен (нет FK).
RAW_TABLES = [
    (RawUser, "users"),
    (RawCompany, "companies"),
    (RawContact, "contacts"),
    (RawProduct, "products"),
    (RawPipelineStage, "pipeline_stages"),
    (RawDeal, "deals"),
    (RawDealProduct, "deal_products"),
    (RawPayment, "payments"),
    (RawStageHistory, "stage_history"),
    (RawActivity, "activities"),
    (RawProductionOrder, "production_orders"),
    (RawShipment, "shipments"),
    (RawMarketingCost, "marketing_costs"),
]
