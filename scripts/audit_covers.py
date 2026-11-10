"""Аудит обложек: у каких гайдов фото явно не той техники.

Сравниваем слаги и названия гайдов с именем файла-обложки на Commons.
Если ни одно «значимое» слово слага не встречается в имени файла —
обложку стоит проверить глазами.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

COVERS = json.loads((ROOT / "paintguide/seed/covers.json").read_text(encoding="utf-8"))
GUIDES = json.loads((ROOT / "paintguide/seed/guides_index.json").read_text(encoding="utf-8")) \
    if (ROOT / "paintguide/seed/guides_index.json").exists() else None

# Нейтральные слова: их присутствие ничего не доказывает.
STOP = {
    "tank", "tanks", "panzer", "panzers", "german", "germany", "soviet", "russian",
    "british", "american", "usa", "japanese", "italian", "french", "polish", "swedish",
    "finnish", "chinese", "israeli", "museum", "museo", "war", "world", "wwii", "ww2",
    "the", "and", "of", "in", "at", "on", "with", "for", "photo", "image", "file",
    "army", "military", "history", "historical", "parade", "day", "victory", "tankfest",
    "bovington", "kubinka", "munster", "saumur", "aberdeen", "bulgaria", "sofia",
    "scale", "model", "models", "modelling", "modelling", "diorama", "built", "kit",
}


def tokens(value: str) -> set[str]:
    value = re.sub(r"^File:", "", value, flags=re.I)
    value = re.sub(r"\.(jpe?g|png|gif|tiff?|webp)$", "", value, flags=re.I)
    parts = re.split(r"[^a-z0-9]+", value.lower())
    return {part for part in parts if len(part) >= 2}


def main() -> int:
    from paintguide import create_app
    from paintguide.extensions import db
    from paintguide.models import Guide

    app = create_app()
    with app.app_context():
        guides = list(db.session.scalars(db.select(Guide).order_by(Guide.slug)))

        suspicious = []
        missing = []
        for guide in guides:
            entry = COVERS.get(guide.slug)
            if not entry:
                missing.append(guide.slug)
                continue
            title = entry.get("title", "")
            if not title or entry.get("kind") != "vehicle":
                continue
            slug_tokens = tokens(guide.slug) - STOP
            slug_tokens |= tokens(guide.title) - STOP
            title_tokens = tokens(title)
            if not (slug_tokens & title_tokens):
                suspicious.append((guide.slug, guide.title, title))

    print(f"Всего гайдов: {len(guides)}; без записи в covers.json: {len(missing)}")
    if missing:
        print("  без обложки:", ", ".join(missing[:20]), "..." if len(missing) > 20 else "")
    print(f"\nПодозрительных обложек: {len(suspicious)}")
    for slug, title, cover in suspicious:
        print(f"  {slug:<28} | {title[:34]:<34} | {cover[5:90]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
