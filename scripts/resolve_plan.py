"""Сбор кандидатов на обложки: поиск по API без скачивания.

Хранилище Wikimedia отказывает при частых обращениях, поэтому поиск и
скачивание разнесены по разным шагам: сначала через API находится файл
для каждой машины, потом файлы скачиваются медленно, по одному.

Запуск:  python scripts/resolve_plan.py [план.json]
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
DEFAULT_OUT = Path(
    r"C:\Users\shist\AppData\Local\Temp\opencode\cover_plan_all.json"
)

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = (
    "PaintGuideBot/1.0 (https://example.org/paintguide; paintguide@example.com) "
    "python-urllib/3"
)


def api_get(params: dict, attempts: int = 8) -> dict:
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
            time.sleep(30.0 if "429" in str(error) else 4.0)
    raise RuntimeError(f"API не ответил: {last}")


def fetch_files(titles: list[str]) -> dict[str, dict]:
    """Метаданные файлов пачками по сорок."""
    import re

    result: dict[str, dict] = {}
    for start in range(0, len(titles), 40):
        chunk = titles[start:start + 40]
        data = api_get(
            {
                "action": "query",
                "titles": "|".join(chunk),
                "prop": "imageinfo",
                "iiprop": "url|extmetadata|size",
                "iiurlwidth": 960,
                "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl|License|"
                "ImageDescription|Credit|Categories",
            }
        )
        for page in data.get("query", {}).get("pages", {}).values():
            info = (page.get("imageinfo") or [{}])[0]
            if not info.get("url"):
                continue
            meta = info.get("extmetadata", {}) or {}

            def field(name: str) -> str:
                value = meta.get(name, {}).get("value", "")
                if not isinstance(value, str):
                    return ""
                text = re.sub(r"<[^>]+>", " ", value)
                return re.sub(r"\s+", " ", text).strip()

            result[page.get("title", "")] = {
                "title": page.get("title", ""),
                "author": field("Artist") or field("Credit"),
                "license": field("LicenseShortName") or field("License"),
                "license_url": field("LicenseUrl"),
                "description": field("ImageDescription"),
                "categories": field("Categories"),
                "source": info.get("descriptionurl", ""),
                "url": info.get("url", ""),
                "thumb_url": info.get("thumburl", ""),
                "width": info.get("width", 0),
                "height": info.get("height", 0),
            }
        time.sleep(2.0)
    return result


def main() -> int:
    from scripts.fetch_covers import (
        _names_for,
        category_says_vehicle,
        candidates_for,
        match_article,
        match_quality,
        title_ok,
        wrong_vehicle,
    )

    covers = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    missing = [g["slug"] for g in ALL_GUIDES if g["slug"] not in covers]
    print(f"без обложки: {len(missing)}")

    # Аргументом может быть путь к плану; ключи вида "-u" — это флаги
    # интерпретатора, путь для них не годится.
    arguments = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
    out = Path(arguments[0]) if arguments else DEFAULT_OUT
    plan: dict[str, dict] = {}
    if out.exists():
        plan = json.loads(out.read_text(encoding="utf-8"))
        print(f"в плане уже {len(plan)} машин")

    for index, slug in enumerate(missing, 1):
        if slug in plan:
            continue
        names = _names_for(slug)
        print(f"[{index}/{len(missing)}] {slug}", flush=True)
        try:
            candidates = candidates_for(slug, names, False)
        except Exception as error:  # noqa: BLE001
            print(f"  ! поиск не удался: {error}")
            continue
        for item in candidates[:4]:
            plan[slug] = {
                "file": item["title"].removeprefix("File:"),
                "source": item.get("context", ""),
                "kind": "vehicle",
                # Категории нужны для проверки: по названию файла «Type 89»
                # не отличить танк от орудия.
                "categories": (item.get("categories") or "")[:1200],
            }
            print(f"  > {item['title'][:62]}")
            break
        # План сохраняем сразу: работа идёт долго, и её не жалко терять.
        out.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(1.0)

    print(f"\nнайдено файлов: {len(plan)}; план: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
