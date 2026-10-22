"""Обновление каталога на существующей базе — без полного сброса.

Обычная загрузка данных (`flask seed`) умеет только дополнять каталог.
Но после правки исходных данных старые гайды остаются в базе, и на сайте
видны машины, которых больше нет в исходниках.

Этот скрипт делает три вещи:

1. Убирает гайды, которых больше нет в `paintguide/seed/`.
2. Догружает новые гайды через обычный `flask seed`.
3. Переставляет обложки по актуальному `covers.json`.

Аккаунты, избранное и вишлист сохраняются: удаляются только записи
каталога. Избранное и вишлист тех гайдов, которых больше нет, исчезают
вместе с ними — ссылка на удалённый гайд бессмысленна.

Запуск:

    python scripts/update_catalog.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from paintguide import create_app  # noqa: E402
from paintguide.extensions import db  # noqa: E402
from paintguide.models import Favorite, Guide, WishlistItem  # noqa: E402
from paintguide.seed import ALL_GUIDES  # noqa: E402
from sqlalchemy import select  # noqa: E402


def main() -> int:
    app = create_app()
    with app.app_context():
        alive = {guide["slug"] for guide in ALL_GUIDES}
        stored = {row.slug: row.id for row in db.session.scalars(select(Guide))}

        obsolete = [slug for slug in stored if slug not in alive]
        if obsolete:
            for slug in obsolete:
                guide = db.session.get(Guide, stored[slug])
                db.session.delete(guide)
            db.session.commit()
            print(f"Удалено гайдов: {len(obsolete)}", flush=True)
        else:
            print("Удалять нечего — все гайды на месте.", flush=True)

        # Избранное и вишлист хранят номер гайда обычным числом, без
        # внешнего ключа, поэтому записи об удалённых гайдах остаются
        # сами по себе. Их тоже убираем.
        guide_ids = set(stored.values()) - {stored[slug] for slug in obsolete}
        for model, field in ((Favorite, "target_id"), (WishlistItem, "item_id")):
            dangling = [
                row.id
                for row in db.session.scalars(select(model))
                if getattr(row, "target_type", getattr(row, "item_type", "")) == "guide"
                and getattr(row, field) not in guide_ids
            ]
            if dangling:
                for row_id in dangling:
                    db.session.delete(db.session.get(model, row_id))
                db.session.commit()
                print(f"Убрано записей из {model.__tablename__}: {len(dangling)}", flush=True)

        from paintguide.seed import load_seed_data

        created = load_seed_data(reset=False)
        print("Догружено: {guides} гайдов, {variants} уровней, {steps} шагов.".format(**created), flush=True)

        total = db.session.scalar(select(db.func.count(Guide.id))) or 0
        without = db.session.scalar(
            select(db.func.count(Guide.id)).where(Guide.cover_url == "")
        ) or 0
        print(f"Всего гайдов: {total}; без обложки: {without}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
