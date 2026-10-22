"""Справочник красок: каталог, фильтры, карточка краски."""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from ..extensions import db
from ..models import (
    Brand,
    Favorite,
    Guide,
    GuideStep,
    GuideVariant,
    Paint,
    PaintLine,
    StepPaint,
    WishlistItem,
)
from ..services.loaders import guide_card_options
from ..services.log import log_action
from ..services.stats import track_visit

bp = Blueprint("paints", __name__, url_prefix="/paints")

SORTS = {
    "alpha": "По бренду и названию",
    "tone_asc": "От тёмного к светлому",
    "tone_desc": "От светлого к тёмному",
    "code": "По коду",
}


@bp.get("/")
def paints_index():
    """Таблица красок с фильтрами по бренду, линейке и типу."""
    per_page = 40
    search = (request.args.get("q") or "").strip()[:100]
    brand_slug = (request.args.get("brand") or "").strip()[:60]
    line_slug = (request.args.get("line") or "").strip()[:80]
    paint_type = (request.args.get("type") or "").strip()[:30]
    technique = (request.args.get("technique") or "").strip()[:40]
    sort = (request.args.get("sort") or "alpha").strip().lower()
    if sort not in SORTS:
        sort = "alpha"
    try:
        page = max(1, int(request.args.get("page") or 1))
    except (TypeError, ValueError):
        page = 1

    stmt = select(Paint).join(Paint.brand).join(Paint.line)

    if search:
        # SQLite LIKE регистрозависим для кириллицы.
        pattern = f"%{search.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Paint.name).like(pattern),
                func.lower(Paint.code).like(pattern),
                func.lower(Paint.description).like(pattern),
                func.lower(Brand.name).like(pattern),
                func.lower(PaintLine.name).like(pattern),
            )
        )
    if brand_slug:
        stmt = stmt.where(Brand.slug == brand_slug)
    if line_slug:
        stmt = stmt.where(PaintLine.slug == line_slug)
    if paint_type:
        stmt = stmt.where(Paint.paint_type == paint_type)
    if technique:
        # Краски, которые применяются на шаге выбранной техники:
        # «Проливка», «Тонировка», «Овербраш» и прочие.
        stmt = stmt.where(
            Paint.id.in_(
                select(StepPaint.paint_id)
                .join(StepPaint.step)
                .where(func.lower(GuideStep.title) == technique.lower())
            )
        )

    stmt = _apply_sort(stmt, sort)
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False, max_per_page=100)

    track_visit("/paints")
    return render_template(
        "paints.html",
        title="Справочник красок",
        nav_active="paints",
        paints=pagination.items,
        pagination=pagination,
        brands=Brand.query.order_by(Brand.sort_order, Brand.name).all(),
        lines=_lines_for(brand_slug),
        techniques=_techniques(),
        sort_labels=SORTS,
        filters={
            "q": search,
            "brand": brand_slug,
            "line": line_slug,
            "type": paint_type,
            "technique": technique,
            "sort": sort,
        },
    )


def _techniques() -> list[str]:
    """Названия техник, встречающиеся в шагах руководств."""
    stmt = select(GuideStep.title).distinct().order_by(GuideStep.title)
    return [title for title in db.session.scalars(stmt) if title]


def _apply_sort(stmt, sort: str):
    if sort == "tone_asc":
        return stmt.order_by(Paint.tone.asc(), Paint.name.asc())
    if sort == "tone_desc":
        return stmt.order_by(Paint.tone.desc(), Paint.name.asc())
    if sort == "code":
        return stmt.order_by(Paint.code.asc(), Paint.name.asc())
    return stmt.order_by(Brand.sort_order, Brand.name, PaintLine.sort_order, PaintLine.name, Paint.name)


def _lines_for(brand_slug: str):
    stmt = select(PaintLine)
    if brand_slug:
        stmt = stmt.join(PaintLine.brand).where(Brand.slug == brand_slug)
    stmt = stmt.order_by(PaintLine.sort_order, PaintLine.name)
    return list(db.session.scalars(stmt))


@bp.get("/<int:paint_id>")
def paint_detail(paint_id: int):
    """Карточка краски: образец, соответствия и применение в гайдах."""
    paint = db.get_or_404(Paint, paint_id)
    equivalents = paint.all_equivalents

    # Гайды, где применяется краска: одним запросом, без поштучной
    # загрузки связей — их сотни, и поштучный обход заметно тормозит.
    # Показываем первые два десятка: полный список не нужен, а шаги
    # каждого гайда тянуть тем более незачем.
    guides = list(
        db.session.scalars(
            select(Guide)
            .join(GuideVariant)
            .join(GuideStep)
            .join(StepPaint)
            .where(StepPaint.paint_id == paint.id)
            .distinct()
            .order_by(Guide.title)
            .limit(24)
            .options(*guide_card_options())
        )
    )

    is_favorite = False
    from flask_login import current_user

    if current_user.is_authenticated:
        is_favorite = (
            db.session.scalar(
                select(func.count(Favorite.id)).where(
                    Favorite.user_id == current_user.id,
                    Favorite.target_type == "paint",
                    Favorite.target_id == paint.id,
                )
            )
            or 0
        ) > 0

    track_visit(f"/paints/{paint.id}")
    return render_template(
        "paint_detail.html",
        title=paint.display_name,
        nav_active="paints",
        paint=paint,
        equivalents=equivalents,
        guides=guides,
        is_favorite=is_favorite,
    )


@bp.post("/<int:paint_id>/favorite")
@login_required
def toggle_favorite(paint_id: int):
    from flask_login import current_user

    paint = db.get_or_404(Paint, paint_id)
    favorite = db.session.scalar(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.target_type == "paint",
            Favorite.target_id == paint.id,
        )
    )
    if favorite:
        db.session.delete(favorite)
        flash("Краска удалена из избранного.", "success")
    else:
        db.session.add(
            Favorite(user_id=current_user.id, target_type="paint", target_id=paint.id)
        )
        flash("Краска добавлена в избранное.", "success")
    db.session.commit()
    log_action(current_user.id, "paint.favorite", "paint", paint.display_name)
    return redirect(request.referrer or url_for("paints.paints_index"))


@bp.post("/<int:paint_id>/wishlist")
@login_required
def add_to_wishlist(paint_id: int):
    from flask_login import current_user

    paint = db.get_or_404(Paint, paint_id)
    existing = db.session.scalar(
        select(WishlistItem).where(
            WishlistItem.user_id == current_user.id,
            WishlistItem.item_type == "paint",
            WishlistItem.item_id == paint.id,
        )
    )
    if existing is None:
        db.session.add(
            WishlistItem(
                user_id=current_user.id,
                item_type="paint",
                item_id=paint.id,
                name=f"{paint.brand.name} — {paint.name}",
                notes=f"Оттенок {paint.color_hex}",
            )
        )
        db.session.commit()
        flash("Краска добавлена в вишлист.", "success")
    return redirect(request.referrer or url_for("paints.paints_index"))


@bp.post("/<int:paint_id>/inventory")
@login_required
def add_to_inventory(paint_id: int):
    from flask_login import current_user

    from ..models import PaintStock

    paint = db.get_or_404(Paint, paint_id)
    stock = db.session.scalar(
        select(PaintStock).where(
            PaintStock.user_id == current_user.id, PaintStock.paint_id == paint.id
        )
    )
    if stock is None:
        db.session.add(PaintStock(user_id=current_user.id, paint_id=paint.id, status="owned"))
        flash("Краска добавлена в инвентарь.", "success")
    else:
        flash("Краска уже есть в инвентаре.", "info")
    db.session.commit()
    log_action(current_user.id, "paint.inventory", "paint", paint.display_name)
    return redirect(request.referrer or url_for("paints.paints_index"))
