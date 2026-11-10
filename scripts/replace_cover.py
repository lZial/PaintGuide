"""Быстрая замена обложек гайдов.

Источник — файл Wikimedia Commons или локальная картинка. Скрипт
скачивает фото, приводит его к 3:2 (центр), сжимает в JPEG 960 px,
кладёт в static/img/vehicles/<slug>.jpg, обновляет covers.json и
строку гайда в базе — чтобы сайт сразу показывал новую обложку.

Примеры:

    python scripts/replace_cover.py jagdpanzer-iv "File:Panzermuseum Munster 2010 0449.JPG"
    python scripts/replace_cover.py jagdpanzer-iv --file C:\\photos\\jagd.jpg
    python scripts/replace_cover.py --batch replacements.txt   # строки: slug|File:... или slug|путь
    python scripts/replace_cover.py jagdpanzer-iv "File:..." --no-db
"""

from __future__ import annotations

import html
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA_FILE = ROOT / "paintguide/seed/covers.json"
COVERS_DIR = ROOT / "paintguide/static/img/vehicles"
API = "https://commons.wikimedia.org/w/api.php"

WIDTH = 960
HEIGHT = 640  # 3:2
QUALITY = 84
DELAY = 0.6

_APP = None


def _get_app():
    """Одно приложение на весь батч: старт с миграциями стоит ~15 секунд."""
    global _APP
    if _APP is None:
        from paintguide import create_app

        _APP = create_app()
    return _APP

BOT_UA = "PaintGuideBot/1.0 (https://paint-guide.vercel.app; paintguide@example.com)"
DOWNLOAD_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _clean(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def _fetch(url: str, ua: str, attempts: int = 3) -> bytes:
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": ua})
            with urllib.request.urlopen(request, timeout=90) as response:
                return response.read()
        except Exception as error:  # noqa: BLE001
            last = error
            if attempt < attempts:
                time.sleep(2 * attempt)
    raise RuntimeError(f"не скачалось {url}: {last}")


def commons_info(title: str) -> dict:
    """Метаданные файла Commons: ссылка на оригинал, автор, лицензия."""
    if not title.lower().startswith("file:"):
        title = f"File:{title}"
    params = {
        "action": "query",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "iiurlwidth": 1600,
        "format": "json",
    }
    url = API + "?" + urllib.parse.urlencode(params)
    data = json.loads(_fetch(url, BOT_UA))
    pages = data.get("query", {}).get("pages", {})
    page = next(iter(pages.values()), {})
    if "imageinfo" not in page:
        raise SystemExit(f"Файл не найден на Commons: {title}")
    info = page["imageinfo"][0]
    meta = info.get("extmetadata", {})

    def field(name: str) -> str:
        return _clean((meta.get(name) or {}).get("value", ""))

    return {
        "title": page.get("title", title),
        "image_url": info.get("thumburl") or info.get("url", ""),
        "author": field("Artist") or field("Credit"),
        "license": field("LicenseShortName") or field("License"),
        "license_url": field("LicenseUrl"),
        "source": info.get("descriptionurl", ""),
    }


def _to_cover(raw: bytes) -> bytes:
    """3:2 по центру, 960x640, JPEG."""
    image = Image.open(io.BytesIO(raw))
    image = ImageOps.exif_transpose(image).convert("RGB")
    target = WIDTH / HEIGHT
    width, height = image.size
    if width / height > target:
        new_width = int(height * target)
        left = (width - new_width) // 2
        image = image.crop((left, 0, left + new_width, height))
    else:
        new_height = int(width / target)
        top = (height - new_height) // 2
        image = image.crop((0, top, width, top + new_height))
    image = image.resize((WIDTH, HEIGHT), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    return buffer.getvalue()


def replace(slug: str, source: str, update_db: bool = True) -> bool:
    start = time.time()

    if source.lower().startswith(("http://", "https://")):
        raw = _fetch(source, DOWNLOAD_UA)
        info = {"title": source, "author": "", "license": "", "license_url": "", "source": source}
    elif source.lower().startswith(("file:", "commons:")):
        info = commons_info(source.split(":", 1)[1] if source.lower().startswith("commons:") else source)
        raw = _fetch(info["image_url"], DOWNLOAD_UA)
    else:
        path = Path(source)
        if not path.is_absolute():
            path = ROOT / path
        if not path.exists():
            print(f"  ! {slug}: нет файла {path}")
            return False
        raw = path.read_bytes()
        info = {
            "title": f"Локальный файл: {path.name}",
            "author": "",
            "license": "",
            "license_url": "",
            "source": "",
        }

    cover = _to_cover(raw)
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    target = COVERS_DIR / f"{slug}.jpg"
    target.write_bytes(cover)

    url = f"/static/img/vehicles/{slug}.jpg"
    data = json.loads(DATA_FILE.read_text(encoding="utf-8")) if DATA_FILE.exists() else {}
    data[slug] = {
        "file": f"static/img/vehicles/{slug}.jpg",
        "title": info["title"],
        "author": info["author"],
        "license": info["license"],
        "license_url": info["license_url"],
        "source": info["source"],
        "kind": data.get(slug, {}).get("kind", "vehicle"),
        "scale": data.get(slug, {}).get("scale", ""),
    }
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if update_db:
        from sqlalchemy import select

        from paintguide.extensions import db
        from paintguide.models import Guide

        with _get_app().app_context():
            guide = db.session.scalar(select(Guide).where(Guide.slug == slug))
            if guide is None:
                print(f"  ! {slug}: гайда нет в базе (файл и covers.json обновлены)")
            else:
                guide.cover_url = url
                guide.cover_credit = info["author"]
                guide.cover_license = info["license"]
                guide.cover_source = info["source"]
                guide.cover_kind = data[slug]["kind"]
                db.session.commit()

    seconds = time.time() - start
    print(f"  {slug}: {len(cover) // 1024} КБ · {seconds:.1f} с · {info['title']}")
    return True


def main() -> int:
    args = sys.argv[1:]
    update_db = "--no-db" not in args
    args = [arg for arg in args if arg != "--no-db"]

    pairs: list[tuple[str, str]] = []
    if "--batch" in args:
        batch_file = Path(args[args.index("--batch") + 1])
        for line in batch_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            slug, source = line.split("|", 1)
            pairs.append((slug.strip(), source.strip()))
    elif "--file" in args:
        index = args.index("--file")
        slug = args[0] if args and not args[0].startswith("--") else ""
        pairs.append((slug, args[index + 1]))
    elif len(args) >= 2:
        pairs.append((args[0], " ".join(args[1:])))
    else:
        print(__doc__)
        return 2

    ok = 0
    if update_db:
        _get_app()  # прогреваем приложение один раз
    for index, (slug, source) in enumerate(pairs, 1):
        print(f"[{index}/{len(pairs)}] {slug}")
        try:
            if replace(slug, source, update_db):
                ok += 1
        except Exception as error:  # noqa: BLE001
            print(f"  ! {slug}: {error}")
        if index < len(pairs):
            time.sleep(DELAY)

    print(f"\nГотово: {ok} из {len(pairs)}")
    return 0 if ok == len(pairs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
