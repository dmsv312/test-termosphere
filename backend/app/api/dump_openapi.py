"""Выгрузка OpenAPI-схемы FastAPI в docs/openapi.json (машинный контракт API).

Схема идентична той, что живой сервер отдаёт на `/openapi.json` (и рисует
Swagger UI на `/docs`). Держим её в git отдельным артефактом — чтобы контракт
можно было читать и диффать без запуска сервера. Человекочитаемое описание с
формой ответа и примерами — в docs/api-contract.md.

Запуск: `make openapi` (или `python -m app.api.dump_openapi`).
"""

import json
from pathlib import Path

from app.main import app

# repo_root/backend/app/api/dump_openapi.py → repo_root/docs/openapi.json
OUT_PATH = Path(__file__).resolve().parents[3] / "docs" / "openapi.json"


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()
    OUT_PATH.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Записано {OUT_PATH} ({len(schema.get('paths', {}))} путей).")


if __name__ == "__main__":
    main()
