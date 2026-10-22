"""Поиск, фильтрация, сортировка и пагинация каталога руководств."""

from __future__ import annotations

from dataclasses import dataclass, field

from flask import request
from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import (
    Country,
    Difficulty,
    Guide,
    GuideStep,
    GuideVariant,
    Paint,
    StepPaint,
    VehicleType,
)
from .loaders import guide_card_options

SORTS = {
    "date": "date",
    "popularity": "popularity",
    "difficulty": "difficulty",
    "alphabetical": "alphabetical",
}


@dataclass
class CatalogQuery:
    """Разобранные параметры каталога."""

    search: str = ""
    country: str = ""
    vehicle_type: str = ""
    difficulty: str = ""
    year: str = ""
    sort: str = "date"
    page: int = 1
    per_page: int = 24
    countries: list[Country] = field(default_factory=list)
    vehicle_types: list[VehicleType] = field(default_factory=list)
    difficulties: list[Difficulty] = field(default_factory=list)
    years: list[int] = field(default_factory=list)

    @property
    def has_filters(self) -> bool:
        return bool(
            self.search
            or self.country
            or self.vehicle_type
            or self.difficulty
            or self.year
        )


def parse_catalog_request(args, per_page: int = 24) -> CatalogQuery:
    """Собрать объект фильтров из query-строки."""
    search = (args.get("q") or "").strip()[:120]
    country = (args.get("country") or "").strip()[:60]
    vehicle_type = (args.get("vehicle_type") or "").strip()[:60]
    difficulty = (args.get("difficulty") or "").strip()[:40]
    year_raw = (args.get("year") or "").strip()[:4]
    sort = (args.get("sort") or "date").strip().lower()
    if sort not in SORTS:
        sort = "date"
    try:
        page = max(1, int(args.get("page") or 1))
    except (TypeError, ValueError):
        page = 1

    year = year_raw if year_raw.isdigit() and 1900 <= int(year_raw) <= 2100 else ""

    return CatalogQuery(
        search=search,
        country=country,
        vehicle_type=vehicle_type,
        difficulty=difficulty,
        year=year,
        sort=sort,
        page=page,
        per_page=per_page,
    )


def build_guide_query(query: CatalogQuery):
    """Собрать SELECT для каталога с учётом всех фильтров."""
    stmt = (
        select(Guide)
        .join(Guide.country)
        .join(Guide.vehicle_type)
        .where(Guide.published.is_(True))
    )

    if query.search:
        # SQLite LIKE регистрозависим для кириллицы, поэтому приводим
        # обе стороны к нижнему регистру через lower().
        needle = query.search.lower()
        pattern = f"%{needle}%"
        # Поиск идёт по карточке гайда, по названиям техник в шагах
        # («Проливка», «Тонировка») и по краскам, которые в них
        # применяются: по коду и названию.
        stmt = stmt.where(
            or_(
                func.lower(Guide.title).like(pattern),
                func.lower(Guide.subtitle).like(pattern),
                func.lower(Guide.description).like(pattern),
                func.lower(Guide.production).like(pattern),
                func.lower(Country.name_ru).like(pattern),
                func.lower(Country.name_en).like(pattern),
                func.lower(VehicleType.name_ru).like(pattern),
                func.lower(VehicleType.name_en).like(pattern),
                Guide.id.in_(
                    select(GuideVariant.guide_id)
                    .join(GuideVariant.steps)
                    .where(func.lower(GuideStep.title).like(pattern))
                ),
                Guide.id.in_(
                    select(GuideStep.variant_id)
                    .join(GuideVariant)
                    .where(
                        GuideVariant.id.in_(
                            select(StepPaint.step_id)
                            .join(StepPaint.step)
                            .join(Paint)
                            .where(
                                or_(
                                    func.lower(Paint.name).like(pattern),
                                    func.lower(Paint.code).like(pattern),
                                    func.lower(Paint.description).like(pattern),
                                )
                            )
                        )
                    )
                ),
            )
        )

    if query.country:
        stmt = stmt.where(Country.slug == query.country)

    if query.vehicle_type:
        stmt = stmt.where(VehicleType.slug == query.vehicle_type)

    if query.difficulty:
        stmt = stmt.join(Guide.variants).where(
            GuideVariant.difficulty_id.in_(
                select(Difficulty.id).where(Difficulty.slug == query.difficulty)
            )
        )

    if query.year:
        year_value = int(query.year)
        stmt = stmt.where(
            and_(
                func.coalesce(Guide.year_from, 0) <= year_value,
                func.coalesce(Guide.year_to, 9999) >= year_value,
            )
        )

    stmt = _apply_sort(stmt, query.sort)
    return stmt


def _apply_sort(stmt, sort: str):
    if sort == "popularity":
        return stmt.order_by(Guide.views_count.desc(), Guide.created_at.desc())
    if sort == "alphabetical":
        return stmt.order_by(Guide.title.asc())
    if sort == "difficulty":
        min_rank = (
            select(func.min(Difficulty.rank))
            .select_from(GuideVariant)
            .join(Difficulty, Difficulty.id == GuideVariant.difficulty_id)
            .where(GuideVariant.guide_id == Guide.id)
            .scalar_subquery()
        )
        return stmt.order_by(min_rank.asc(), Guide.title.asc())
    return stmt.order_by(Guide.created_at.desc(), Guide.id.desc())


def run_catalog(query: CatalogQuery):
    """Выполнить запрос и вернуть (страница объектов, объект пагинации)."""
    stmt = build_guide_query(query)
    # Карточке каталога нужны уровни сложности, но не шаги: без этой
    # настройки каждый гайд подтягивал бы все свои шаги и краски.
    stmt = stmt.options(*guide_card_options())
    pagination = db.paginate(
        stmt,
        page=query.page,
        per_page=query.per_page,
        error_out=False,
        max_per_page=100,
    )
    return pagination.items, pagination


def available_years() -> list[int]:
    """Все годы выпуска, представленные в каталоге (по убыванию)."""
    rows = db.session.query(Guide.year_from).filter(
        Guide.published.is_(True), Guide.year_from.isnot(None)
    ).distinct()
    years = sorted({row[0] for row in rows if row[0]}, reverse=True)
    return years


def related_guides(guide: Guide, limit: int = 3) -> list[Guide]:
    """Похожие гайды: та же страна или тот же тип техники."""
    stmt = (
        select(Guide)
        .where(
            Guide.published.is_(True),
            Guide.id != guide.id,
            or_(
                Guide.country_id == guide.country_id,
                Guide.vehicle_type_id == guide.vehicle_type_id,
            ),
        )
        .order_by(Guide.views_count.desc(), Guide.title.asc())
        .limit(limit)
        .options(*guide_card_options())
    )
    return list(db.session.scalars(stmt))


def guide_search_index() -> str:
    """Текстовая копия полей для полнотекстового поиска по SQLite."""
    return cast(Guide.title, String)
