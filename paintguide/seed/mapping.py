"""Классификация красок: техника окраски и поверхность.

За образец взят Warhammer Colour: у каждой краски указано, к какой группе
деталей («White areas», «Gunmetal areas») она относится, и одна и та же
группа повторяется в разных шагах. Здесь то же самое: краска привязана к
поверхности (корпус, ходовая часть, металл, дерево, оптика, знаки), а
техника определяется по тому, как краска наносится.

Поверхности
    «Все поверхности» — грунт и финиш: вся модель целиком.
    «Корпус» — корпус, башня, рубка, верхние и нижние плоскости.
    «Ходовая часть» — гусницы, катки, колёса, рама.
    «Металл» — ствол, люки, металлическая оснастка.
    «Дерево» — ящики ЗИП, брезентовые тенты.
    «Оптика» — смотровые приборы, стёкла, фары.
    «Знаки» — звёзды, кокарды, номера, полосы.
"""

from __future__ import annotations

import re

# --- Поверхности ------------------------------------------------------------
ALL = "Все поверхности"
HULL = "Корпус"
RUNNING = "Ходовая часть"
METAL = "Металл"
WOOD = "Дерево"
GLASS = "Оптика"
MARKS = "Знаки"

SURFACES = [ALL, HULL, RUNNING, METAL, WOOD, GLASS, MARKS]

# Как поверхность называется в тексте шага.
SURFACE_PHRASE = {
    ALL: "по всей модели",
    HULL: "на корпусе и башне",
    RUNNING: "на ходовой части",
    METAL: "на металлических деталях",
    WOOD: "на дереве и тенте",
    GLASS: "на оптике",
    MARKS: "на опознавательных знаках",
}

# Тот же список по-английски — для английской версии страницы.
SURFACE_PHRASE_EN = {
    ALL: "over the whole model",
    HULL: "on the hull and turret",
    RUNNING: "on the running gear",
    METAL: "on the metal fittings",
    WOOD: "on the wood and canvas",
    GLASS: "on the optics",
    MARKS: "on the markings",
}

# Название поверхности в интерфейсе.
SURFACE_LABELS_EN = {
    ALL: "All surfaces",
    HULL: "Hull",
    RUNNING: "Running gear",
    METAL: "Metal",
    WOOD: "Wood",
    GLASS: "Optics",
    MARKS: "Markings",
}

# Порядок проверки: первое совпадение и определяет поверхность.
AREA_SURFACE_RULES: list[tuple[str, str]] = [
    (r"знаки|звёзд|звезд|кокард|хинари|номер|контур|полос|кайм|круг|отметин"
     r"|треугольник|ор[её]?л|крест|надпис|эмблем|шеврон",
     MARKS),
    (r"смотров|прибор|стекл|фар|зрк|лобов|оптик", GLASS),
    (r"дерев|тент|брезент|ящик|запчаст", WOOD),
    (r"ствол|оруди|стволь|металл|створк|труб|люк", METAL),
    (r"гус|катк|кол[её]с|шины|ходов|рама|бампер|под крыль|низкие листы",
     RUNNING),
    (r"^все области$|^вся модель$|^все$", ALL),
    (r"^.*$", HULL),
]

# --- Техники ----------------------------------------------------------------
# По названию шага: какие техники в нём упомянуты.
TITLE_TECHNIQUES: list[tuple[str, str]] = [
    (r"грунт|подложк", "primer"),
    (r"финиш|лак", "finish"),
    (r"знак|звёзд|звезд|кокард|хинари|номер|полос|кайм|контур|круг|отметин",
     "markings"),
    (r"выветрив|сухое|драйбраш", "drybrush"),
    (r"овербраш|overbrush|перекрыт", "overbrush"),
    (r"тонир|tone", "tone"),
    (r"смывк|пролив|wash", "wash"),
    (r"тень|тен[ий]|затень|зат[её]к|затемн", "shade"),
    (r"гряз|пыл|след|потёк|масл|снег|налед|ржав|скол|отсло|зимн|побелк|weather",
     "weathering"),
    (r"высветл|подсвет|highlight|кант|кромк", "highlight"),
    (r"пятн|участ|разброс|камуфляж|4ф", "camo"),
    (r"баз|основ|olive drab|khaki|панцирный|тёмно-жёлт|тёмно-желт|хаки-зел|хаки-зел|двухт|верхн|нижн|светлый низ|тёмный верх|темный верх|тёмн|темн",
     "base"),
]

# По прежней области применения: какая техника подразумевается.
# Прямые указания («тени», «смывка») важнее прочих; стыки и углубления
# достаются смывке — их затемняют разбавленным цветом.
AREA_TECHNIQUE_RULES: list[tuple[str, str]] = [
    (r"тень|тен[ий]|затень|зат[её]к|затемн", "shade"),
    (r"смывк|пролив|wash", "wash"),
    (r"знаки|звёзд|звезд|кокард|хинари|номер|контур|полос|кайм|круг|отметин",
     "markings"),
    (r"пятн|участ|разброс|камуфляж|4ф|прямоугольник", "camo"),
    (r"высветл|осветл|подсвет", "highlight"),
    (r"гряз|пыл|след|масл|снег|налед|ржав|скол|отсло|зимн|побелк|очаг|под[её]к|пот[её]к",
     "weathering"),
    (r"стик|шв|углублен|под башн|под навес|складк|тент", "wash"),
    (r"^$", "base"),
]

# Техника по умолчанию, если ничего не подошло.
DEFAULT_TECHNIQUE = "base"

# Приоритет техник, когда название шага упоминает сразу несколько.
TECHNIQUE_PRIORITY = [
    "primer", "camo", "markings", "highlight", "shade", "wash", "drybrush",
    "overbrush", "tone", "weathering", "base", "finish",
]


def normalise_area(area: str) -> str:
    """Привести прежнюю формулировку области к поверхности."""
    text = (area or "").strip().lower()
    for pattern, surface in AREA_SURFACE_RULES:
        if re.search(pattern, text):
            return surface
    return HULL


def explicit_title_techniques(title: str) -> list[str]:
    """Техники, прямо названные в заголовке шага.

    Пустой список значит, что заголовок ничего не сообщает о технике: тогда
    решение принимается по самой краске и по области нанесения.
    """
    text = (title or "").lower()
    found: list[str] = []
    for pattern, technique in TITLE_TECHNIQUES:
        if re.search(pattern, text) and technique not in found:
            found.append(technique)
    # «Тёмный верх» — это база, а не тон: тёмный цвет красится сплошным слоем.
    if "base" in found and len(found) > 1:
        found.remove("base")
    return found


def techniques_in_title(title: str) -> list[str]:
    """Какие техники упомянуты в названии шага."""
    return explicit_title_techniques(title) or [DEFAULT_TECHNIQUE]


def classify(title: str) -> str:
    """Основная техника шага по его названию."""
    found = techniques_in_title(title)
    for technique in TECHNIQUE_PRIORITY:
        if technique in found:
            return technique
    return found[0]


def technique_for_area(area: str) -> str | None:
    """Техника, подсказанная прежней областью применения."""
    text = (area or "").strip().lower()
    for pattern, technique in AREA_TECHNIQUE_RULES:
        if re.search(pattern, text):
            return technique
    return None
