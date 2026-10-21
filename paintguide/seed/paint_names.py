"""Название краски для показа пользователю.

Ручные номера красок в гайдах устарели: у AK Interactive их перенумеровали,
а у части линеек Vallejo номера заняты красками Game Color. Поэтому в
гайде цвет называют по-разному — «Red Oxide» по привычке моделиста и
«Primer Red» по каталогу производителя.

Здесь одно имя для обоих случаев: каталожное. Оно совпадает с тем, что
написано на плашке краски, поэтому в тексте шага и в палитре называется
одна и та же краска.
"""

from __future__ import annotations

import json
from pathlib import Path

MAP_FILE = Path(__file__).resolve().parent / "paint_map.json"

_cache: dict | None = None
_hex_cache: dict | None = None


def _paint_map() -> dict:
    global _cache
    if _cache is None:
        if not MAP_FILE.exists():
            _cache = {}
        else:
            data = json.loads(MAP_FILE.read_text(encoding="utf-8"))
            _cache = data.get("paints", {})
    return _cache


def _hex_by_code() -> dict[str, str]:
    """Образец цвета по коду из итогового каталога."""
    global _hex_cache
    if _hex_cache is None:
        from .catalog import build_catalog

        _hex_cache = {}
        for item in build_catalog():
            if item.get("hex"):
                _hex_cache.setdefault(item["code"], item["hex"])
    return _hex_cache


def display_name(code: str, name: str) -> str:
    """Название краски из каталога — как на плашке."""
    if not code:
        return name
    mapped = _paint_map().get(f"{code}|{name}")
    if mapped:
        return mapped["name"]
    return name


def paint_hex(code: str, name: str) -> str:
    """Образец цвета краски из каталога."""
    if not code:
        return ""
    mapped = _paint_map().get(f"{code}|{name}")
    target = mapped["code"] if mapped else code
    return _hex_by_code().get(target, "")


def luminance(hex_value: str) -> float:
    """Яркость цвета: чем темнее краска, тем меньше значение."""
    value = (hex_value or "").lstrip("#")
    if len(value) != 6:
        return 999.0
    red, green, blue = (
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
    )
    return 0.299 * red + 0.587 * green + 0.114 * blue
