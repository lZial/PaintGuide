"""Перестройка гайдов по образцу Warhammer Colour.

В приложении шаг гайда — это одна техника окраски, а краски внутри шага
привязаны к поверхностям («White areas», «Gunmetal areas»). Одни и те же
поверхности повторяются от шага к шагу: база, тень, проливка и высветление
красят одну и ту же деталь, — поэтому по краске сразу видно, где её искать.

Здесь тот же принцип. Поверхности сведены к единому словарю: корпус,
ходовая часть, металл, дерево, оптика, знаки. Куда именно наносить («в
стыках», «на верхних плоскостях», «на гусницах») — уходит в текст
инструкции, а сама поверхность остаётся одинаковой от шага к шагу.

Порядок шагов задаётся лестницей техник, набор техник — уровнем сложности.
Недостающие техники достраиваются из красок самой машины: проливка — это
разбавленный цвет тени, сухое крашение — светлый цвет сухой кистью,
тонировка — полупрозрачный слой основного цвета, овербраш — основной
цвет по сухому грунту.
"""

from __future__ import annotations

import re

from .mapping import (
    ALL,
    DEFAULT_TECHNIQUE,
    HULL,
    MARKS,
    SURFACE_PHRASE,
    SURFACE_PHRASE_EN,
    classify,
    explicit_title_techniques,
    normalise_area,
    technique_for_area,
    techniques_in_title,
)
from .paint_names import display_name, luminance, paint_hex
from .techniques import (
    DIFFICULTY_TECHNIQUES,
    TECHNIQUES,
    TECHNIQUES_EN,
    TECHNIQUE_ORDER,
)

# --- Подсказки по самой краске ----------------------------------------------
# Пыль, земля и ржавчина — это всегда погодные эффекты, даже если шаг назван
# иначе.
PAINT_TECHNIQUE_RULES: list[tuple[str, str]] = [
    (r"earth|dust|soil|mud|rust|grime|sand$|desert sand|pale sand", "weathering"),
    (r"snow|ice|winter|ozone", "weathering"),
]

# --- Техники, достраиваемые из палитры машины ------------------------------
# Проливка — разбавленный цвет тени, сухое крашение — светлый цвет сухой
# кистью, овербраш — основной цвет по сухому грунту, тонировка —
# полупрозрачный слой основного цвета.
DERIVED_NOTES = {
    "shade": "затемнить в стыках и углублениях",
    "wash": "разбавить 1:2 водой",
    "drybrush": "сухой кистью по верхним плоскостям",
    "overbrush": "второй слой по сухому грунту",
    "tone": "тонкий полупрозрачный слой",
    "edge": "только по острым кромкам",
}


def _paint_list(entries: list[dict]) -> str:
    """Названия красок через запятую с «и» перед последним.

    Названия берутся из каталога, чтобы текст шага и плашки называли одну и
    ту же краску одинаково.
    """
    names: list[str] = []
    for entry in entries:
        name = display_name(entry["code"], entry["name"])
        if name not in names:
            names.append(name)
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " и " + names[-1]


def _zone_phrase(entries: list[dict], english: bool = False) -> str:
    """Куда наносить: перечисление поверхностей с предлогом."""
    table = SURFACE_PHRASE_EN if english else SURFACE_PHRASE
    phrases: list[str] = []
    for entry in entries:
        phrase = table.get(entry["surface"], "")
        if phrase and phrase not in phrases:
            phrases.append(phrase)
    if not phrases:
        return ""
    if len(phrases) == 1:
        return phrases[0]
    if english:
        return ", ".join(phrases[:-1]) + " and " + phrases[-1]
    return ", ".join(phrases[:-1]) + " и " + phrases[-1]


def _group_by_surface(entries: list[dict]) -> list[dict]:
    """Сгруппировать краски по поверхностям, сохранив порядок.

    Одна и та же краска может быть указана для нескольких зон — например,
    красная хинари и кайма звёзд. Зоны сливаются в одну поверхность, и
    краска в списке повторяется. Повтор убираем: для одной поверхности
    краска нужна один раз.
    """
    order: list[str] = []
    grouped: dict[str, list[dict]] = {}
    seen: dict[str, set[tuple[str, str]]] = {}
    for entry in entries:
        surface = entry["surface"]
        if surface not in grouped:
            grouped[surface] = []
            seen[surface] = set()
            order.append(surface)
        key = (entry["code"], entry["name"])
        if key in seen[surface]:
            continue
        seen[surface].add(key)
        grouped[surface].append(entry)
    return [
        {"surface": surface, "paints": grouped[surface]} for surface in order
    ]


def _technique_of(name: str, raw_area: str, explicit: list[str]) -> str:
    """Определить технику одной краски.

    Сначала заголовок шага — он говорит о технике прямо, затем прежняя
    область применения, и только если заголовок молчит, решает сама краска
    (пыль и ржавчина — это погодные эффекты).

    Так песочная основа не уезжает в погодные эффекты из-за слова «песок»
    в названии краски.
    """
    lowered = (name or "").lower()

    if not explicit:
        for pattern, technique in PAINT_TECHNIQUE_RULES:
            if re.search(pattern, lowered):
                return technique

    title_techniques = explicit or [DEFAULT_TECHNIQUE]
    hint = technique_for_area(raw_area)
    if hint and (hint in title_techniques or len(title_techniques) == 1):
        return hint

    technique = classify_of(title_techniques)

    # Финиш — это матовый лак, а лак не краска. Если в шаге «Финиш» всё же
    # перечислены краски, значит это пыль и грязь, которые добавляли в конце
    # окраски: относятся к погодным эффектам.
    if technique == "finish" and not re.search(r"лак|varnish|clear", lowered):
        return "weathering"

    return technique


def classify_of(title_techniques: list[str]) -> str:
    """Основная техника из набора, упомянутого в названии шага."""
    from .mapping import TECHNIQUE_PRIORITY

    for technique in TECHNIQUE_PRIORITY:
        if technique in title_techniques:
            return technique
    return title_techniques[0] if title_techniques else "base"


def _collect(variant: dict) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """Разложить краски варианта по техникам и запомнить исходные шаги."""
    paints: dict[str, list[dict]] = {}
    sources: dict[str, list[dict]] = {}

    for step in variant.get("steps", []):
        title = step.get("title", "")
        title_techniques = techniques_in_title(title)
        explicit = explicit_title_techniques(title)
        for entry in step.get("paints", []):
            code, name = entry[0]
            raw_area = entry[1] if len(entry) > 1 else ""
            note = entry[2] if len(entry) > 2 else ""
            surface = normalise_area(raw_area)
            technique = _technique_of(name, raw_area, explicit)
            paints.setdefault(technique, []).append(
                {
                    "code": code,
                    "name": name,
                    "surface": surface,
                    "note": note,
                    "raw_area": raw_area,
                }
            )
            sources.setdefault(technique, []).append(
                {
                    "title": title,
                    "instruction": step.get("instruction", ""),
                    "tip": step.get("tip", ""),
                }
            )

    # Краски без области (например, «добавляется в базу») относятся к той
    # же поверхности, что и соседние краски шага.
    for entries in paints.values():
        known = [e["surface"] for e in entries if e["raw_area"]]
        if not known:
            continue
        dominant = max(set(known), key=known.count)
        for entry in entries:
            if not entry["raw_area"]:
                entry["surface"] = dominant

    # «Все поверхности» — это грунт и финиш: вся модель целиком. Окраска
    # всей машины одним цветом относится к корпусу, чтобы поверхность
    # повторялась от шага к шагу.
    for technique, entries in paints.items():
        if technique in ("primer", "finish"):
            for entry in entries:
                entry["surface"] = ALL
            continue
        for entry in entries:
            if entry["surface"] == ALL:
                entry["surface"] = HULL

    return paints, sources


def _make_step(technique: str, entries: list[dict], tip: str) -> dict:
    """Собрать шаг по технике."""
    meta = TECHNIQUES[technique]
    paints: list[list] = []
    for group in _group_by_surface(entries):
        for entry in group["paints"]:
            paints.append(
                [entry["code"], entry["name"], group["surface"], entry["note"]]
            )

    instruction = meta["instruction"].format(
        paints=_paint_list(entries),
        zones=_zone_phrase(entries),
    )
    step = {
        "title": meta["title"],
        "instruction": instruction,
        "tip": tip or meta["tip"],
        "paints": paints,
    }

    # Английская версия шага: тот же текст техники с теми же подстановками.
    english = TECHNIQUES_EN.get(technique)
    if english:
        step["title_en"] = english["title"]
        step["instruction_en"] = english["instruction"].format(
            paints=_paint_list(entries),
            zones=_zone_phrase(entries, english=True),
        )
        # Совет из исходных данных написан по-русски, поэтому в
        # английской версии берём совет самой техники.
        step["tip_en"] = english["tip"]
    return step


def _derive(technique: str, variant: dict, paints: dict) -> list[dict] | None:
    """Достроить технику красками самой машины."""
    easy = variant.get("difficulty", "easy") == "easy"

    def first_of(key: str) -> dict | None:
        items = paints.get(key) or []
        return items[0] if items else None

    def surfaces_of(key: str) -> list[str]:
        result: list[str] = []
        for entry in paints.get(key) or []:
            if entry["surface"] not in result:
                result.append(entry["surface"])
        return result

    def darkest() -> dict | None:
        """Самая тёмная краска палитры — ею затемняют углубления.

        Выбираем по образцу цвета, а не по слову в названии: тёмно-зелёная
        база темнее светлого песка, даже если «Sand» не похоже на «Dark».
        """
        best = None
        best_light = 999.0
        for key in TECHNIQUE_ORDER:
            for entry in paints.get(key) or []:
                value = luminance(paint_hex(entry["code"], entry["name"]))
                if value < best_light:
                    best_light = value
                    best = entry
        return best

    if technique == "shade":
        # Тень — тёмный цвет в стыках и углублениях. Берём самую тёмную
        # краску палитры: смывка может быть и охристой, а затемнять ею нельзя.
        source = darkest() or first_of("wash")
        if not source:
            return None
        # Тенять базовой краской бессмысленно: если темнее неё в палитре
        # ничего нет, шага тени не будет.
        base_colors = {
            (entry["code"], entry["name"]) for entry in paints.get("base") or []
        }
        if (source["code"], source["name"]) in base_colors:
            return None
        surfaces = surfaces_of("base") or [HULL]
        return [
            {
                "code": source["code"],
                "name": source["name"],
                "surface": surface,
                "note": DERIVED_NOTES["shade"],
                "raw_area": surface,
            }
            for surface in surfaces
        ]

    if technique == "wash":
        if easy:
            return None
        shade = first_of("shade") or darkest()
        if not shade or not surfaces_of("base"):
            return None
        return [
            {
                "code": shade["code"],
                "name": shade["name"],
                "surface": surface,
                "note": DERIVED_NOTES["wash"],
                "raw_area": surface,
            }
            for surface in surfaces_of("base")
        ]

    if technique == "drybrush":
        highlight = first_of("highlight")
        if not highlight:
            return None
        return [
            {
                "code": highlight["code"],
                "name": highlight["name"],
                "surface": HULL,
                "note": DERIVED_NOTES["drybrush"],
                "raw_area": HULL,
            }
        ]

    if technique == "tone":
        base = first_of("base")
        if not base or not surfaces_of("base"):
            return None
        return [
            {
                "code": base["code"],
                "name": base["name"],
                "surface": surface,
                "note": DERIVED_NOTES["tone"],
                "raw_area": surface,
            }
            for surface in surfaces_of("base")
        ]

    if technique == "edge":
        highlight = first_of("highlight")
        if not highlight:
            return None
        return [
            {
                "code": highlight["code"],
                "name": highlight["name"],
                "surface": HULL,
                "note": DERIVED_NOTES["edge"],
                "raw_area": HULL,
            }
        ]

    if technique == "overbrush":
        # Овербраш — второй слой основного цвета по сухому грунту: он
        # выравнивает тон и закрывает пропуски первого слоя.
        base = first_of("base")
        if not base or not surfaces_of("base"):
            return None
        return [
            {
                "code": base["code"],
                "name": base["name"],
                "surface": surface,
                "note": DERIVED_NOTES["overbrush"],
                "raw_area": surface,
            }
            for surface in surfaces_of("base")
        ]

    return None


def restructure(variant: dict) -> list[dict]:
    """Перестроить шаги варианта в лестницу техник."""
    paints, sources = _collect(variant)
    allowed = DIFFICULTY_TECHNIQUES.get(
        variant.get("difficulty", "easy"), TECHNIQUE_ORDER
    )

    steps: list[dict] = []
    for technique in TECHNIQUE_ORDER:
        if technique not in allowed:
            continue
        entries = paints.get(technique)
        tip = ""
        for source in sources.get(technique, []):
            if source.get("tip"):
                tip = source["tip"]
                break

        if not entries:
            entries = _derive(technique, variant, paints) or []
            if not entries:
                continue
            tip = ""

        steps.append(_make_step(technique, entries, tip))

    # Финиш: матовый лак — отдельный шаг без красок.
    if "finish" in allowed and not any(
        step["title"] == TECHNIQUES["finish"]["title"] for step in steps
    ):
        steps.append(
            {
                "title": TECHNIQUES["finish"]["title"],
                "instruction": TECHNIQUES["finish"]["instruction"],
                "tip": TECHNIQUES["finish"]["tip"],
                "paints": [],
            }
        )

    return steps
