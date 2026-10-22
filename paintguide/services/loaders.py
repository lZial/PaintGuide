"""Подгрузка связанных данных.

Без явной подгрузки каждая карточка гайда тянет страну, тип техники и
уровни сложности отдельными запросами. На локальной машине это
незаметно, а к удалённой базе каждый запрос — это сеть: каталог из
24 гайдов превращался в сотню запросов и в несколько секунд ожидания.
"""

from __future__ import annotations

from sqlalchemy.orm import selectinload

from ..models import Guide, GuideStep, GuideVariant, Paint, StepPaint


def guide_card_options() -> tuple:
    """Данные для карточки гайда: страна, тип техники, уровни сложности."""
    return (
        selectinload(Guide.country),
        selectinload(Guide.vehicle_type),
        selectinload(Guide.variants).selectinload(GuideVariant.difficulty),
    )


def guide_detail_options() -> tuple:
    """Данные для страницы гайда: уровни, шаги, краски и их бренды."""
    return (
        selectinload(Guide.country),
        selectinload(Guide.vehicle_type),
        # Две отдельные ветви: сложность и шаги — разные связи
        # одного уровня, идти дальше по цепочке от сложности нельзя.
        selectinload(Guide.variants).selectinload(GuideVariant.difficulty),
        selectinload(Guide.variants)
        .selectinload(GuideVariant.steps)
        .selectinload(GuideStep.paints)
        .selectinload(StepPaint.paint)
        .selectinload(Paint.brand),
    )
