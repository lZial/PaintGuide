"""Каталог руководств: поиск, фильтры, сортировка, пагинация."""

from __future__ import annotations

from flask import Blueprint, current_app, render_template, request

from ..models import Difficulty
from ..services.search import available_years, parse_catalog_request, run_catalog
from ..services.stats import track_visit

bp = Blueprint("catalog", __name__)


@bp.get("/catalog")
@bp.get("/guides")
def catalog():
    """Каталог с полнотекстовым поиском и фильтрами по справочникам."""
    per_page = current_app.config.get("PER_PAGE", 24)
    query = parse_catalog_request(request.args, per_page=per_page)

    query.countries = _countries()
    query.vehicle_types = _vehicle_types()
    query.difficulties = _difficulties()
    query.years = available_years()

    items, pagination = run_catalog(query)

    track_visit("/catalog")
    return render_template(
        "catalog.html",
        title="Каталог руководств",
        nav_active="catalog",
        guides=items,
        pagination=pagination,
        catalog=query,
        sort_options=SORT_LABELS,
    )


def _countries():
    from ..models import Country

    return Country.query.order_by(Country.sort_order, Country.name_ru).all()


def _vehicle_types():
    from ..models import VehicleType

    return VehicleType.query.order_by(VehicleType.sort_order, VehicleType.name_ru).all()


def _difficulties():
    return Difficulty.query.order_by(Difficulty.rank).all()


SORT_LABELS = {
    "date": "По дате",
    "popularity": "По популярности",
    "difficulty": "По сложности",
    "alphabetical": "По алфавиту",
}
