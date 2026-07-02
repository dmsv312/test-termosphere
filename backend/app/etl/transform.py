"""Transform: raw → core. Обобщённая нормализация (не завязана на конкретные ID).

Каждое решение по «грязной» строке — одна из трёх реакций (см. AGENTS.md):
  fixed      — есть однозначно верное значение, нормализуем;
  quarantined— строка бессмысленна (битая связь, дубль) — в core НЕ вставляем;
  flagged    — это бизнес-сигнал, оставляем строку и помечаем has_quality_issue.
Каждая реакция логируется строкой в data_quality_issues.

Логика общая: дубли ловим группировкой по ключу; сироты — проверкой существования
ссылки в уже загруженных справочниках; нелегальные переходы — по карте FSM; домены
статусов/каналов — по справочникам. Никаких `if id == 'D9999'`: конкретные строки
этой выгрузки всплывают только при сверке, но не в правилах.

Порядок (важно из-за FK и построения множеств валидных ключей):
  справочники (users, companies, contacts, products, pipeline_stages)
    → deals (дедуп)
      → дети сделок (deal_products, payments, stage_history, activities,
        production_orders, shipments)
    → marketing_costs
Идемпотентно: перед проходом TRUNCATE core (кроме сида sources).
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import text

from app.db.session import SessionLocal
from app.etl import clean
from app.models import core as c
from app.models import raw as r

# Легальные переходы стадий (FSM — см. docs/architecture.md). Правило: внутри воронки движемся на
# следующую стадию (форвардные прыжки через стадии — нарушение), а терминальные
# исходы WON/LOST достижимы из ЛЮБОЙ активной стадии (сделку можно закрыть/проиграть
# в любой момент). Пустое множество — терминальная стадия; old_stage=None
# (инициализация) переходом не считаем.
_TERMINAL = {"WON", "LOST"}
ALLOWED_TRANSITIONS = {
    "NEW": {"QUALIFICATION"} | _TERMINAL,
    "QUALIFICATION": {"CALCULATION"} | _TERMINAL,
    "CALCULATION": {"PROPOSAL"} | _TERMINAL,
    "PROPOSAL": {"CONTRACT"} | _TERMINAL,
    "CONTRACT": {"PRODUCTION"} | _TERMINAL,
    "PRODUCTION": {"SHIPPED"} | _TERMINAL,
    "SHIPPED": set() | _TERMINAL,
    "WON": set(),
    "LOST": set(),
}

# Домены статусов/типов — зеркалят CHECK-и в core-моделях. Значение вне домена НЕ
# пускаем в CHECK-колонку (иначе весь проход упадёт на commit): зануляем (NULL
# проходит CHECK) и логируем. Пустое поле — легально (колонки nullable).
PAYMENT_TYPES = {"prepayment", "full", "correction", "unknown"}
PAYMENT_STATUSES = {"paid", "pending"}
ACTIVITY_TYPES = {"call", "email", "task"}
PRODUCTION_STATUSES = {"planned", "in_progress", "done"}
SHIPMENT_STATUSES = {"planned", "shipped"}

# Порог для тай-брейка дедупа, когда updated_at не распарсился ни у одной строки.
_MIN_DT = datetime.min

# core-таблицы для идемпотентного пересбора. sources НЕ трогаем — это наш сид.
# Порядок не важен: RESTART IDENTITY CASCADE снимет зависимости FK.
_CORE_RESET_TABLES = (
    "data_quality_issues",
    "deal_products",
    "payments",
    "activities",
    "stage_history",
    "production_orders",
    "shipments",
    "marketing_costs",
    "deals",
    "contacts",
    "companies",
    "products",
    "users",
    "pipeline_stages",
)


def _in_domain(raw_value, allowed) -> tuple[str | None, bool]:
    """(значение | None, is_invalid). Пусто → (None, False); вне домена → (None, True).

    NULL проходит CHECK-ограничение, поэтому невалидное значение безопасно зануляем
    (не роняем проход), а факт логируем отдельно.
    """
    value = (raw_value or "").strip() or None
    if value is None or value in allowed:
        return value, False
    return None, True


def _issue(bucket, entity, entity_id, issue_type, action, details=None):
    bucket.append(
        c.DataQualityIssue(
            entity=entity,
            entity_id=entity_id,
            issue_type=issue_type,
            action=action,
            details=details,
        )
    )


def _reset_core(session) -> None:
    session.execute(
        text("TRUNCATE " + ", ".join(_CORE_RESET_TABLES) + " RESTART IDENTITY CASCADE")
    )


# --- Справочники --------------------------------------------------------------


def _load_users(session) -> dict[str, bool | None]:
    """→ {user_id: active}. Активность нужна для флага «неактивный менеджер»."""
    active: dict[str, bool | None] = {}
    for u in session.query(r.RawUser).all():
        is_active = clean.parse_bool(u.active)
        session.add(
            c.User(
                user_id=u.user_id,
                name=u.name,
                role=u.role,
                active=is_active,
                department=u.department,
                email=u.email,
            )
        )
        active[u.user_id] = is_active
    return active


def _load_companies(session, issues) -> set[str]:
    ids: set[str] = set()
    for co in session.query(r.RawCompany).all():
        flagged = False
        # Компания без опорных полей (ни названия, ни ИНН, ни отрасли) — сигнал.
        if clean.is_blank(co.name) and clean.is_blank(co.inn) and clean.is_blank(co.industry):
            _issue(issues, "company", co.company_id, "incomplete_company", "flagged",
                   "нет name/inn/industry")
            flagged = True
        created_at, _ = clean.parse_dt(co.created_at)
        session.add(
            c.Company(
                company_id=co.company_id,
                name=co.name,
                inn=clean.norm_inn(co.inn),
                city=co.city,
                industry=co.industry,
                created_at=created_at,
                has_quality_issue=flagged,
            )
        )
        ids.add(co.company_id)
    return ids


def _load_contacts(session, issues, company_ids) -> set[str]:
    ids: set[str] = set()
    for ct in session.query(r.RawContact).all():
        flagged = False
        company_id = ct.company_id if ct.company_id in company_ids else None
        if not clean.is_blank(ct.company_id) and company_id is None:
            _issue(issues, "contact", ct.contact_id, "orphan_company", "flagged",
                   f"company_id={ct.company_id} отсутствует → NULL")
            flagged = True
        phone, phone_status = clean.norm_phone(ct.phone)
        if phone_status == "fixed":
            _issue(issues, "contact", ct.contact_id, "normalized_phone", "fixed",
                   f"{ct.phone} → {phone}")
            flagged = True
        elif phone_status == "unrecognized":
            _issue(issues, "contact", ct.contact_id, "unnormalized_phone", "flagged",
                   f"не РФ-формат, оставлен как есть: {ct.phone}")
            flagged = True
        if clean.is_blank(ct.email):
            _issue(issues, "contact", ct.contact_id, "missing_email", "flagged")
            flagged = True
        created_at, _ = clean.parse_dt(ct.created_at)
        session.add(
            c.Contact(
                contact_id=ct.contact_id,
                company_id=company_id,
                name=ct.name,
                phone=phone,
                email=ct.email,
                created_at=created_at,
                has_quality_issue=flagged,
            )
        )
        ids.add(ct.contact_id)
    return ids


def _load_products(session, issues) -> set[str]:
    """Дедуп по SKU: канонический = минимальный product_id в группе; дубли —
    оставляем, но помечаем и связываем через canonical_id."""
    # Сортировка по product_id: канонический (min product_id в группе) вставится
    # раньше своих дублей — самоссылочный FK canonical_id не упрётся в порядок строк.
    raws = session.query(r.RawProduct).order_by(r.RawProduct.product_id).all()
    by_sku: dict[str, list[str]] = {}
    for p in raws:
        if p.sku is not None:
            by_sku.setdefault(p.sku, []).append(p.product_id)
    canonical = {sku: min(pids) for sku, pids in by_sku.items()}

    ids: set[str] = set()
    for p in raws:
        flagged = False
        canonical_id = None
        if p.sku is not None and len(by_sku.get(p.sku, [])) > 1:
            canon = canonical[p.sku]
            if p.product_id != canon:
                canonical_id = canon
                _issue(issues, "product", p.product_id, "duplicate_sku", "flagged",
                       f"SKU {p.sku} дублирует {canon}")
                flagged = True
        session.add(
            c.Product(
                product_id=p.product_id,
                sku=p.sku,
                name=p.name,
                category=p.category,
                cost_price=clean.parse_amount(p.cost_price),
                is_active=clean.parse_bool(p.is_active),
                canonical_id=canonical_id,
                has_quality_issue=flagged,
            )
        )
        ids.add(p.product_id)
    return ids


def _load_stages(session) -> set[str]:
    ids: set[str] = set()
    for s in session.query(r.RawPipelineStage).all():
        session.add(
            c.PipelineStage(
                stage_id=s.stage_id,
                pipeline_id=s.pipeline_id,
                stage_name=s.stage_name,
                sort_order=clean.parse_int(s.sort_order),
                is_final=clean.parse_bool(s.is_final),
                is_success=clean.parse_bool(s.is_success),
            )
        )
        ids.add(s.stage_id)
    return ids


# --- Сделки -------------------------------------------------------------------


def _dedup_deals(session, issues) -> dict[str, r.RawDeal]:
    """Группируем по deal_id, оставляем строку с max(updated_at); при равных/None —
    детерминированный тай-брейк по raw.id. Вытеснённые — в лог как quarantined."""
    groups: dict[str, list[tuple[r.RawDeal, object]]] = {}
    for d in session.query(r.RawDeal).all():
        dt, _ = clean.parse_dt(d.updated_at)
        groups.setdefault(d.deal_id, []).append((d, dt))

    kept: dict[str, r.RawDeal] = {}
    for deal_id, rows in groups.items():
        # Ключ: сперва наличие даты, затем сама дата, затем raw.id (детерминизм).
        winner = max(rows, key=lambda rd: (rd[1] is not None, rd[1] or _MIN_DT, rd[0].id))[0]
        for raw_row, _dt in rows:
            if raw_row is winner:
                continue
            _issue(issues, "deal", deal_id, "duplicate_deal", "quarantined",
                   f"вытеснена строка raw.id={raw_row.id} (updated_at={raw_row.updated_at}); "
                   f"оставлена id={winner.id}")
        kept[deal_id] = winner
    return kept


def _load_deals(session, issues, user_active, company_ids, contact_ids, stage_ids,
                source_map) -> tuple[set[str], dict[str, object]]:
    user_ids = set(user_active)
    kept = _dedup_deals(session, issues)
    deal_created: dict[str, object] = {}

    for deal_id, d in kept.items():
        flagged = False

        # Канал → sources (нормализация регистра/алфавита; неизвестный — флаг).
        source_code, unknown = clean.norm_source(d.source)
        source_id = source_map.get(source_code) if source_code else None
        if unknown:
            # неизвестный канал: source_id=NULL, ничего не «починили» — только флаг
            _issue(issues, "deal", deal_id, "unknown_source", "flagged", d.source)
            flagged = True
        elif source_code and source_code != (d.source or "").strip():
            _issue(issues, "deal", deal_id, "normalized_source", "fixed",
                   f"{d.source} → {source_code}")  # косметика: строку не флагуем

        # Стадия вне справочника → NULL + флаг.
        stage_id = d.stage_id if d.stage_id in stage_ids else None
        if not clean.is_blank(d.stage_id) and stage_id is None:
            _issue(issues, "deal", deal_id, "orphan_stage", "flagged", d.stage_id)
            flagged = True

        # Менеджер: нет / битая ссылка / неактивный.
        manager_id = d.manager_id if d.manager_id in user_ids else None
        if clean.is_blank(d.manager_id):
            _issue(issues, "deal", deal_id, "missing_manager", "flagged")
            flagged = True
        elif manager_id is None:
            _issue(issues, "deal", deal_id, "orphan_manager", "flagged", d.manager_id)
            flagged = True
        elif user_active.get(manager_id) is False:
            _issue(issues, "deal", deal_id, "inactive_manager", "flagged", manager_id)
            flagged = True

        # Компания: нет / битая ссылка.
        company_id = d.company_id if d.company_id in company_ids else None
        if clean.is_blank(d.company_id):
            _issue(issues, "deal", deal_id, "missing_company", "flagged")
            flagged = True
        elif company_id is None:
            _issue(issues, "deal", deal_id, "orphan_company", "flagged", d.company_id)
            flagged = True

        # Контакт: битая ссылка (пустой контакт — норма).
        contact_id = d.contact_id if d.contact_id in contact_ids else None
        if not clean.is_blank(d.contact_id) and contact_id is None:
            _issue(issues, "deal", deal_id, "orphan_contact", "flagged", d.contact_id)
            flagged = True

        # Сумма из карточки: отрицательная — бизнес-сигнал.
        amount = clean.parse_amount(d.expected_amount)
        if amount is not None and amount < 0:
            _issue(issues, "deal", deal_id, "negative_amount", "flagged", str(amount))
            flagged = True

        # Валюта: пусто → RUB.
        currency = (d.currency or "").strip() or "RUB"
        if clean.is_blank(d.currency):
            _issue(issues, "deal", deal_id, "missing_currency", "fixed", "→ RUB")
            flagged = True

        # Даты.
        created_at, created_nonstd = clean.parse_dt(d.created_at)
        if created_nonstd:
            _issue(issues, "deal", deal_id, "nonstandard_date", "fixed",
                   f"created_at={d.created_at}")
            flagged = True
        updated_at, _ = clean.parse_dt(d.updated_at)
        closed_at, _ = clean.parse_dt(d.closed_at)
        custom_deadline, _ = clean.parse_date(d.custom_deadline)  # дата без времени

        # WON без даты закрытия — флаг (дату не выдумываем).
        if stage_id == "WON" and clean.is_blank(d.closed_at):
            _issue(issues, "deal", deal_id, "won_without_close_date", "flagged")
            flagged = True

        session.add(
            c.Deal(
                deal_id=deal_id,
                title=d.title,
                created_at=created_at,
                updated_at=updated_at,
                closed_at=closed_at,
                custom_deadline=custom_deadline,
                stage_id=stage_id,
                manager_id=manager_id,
                company_id=company_id,
                contact_id=contact_id,
                source_id=source_id,
                expected_amount=amount,
                currency=currency,
                lost_reason=d.lost_reason,
                has_quality_issue=flagged,
            )
        )
        deal_created[deal_id] = created_at
    return set(kept), deal_created


# --- Дети сделок --------------------------------------------------------------


def _load_deal_products(session, issues, deal_ids, product_ids) -> None:
    for dp in session.query(r.RawDealProduct).all():
        if dp.deal_id not in deal_ids:
            _issue(issues, "deal_product", dp.deal_id, "orphan_deal", "quarantined",
                   f"позиция ссылается на отсутствующую сделку {dp.deal_id}")
            continue
        if dp.product_id not in product_ids:
            _issue(issues, "deal_product", dp.deal_id, "orphan_product", "quarantined",
                   f"позиция ссылается на отсутствующий товар {dp.product_id}")
            continue
        flagged = False
        qty = clean.parse_amount(dp.quantity)
        price = clean.parse_amount(dp.unit_price)
        discount = clean.parse_amount(dp.discount) or Decimal(0)
        # Защита допущения «скидка в рублях»: скидка больше суммы позиции — аномалия.
        if qty is not None and price is not None and discount > qty * price:
            _issue(issues, "deal_product", dp.deal_id, "discount_exceeds_line", "flagged",
                   f"discount={discount} > {qty}·{price}")
            flagged = True
        session.add(
            c.DealProduct(
                deal_id=dp.deal_id,
                product_id=dp.product_id,
                quantity=qty,
                unit_price=price,
                discount=discount,
                has_quality_issue=flagged,
            )
        )


def _load_payments(session, issues, deal_ids) -> None:
    for p in session.query(r.RawPayment).all():
        if p.deal_id not in deal_ids:
            _issue(issues, "payment", p.payment_id, "orphan_deal", "quarantined",
                   f"оплата на отсутствующую сделку {p.deal_id}")
            continue
        flagged = False
        ptype, ptype_bad = _in_domain(p.payment_type, PAYMENT_TYPES)
        status, status_bad = _in_domain(p.status, PAYMENT_STATUSES)
        if ptype_bad:
            _issue(issues, "payment", p.payment_id, "invalid_payment_type", "flagged",
                   f"{p.payment_type} → NULL")
            flagged = True
        if status_bad:
            _issue(issues, "payment", p.payment_id, "invalid_payment_status", "flagged",
                   f"{p.status} → NULL")
            flagged = True
        if ptype == "unknown":
            _issue(issues, "payment", p.payment_id, "unknown_payment_type", "flagged", ptype)
            flagged = True
        payment_date, nonstd = clean.parse_date(p.payment_date)  # дата без времени
        if nonstd:
            _issue(issues, "payment", p.payment_id, "nonstandard_date", "fixed",
                   f"payment_date={p.payment_date}")
            flagged = True
        session.add(
            c.Payment(
                payment_id=p.payment_id,
                deal_id=p.deal_id,
                payment_date=payment_date,
                amount=clean.parse_amount(p.amount),
                payment_type=ptype,
                status=status,
                has_quality_issue=flagged,
            )
        )


def _load_stage_history(session, issues, deal_ids, stage_ids, user_ids) -> None:
    seen: set[tuple] = set()
    for e in session.query(r.RawStageHistory).all():
        if e.deal_id not in deal_ids:
            _issue(issues, "stage_history", e.event_id, "orphan_deal", "quarantined",
                   f"событие на отсутствующую сделку {e.deal_id}")
            continue
        signature = (e.event_id, e.deal_id, e.old_stage_id, e.new_stage_id,
                     e.changed_at, e.changed_by_id)
        if signature in seen:
            _issue(issues, "stage_history", e.event_id, "duplicate_event", "quarantined",
                   "идентичная строка события")
            continue
        seen.add(signature)
        flagged = False
        old_stage = e.old_stage_id if e.old_stage_id in stage_ids else None
        new_stage = e.new_stage_id if e.new_stage_id in stage_ids else None
        # Нелегальный переход по FSM (инициализацию old=None не проверяем).
        if old_stage is not None and new_stage is not None \
                and new_stage not in ALLOWED_TRANSITIONS.get(old_stage, set()):
            _issue(issues, "stage_history", e.event_id, "illegal_transition", "flagged",
                   f"{old_stage} → {new_stage}")
            flagged = True
        changed_by_id = e.changed_by_id if e.changed_by_id in user_ids else None
        if not clean.is_blank(e.changed_by_id) and changed_by_id is None:
            _issue(issues, "stage_history", e.event_id, "orphan_user", "flagged",
                   f"changed_by_id={e.changed_by_id} отсутствует → NULL")
            flagged = True
        changed_at, _ = clean.parse_dt(e.changed_at)
        session.add(
            c.StageHistory(
                event_id=e.event_id,
                deal_id=e.deal_id,
                old_stage_id=old_stage,
                new_stage_id=new_stage,
                changed_at=changed_at,
                changed_by_id=changed_by_id,
                has_quality_issue=flagged,
            )
        )


def _load_activities(session, issues, deal_ids, user_ids) -> None:
    for a in session.query(r.RawActivity).all():
        if a.deal_id not in deal_ids:
            _issue(issues, "activity", a.activity_id, "orphan_deal", "quarantined",
                   f"активность на отсутствующую сделку {a.deal_id}")
            continue
        flagged = False
        activity_type, type_bad = _in_domain(a.activity_type, ACTIVITY_TYPES)
        if type_bad:
            _issue(issues, "activity", a.activity_id, "invalid_activity_type", "flagged",
                   f"{a.activity_type} → NULL")
            flagged = True
        responsible_user_id = a.responsible_user_id if a.responsible_user_id in user_ids else None
        if not clean.is_blank(a.responsible_user_id) and responsible_user_id is None:
            _issue(issues, "activity", a.activity_id, "orphan_user", "flagged",
                   f"responsible_user_id={a.responsible_user_id} отсутствует → NULL")
            flagged = True
        deadline_at, _ = clean.parse_dt(a.deadline_at)
        completed_at, _ = clean.parse_dt(a.completed_at)
        session.add(
            c.Activity(
                activity_id=a.activity_id,
                deal_id=a.deal_id,
                activity_type=activity_type,
                direction=(a.direction or "").strip() or None,
                subject=a.subject,
                responsible_user_id=responsible_user_id,
                completed=clean.parse_bool(a.completed),
                deadline_at=deadline_at,
                completed_at=completed_at,
                has_quality_issue=flagged,
            )
        )


def _load_production_orders(session, issues, deal_ids, deal_created) -> None:
    for po in session.query(r.RawProductionOrder).all():
        if po.deal_id not in deal_ids:
            _issue(issues, "production_order", po.production_order_id, "orphan_deal",
                   "quarantined", f"заказ на отсутствующую сделку {po.deal_id}")
            continue
        flagged = False
        status, status_bad = _in_domain(po.status, PRODUCTION_STATUSES)
        if status_bad:
            _issue(issues, "production_order", po.production_order_id,
                   "invalid_production_status", "flagged", f"{po.status} → NULL")
            flagged = True
        created_at, _ = clean.parse_dt(po.created_at)
        deal_dt = deal_created.get(po.deal_id)
        # Заказ создан раньше своей сделки — нарушение хронологии.
        if created_at and deal_dt and created_at < deal_dt:
            _issue(issues, "production_order", po.production_order_id,
                   "temporal_inconsistency", "flagged",
                   f"заказ {created_at.date()} раньше сделки {deal_dt.date()}")
            flagged = True
        session.add(
            c.ProductionOrder(
                production_order_id=po.production_order_id,
                deal_id=po.deal_id,
                created_at=created_at,
                planned_finish_at=clean.parse_date(po.planned_finish_at)[0],  # даты без времени
                actual_finish_at=clean.parse_date(po.actual_finish_at)[0],
                status=status,
                workshop=po.workshop,
                has_quality_issue=flagged,
            )
        )


def _load_shipments(session, issues, deal_ids) -> None:
    for s in session.query(r.RawShipment).all():
        if s.deal_id not in deal_ids:
            _issue(issues, "shipment", s.shipment_id, "orphan_deal", "quarantined",
                   f"отгрузка на отсутствующую сделку {s.deal_id}")
            continue
        status, status_bad = _in_domain(s.status, SHIPMENT_STATUSES)
        flagged = False
        if status_bad:
            _issue(issues, "shipment", s.shipment_id, "invalid_shipment_status", "flagged",
                   f"{s.status} → NULL")
            flagged = True
        session.add(
            c.Shipment(
                shipment_id=s.shipment_id,
                deal_id=s.deal_id,
                planned_date=clean.parse_date(s.planned_date)[0],
                actual_date=clean.parse_date(s.actual_date)[0],
                status=status,
                has_quality_issue=flagged,
            )
        )


def _load_marketing_costs(session, issues, source_map) -> None:
    for m in session.query(r.RawMarketingCost).all():
        source_code, unknown = clean.norm_source(m.source)
        source_id = source_map.get(source_code) if source_code else None
        if unknown:
            _issue(issues, "marketing_cost", None, "unknown_source", "flagged", m.source)
        elif source_code and source_code != (m.source or "").strip():
            _issue(issues, "marketing_cost", None, "normalized_source", "fixed",
                   f"{m.source} → {source_code}")
        session.add(
            c.MarketingCost(
                cost_date=clean.parse_date(m.cost_date)[0],
                source_id=source_id,
                campaign=m.campaign,
                cost_amount=clean.parse_amount(m.cost_amount),
                currency=(m.currency or "").strip() or "RUB",
            )
        )


# --- Оркестратор --------------------------------------------------------------


def run_transform(session) -> list:
    """Полный проход raw → core. Возвращает список записей качества."""
    issues: list = []
    _reset_core(session)

    # Модели без relationship() → порядок вставки между таблицами SQLAlchemy сам не
    # гарантирует. Грузим в FK-безопасном порядке и flush'им после каждого уровня,
    # чтобы к моменту вставки детей их родители уже были в БД.
    user_active = _load_users(session)
    session.flush()
    company_ids = _load_companies(session, issues)
    session.flush()
    contact_ids = _load_contacts(session, issues, company_ids)
    session.flush()
    product_ids = _load_products(session, issues)
    session.flush()
    stage_ids = _load_stages(session)
    session.flush()
    source_map = {s.code: s.id for s in session.query(c.Source).all()}

    deal_ids, deal_created = _load_deals(
        session, issues, user_active, company_ids, contact_ids, stage_ids, source_map
    )
    session.flush()
    _load_deal_products(session, issues, deal_ids, product_ids)
    _load_payments(session, issues, deal_ids)
    _load_stage_history(session, issues, deal_ids, stage_ids, set(user_active))
    _load_activities(session, issues, deal_ids, set(user_active))
    _load_production_orders(session, issues, deal_ids, deal_created)
    _load_shipments(session, issues, deal_ids)
    _load_marketing_costs(session, issues, source_map)

    session.add_all(issues)
    session.commit()
    return issues


def main() -> None:
    with SessionLocal() as session:
        issues = run_transform(session)
    print(f"Transform завершён. Записей в data_quality_issues: {len(issues)}")


if __name__ == "__main__":
    main()
