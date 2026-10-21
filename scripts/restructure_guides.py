"""Перевод гайдов на технический вид — по образцу Warhammer Colour.

Задача — привести содержимое руководств к виду, в котором шаг означает одну
технику окраски, а краски внутри шага привязаны к поверхностям:

    Шаг 1 · Грунт        — краска на все поверхности
    Шаг 2 · База         — основной цвет по корпусу, башне, гусницам
    Шаг 3 · Камуфляж     — пятна по корпусу
    Шаг 4 · Тень         — затемнение в стыках
    Шаг 5 · Проливка     — разбавленный тон по корпусу
    Шаг 6 · Высветление  — светлое по верхним плоскостям
    Шаг 7 · Знаки        — опознавательные знаки
    Шаг 8 · Погода       — грязь и пыль
    Шаг 9 · Финиш        — матовый лак

Одни и те же поверхности повторяются от шага к шагу, поэтому по краске
видно, где её искать на модели, — как в приложении, где «White areas»
встречается в Step 2, Step 3, Step 5 и Step 6.

Историческая достоверность сохраняется: переносятся те же краски, те же
практические советы и те же примечания, что были в исходных данных.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from paintguide.seed.mapping import classify, normalise_area  # noqa: E402
from paintguide.seed.techniques import (  # noqa: E402
    DIFFICULTY_TECHNIQUES,
    TECHNIQUES,
    TECHNIQUE_ORDER,
)

# Названия шагов, которые уже описывают технику, — оставляем как есть.
GENERIC_TITLES = {
    "Грунтовка", "База", "Высветление", "Смывка", "Финиш", "Грязь", "Пыль",
    "Звёзды", "Кокарды", "Знаки и номера", "Белые круги", "Белые полосы",
}


def _join(values: list[str]) -> str:
    """Список названий через запятую с «и» перед последним."""
    values = [v for v in values if v]
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    return ", ".join(values[:-1]) + " и " + values[-1]


def _paint_names(entries: list[dict]) -> str:
    return _join([e["name"] for e in entries])


def _zones(entries: list[dict]) -> str:
    seen: list[str] = []
    for entry in entries:
        zone = entry["area"]
        if zone and zone not in seen:
            seen.append(zone)
    return _join(seen)


def convert_steps(variant: dict) -> list[dict]:
    """Перестроить шаги варианта: один шаг — одна техника."""
    # 1. Разложить краски по техникам.
    buckets: dict[str, list[dict]] = defaultdict(list)
    for step in variant.get("steps", []):
        title = step.get("title", "")
        technique = classify(title)
        for entry in step.get("paints", []):
            alias = entry[0]
            code, name = alias
            raw_area = entry[1] if len(entry) > 1 else ""
            note = entry[2] if len(entry) > 2 else ""
            area = normalise_area(raw_area)
            if not area and raw_area:
                # Область оказалась примечанием к смеси.
                note = f"{note} {raw_area}".strip() if note else raw_area
            buckets[technique].append(
                {
                    "code": code,
                    "name": name,
                    "area": area,
                    "note": note,
                    "source_title": title,
                    "source_instruction": step.get("instruction", ""),
                    "source_tip": step.get("tip", ""),
                }
            )

    # 2. Оставить только техники, предусмотренные для этой сложности.
    allowed = DIFFICULTY_TECHNIQUES.get(variant.get("difficulty", "easy"), [])
    if not allowed:
        allowed = TECHNIQUE_ORDER

    steps: list[dict] = []
    for technique in TECHNIQUE_ORDER:
        entries = buckets.get(technique)
        if not entries:
            continue
        if technique not in allowed and technique not in ("base", "primer"):
            continue
        meta = TECHNIQUES[technique]
        paints = []
        for entry in entries:
            paints.append([entry["code"], entry["name"], entry["area"], entry["note"]])
        steps.append(
            {
                "title": meta["title"],
                "instruction": meta["instruction"].format(
                    paints=_paint_names(entries),
                    zones=_zones(entries),
                ),
                "tip": meta["tip"],
                "paints": paints,
            }
        )
    return steps


def main() -> int:
    from paintguide.seed import ALL_GUIDES

    total_steps = 0
    for guide in ALL_GUIDES:
        for variant in guide.get("variants", []):
            before = len(variant.get("steps", []))
            variant["steps"] = convert_steps(variant)
            total_steps += len(variant["steps"])
    print(f"шагов после перестройки: {total_steps}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
