"""Загрузка обложек по готовому плану.

План — это список «гайд → файл Commons», собранный заранее. Метаданные
файлов запрашиваются одним пакетом (до 40 названий за раз), а сами
картинки тянутся напрямую: так на каждый гайд приходится один запрос
к хранилищу, а не десяток.

Запуск:  python scripts/download_plan.py [план.json]
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "paintguide"
OUT_DIR = PACKAGE / "static" / "img" / "vehicles"
DATA_FILE = PACKAGE / "seed" / "covers.json"
DEFAULT_PLAN = Path(
    r"C:\Users\shist\AppData\Local\Temp\opencode\cover_plan.json"
)

API = "https://commons.wikimedia.org/w/api.php"
FILEPATH = "https://commons.wikimedia.org/wiki/Special:FilePath/"
USER_AGENT = (
    "PaintGuideBot/1.0 (https://example.org/paintguide; paintguide@example.com) "
    "python-urllib/3"
)
DOWNLOAD_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
THUMB_WIDTH = 960
# Пауза между файлами: хранилище Wikimedia отказывает при частых
# обращениях, и после отказа приходится ждать минутами.
DELAY = 60.0


def api_get(params: dict, attempts: int = 6) -> dict:
    """Запрос к API с повторами: при 429 ждём подольше."""
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
            time.sleep(60.0 if "429" in str(error) else 5.0)
    raise RuntimeError(f"API не ответил: {last}")


def fetch_metadata(titles: list[str]) -> dict[str, dict]:
    """Метаданные файлов пачками по сорок названий."""
    result: dict[str, dict] = {}
    for start in range(0, len(titles), 40):
        chunk = titles[start:start + 40]
        data = api_get(
            {
                "action": "query",
                "titles": "|".join(chunk),
                "prop": "imageinfo",
                "iiprop": "url|extmetadata|size",
                "iiurlwidth": THUMB_WIDTH,
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
                import re

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
                "thumb_url": info.get("thumburl", ""),
                "url": info.get("url", ""),
                "width": info.get("width", 0),
                "height": info.get("height", 0),
            }
        time.sleep(3.0)
    return result


def thumb_url(original_url: str, width: int = THUMB_WIDTH) -> str:
    """Собрать ссылку на миниатюру по адресу оригинала.

    API отдаёт готовую миниатюру, но если оригинал меньше запрошенного
    размера — возвращает сам оригинал. Он тяжёлый, и хранилище начинает
    отказывать. Поэтому миниатюру собираем сами, размером 960.
    """
    if not original_url:
        return ""
    marker = "/wikipedia/commons/"
    if marker not in original_url:
        return ""
    head, _, tail = original_url.partition(marker)
    name = tail.rsplit("/", 1)[-1]
    if not name:
        return ""
    folder = tail.rsplit("/", 1)[0]
    return f"{head}{marker}thumb/{folder}/{width}px-{name}"


def download(item: dict, target: Path) -> bool:
    """Скачать файл.

    Хранилище Wikimedia отвечает отказом при частых обращениях, поэтому
    берём ровно один адрес — миниатюру нужного размера — и при отказе
    ждём долго, а не пробуем следующий адрес сразу.
    """
    title = item["title"].removeprefix("File:")
    quoted = urllib.parse.quote(title.replace(" ", "_"))
    candidates = [
        thumb_url(item.get("url", "")),
        item.get("thumb_url", ""),
        f"{FILEPATH}{quoted}?width={THUMB_WIDTH}",
    ]
    payload = b""
    content_type = "image/jpeg"
    for url in candidates:
        if not url:
            continue
        for attempt in range(3):
            request = urllib.request.Request(
                url,
                headers={"User-Agent": DOWNLOAD_UA, "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"},
            )
            try:
                with urllib.request.urlopen(request, timeout=90) as response:
                    payload = response.read()
                    content_type = response.headers.get("Content-Type", "image/jpeg")
                if len(payload) > 4096:
                    break
            except Exception as error:  # noqa: BLE001
                if "429" in str(error):
                    # Хранилище отказывает по частоте. По наблюдениям
                    # блокировка сходит минут через десять, поэтому
                    # ждём сразу долго, а не долбим почаще.
                    print(f"      ! отказ по частоте, пауза {600} с", flush=True)
                    time.sleep(600)
                    continue
                print(f"      ! {url[-40:]}: {str(error)[:50]}")
                break
        if len(payload) > 4096:
            break
        time.sleep(2.0)

    if len(payload) < 4096:
        return False
    extension = ".png" if "png" in content_type else ".jpg"
    target = target.with_suffix(extension)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return True


def machine_matches(slug: str, info: dict, article: str, plan_categories: str = "") -> bool:
    """Проверить, что файл относится к нужной машине.

    Статью с похожим названием легко спутать: «K-33» — и финский танк, и
    класс польских подводных лодок, а «SA 201» — и шведский танкет, и
    самолёт. Категории Commons в этом случае надёжнее заголовка.
    """
    sys.path.insert(0, str(ROOT))
    from scripts.fetch_covers import (
        _names_for,
        _tokens,
        category_says_machine,
        category_says_vehicle,
        wrong_vehicle,
    )

    categories = info.get("categories") or ""
    if not categories:
        categories = plan_categories or ""
    names = _names_for(slug)
    if categories and (
        category_says_machine(names, {"categories": categories})
        or category_says_vehicle(slug, {"categories": categories})
    ):
        return True

    title = (info.get("title") or "").removeprefix("File:")
    normalized = _normalize(title)

    # На фотографии может быть другая машина из каталога: «T-55» вместо
    # «T-54», «Strv 122» вместо «Strv 106».
    if wrong_vehicle(slug, {"title": title}):
        return False

    for name in names:
        for token in _tokens(name):
            if token and token in normalized:
                return True

    # Обозначение может состоять из букв и чисел: «105 K/13» у орудия
    # называется «105mm M1913». Сверяемся по числам — отдельным числом,
    # иначе «13» нашлось бы внутри «1913».
    import re as _re

    digits: set[str] = set()
    for name in names:
        for part in _re.findall(r"\d{2,}", _normalize(name)):
            digits.add(part)
    if digits:
        numbers_in_title = set(_re.findall(r"\d{2,}", normalized))
        if digits <= numbers_in_title:
            return True

    # Категорий нет — сверяемся с названием статьи.
    for word in (article or "").lower().replace("-", " ").split():
        if len(word) >= 4 and word in title.replace("_", " ").lower():
            return True
    return False


def _normalize(value: str) -> str:
    import re

    return re.sub(r"[^a-z0-9а-яё]+", "", (value or "").lower())


def main() -> int:
    plan_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PLAN
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    covers: dict = {}
    if DATA_FILE.exists():
        covers = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    todo = {
        slug: item for slug, item in plan.items()
        if slug not in covers or not (PACKAGE / covers[slug]["file"]).exists()
    }
    print(f"в плане {len(plan)}, к загрузке {len(todo)}")

    titles = [
        "File:" + urllib.parse.unquote(item["file"]) for item in todo.values()
    ]
    unique = list(dict.fromkeys(titles))
    print(f"запрашиваем метаданные {len(unique)} файлов")
    metadata = fetch_metadata(unique)

    done = 0
    failed: list[str] = []
    # API нормализует подчёркивания в пробелы, поэтому ищем по обоим
    # вариантам написания.
    lookup = {title.replace("_", " "): value for title, value in metadata.items()}
    for slug, item in todo.items():
        key = "File:" + urllib.parse.unquote(item["file"])
        info = metadata.get(key) or lookup.get(key.replace("_", " "))
        if not info:
            print(f"  ! {slug}: нет метаданных для {key}")
            continue
        if not machine_matches(
            slug, info, item.get("source", ""), item.get("categories", "")
        ):
            print(f"  ! {slug}: файл не про эту машину — {info['title'][:50]}")
            continue
        target = OUT_DIR / f"{slug}.jpg"
        if download(info, target):
            saved = target if target.exists() else target.with_suffix(".png")
            covers[slug] = {
                "file": f"static/img/vehicles/{saved.name}",
                "title": info["title"],
                "author": info["author"][:200],
                "license": info["license"][:60],
                "license_url": info["license_url"][:300],
                "source": info["source"][:500],
                "kind": "vehicle",
                "scale": "",
            }
            done += 1
            print(f"  > {slug}: {info['title'][:56]} [{info['license']}]")
            temporary = DATA_FILE.with_suffix(".json.tmp")
            temporary.write_text(
                json.dumps(covers, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            temporary.replace(DATA_FILE)
        else:
            print(f"  ! {slug}: не скачалось {key}")
            failed.append(slug)
        time.sleep(DELAY)

    # Второй круг по неудачным: хранилище к этому времени отпускает.
    if failed:
        print(f"\n=== повтор {len(failed)} файлов ===")
        time.sleep(120)
        for slug in failed:
            item = todo[slug]
            key = "File:" + urllib.parse.unquote(item["file"])
            info = metadata.get(key) or lookup.get(key.replace("_", " "))
            if not info:
                continue
            target = OUT_DIR / f"{slug}.jpg"
            if download(info, target):
                saved = target if target.exists() else target.with_suffix(".png")
                covers[slug] = {
                    "file": f"static/img/vehicles/{saved.name}",
                    "title": info["title"],
                    "author": info["author"][:200],
                    "license": info["license"][:60],
                    "license_url": info["license_url"][:300],
                    "source": info["source"][:500],
                    "kind": "vehicle",
                    "scale": "",
                }
                done += 1
                print(f"  > {slug}: {info['title'][:56]} [{info['license']}]")
                temporary = DATA_FILE.with_suffix(".json.tmp")
                temporary.write_text(
                    json.dumps(covers, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                temporary.replace(DATA_FILE)
            time.sleep(DELAY)

    print(f"\nскачано: {done} из {len(todo)}; всего обложек: {len(covers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
