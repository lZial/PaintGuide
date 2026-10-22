"""Перенос избранного и вишлиста под новый смысл разделов.

Раньше избранное хранило и гайды, и краски, а вишлист — записи
любых типов. Теперь избранное — про модели, а вишлист — про краски.

Скрипт переносит данные из старой структуры в новую:

* избранные краски → вишлист;
* гайды в вишлисте → избранное;
* свободные записи (модель, идея) остаются в вишлисте как заметки.

Запуск:

    python scripts/migrate_favorites_wishlist.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from paintguide import create_app  # noqa: E402
from paintguide.extensions import db  # noqa: E402
from paintguide.models import Favorite, Guide, Paint, WishlistItem  # noqa: E402


def main() -> int:
    app = create_app()
    with app.app_context():
        moved_paints = 0
        moved_guides = 0
        kept_notes = 0

        # 1. Избранные краски → вишлист.
        for favorite in list(
            db.session.scalars(
                select(Favorite).where(Favorite.target_type == "paint")
            )
        ):
            paint = db.session.get(Paint, favorite.target_id)
            if paint is None:
                db.session.delete(favorite)
                continue
            existing = db.session.scalar(
                select(WishlistItem).where(
                    WishlistItem.user_id == favorite.user_id,
                    WishlistItem.item_type == "paint",
                    WishlistItem.item_id == paint.id,
                )
            )
            if existing is None:
                db.session.add(
                    WishlistItem(
                        user_id=favorite.user_id,
                        item_type="paint",
                        item_id=paint.id,
                        name=f"{paint.brand.name} — {paint.name}",
                        notes=f"Оттенок {paint.color_hex}",
                    )
                )
            db.session.delete(favorite)
            moved_paints += 1
        db.session.commit()

        # 2. Гайды из вишлиста → избранное.
        for entry in list(
            db.session.scalars(
                select(WishlistItem).where(WishlistItem.item_type == "guide")
            )
        ):
            guide = db.session.get(Guide, entry.item_id) if entry.item_id else None
            if guide is None:
                db.session.delete(entry)
                continue
            existing = db.session.scalar(
                select(Favorite).where(
                    Favorite.user_id == entry.user_id,
                    Favorite.target_type == "guide",
                    Favorite.target_id == guide.id,
                )
            )
            if existing is None:
                db.session.add(
                    Favorite(
                        user_id=entry.user_id,
                        target_type="guide",
                        target_id=guide.id,
                    )
                )
            db.session.delete(entry)
            moved_guides += 1
        db.session.commit()

        # 3. Свободные записи: оставляем в вишлисте как заметки.
        for entry in list(
            db.session.scalars(
                select(WishlistItem).where(
                    WishlistItem.item_type.in_(("model", "idea"))
                )
            )
        ):
            entry.item_type = "paint"
            entry.item_id = None
            kept_notes += 1
        db.session.commit()

        print(f"Краски перенесены из избранного в вишлист: {moved_paints}", flush=True)
        print(f"Гайды перенесены из вишлиста в избранное: {moved_guides}", flush=True)
        print(f"Свободные записи оставлены в вишлисте: {kept_notes}", flush=True)

        for label, model in (("избранное", Favorite), ("вишлист", WishlistItem)):
            rows = list(db.session.scalars(select(model)))
            kinds = sorted({getattr(row, "target_type", getattr(row, "item_type", "")) for row in rows})
            print(f"{label}: записей {len(rows)}, типы {kinds or '—'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
