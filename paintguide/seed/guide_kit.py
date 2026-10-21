"""Сборка руководств из коротких записей.

Гайд описывает машину: страна, тип, годы, выпуск, экипаж и окраска. Шаги
внутри — это техники окраски, а текст шага формируется по лестнице техник
(см. techniques.py). Поэтому здесь хранится то, что действительно различает
машины: краски, поверхности и практические советы.

Пример:

    G(
        slug="amx-30",
        title="AMX-30",
        subtitle="Французский основной танк: тёмно-зелёная броня",
        country="france",
        vtype="tank",
        years=(1960, 1968),
        production="ARE",
        crew="4 человека",
        description="...",
        views=180,
        variants=[
            V(
                "easy", "Ровный тёмно-зелёный", "База и знаки.", 5,
                default=True,
                steps=[
                    S("Грунтовка", "Грунт наносите тонко.", [(REDOXIDE, "Все области")]),
                    S("База", "Дайте краске высохнуть между слоями.", [(FR_VERT, "Корпус и башня")]),
                ],
            ),
        ],
    )
"""

from __future__ import annotations

from typing import Iterable

PaintRef = tuple[str, str] | tuple[str, str, str]
Step = dict
Variant = dict
Guide = dict


def _instruction(title: str) -> str:
    """Опорный текст шага по его названию.

    На странице текст формируется по лестнице техник, поэтому здесь нужен
    лишь связующий текст, который читается в исходных данных.
    """
    text = (title or "").lower()
    if "грунт" in text or "подложк" in text:
        return "Нанесите грунт ровным тонким слоем по всей модели и дайте высохнуть."
    if "баз" in text or "основ" in text:
        return "Нанесите базовый цвет в два-три тонких слоя, каждый полностью просушив."
    if "камуфляж" in text or "пятн" in text or "участ" in text:
        return "Нанесите пятна поверх высохшей основы, мягко разбивая рисунок."
    if "смывк" in text or "пролив" in text:
        return "Проведите смывкой по швам, стыкам и углублениям."
    if "тень" in text or "затемн" in text:
        return "Затемните углубления и под выступающими деталями."
    if "высветл" in text or "подсвет" in text:
        return "Осветлите центры крупных плоскостей смесью базового цвета с белым."
    if "знак" in text or "звёзд" in text or "номер" in text:
        return "Нанесите знаки по трафарету или по макету."
    if "гряз" in text or "пыл" in text or "след" in text:
        return "Добавьте грязь и пыль на ходовую часть и в нижние части корпуса."
    if "тонир" in text:
        return "Наложите полупрозрачный тон, объединяя цвета в один."
    if "финиш" in text or "лак" in text:
        return "Закрепите результат матовым лаком, предварительно убрав пыль."
    return "Выполните шаг по инструкции."


def S(title: str, tip: str, paints: Iterable[PaintRef] = ()) -> Step:
    """Шаг гайда: название, практический совет и краски с областями."""
    return {
        "title": title,
        "instruction": _instruction(title),
        "tip": tip,
        "paints": [list(paint) for paint in paints],
    }


def V(
    difficulty: str,
    title: str,
    summary: str,
    hours: int,
    steps: Iterable[Step],
    default: bool = False,
) -> Variant:
    """Вариант окраски: уровень сложности, описание и шаги."""
    return {
        "difficulty": difficulty,
        "title": title,
        "summary": summary,
        "hours": hours,
        "default": default,
        "steps": list(steps),
    }


def G(
    slug: str,
    title: str,
    subtitle: str,
    country: str,
    vtype: str,
    years: tuple[int, int],
    production: str,
    crew: str,
    description: str,
    views: int,
    variants: Iterable[Variant],
) -> Guide:
    """Руководство по окраске одной машины."""
    return {
        "slug": slug,
        "title": title,
        "subtitle": subtitle,
        "country": country,
        "vehicle_type": vtype,
        "year_from": years[0],
        "year_to": years[1],
        "production": production,
        "crew": crew,
        "description": description,
        "views": views,
        "variants": list(variants),
    }
