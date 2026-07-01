"""Чистые функции нормализации + доменные справочники для transform.

Маленькие, без побочных эффектов, покрыты юнит-тестами. Логика ОБОБЩЁННАЯ — она
не завязана на конкретные строки этой выгрузки, а работает по правилам (регистр,
формат, домен), поэтому применима и к другим данным. Каждая функция, где уместно,
возвращает флаг «значение чинилось» — по нему transform решает, логировать ли
проблему в data_quality_issues.
"""

import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

# Часовой пояс данных выгрузки (+05:00) — проставляем «наивным» датам без TZ.
DATA_TZ = timezone(timedelta(hours=5))

# Канонические каналы (нижний регистр). Всё, что после strip().lower() не совпало
# ни с кодом, ни с алиасом ниже, — считаем неизвестным каналом (флаг).
CANONICAL_SOURCES = {
    "avito",
    "website",
    "yandex_direct",
    "phone",
    "referral",
    "telegram",
}
# Алиасы иного алфавита/написания → канонический код.
SOURCE_ALIASES = {
    "авито": "avito",
    "сайт": "website",
}

# Форматы дат: (strptime-формат, is_nonstandard). ISO 8601 (с TZ и «голая» дата) —
# чистые, без флага; остальные — «кривые», чиним и помечаем.
DATE_FORMATS = (
    ("%Y-%m-%dT%H:%M:%S%z", False),
    ("%Y-%m-%d", False),
    ("%Y/%m/%d", True),
    ("%d.%m.%Y %H:%M", True),
    ("%d.%m.%Y", True),
)


def is_blank(v) -> bool:
    """None или пустая/пробельная строка."""
    return v is None or (isinstance(v, str) and v.strip() == "")


def norm_source(raw: str | None) -> tuple[str | None, bool]:
    """(канонический_код | None, is_unknown).

    Приводит регистр и алфавит к канону (Avito/AVITO/Авито → avito). Если код не
    из справочника каналов — возвращаем его как есть и помечаем is_unknown=True.
    """
    if is_blank(raw):
        return None, False
    key = raw.strip().lower()
    code = SOURCE_ALIASES.get(key, key)
    return code, code not in CANONICAL_SOURCES


def parse_dt(raw: str | None, tz: timezone = DATA_TZ) -> tuple[datetime | None, bool]:
    """(aware datetime | None, is_nonstandard).

    Понимает ISO с TZ, «голую» дату ISO и кривые форматы (DD.MM.YYYY[ HH:MM],
    YYYY/MM/DD). Наивным датам проставляет TZ данных. Нераспознанное → (None, True).
    """
    if is_blank(raw):
        return None, False
    s = raw.strip()
    for fmt, nonstandard in DATE_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        return dt, nonstandard
    return None, True


def parse_date(raw: str | None) -> tuple[date | None, bool]:
    """(date | None, is_nonstandard) — для чисто-датных полей (отгрузки, затраты)."""
    dt, nonstandard = parse_dt(raw)
    return (dt.date() if dt else None), nonstandard


def norm_phone(raw: str | None) -> tuple[str | None, str | None]:
    """(значение | None, status).

    Приводит 11-значные РФ-номера к виду +7XXXXXXXXXX. status:
      None           — пусто, либо уже +7 (косметическая чистка пробелов/дефисов —
                       не дефект);
      "fixed"        — приведён к +7 из иного формата (например 8XXXXXXXXXX);
      "unrecognized" — не свёлся к 11-значному РФ-номеру (добавочный, 12+ цифр);
                       хранится как есть (данные не теряем) и помечается transform'ом.
    """
    if is_blank(raw):
        return None, None
    s = raw.strip()
    digits = re.sub(r"\D", "", s)
    if len(digits) == 11 and digits[0] == "8":
        digits = "7" + digits[1:]
    if len(digits) == 11 and digits[0] == "7":
        return "+" + digits, (None if s.startswith("+7") else "fixed")
    return s, "unrecognized"


def parse_amount(raw: str | None) -> Decimal | None:
    """Decimal (деньги/ИНН — не float). Нераспознанное → None."""
    if is_blank(raw):
        return None
    try:
        return Decimal(raw.strip())
    except (InvalidOperation, ValueError):
        return None


def parse_int(raw: str | None) -> int | None:
    if is_blank(raw):
        return None
    try:
        return int(raw.strip())
    except ValueError:
        return None


def parse_bool(raw: str | None) -> bool | None:
    """true/1/yes/t → True; false/0/no/f → False; пусто/нераспознанное → None.

    Нераспознанное (опечатка) возвращаем None, а не False: иначе, например,
    менеджер молча стал бы «неактивным» и дал ложный сигнал.
    """
    if is_blank(raw):
        return None
    v = raw.strip().lower()
    if v in ("true", "1", "yes", "t"):
        return True
    if v in ("false", "0", "no", "f"):
        return False
    return None


def norm_inn(raw: str | None) -> str | None:
    """ИНН — строка (ведущие нули значимы), просто чистим пробелы."""
    return None if is_blank(raw) else raw.strip()
