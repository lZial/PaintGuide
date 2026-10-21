"""Лестница техник окраски — каркас, по которому собираются все гайды.

За образец взят разбор проекта Warhammer Colour: шаг гайда — это одна
техника окраски, а внутри шага краски привязаны к поверхностям. Одни и те же
поверхности повторяются от шага к шагу: база, тень, проливка и высветление
красят одну и ту же деталь, — поэтому по краске видно, где её искать.

Каждой технике соответствуют:
  * название шага;
  * текст инструкции — что именно делать;
  * практический совет — на что обратить внимание.

Поверхности заданы единым словарём (см. ZONES), чтобы в разных гайдах
одна и та же деталь называлась одинаково.
"""

from __future__ import annotations

# --- Поверхности ------------------------------------------------------------
# Единый словарь: одна и та же деталь во всех гайдах называется одинаково.
ZONES = [
    "Все поверхности",
    "Корпус",
    "Верхние плоскости",
    "Нижние плоскости",
    "Стыки и углубления",
    "Камуфляжные пятна",
    "Кромки деталей",
    "Ходовая часть",
    "Низ и следы",
    "Металл и детали",
    "Дерево и тенты",
    "Оптика и приборы",
    "Знаки",
]

# --- Техники ----------------------------------------------------------------
TECHNIQUES: dict[str, dict[str, str]] = {
    "primer": {
        "title": "Грунт",
        "instruction": "Нанесите {paints} по всей модели в один тонкий слой и дайте высохнуть.",
        "tip": "Грунт даёт адгезию, но не должен забивать рельеф: наносите его тонко.",
    },
    "base": {
        "title": "База",
        "instruction": "Нанесите {paints} {zones} в два-три тонких слоя, каждый полностью просушив.",
        "tip": "Между слоями дайте краске высохнуть 20–30 минут — так не появятся потёки.",
    },
    "camo": {
        "title": "Камуфляж",
        "instruction": "Нанесите {paints} {zones} поверх высохшей базы, мягко разбивая пятна.",
        "tip": "Рисуйте пятна по сухой базе, без чёрного контура: контур появится позже, на этапе тени.",
    },
    "shade": {
        "title": "Тень",
        "instruction": "Затемните {paints} в стыках, углублениях и под выступающими деталями.",
        "tip": "Тень наносите по сухой базе: она должна осесть в рельефе, а не залить плоскости.",
    },
    "wash": {
        "title": "Проливка",
        "instruction": "Разбавьте {paints} водой примерно 1:2 и пройдитесь кистью {zones}.",
        "tip": "Проливку наносят после полного высыхания базы, иначе она размоет краску.",
    },
    "drybrush": {
        "title": "Сухое крашение",
        "instruction": "Сухой кистью с минимумом {paints} пройдитесь {zones}.",
        "tip": "Работайте лёгкими движениями вдоль детали, не набивая краску в углубления.",
    },
    "overbrush": {
        "title": "Овербраш",
        "instruction": "Наложите {paints} {zones} вторым слоем поверх высохшей основы.",
        "tip": "Овербраш выравнивает цвет: слой кладут по сухому, без разводов и пропусков.",
    },
    "tone": {
        "title": "Тонировка",
        "instruction": "Наложите {paints} общим полупрозрачным тоном {zones}, объединяя цвета в один.",
        "tip": "Тон наносите сильно разбавленным: он должен подкрашивать, а не заливать.",
    },
    "highlight": {
        "title": "Высветление",
        "instruction": "Осветлите {paints} по центрам крупных плоскостей.",
        "tip": "Двигайтесь сухой мягкой кистью в одно-два приёма, не заходя в углубления.",
    },
    "edge": {
        "title": "Кромки",
        "instruction": "Подчеркните острые кромки деталей {paints}.",
        "tip": "Кромки работают только на настоящих гранях: плоские участки не трогайте.",
    },
    "markings": {
        "title": "Знаки",
        "instruction": "Нанесите {paints} {zones} по трафарету или по макету.",
        "tip": "Знаки удобнее наносить после матового лака — так краска не впитается в основу.",
    },
    "weathering": {
        "title": "Погодные эффекты",
        "instruction": "Добавьте {paints} {zones} и в нижние части корпуса.",
        "tip": "Грязь скапливается там, где вода стекает вниз: проверьте поддоны и кромки над ними.",
    },
    "finish": {
        "title": "Финиш",
        "instruction": "Закрепите результат матовым лаком, предварительно убрав пыль.",
        "tip": "Матовая плёнка убирает блеск пластика — модель начинает выглядеть окрашенной.",
    },
}

# --- Техники по-английски -----------------------------------------------------
# Названия и тексты шагов переводимы: без них английская версия страницы
# осталась бы русской, хотя интерфейс переведён.
TECHNIQUES_EN: dict[str, dict[str, str]] = {
    "primer": {
        "title": "Primer",
        "instruction": "Apply {paints} over the whole model in one thin coat and let it dry.",
        "tip": "Primer gives adhesion but must not fill the detail: keep the coat thin.",
    },
    "base": {
        "title": "Base coat",
        "instruction": "Apply {paints} {zones} in two or three thin coats, each fully dry.",
        "tip": "Give the paint 20–30 minutes between coats — that keeps runs out of the panels.",
    },
    "camo": {
        "title": "Camouflage",
        "instruction": "Apply {paints} {zones} over the dry base coat, breaking the patches up softly.",
        "tip": "Paint patches on a dry base and keep them free of black outlines: the outline comes later, with the shade.",
    },
    "shade": {
        "title": "Shade",
        "instruction": "Darken {paints} in panel lines, recesses and under overhanging details.",
        "tip": "Shade a dry base coat: it should settle into the relief, not flood the flat panels.",
    },
    "wash": {
        "title": "Wash",
        "instruction": "Dilute {paints} with water at roughly 1:2 and run the brush over {zones}.",
        "tip": "Only wash a fully dry base coat, otherwise it will wash the paint back off.",
    },
    "drybrush": {
        "title": "Drybrush",
        "instruction": "With a dry brush carrying a minimum of {paints}, stroke {zones}.",
        "tip": "Work in light strokes along the detail and do not pack paint into the recesses.",
    },
    "overbrush": {
        "title": "Overbrush",
        "instruction": "Lay {paints} {zones} as a second coat over the dry base.",
        "tip": "The overbrush evens the tone out: lay it on dry paint, without streaks or gaps.",
    },
    "tone": {
        "title": "Glaze",
        "instruction": "Apply {paints} as a single translucent glaze over {zones} to pull the colours together.",
        "tip": "Keep the glaze heavily thinned: it should tint the surface, not cover it.",
    },
    "highlight": {
        "title": "Highlight",
        "instruction": "Lighten {paints} along the centres of the larger panels.",
        "tip": "Use a dry, soft brush in one or two passes and keep out of the recesses.",
    },
    "edge": {
        "title": "Edge highlights",
        "instruction": "Pick out the sharp edges of details with {paints}.",
        "tip": "Edge highlights only work on real edges — leave flat areas alone.",
    },
    "markings": {
        "title": "Markings",
        "instruction": "Apply {paints} {zones} using a stencil or the original artwork.",
        "tip": "Markings go on more easily after a matt varnish, so the paint does not sink into the base.",
    },
    "weathering": {
        "title": "Weathering",
        "instruction": "Add {paints} {zones} and to the lower parts of the hull.",
        "tip": "Dirt collects where water runs down: check the sills and the edges above them.",
    },
    "finish": {
        "title": "Finish",
        "instruction": "Seal the result with matt varnish after removing the dust.",
        "tip": "The matt film takes away the shine of the plastic — the model starts to look painted.",
    },
}

# --- Порядок шагов -----------------------------------------------------------
# Строгая последовательность: грунт → база → камуфляж → тень → проливка →
# сухое крашение → овербраш → тонировка → высветление → кромки → знаки →
# погода → финиш.
TECHNIQUE_ORDER = [
    "primer",
    "base",
    "camo",
    "shade",
    "wash",
    "drybrush",
    "overbrush",
    "tone",
    "highlight",
    "edge",
    "markings",
    "weathering",
    "finish",
]

# Сколько техник показывать на каждом уровне сложности.
DIFFICULTY_TECHNIQUES = {
    "easy": ["primer", "base", "shade", "highlight", "markings", "finish"],
    "medium": [
        "primer", "base", "camo", "shade", "wash", "overbrush", "highlight",
        "markings", "weathering", "finish",
    ],
    "hard": [
        "primer", "base", "camo", "shade", "wash", "drybrush", "overbrush",
        "highlight", "edge", "markings", "weathering", "finish",
    ],
    "expert": [
        "primer", "base", "camo", "shade", "wash", "drybrush", "overbrush",
        "tone", "highlight", "edge", "markings", "weathering", "finish",
    ],
}
