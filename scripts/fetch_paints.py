"""Сбор каталога красок с Scalemates.

Источник — открытые цветовые ряды Scalemates: код, название, тип, финиш и
HEX-образец. Данные соответствуют официальным каталогам производителей.

Запуск:

    python scripts/fetch_paints.py             # все ряды
    python scripts/fetch_paints.py tamiya      # один ряд
    python scripts/fetch_paints.py --no-hex    # без HEX (быстрее)

Результат: paintguide/seed/paints_extended.json
"""

from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_FILE = ROOT / "paintguide" / "seed" / "paints_extended.json"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}
BASE = "https://www.scalemates.com"

# Наш бренд → (slug ряда на Scalemates, наша линейка, наш тип, фильтр кодов)
RANGES = {
    "tamiya": ("tamiya--655", "xf", "acrylic", r"^(XF|TS|IG)-\d+"),
    "tamiya_lacquer": ("tamiya-color-lacquer-paint--834", "lacquer", "enamel", r"^LP-\d+"),
    "vallejo": ("vallejo-model-color--827", "mc", "acrylic", r"^7[01]\.\d+"),
    "vallejo_gc": ("vallejo-game-color--804", "gc", "acrylic", r"^7[12]\.\d+"),
    "ak": ("ak-3rd-generation--892", "gen", "acrylic", r"^AK\s?11\d{3}$"),
    "ak_afv": ("ak-3rd-generation-afv--976", "afv", "acrylic", r"^AK\s?11\d{3}$"),
    "ak_air": ("ak-3rd-generation-air--978", "air", "acrylic", r"^AK\s?11\d{3}$"),
    "ak_figure": ("ak-3rd-generation-figure--977", "figure", "acrylic", r"^AK\s?11\d{3}$"),
    "ak_legacy": ("ak-interactive--677", "legacy", "acrylic", r"^AK\s?\d{3,4}$"),
    "ak_air_series": ("ak-interactive-air-series--858", "air", "acrylic", r"^AK\s?\d{4}$"),
    "ak_rc": ("ak-real-colors--799", "rc", "acrylic", r"^RCM\d{3}$"),
    "humbrol": ("humbrol--652", "mat", "acrylic", r"^\d{1,3}$"),
    "mrcolor": ("mr-color--657", "cmc", "acrylic", r"^\d{1,3}$|^T-\d+|^B\d+"),
    "mrcolor_wx": ("mr-weathering-color--995", "wx", "acrylic", r"^EWC\d+$"),
    "lifecolor": ("lifecolor--649", "lc", "acrylic", r"^LC\s?\d+$|^BC\s?\d+$"),
    "pacific88": ("pacific88--902", "art", "acrylic", r"^(F-\d+|0\d{2}F|4\d{3})$"),
}

# Ряды, где коды повторяются между брендами, но наборы разные.
BRAND_OF_RANGE = {
    "tamiya": "tamiya",
    "tamiya_lacquer": "tamiya",
    "vallejo": "vallejo",
    "vallejo_gc": "vallejo",
    "ak": "ak",
    "ak_afv": "ak",
    "ak_air": "ak",
    "ak_figure": "ak",
    "ak_legacy": "ak",
    "ak_air_series": "ak",
    "ak_rc": "ak",
    "humbrol": "humbrol",
    "mrcolor": "mrcolor",
    "mrcolor_wx": "mrcolor",
    "lifecolor": "lifecolor",
    "pacific88": "pacific88",
}

# Пресмы, «средства» и инструменты — не краски.
NOT_PAINT = re.compile(
    r"cleaner|thinner|varnish|brush|tool|glue|cement|mask|masking|putty|"
    r"filler|sandpaper|sponge|cloth|tweezer|scalpel|pin vise|airbrush|"
    r"polish|carrier|agent|plasti|dry pastel|paint pot|bottle cap|"
    r"decal|instruction|manual|storage|case|set of|holder|paint handle|"
    r"weathering powder|chipping|oil|grease|pigment powder",
    re.IGNORECASE,
)

HEX_RE = re.compile(r"rgb\.php\?id=([0-9a-fA-F]{6})")
CODE_RE = re.compile(r"class=\"bgb nw\">([^<]{1,30})</span>")
LINK_RE = re.compile(r'href="(/colors/[^"]+)"')


def fetch(url: str, attempts: int = 3) -> str:
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read().decode("utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            time.sleep(1.2 * (attempt + 1))
    return ""


def parse_list(raw: str) -> list[dict]:
    """Разобрать страницу цветового ряда."""
    items: list[dict] = []
    for chunk in raw.split('<div class="ar">')[1:]:
        chunk = chunk.split('</div></div>')[0]
        href = LINK_RE.search(chunk)
        code = CODE_RE.search(chunk)
        if not (href and code):
            continue
        after = chunk.split('</span>', 1)[1] if '</span>' in chunk else ''
        name_match = re.match(r"\s*([^<]{1,90})", after)
        name = html.unescape(name_match.group(1)).strip() if name_match else ""
        if not name:
            continue
        tail = re.findall(r"<div[^>]*>([^<]{1,40})</div>", chunk)
        tail = [html.unescape(t).strip() for t in tail if t.strip()]
        paint_type = ""
        finish = ""
        for value in tail:
            low = value.lower()
            if low in {"acrylic", "enamel", "polyurethane", "metallic", "pigment"}:
                paint_type = low
            elif low in {"matt", "gloss", "satin", "semi gloss", "matte", "flat"}:
                finish = low
        if not paint_type:
            joined = " ".join(tail).lower()
            for candidate in ("polyurethane", "acrylic", "enamel", "metallic"):
                if candidate in joined:
                    paint_type = candidate
                    break
        items.append(
            {
                "href": href.group(1),
                "code": html.unescape(code.group(1)).strip(),
                "name": name,
                "type": paint_type,
                "finish": finish,
            }
        )
    return items


def fetch_hex(href: str) -> str:
    """HEX-образец со страницы отдельного цвета."""
    raw = fetch(BASE + href)
    match = HEX_RE.search(raw)
    return f"#{match.group(1).lower()}" if match else ""


def collect(key: str) -> list[dict]:
    slug, line, default_type, code_pattern = RANGES[key]
    url = f"{BASE}/colors/{slug}"
    raw = fetch(url)
    if not raw:
        print(f"  ! {key}: страница не загрузилась")
        return []
    items = parse_list(raw)
    pattern = re.compile(code_pattern)

    result = []
    for item in items:
        code = re.sub(r"\s+", "", item["code"].strip())
        if not pattern.match(code):
            continue
        if NOT_PAINT.search(item["name"]):
            continue
        if len(item["name"]) < 3:
            continue
        result.append(
            {
                "brand": BRAND_OF_RANGE.get(key, key.split("_")[0]),
                "line": line,
                "code": code,
                "name": item["name"],
                "type": item["type"] or default_type,
                "finish": item["finish"],
                "href": item["href"],
            }
        )
    print(f"  {key}: {len(result)} красок отобрано из {len(items)}")
    return result


def collect_scale75() -> list[dict]:
    """Scale75: свой магазин, коды вида SC-00."""
    handles = (
        "pinturas-para-miniaturas-colores-pinturas-acrilicas",
        "scalecolor-individual",
        "pinturas-para-miniaturas-pack-scalecolor",
    )
    found: dict[str, str] = {}
    for handle in handles:
        for page in range(1, 4):
            url = (
                f"https://scale75.com/collections/{handle}/products.json"
                f"?limit=250&page={page}"
            )
            try:
                request = urllib.request.Request(url, headers=UA)
                raw = urllib.request.urlopen(request, timeout=45).read().decode("utf-8")
                data = json.loads(raw)
            except Exception as error:  # noqa: BLE001
                print(f"  scale75/{handle}: {error}")
                break
            products = data.get("products", []) if isinstance(data, dict) else data
            if not products:
                break
            for product in products:
                title = (product.get("title") or "").strip()
                for variant in product.get("variants") or []:
                    sku = (variant.get("sku") or "").strip()
                    if not sku.upper().startswith("SC-"):
                        continue
                    name = title
                    variant_title = (variant.get("title") or "").strip()
                    # У варианта часто стоит заглушка «Default Title» —
                    # тогда берём название товара.
                    if (
                        variant_title
                        and variant_title.lower() != "default title"
                        and variant_title.upper() != sku.upper()
                    ):
                        name = variant_title
                    found.setdefault(sku, name)
            if len(products) < 250:
                break
            time.sleep(0.4)
    result = [
        {
            "brand": "scale75",
            "line": "sc",
            "code": code,
            "name": name,
            "type": "acrylic",
            "finish": "",
            "href": "",
        }
        for code, name in sorted(found.items())
        if len(name) >= 3
    ]
    print(f"  scale75: {len(result)} красок")
    return result


def main() -> int:
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    no_hex = "--no-hex" in sys.argv
    keys = args or (list(RANGES) + ["scale75"])

    collected: list[dict] = []
    for key in keys:
        if key == "scale75":
            collected.extend(collect_scale75())
            continue
        if key not in RANGES:
            print(f"  ! {key}: нет такого ряда")
            continue
        collected.extend(collect(key))

    if not no_hex:
        print(f"\nЗагружаю HEX для {len(collected)} цветов…")
        done = 0

        def worker(item: dict) -> dict:
            item = dict(item)
            if item.get("href"):
                item["hex"] = fetch_hex(item["href"])
            return item

        with ThreadPoolExecutor(max_workers=12) as pool:
            for item in pool.map(worker, collected):
                collected[done] = item
                done += 1
                if done % 100 == 0:
                    print(f"  {done}/{len(collected)}")

    for item in collected:
        item.pop("href", None)

    # Дописываем к уже сохранённым данным, чтобы не терять другие ряды.
    if OUT_FILE.exists():
        try:
            existing = json.loads(OUT_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = []
        known = {(i["brand"], i["code"], i["name"]) for i in existing}
        added = 0
        for item in collected:
            key = (item["brand"], item["code"], item["name"])
            if key in known:
                continue
            known.add(key)
            existing.append(item)
            added += 1
        if added:
            print(f"\nДописано новых записей: {added}")
        collected = existing

    OUT_FILE.write_text(
        json.dumps(collected, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    with_hex = sum(1 for item in collected if item.get("hex"))
    print(f"\nГотово: {len(collected)} красок, из них с HEX: {with_hex}")
    print(f"Файл: {OUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
