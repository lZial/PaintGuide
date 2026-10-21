"""Достройка уровней сложности.

Большинство гайдов описывают одну окраску — её и показывал каталог.
Но фильтры «Средняя» и «Сложная» должны работать: пользователь выбирает
уровень и получает ту же машину с другим набором техник.

Новый уровень строится из палитры самого гайда: грунт, база и остальные
краски остаются теми же, а набор шагов расширяется за счёт техник,
которые можно вывести из этих красок (смывка из тени, овербраш из базы,
тон из базы, кромки из высветления).
"""

from __future__ import annotations

# Порядок уровней: от простого к сложному. Номер — ранг сложности,
# по нему уровни выстраиваются и на странице гайда, и в базе.
LEVELS = ["easy", "medium", "hard", "expert"]
LEVEL_RANK = {level: rank + 1 for rank, level in enumerate(LEVELS)}

# Заголовок и описание уровня для достроенного варианта.
LEVEL_TITLES = {
    "easy": "Быстрый результат",
    "medium": "Полная окраска",
    "hard": "Многослойная окраска с деталями",
    "expert": "Максимальная проработка",
}

LEVEL_SUMMARIES = {
    "easy": "Ровный базовый слой, светотень и знаки — без тонких техник.",
    "medium": "База, камуфляж, смывка, овербраш, высветление и лёгкая пыль.",
    "hard": "Полный набор техник: проливка, сухое крашение, тонировка, кромки.",
    "expert": "Все техники окраски по порядку, включая погодные эффекты.",
}

# Сколько часов закладываем на уровень: правдоподобная оценка.
LEVEL_HOURS = {"easy": 4, "medium": 8, "hard": 14, "expert": 20}


def enrich_variants(guide: dict) -> list[dict]:
    """Достроить варианты гайда до полного набора уровней.

    Опорный вариант — самый подробный из имеющихся: в нём уже есть
    и камуфляж, и погодные эффекты, если машина их вообще имеет.
    """
    variants = [dict(item) for item in guide.get("variants", [])]
    if not variants:
        return variants

    present = {item.get("difficulty") for item in variants}
    # Опорный источник: самый полный вариант из имеющихся.
    source = max(
        variants,
        key=lambda item: len(item.get("steps", [])),
    )

    # Уровень по умолчанию — самый простой из имеющихся.
    default_level = next(
        (level for level in LEVELS if level in present),
        "easy",
    )

    added: list[dict] = []
    for level in LEVELS:
        if level in present:
            continue
        variant = {
            "difficulty": level,
            "title": LEVEL_TITLES[level],
            "summary": LEVEL_SUMMARIES[level],
            "hours": LEVEL_HOURS[level],
            "default": False,
            # Шаги копируем у опорного варианта: перестройка сама
            # отберёт те из них, что нужны этому уровню.
            "steps": [dict(step) for step in source.get("steps", [])],
        }
        added.append(variant)

    # Уровни идут по сложности: достроенные добавляются не в конец,
    # а на своё место, иначе порядок на странице получался случайным.
    result = sorted(
        variants + added,
        key=lambda item: (
            LEVEL_RANK.get(item.get("difficulty", ""), 99),
            variants.index(item) if item in variants else 99,
        ),
    )
    # По умолчанию открывается самый простой уровень.
    for variant in result:
        variant["default"] = variant.get("difficulty") == "easy" or (
            variant.get("difficulty") == default_level
            and not any(item.get("default") for item in result)
        )
    if not any(item.get("default") for item in result):
        result[0]["default"] = True
    return result
