"""Выгрузка канонического SQL отчётов в db/reports.sql (человекочитаемый дамп).

Файл db/reports.sql генерируется из `queries.py` — единственного источника правды,
который же исполняет API. Запуск: `make reports-sql` (или `python -m app.reports.dump_sql`).
Плейсхолдер бинда `:n_days` (отчёт 5) подставляется дефолтом, чтобы файл исполнялся
как есть в psql.
"""

from pathlib import Path

from app.reports.queries import DEFAULT_STALE_DAYS, REPORTS

# repo_root/backend/app/reports/dump_sql.py → repo_root/db/reports.sql
OUT_PATH = Path(__file__).resolve().parents[3] / "db" / "reports.sql"

_HEADER = """\
-- db/reports.sql — семь управленческих отчётов (ТермоСфера).
--
-- СГЕНЕРИРОВАНО из backend/app/reports/queries.py (не править вручную:
-- правки внесите в queries.py и выполните `make reports-sql`).
-- Тот же SQL исполняет API (/api/reports/*), поэтому файл и живые отчёты совпадают.
--
-- Считаем по core-слою (карантинные строки в core не попали). Бизнес-правила —
-- в ASSUMPTIONS.md. Все запросы read-only.
"""


def render() -> str:
    parts = [_HEADER]
    for title, sql in REPORTS:
        # :n_days — единственный бинд (отчёт 5); подставляем дефолт для psql.
        body = sql.replace(":n_days", str(DEFAULT_STALE_DAYS)).rstrip()
        if not body.endswith(";"):
            body += ";"
        parts.append(f"\n-- === {title} ===\n{body}\n")
    return "\n".join(parts)


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(render(), encoding="utf-8")
    print(f"Записано {OUT_PATH} ({len(REPORTS)} отчётов).")


if __name__ == "__main__":
    main()
