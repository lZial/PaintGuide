"""Поиск кандидатов-обложек на Commons и контактные листы.

Читает список «slug|запрос» (по одному в строке), ищет файлы на
Wikimedia Commons, скачивает миниатюры и собирает контактный лист,
чтобы глазами выбрать нужное фото.

    python scripts/cover_candidates.py --list missing.txt --out tmp_covers
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
API = "https://commons.wikimedia.org/w/api.php"
BOT_UA = "PaintGuideBot/1.0 (https://paint-guide.vercel.app; paintguide@example.com)"
DOWNLOAD_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
BAD = re.compile(
    r"logo|map\b|diagram|drawing|blueprint|scale model|diorama|toy|lego|stamp|coin|"
    r"patch\b|insignia|banknote|\.svg|\.gif|wargame|miniature|box art|cover art|"
    r"poster|screenshot|render",
    re.I,
)
CELL_W, CELL_H = 320, 214
LABEL_H = 22
COLS = 4
ROWS_PER_SHEET = 6


def api(params: dict) -> dict:
    params = dict(params, format="json")
    url = API + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": BOT_UA})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


def download(url: str, target: Path) -> bool:
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": DOWNLOAD_UA})
            with urllib.request.urlopen(request, timeout=60) as response:
                target.write_bytes(response.read())
            return True
        except Exception:  # noqa: BLE001
            time.sleep(1.5 * (attempt + 1))
    return False


def _tokens(value: str) -> set[str]:
    parts = re.split(r"[^a-zа-я0-9]+", value.lower())
    return {part for part in parts if len(part) >= 2}


def candidates(query: str, per: int = 4) -> list[dict]:
    data = api(
        {
            "action": "query",
            "list": "search",
            "srsearch": f"{query} filetype:bitmap",
            "srnamespace": 6,
            "srlimit": 20,
        }
    )
    hits = [item["title"] for item in data.get("query", {}).get("search", [])]
    wanted = _tokens(query)
    scored = []
    for position, title in enumerate(hits):
        if BAD.search(title):
            continue
        score = len(wanted & _tokens(title))
        scored.append((score, -position, title))
    scored.sort(reverse=True)
    titles = [title for _, _, title in scored[: per * 2]]

    if not titles:
        return []

    info = api(
        {
            "action": "query",
            "titles": "|".join(titles),
            "prop": "imageinfo",
            "iiprop": "url|size",
            "iiurlwidth": 520,
        }
    )
    by_title = {}
    for page in info.get("query", {}).get("pages", {}).values():
        if "imageinfo" in page:
            by_title[page["title"]] = page["imageinfo"][0]

    result = []
    for title in titles:
        item = by_title.get(title)
        if item:
            result.append(
                {
                    "title": title,
                    "thumb": item.get("thumburl"),
                    "width": item.get("width"),
                    "height": item.get("height"),
                }
            )
        if len(result) >= per:
            break
    return result


def main() -> int:
    args = sys.argv[1:]
    list_file = Path(args[args.index("--list") + 1])
    out = Path(args[args.index("--out") + 1]) if "--out" in args else Path("tmp_covers")
    out.mkdir(parents=True, exist_ok=True)

    tasks = []
    for line in list_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        slug = parts[0].strip()
        query = parts[1].strip() if len(parts) > 1 and parts[1].strip() else slug
        tasks.append((slug, query))

    catalogue: dict[str, list[dict]] = {}
    for index, (slug, query) in enumerate(tasks, 1):
        print(f"[{index}/{len(tasks)}] {slug}: {query}")
        try:
            items = candidates(query)
        except Exception as error:  # noqa: BLE001
            print(f"  ! поиск не удался: {error}")
            items = []
        folder = out / slug
        folder.mkdir(exist_ok=True)
        for position, item in enumerate(items):
            target = folder / f"{position}.jpg"
            if item["thumb"] and download(item["thumb"], target):
                item["local"] = str(target)
        catalogue[slug] = items
        time.sleep(0.6)

    (out / "candidates.json").write_text(
        json.dumps(catalogue, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    font = ImageFont.load_default(size=13)
    slugs = [slug for slug, items in catalogue.items() if items]
    for sheet_index in range(0, len(slugs), ROWS_PER_SHEET):
        chunk = slugs[sheet_index : sheet_index + ROWS_PER_SHEET]
        sheet = Image.new("RGB", (COLS * CELL_W, len(chunk) * (CELL_H + LABEL_H)), "#15130f")
        draw = ImageDraw.Draw(sheet)
        for row, slug in enumerate(chunk):
            for col, item in enumerate(catalogue[slug]):
                x = col * CELL_W
                y = row * (CELL_H + LABEL_H)
                local = Path(item.get("local", ""))
                if local.exists():
                    try:
                        thumb = Image.open(local).convert("RGB")
                        thumb.thumbnail((CELL_W - 4, CELL_H - 4))
                        sheet.paste(thumb, (x + 2, y + 2))
                    except Exception:  # noqa: BLE001
                        pass
                draw.text((x + 4, y + CELL_H), f"{slug} #{col}", fill="#ffffff", font=font)
        name = out / f"sheet_{sheet_index // ROWS_PER_SHEET + 1}.png"
        sheet.save(name)
        print("лист:", name)

    empty = [slug for slug, items in catalogue.items() if not items]
    if empty:
        print("ничего не найдено:", ", ".join(empty))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
