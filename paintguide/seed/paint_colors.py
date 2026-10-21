"""Образец цвета краски, которого нет в каталоге.

У 622 красок из 3009 нет HEX-образца: у наборов красок он и не может
быть один, а у части одиночных цветов источник его не отдал.

Здесь цвет восстанавливается по названию: «Dark Olive Green» — тёмно-
оливковый зелёный. Наборы получают нейтральный серый, но всё равно
получают образец: в палитре и в подсказках цвет виден сразу.
"""

from __future__ import annotations

# Базовые цвета: слово → образец.
BASE_COLORS: dict[str, str] = {
    "red": "#a02c22",
    "crimson": "#8e2230",
    "scarlet": "#a32b22",
    "maroon": "#5c2b25",
    "burgundy": "#4a1f26",
    "orange": "#c06a1e",
    "amber": "#c68a1c",
    "ochre": "#b07830",
    "yellow": "#c8b022",
    "cream": "#ded3b0",
    "ivory": "#e2dcc6",
    "straw": "#c9b26a",
    "khaki": "#8a7a4e",
    "sand": "#c2b280",
    "buff": "#cbb98a",
    "green": "#4f6b3a",
    "olive": "#5a6136",
    "dark green": "#39482c",
    "light green": "#8ba36a",
    "pale green": "#a9bb8e",
    "mint": "#a8c4a0",
    "forest": "#2f4429",
    "emerald": "#2e6b46",
    "turquoise": "#2f7d80",
    "teal": "#2c5f63",
    "cyan": "#3f8f96",
    "blue": "#2f4f78",
    "navy": "#23324f",
    "sky blue": "#7fa8c4",
    "grey": "#7c7d78",
    "gray": "#7c7d78",
    "black": "#1c1c1c",
    "white": "#e8e6de",
    "brown": "#6b4a2e",
    "dark brown": "#452e1c",
    "light brown": "#9a7348",
    "tan": "#b08a5c",
    "chocolate": "#4f3524",
    "rust": "#8a3f22",
    "copper": "#a05a32",
    "bronze": "#8a6236",
    "gold": "#c19a35",
    "silver": "#b8bcc0",
    "steel": "#6e7378",
    "gunmetal": "#4a4e52",
    "purple": "#5c3a6b",
    "violet": "#6a4a80",
    "magenta": "#8c2f5c",
    "pink": "#d59aa4",
    "flesh": "#c9a487",
    "skin": "#d3ae8d",
    "peach": "#e0b093",
    "umber": "#6a4a34",
    "beige": "#c8b89a",
    "sepia": "#6b5a45",
    "desert": "#c3b189",
    "camo": "#5a6046",
    "camouflage": "#5a6046",
    "wood": "#7a5a38",
    "earth": "#7a5f42",
    "soil": "#5c4a38",
    "shadow": "#3a3a3c",
    "black primer": "#1a1a1a",
    "primer": "#8a4030",
    "rust red": "#8a3f22",
    "sun": "#d8c53a",
    "lunar": "#b9bcc2",
    "star": "#d8d4c2",
    "winter": "#c9ccd2",
    "zimmerit": "#5d6b45",
    "net": "#4e5a3a",
    "web": "#6b6450",
    "signal": "#b8352c",
    "rail": "#6a625a",
    "wheel": "#2a2a2c",
    "track": "#35322c",
    "pinion": "#4a4640",
}

# Модификаторы тона.
MODIFIERS: dict[str, float] = {
    "dark": 0.55,
    "deep": 0.7,
    "shadow": 0.7,
    "light": 1.45,
    "pale": 1.6,
    "medium": 1.0,
}

NEUTRAL = "#7c7d78"

# Как цвет звучит по-русски.
COLOR_NAMES: dict[str, str] = {
    "red": "красный",
    "crimson": "малиновый",
    "scarlet": "алый",
    "maroon": "бордовый",
    "burgundy": "винный",
    "orange": "оранжевый",
    "amber": "янтарный",
    "ochre": "охристый",
    "yellow": "жёлтый",
    "cream": "кремовый",
    "ivory": "цвета слоновой кости",
    "straw": "соломенный",
    "khaki": "хаки",
    "sand": "песочный",
    "buff": "светло-бурый",
    "green": "зелёный",
    "olive": "оливковый",
    "dark green": "тёмно-зелёный",
    "light green": "светло-зелёный",
    "pale green": "бледно-зелёный",
    "mint": "мятный",
    "forest": "тёмно-хвойный",
    "emerald": "изумрудный",
    "turquoise": "бирюзово-зелёный",
    "teal": "сине-зелёный",
    "cyan": "голубой",
    "blue": "синий",
    "sky": "небесно-голубой",
    "azure": "лазурный",
    "navy": "тёмно-синий",
    "sky blue": "небесно-голубой",
    "grey": "серый",
    "gray": "серый",
    "black": "чёрный",
    "white": "белый",
    "brown": "коричневый",
    "dark brown": "тёмно-коричневый",
    "light brown": "светло-коричневый",
    "tan": "рыжевато-коричневый",
    "chocolate": "шоколадный",
    "rust": "ржавый",
    "copper": "медный",
    "bronze": "бронзовый",
    "gold": "золотой",
    "silver": "серебристый",
    "steel": "стальной",
    "gunmetal": "тёмно-серый металлик",
    "purple": "фиолетовый",
    "violet": "сиреневый",
    "magenta": "пурпурный",
    "pink": "розовый",
    "rose": "розово-красный",
    "salmon rose": "розово-персиковый",
    "lavender": "сиренево-голубой",
    "stone": "каменно-серый",
    "mud": "грязно-коричневый",
    "canvas": "холщовый",
    "flesh": "телесный",
    "skin": "телесный",
    "peach": "персиковый",
    "umber": "умбровый",
    "beige": "бежевый",
    "sepia": "сепийный",
    "desert": "пустынный",
    "camo": "камуфляжный",
    "camouflage": "камуфляжный",
    "wood": "деревянный",
    "earth": "землистый",
    "soil": "землистый",
    "shadow": "теневой",
    "black primer": "чёрный грунт",
    "primer": "грунтово-красный",
    "sun": "солнечно-жёлтый",
    "lunar": "лунно-белый",
    "star": "звёздно-белый",
    "winter": "зимне-белый",
    "zimmerit": "защитный зелёный",
    "net": "сетчатый зелёный",
    "web": "паутинный",
    "signal": "сигнальный красный",
    "rail": "рельсовый",
    "wheel": "чёрный для катков",
    "track": "цвета гусениц",
    "pinion": "цвета катков",
}

# Чем такая краска обычно используется.
USAGE: dict[str, str] = {
    "red": "для знаков и аварийных полос",
    "crimson": "для знаков и аварийных полос",
    "scarlet": "для знаков и аварийных полос",
    "signal": "для знаков и аварийных полос",
    "orange": "для позывных и номеров",
    "amber": "для позывных и номеров",
    "yellow": "для номеров и предупреждающих полос",
    "sun": "для номеров и предупреждающих полос",
    "green": "для базового слоя корпуса",
    "olive": "для базового слоя корпуса",
    "dark green": "для базового слоя корпуса",
    "light green": "для базового слоя корпуса",
    "pale green": "для базового слоя корпуса",
    "forest": "для базового слоя корпуса",
    "emerald": "для базового слоя корпуса",
    "zimmerit": "для базового слоя корпуса",
    "net": "для сетки и мешков",
    "web": "для сетки и мешков",
    "khaki": "для базового слоя и тентов",
    "sand": "для базового слоя в пустынной окраске",
    "buff": "для базового слоя в пустынной окраске",
    "desert": "для базового слоя в пустынной окраске",
    "straw": "для базового слоя в пустынной окраске",
    "brown": "для базового слоя и земли",
    "dark brown": "для базового слоя и земли",
    "light brown": "для базового слоя и земли",
    "earth": "для земли и нижней части корпуса",
    "soil": "для земли и нижней части корпуса",
    "tan": "для кожи и разных поверхностей",
    "rust": "для имитации ржавчины и потёков",
    "umber": "для имитации ржавчины и потёков",
    "sepia": "для имитации ржавчины и потёков",
    "copper": "для металла и имитации окислов",
    "bronze": "для металла и имитации окислов",
    "gold": "для деталей и надписей",
    "silver": "для металла и деталей",
    "steel": "для металла и деталей",
    "gunmetal": "для металла и деталей",
    "black": "для деталей, оптики и кромок",
    "shadow": "для теней и кромок",
    "wheel": "для катков и деталей ходовой",
    "track": "для гусениц и ходовой части",
    "pinion": "для катков и ходовой части",
    "white": "для обозначений и светлых поверхностей",
    "ivory": "для обозначений и светлых поверхностей",
    "cream": "для обозначений и светлых поверхностей",
    "lunar": "для зимней окраски",
    "star": "для зимней окраски",
    "winter": "для зимней окраски",
    "grey": "для деталей и теней",
    "gray": "для деталей и теней",
    "blue": "для оптики, приборов и деталей",
    "navy": "для оптики, приборов и деталей",
    "sky blue": "для оптики, приборов и деталей",
    "cyan": "для оптики, приборов и деталей",
    "turquoise": "для оптики, приборов и деталей",
    "teal": "для оптики, приборов и деталей",
    "flesh": "для открытых участков и деталей",
    "skin": "для открытых участков и деталей",
    "peach": "для открытых участков и деталей",
    "wood": "для деревянных деталей",
    "camo": "для камуфляжных пятен",
    "camouflage": "для камуфляжных пятен",
    "purple": "для деталей и приборов",
    "violet": "для деталей и приборов",
    "magenta": "для деталей и приборов",
    "pink": "для деталей и приборов",
    "beige": "для базового слоя и тентов",
    "ochre": "для земли и выветривания",
    "straw": "для земли и выветривания",
}

TYPE_NAMES = {
    "acrylic": "акриловая краска",
    "enamel": "эмаль",
    "pigment": "пигмент",
    "metallic": "металлик",
    "panzer": "панцерная краска",
}

# Прозрачные и полупрозрачные лаки: цвета у них нет by design.
TRANSPARENT = {
    "clear": "Прозрачный лак: добавляет глянец и защищает лак.",
    "semi gloss clear": "Полупрозрачный лак: добавляет глянец и защищает лак.",
    "semi-gloss clear": "Полупрозрачный лак: добавляет глянец и защищает лак.",
    "flat clear": "Прозрачный матовый лак: добавляет матовость и защищает лак.",
    "pearl clear": "Жемчужно-прозрачный лак для придания мягкого блеска.",
    "transparent": "Прозрачная краска для тонировки и стекла.",
    "smoke": "Дымчатая полупрозрачная краска для оптики и приборов.",
}

# Металлы и их оттенки.
METALS = {
    "aluminium": ("алюминиевый", "#b8bcc0"),
    "aluminum": ("алюминиевый", "#b8bcc0"),
    "gun metal": ("тёмно-серый металлик", "#4a4e52"),
    "gunmetal": ("тёмно-серый металлик", "#4a4e52"),
    "dark iron": ("тёмный металл", "#3f4245"),
    "iron": ("металл", "#6e7378"),
    "brass": ("латунный", "#b08d3f"),
    "verdigris": ("патинированный", "#5f9a86"),
    "pewter": ("оловянный", "#8a8f94"),
    "nickel": ("никелевый", "#b4b8bb"),
    "vermillion": ("ярко-красный", "#c33a1e"),
}

# Пояснения к линейкам: у них свой характер и своё назначение.
LINE_NOTES = {
    "game color": "Серия Game Color: густая краска, которая не требует разбавления.",
    "art color": "Серия Art Color: насыщенные цвета для фигурок и диорам.",
    "panzer colors": "Панцерная серия: краски стойкие к химии и ультрафиолету.",
    "metallic colors": "Металлические эффекты: блеск и переходы на металле.",
    "face painting": "Цвета для росписи лиц фигурок.",
    "building colors": "Цвета для зданий и диорам.",
    "surface color": "Цвета для окраски поверхностей и настенной живописи.",
    "enamels": "Эмали: плотное покрытие для стенок и подвижных деталей.",
    "filters": "Фильтры: прозрачные слои для изменения тона основной краски.",
    "mr weathering": "Средства погодных эффектов: потёки, налёт и следы.",
    "real colors": "Серия Real Colors: оттенки, снятые с настоящей техники.",
    "scale color": "Серия Scale 75: точные цвета реальной техники.",
    "3rd generation afv": "Серия AFV: краски для бронетехники.",
}




def _to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _to_hex(red: int, green: int, blue: int) -> str:
    return f"#{max(0, min(255, red)):02x}{max(0, min(255, green)):02x}{max(0, min(255, blue)):02x}"


def _shift(hex_value: str, factor: float) -> str:
    red, green, blue = _to_rgb(hex_value)
    if factor <= 1.0:
        return _to_hex(int(red * factor), int(green * factor), int(blue * factor))
    # Светлый оттенок — смесь с белым.
    mix = min(0.75, factor - 1.0)
    return _to_hex(
        int(red + (255 - red) * mix),
        int(green + (255 - green) * mix),
        int(blue + (255 - blue) * mix),
    )


def derive_hex(name: str) -> str:
    """Образец цвета по названию краски."""
    text = (name or "").lower()
    if not text:
        return NEUTRAL

    # Берём первое цветовое слово в названии: «Sand Yellow» — это песок,
    # а не жёлтый, а «Dark Olive Green» — оливковый.
    best_position = len(text)
    best_word = ""
    best_color = ""
    for word, color in BASE_COLORS.items():
        position = text.find(word)
        if position < 0:
            continue
        if position < best_position or (
            position == best_position and len(word) > len(best_word)
        ):
            best_position = position
            best_word = word
            best_color = color
    if not best_color:
        return NEUTRAL

    result = best_color
    for modifier, factor in MODIFIERS.items():
        if modifier in text and modifier not in best_word:
            result = _shift(result, factor)
    return result


def describe(name: str, brand: str = "", line: str = "", paint_type: str = "") -> str:
    """Короткое пояснение к краске по её названию.

    У большинства красок каталога нет авторского описания, но по названию
    можно сказать, что это за цвет и где он применяется. Пояснение
    получается честным: цвет и назначение названия не выдумываются.
    """
    text = (name or "").lower()
    if not text:
        return ""

    # Набор красок и цвета формы — особый случай.
    if "paint set" in text or "set of paints" in text:
        return "Набор красок: несколько цветов в одной упаковке."
    if "uniform" in text:
        return "Цвет формы: для окраски фигурок и личных деталей экипажа."
    if "armour" in text or "infantry" in text:
        return "Набор цветов для окраски техники и пехоты: несколько оттенков в одной упаковке."

    # Прозрачные и полупрозрачные лаки.
    for word, note in TRANSPARENT.items():
        if word in text:
            return note

    # Металлы и их оттенки.
    for word, (title, _hex) in METALS.items():
        if word in text:
            return f"{title.capitalize()} цвет — для стволов, деталей и металла."

    best_position = len(text)
    best_word = ""
    for word in COLOR_NAMES:
        position = text.find(word)
        if position < 0:
            continue
        if position < best_position or (
            position == best_position and len(word) > len(best_word)
        ):
            best_position = position
            best_word = word

    if not best_word:
        # Цвет в названии не назван — описываем набор или линейку.
        if "colors" in text or "colours" in text or "&" in text:
            return "Набор цветов: несколько оттенков в одной упаковке."
        note = LINE_NOTES.get((line or "").lower())
        if note:
            return note
        kind = TYPE_NAMES.get(paint_type, "краска")
        where = f", {line}" if line else ""
        return f"{kind.capitalize()} {brand}{where}. Цвет по каталогу производителя."

    color_word = COLOR_NAMES[best_word]
    usage = USAGE.get(best_word, "")
    if usage:
        return f"{color_word.capitalize()} цвет — {usage}."

    kind = TYPE_NAMES.get(paint_type, "краска")
    where = f", {line}" if line else ""
    return f"{color_word.capitalize()} цвет. {kind.capitalize()} {brand}{where}."
