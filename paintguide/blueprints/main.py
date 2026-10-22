"""Главная страница, статические страницы и переключатели темы/языка."""

from __future__ import annotations

from datetime import date, timedelta

from flask import (
    Blueprint,
    current_app,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import func, select

from ..extensions import db
from ..models import Country, Guide, Paint, VehicleType
from ..services.loaders import guide_card_options
from ..services.stats import track_visit

bp = Blueprint("main", __name__)


@bp.get("/")
def home():
    """Витрина: популярные гайды, подборки по странам и типам техники."""
    popular = list(
        db.session.scalars(
            select(Guide)
            .where(Guide.published.is_(True))
            .order_by(Guide.views_count.desc(), Guide.created_at.desc())
            .limit(6)
            .options(*guide_card_options())
        )
    )
    latest = list(
        db.session.scalars(
            select(Guide)
            .where(Guide.published.is_(True))
            .order_by(Guide.created_at.desc(), Guide.id.desc())
            .limit(6)
            .options(*guide_card_options())
        )
    )

    country_rows = db.session.execute(
        select(Country, func.count(Guide.id))
        .join(Guide, Guide.country_id == Country.id)
        .where(Guide.published.is_(True))
        .group_by(Country.id)
        .order_by(func.count(Guide.id).desc())
    ).all()

    type_rows = db.session.execute(
        select(VehicleType, func.count(Guide.id))
        .join(Guide, Guide.vehicle_type_id == VehicleType.id)
        .where(Guide.published.is_(True))
        .group_by(VehicleType.id)
        .order_by(func.count(Guide.id).desc())
    ).all()

    era_rows = db.session.execute(
        select(Guide.year_from, func.count(Guide.id))
        .where(Guide.published.is_(True), Guide.year_from.isnot(None))
        .group_by(Guide.year_from)
        .order_by(Guide.year_from.asc())
    ).all()

    # Счётчики выводим из уже загруженных агрегатов — лишних запросов не делаем.
    stats = {
        "guides": sum(count for _, count in country_rows),
        "paints": db.session.scalar(select(func.count(Paint.id))) or 0,
        "countries": len(country_rows),
        "types": len(type_rows),
    }

    track_visit("/")
    return render_template(
        "home.html",
        title="PaintGuide",
        nav_active="home",
        popular=popular,
        latest=latest,
        country_rows=country_rows,
        type_rows=type_rows,
        era_rows=era_rows,
        stats=stats,
    )


@bp.get("/terms")
def terms():
    return render_template("terms.html", title="Пользовательское соглашение", nav_active="")


@bp.post("/set-theme")
def set_theme():
    """Переключить тему оформления и запомнить выбор в cookie."""
    theme = request.form.get("theme", "dark")
    if theme not in {"dark", "light"}:
        theme = "dark"
    response = make_response(redirect(request.referrer or url_for("main.home")))
    response.set_cookie(
        "pg_theme", theme, max_age=60 * 60 * 24 * 365, samesite="Lax", httponly=False
    )
    return response


@bp.post("/set-language")
def set_language():
    """Сменить язык интерфейса."""
    locale = request.form.get("locale", "ru")
    supported = current_app.config.get("SUPPORTED_LOCALES", ("ru",))
    if locale not in supported:
        locale = current_app.config.get("DEFAULT_LOCALE", "ru")
    session["locale"] = locale
    return redirect(request.referrer or url_for("main.home"))


@bp.get("/credits")
def credits():
    """Источники изображений: авторы, лицензии и ссылки."""
    from sqlalchemy import select

    from ..models import Guide

    rows = list(
        db.session.scalars(
            select(Guide)
            .where(Guide.cover_credit != "", Guide.published.is_(True))
            .order_by(Guide.title)
        )
    )
    return render_template(
        "credits.html",
        title="Источники изображений",
        nav_active="",
        guides=rows,
    )


@bp.get("/healthz")
def healthz():
    return {"status": "ok", "day": date.today().isoformat()}


@bp.app_errorhandler(413)
def too_large(_error):
    flash("Файл слишком большой.", "error")
    return redirect(url_for("main.home"))
