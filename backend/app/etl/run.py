"""Оркестратор загрузки. Шаг 1: CSV → raw. Шаг 3 добавит transform raw → core."""

from app.etl.load_raw import load_all as load_raw


def main() -> None:
    print("Загрузка raw:")
    load_raw()
    # transform raw → core — добавится на шаге 3


if __name__ == "__main__":
    main()
