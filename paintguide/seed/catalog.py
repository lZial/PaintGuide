"""Итоговый каталог красок.

Складывает три источника:

* ``paints_extended.json`` — данные, выкачанные с открытых цветовых рядов
  Scalemates: код, название и HEX-образец. Это достоверный источник, он имеет
  приоритет.
* ``paints.py`` — ручной список с русскими пояснениями. Используется, чтобы
  дать названиям описание; при расхождении кодов приоритет у выкачанных данных.
* ``reference.py`` — бренды и линейки.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .paint_colors import derive_hex, describe
from .paints import PAINTS

DATA_FILE = Path(__file__).resolve().parent / "paints_extended.json"

# Тип краски по нашей линейке. Данные о типе у источника местами ошибочны
# (например, у Tamiya в списке встречается «Enamel»), поэтому тип задаём сами.
LINE_TYPES = {
    ("tamiya", "xf"): "acrylic",
    ("tamiya", "ts"): "acrylic",
    ("tamiya", "ig"): "acrylic",
    ("tamiya", "lacquer"): "enamel",
    ("vallejo", "mc"): "acrylic",
    ("vallejo", "gc"): "acrylic",
    ("vallejo", "sf"): "acrylic",
    ("ak", "gen"): "acrylic",
    ("ak", "afv"): "acrylic",
    ("ak", "air"): "acrylic",
    ("ak", "figure"): "acrylic",
    ("ak", "legacy"): "acrylic",
    ("ak", "rc"): "acrylic",
    ("ak", "panzer"): "acrylic",
    ("humbrol", "mat"): "acrylic",
    ("humbrol", "met"): "metallic",
    ("mrcolor", "cmc"): "acrylic",
    ("mrcolor", "super"): "acrylic",
    ("mrcolor", "wx"): "acrylic",
    ("scale75", "sg"): "acrylic",
    ("scale75", "sc"): "acrylic",
    ("lifecolor", "lc"): "acrylic",
    ("pacific88", "art"): "acrylic",
    ("pacific88", "metal"): "metallic",
    ("pacific88", "enamel"): "enamel",
    ("pacific88", "filter"): "acrylic",
}

# Куда попадает краска внутри бренда — по её коду.
BRAND_LINES = {
    "tamiya": (("XF-", "xf"), ("TS-", "ts"), ("IG-", "ig")),
    "pacific88": (("F-", "art"), ("M-", "metal"), ("4", "enamel"), ("0", "filter")),
}

# Тексты линеек, которые встречаются в коде Pacific88.
PACIFIC88_LINES = {
    "F": "art",
    "M": "metal",
    "4": "enamel",
    "0": "filter",
}


def _line_for(brand: str, code: str, default_line: str) -> str:
    if brand == "pacific88":
        prefix = code[0].upper() if code else ""
        return PACIFIC88_LINES.get(prefix, default_line)
    for prefix, line in BRAND_LINES.get(brand, ()):
        if code.upper().startswith(prefix):
            return line
    return default_line


def _descriptions() -> dict[tuple[str, str], str]:
    """Русские пояснения из ручного списка: (бренд, код) → описание."""
    result: dict[tuple[str, str], str] = {}
    for brand, _line, code, _name, _hex, _type, description in PAINTS:
        if description:
            result[(brand, code)] = description
    return result


def _paint_map() -> dict:
    """Таблица соответствий «ручное название → реальный код»."""
    path = Path(__file__).resolve().parent / "paint_map.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("paints", {})


def _manual_entries() -> list[dict]:
    """Ручной список в формате итогового каталога."""
    return [
        {
            "brand": brand,
            "line": line,
            "code": code,
            "name": name,
            "hex": hex_value,
            "type": paint_type,
            "description": description,
        }
        for brand, line, code, name, hex_value, paint_type, description in PAINTS
    ]


def build_catalog() -> list[dict]:
    """Собрать единый каталог красок."""
    descriptions = _descriptions()
    paint_map = _paint_map()
    # Описание привязываем к реальному коду: ручная запись «AK11080 → Dark Brown»
    # после сверки превращается в «AK11080 → Deep Orange», но пояснение остаётся.
    by_real_code: dict[tuple[str, str], str] = {}
    manual_hex: dict[tuple[str, str], str] = {}
    for (brand, line, code, name, hex_value, _type, description) in PAINTS:
        mapped = paint_map.get(f"{code}|{name}")
        target = (brand, mapped["code"]) if mapped else (brand, code)
        if description:
            by_real_code.setdefault(target, description)
        if hex_value and hex_value != "#77786d":
            manual_hex.setdefault(target, hex_value)

    catalog: list[dict] = []
    seen: set[tuple[str, str]] = set()
    positions: dict[tuple[str, str], int] = {}
    source_types: dict[tuple[str, str], str] = {}

    if DATA_FILE.exists():
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        for item in raw:
            brand = item["brand"]
            code = item["code"].strip()
            name = item["name"].strip()
            if not code or not name:
                continue
            line = _line_for(brand, code, item.get("line", ""))
            key = (brand, code)
            expected_type = LINE_TYPES.get((brand, line))
            if key in seen:
                # Одна и та же краска встречается несколько раз: у линеек
                # Tamiya это один и тот же номер в разных фасовках, и образец
                # цвета у них отличается. Берём запись того типа, который
                # свойственен линейке: акрил для XF и TS, а не эмаль.
                existing = catalog[positions[key]]
                if (
                    expected_type
                    and source_types[key] != expected_type
                    and item.get("type") == expected_type
                    and item.get("hex")
                ):
                    existing["hex"] = item["hex"].lower()
                    source_types[key] = expected_type
                elif not existing.get("hex") and item.get("hex"):
                    existing["hex"] = item["hex"].lower()
                continue
            seen.add(key)
            positions[key] = len(catalog)
            source_types[key] = item.get("type") or ""
            hex_value = (item.get("hex") or manual_hex.get(key) or "").lower()
            if not hex_value:
                # Образца нет в источнике — восстанавливаем по названию.
                hex_value = derive_hex(name)
            description = by_real_code.get(key, "")
            if not description:
                description = describe(
                    name,
                    brand=brand,
                    line=line,
                    paint_type=expected_type or item.get("type") or "acrylic",
                )
            catalog.append(
                {
                    "brand": brand,
                    "line": line,
                    "code": code,
                    "name": name,
                    "hex": hex_value,
                    "type": expected_type or item.get("type") or "acrylic",
                    "description": description,
                }
            )

    for entry in _manual_entries():
        key = (entry["brand"], entry["code"])
        if key in seen:
            continue
        seen.add(key)
        if not entry.get("hex") or entry["hex"] == "#77786d":
            entry["hex"] = derive_hex(entry["name"])
        catalog.append(entry)

    return catalog


def catalog_stats() -> dict:
    catalog = build_catalog()
    brands: dict[str, int] = {}
    for item in catalog:
        brands[item["brand"]] = brands.get(item["brand"], 0) + 1
    return {
        "total": len(catalog),
        "with_hex": sum(1 for item in catalog if item.get("hex")),
        "brands": brands,
    }
