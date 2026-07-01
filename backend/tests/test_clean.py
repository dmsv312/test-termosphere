"""Юнит-тесты чистилок. Проверяем ОБОБЩЁННЫЕ правила (регистр, формат, домен),
а не конкретные строки выгрузки — функции должны работать и на других данных."""

from datetime import date, datetime
from decimal import Decimal

from app.etl import clean


# --- norm_source --------------------------------------------------------------

def test_norm_source_case_and_alphabet():
    for raw in ("Avito", "AVITO", "avito", " avito ", "Авито"):
        assert clean.norm_source(raw) == ("avito", False)


def test_norm_source_website_alias():
    assert clean.norm_source("Website") == ("website", False)
    assert clean.norm_source("Сайт") == ("website", False)


def test_norm_source_unknown_flagged():
    code, unknown = clean.norm_source("vk_ads")
    assert code == "vk_ads" and unknown is True


def test_norm_source_blank():
    assert clean.norm_source("") == (None, False)
    assert clean.norm_source(None) == (None, False)


# --- parse_dt / parse_date ----------------------------------------------------

def test_parse_dt_iso_with_tz_is_standard():
    dt, nonstd = clean.parse_dt("2026-06-08T16:45:00+05:00")
    assert nonstd is False
    assert dt == datetime.fromisoformat("2026-06-08T16:45:00+05:00")


def test_parse_dt_bare_iso_date_gets_data_tz_and_is_standard():
    dt, nonstd = clean.parse_dt("2026-06-03")
    assert nonstd is False
    assert dt.utcoffset().total_seconds() == 5 * 3600
    assert (dt.year, dt.month, dt.day) == (2026, 6, 3)


def test_parse_dt_ru_datetime_is_nonstandard():
    dt, nonstd = clean.parse_dt("14.06.2026 09:20")
    assert nonstd is True
    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == (2026, 6, 14, 9, 20)


def test_parse_dt_slash_date_is_nonstandard():
    dt, nonstd = clean.parse_dt("2026/06/15")
    assert nonstd is True
    assert dt.date() == date(2026, 6, 15)


def test_parse_dt_garbage_flagged_none():
    assert clean.parse_dt("не дата") == (None, True)


def test_parse_dt_blank():
    assert clean.parse_dt(None) == (None, False)


def test_parse_date_returns_date():
    d, nonstd = clean.parse_date("2026-06-11")
    assert d == date(2026, 6, 11) and nonstd is False


# --- norm_phone ---------------------------------------------------------------

def test_norm_phone_leading_8_fixed():
    assert clean.norm_phone("89170003003") == ("+79170003003", "fixed")


def test_norm_phone_pretty_plus7_not_flagged():
    # уже +7 — компактим, но дефектом не считаем
    assert clean.norm_phone("+7 917 000-10-01") == ("+79170001001", None)


def test_norm_phone_unrecognized_kept():
    # не 11-значный РФ-номер → оставляем как есть, помечаем "unrecognized"
    assert clean.norm_phone("123") == ("123", "unrecognized")


def test_norm_phone_extension_unrecognized():
    assert clean.norm_phone("+7 923 709-19-92 доб.5") == ("+7 923 709-19-92 доб.5", "unrecognized")


def test_norm_phone_blank():
    assert clean.norm_phone("") == (None, None)


# --- parse_amount / parse_int / parse_bool / norm_inn -------------------------

def test_parse_amount_decimal_not_float():
    val = clean.parse_amount("21000.10")
    assert val == Decimal("21000.10") and isinstance(val, Decimal)


def test_parse_amount_negative_and_blank():
    assert clean.parse_amount("-12000.00") == Decimal("-12000.00")
    assert clean.parse_amount("") is None
    assert clean.parse_amount("abc") is None


def test_parse_int():
    assert clean.parse_int("10") == 10
    assert clean.parse_int("") is None


def test_parse_bool():
    assert clean.parse_bool("true") is True
    assert clean.parse_bool("false") is False
    assert clean.parse_bool(None) is None


def test_parse_bool_unrecognized_is_none():
    # опечатка/мусор → None, а не False (иначе ложный «неактивный» и т.п.)
    assert clean.parse_bool("maybe") is None
    assert clean.parse_bool("да") is None


def test_norm_inn_preserves_leading_zeros():
    assert clean.norm_inn("0278123456") == "0278123456"
    assert clean.norm_inn(None) is None


def test_is_blank():
    assert clean.is_blank("") and clean.is_blank("  ") and clean.is_blank(None)
    assert not clean.is_blank("x")
