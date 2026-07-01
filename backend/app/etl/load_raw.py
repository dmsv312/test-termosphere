"""Загрузка CSV → raw. Данные кладём «как есть» (пустая ячейка → NULL).

Идемпотентно: перед вставкой TRUNCATE ... RESTART IDENTITY, поэтому повторный
`make load` не плодит дубли. Путь к данным — от корня репозитория (data/), не
зависит от текущей директории запуска.
"""

import csv
from pathlib import Path

from sqlalchemy import text

from app.db.session import SessionLocal
from app.models.raw import RAW_TABLES

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
FILE_PREFIX = "Таблица выгрузки Битрикс - "


def _read_csv(path: Path) -> list[dict]:
    # utf-8-sig — на случай BOM в первой ячейке заголовка.
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [
            {k: (v if v not in ("", None) else None) for k, v in row.items()}
            for row in reader
        ]


def load_all() -> dict[str, int]:
    """Загружает все 13 CSV в raw-таблицы. Возвращает {имя: число строк}."""
    counts: dict[str, int] = {}
    with SessionLocal() as session:
        for model, name in RAW_TABLES:
            path = DATA_DIR / f"{FILE_PREFIX}{name}.csv"
            if not path.exists():
                raise FileNotFoundError(
                    f"нет файла данных: {path}\n"
                    f"положи 13 CSV выгрузки в {DATA_DIR} (см. README)."
                )
            rows = _read_csv(path)
            session.execute(text(f"TRUNCATE {model.__tablename__} RESTART IDENTITY"))
            session.add_all([model(**row) for row in rows])
            session.commit()
            counts[name] = len(rows)
            print(f"  raw_{name}: {len(rows)} строк")
    return counts


if __name__ == "__main__":
    load_all()
