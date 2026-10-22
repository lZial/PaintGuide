"""Сборка для Vercel.

Две задачи:

1. **Статика.** На Vercel папка ``static_folder`` Flask не
   раздаётся — файлы кладутся в ``public/**``, и Vercel отдаёт их
   через CDN. Копируем ``paintguide/static`` в ``public/static``,
   чтобы ссылки вида ``/static/css/site.css`` продолжали работать.

2. **Данные.** Если база пустая, наполняем её: на Vercel база внешняя
   (Postgres из Neon), и на этапе сборки переменная ``DATABASE_URL``
   уже доступна. Так новый деплой не остаётся с пустым сайтом.

Запуск:  python build.py
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "paintguide"
PUBLIC = ROOT / "public"
STATIC_SOURCE = PACKAGE / "static"


def copy_static() -> int:
    """Скопировать статику в public/static."""
    target = PUBLIC / "static"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(STATIC_SOURCE, target)
    return sum(1 for path in target.rglob("*") if path.is_file())


def make_404() -> None:
    """Страница «не найдено» для Vercel."""
    template = PACKAGE / "templates" / "error.html"
    if not template.exists():
        return
    PUBLIC.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template, PUBLIC / "404.html")


def fill_database() -> bool:
    """Наполнить базу, если в ней ещё нет гайдов."""
    sys.path.insert(0, str(ROOT))
    from paintguide import create_app
    from paintguide.extensions import db
    from paintguide.models import Guide

    app = create_app()
    with app.app_context():
        guides = db.session.scalar(db.select(db.func.count(Guide.id)))
        if guides:
            print(f"База уже наполнена: гайдов {guides}.")
            return False
        print("База пустая — загружаем справочники и руководства…")
        from paintguide.seed import load_seed_data

        created = load_seed_data(reset=False)
        print(
            "Загружено: {countries} стран, {vehicles} типов техники, "
            "{paints} красок, {guides} руководств.".format(**created)
        )
        return True


def main() -> int:
    import time

    # Лог сборки на Vercel не терминал: без этой строки вывод
    # залипает в буфере и в логе не видно, что происходит.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):  # pragma: no cover
        pass

    started = time.perf_counter()
    PUBLIC.mkdir(parents=True, exist_ok=True)
    files = copy_static()
    make_404()
    print(
        f"Статика скопирована в public/static: файлов {files} "
        f"({time.perf_counter() - started:.1f} с).",
        flush=True,
    )

    if not (os.environ.get("DATABASE_URL") or "").strip():
        print("DATABASE_URL не задан — база остаётся локальной (для проверки).")
        return 0

    try:
        fill_database()
    except Exception as error:  # noqa: BLE001
        # Пустой сайт хуже, чем красная сборка: с ошибкой в логах
        # видно, что именно сломалось, и деплой можно повторить.
        print(f"Не удалось подготовить базу: {error}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1
    print(f"Сборка заняла {time.perf_counter() - started:.1f} с.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
