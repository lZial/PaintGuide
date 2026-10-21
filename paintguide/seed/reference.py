"""Справочники PaintGuide: страны, типы техники, уровни сложности, бренды, линейки."""

from __future__ import annotations

COUNTRIES = [
    # slug, RU, EN, регион, флаг, порядок
    # Флаг СССР задаём парой региональных индикаторов: у СССР нет
    # эмодзи-флага, а символ ☭ в браузерах рисуется некорректно.
    # Пара SU отображается так же, как флаги остальных стран.
    ("ussr", "СССР", "USSR", "Европа", "🇸🇺", 10),
    ("germany", "Германия", "Germany", "Европа", "🇩🇪", 20),
    ("usa", "США", "USA", "Северная Америка", "🇺🇸", 30),
    ("uk", "Великобритания", "United Kingdom", "Европа", "🇬🇧", 40),
    ("japan", "Япония", "Japan", "Азия", "🇯🇵", 50),
    ("france", "Франция", "France", "Европа", "🇫🇷", 60),
    ("italy", "Италия", "Italy", "Европа", "🇮🇹", 70),
    ("china", "Китай", "China", "Азия", "🇨🇳", 80),
    ("israel", "Израиль", "Israel", "Ближний Восток", "🇮🇱", 90),
    ("sweden", "Швеция", "Sweden", "Европа", "🇸🇪", 100),
    ("finland", "Финляндия", "Finland", "Европа", "🇫🇮", 110),
    ("poland", "Польша", "Poland", "Европа", "🇵🇱", 120),
]

VEHICLE_TYPES = [
    # slug, RU, EN, иконка, порядок
    # Иконки оставлены пустыми: эмодзи в интерфейсе выглядят неуместно
    # и по-разному рисуются в разных браузерах.
    ("tank", "Танк", "Tank", "", 10),
    ("spg", "САУ", "Self-propelled gun", "", 20),
    ("ifv", "БТР", "Armoured personnel carrier", "", 30),
    ("armored_car", "Бронеавтомобиль", "Armoured car", "", 40),
    ("halftrack", "Полугусеница", "Half-track", "", 50),
    ("artillery", "Артиллерия", "Artillery", "", 60),
    ("truck", "Автомобиль", "Truck", "", 70),
    ("aircraft", "Авиация", "Aircraft", "", 80),
]

DIFFICULTIES = [
    # slug, RU, EN, ранг, метка, описание
    ("easy", "Лёгкая", "Easy", 1, "easy", "Ровный базовый слой без погодных эффектов и тонких деталей."),
    ("medium", "Средняя", "Medium", 2, "medium", "Базовый слой с простыми смывками и лёгкой пылью."),
    ("hard", "Сложная", "Hard", 3, "hard", "Многослойная окраска, высветление панелей, сколы и подтёки."),
    ("expert", "Экспертная", "Expert", 4, "expert", "Камуфляж по схеме, полный набор погодных эффектов и декалей."),
]

BRANDS = [
    # slug, название, страна, порядок
    ("tamiya", "Tamiya", "Япония", 10),
    ("vallejo", "Vallejo", "Испания", 20),
    ("ak", "AK Interactive", "Польша", 30),
    ("humbrol", "Humbrol", "Великобритания", 40),
    ("mrcolor", "Mr. Color", "Япония", 50),
    ("scale75", "Scale75", "Испания", 60),
    ("lifecolor", "Lifecolor", "Испания", 70),
    ("pacific88", "Pacific88", "Япония", 80),
]

LINES = [
    # brand_slug, slug, название, тип, порядок
    ("tamiya", "xf", "XF — краски по пластику", "acrylic", 10),
    ("tamiya", "ts", "TS — топовые краски", "acrylic", 20),
    ("tamiya", "ig", "IG — грунт и детали", "acrylic", 30),
    ("vallejo", "mc", "Model Color", "acrylic", 10),
    ("vallejo", "gc", "Game Color", "acrylic", 20),
    ("vallejo", "sf", "Surface Color", "acrylic", 30),
    ("ak", "gen", "3rd Generation", "acrylic", 10),
    ("ak", "rc", "Real Colors", "acrylic", 20),
    ("ak", "panzer", "Panzer Colors", "acrylic", 30),
    ("ak", "afv", "3rd Generation AFV", "acrylic", 40),
    ("ak", "air", "Авиационная серия", "acrylic", 50),
    ("ak", "figure", "Фигурная серия", "acrylic", 60),
    ("ak", "legacy", "Первые серии AK", "acrylic", 70),
    ("humbrol", "mat", "Matt", "acrylic", 10),
    ("humbrol", "met", "Metallic", "metallic", 20),
    ("mrcolor", "cmc", "CMC", "acrylic", 10),
    ("mrcolor", "super", "Super", "acrylic", 20),
    ("mrcolor", "wx", "Mr. Weathering", "acrylic", 30),
    ("scale75", "sg", "Scale 75", "acrylic", 10),
    ("scale75", "sc", "ScaleColor", "acrylic", 20),
    ("lifecolor", "lc", "Lifecolor", "acrylic", 10),
    ("tamiya", "lacquer", "Цветные лаки LP", "enamel", 40),
    ("pacific88", "art", "Art Color — акрил", "acrylic", 10),
    ("pacific88", "metal", "Металлические серии", "metallic", 20),
    ("pacific88", "enamel", "Эмали и грунты", "enamel", 30),
    ("pacific88", "filter", "Фильтры", "acrylic", 40),
]
