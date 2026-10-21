"""Проверка обложек: действительно ли фотография показывает нужную машину.

Для каждой обложки смотрим категории Commons: там машина названа точно.
Название файла может совпадать случайно («SA 201» — и танкет, и самолёт),
а категория — надёжный признак.

Запуск:  python scripts/check_covers.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from paintguide.seed import ALL_GUIDES  # noqa: E402

PACKAGE = ROOT / "paintguide"
DATA_FILE = PACKAGE / "seed" / "covers.json"
API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = (
    "PaintGuideBot/1.0 (https://example.org/paintguide; paintguide@example.com) "
    "python-urllib/3"
)


def api_get(params: dict, attempts: int = 6) -> dict:
    query = urllib.parse.urlencode({**params, "format": "json"})
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(
                f"{API}?{query}", headers={"User-Agent": USER_AGENT}
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as error:  # noqa: BLE001
            last = error
            time.sleep(45.0 if "429" in str(error) else 4.0)
    raise RuntimeError(f"API не ответил: {last}")


def fetch_categories(titles: list[str]) -> dict[str, str]:
    """Категории Commons для пачки файлов."""
    import re

    result: dict[str, str] = {}
    for start in range(0, len(titles), 40):
        chunk = titles[start:start + 40]
        data = api_get(
            {
                "action": "query",
                "titles": "|".join(chunk),
                "prop": "imageinfo",
                "iiprop": "extmetadata",
                "iiextmetadatafilter": "Categories",
            }
        )
        for page in data.get("query", {}).get("pages", {}).values():
            meta = (page.get("imageinfo") or [{}])[0].get("extmetadata", {}) or {}
            value = meta.get("Categories", {}).get("value", "")
            if not isinstance(value, str):
                value = ""
            text = re.sub(r"<[^>]+>", " ", value)
            result[page.get("title", "")] = re.sub(r"\s+", " ", text).strip()
        time.sleep(2.0)
    return result


def main() -> int:
    from scripts.fetch_covers import (
        _names_for,
        _tokens,
        _normalize,
        category_says_vehicle,
        wrong_vehicle,
    )

    covers = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    titles = list(dict.fromkeys(
        entry["title"] for entry in covers.values() if entry.get("title")
    ))
    print(f"обложек: {len(covers)}, файлов для проверки: {len(titles)}")

    categories = fetch_categories(titles)
    lookup = {title.replace("_", " "): value for title, value in categories.items()}

    suspect: list[tuple[str, str, str]] = []
    for slug, entry in sorted(covers.items()):
        title = entry.get("title", "")
        if not title:
            continue
        cats = categories.get(title, "") or lookup.get(title.replace("_", " "), "")
        names = _names_for(slug)
        if cats:
            if category_says_vehicle(slug, {"categories": cats}):
                continue
            suspect.append((slug, title, f"категории: {cats[:70]}"))
            continue
        # Категорий нет — сверяемся по названию файла.
        normalized = _normalize(title)
        if any(token in normalized for name in names for token in _tokens(name)):
            continue
        if wrong_vehicle(slug, {"title": title}):
            suspect.append((slug, title, "на фото другая машина из каталога"))
            continue
        suspect.append((slug, title, "признаков машины не найдено"))

    print(f"\nподозрительных: {len(suspect)}")
    for slug, title, reason in suspect:
        print(f"  {slug:26s} {title[:52]:52s} {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
