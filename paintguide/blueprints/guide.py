"""Карточка руководства: уровни сложности, палитра и пошаговые этапы."""

from __future__ import annotations

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy import func, select

from ..extensions import db
from ..models import (
    Favorite,
    Guide,
    GuideVariant,
    Paint,
    StepPaint,
    WishlistItem,
)
from ..services.log import log_action
from ..services.stats import track_visit

bp = Blueprint("guide", __name__, url_prefix="/guides")


@bp.get("/<slug>")
def guide_detail(slug: str):
    """Страница руководства с вкладками уровней сложности."""
    guide = db.session.scalar(
        select(Guide).where(Guide.slug == slug, Guide.published.is_(True))
    )
    if guide is None:
        abort(404)

    guide.views_count = (guide.views_count or 0) + 1
    db.session.commit()

    # Уровни идут по сложности: лёгкая → средняя → сложная → экспертная.
    # Позиция в базе может остаться от прежней правки, поэтому
    # порядок определяем по рангу difficulty.
    variants = sorted(
        guide.variants,
        key=lambda item: (
            item.difficulty.rank if item.difficulty else 99,
            item.position,
        ),
    )
    selected_slug = request.args.get("level", "")
    selected = None
    for variant in variants:
        if variant.difficulty and variant.difficulty.slug == selected_slug:
            selected = variant
            break
    if selected is None:
        selected = guide.default_variant

    palette = _palette(guide, selected)
    is_favorite = False
    in_wishlist = False
    if current_user_id():
        is_favorite = (
            db.session.scalar(
                select(func.count(Favorite.id)).where(
                    Favorite.user_id == current_user_id(),
                    Favorite.target_type == "guide",
                    Favorite.target_id == guide.id,
                )
            )
            or 0
        ) > 0
        in_wishlist = (
            db.session.scalar(
                select(func.count(WishlistItem.id)).where(
                    WishlistItem.user_id == current_user_id(),
                    WishlistItem.item_type == "guide",
                    WishlistItem.item_id == guide.id,
                )
            )
            or 0
        ) > 0

    track_visit(f"/guides/{slug}")
    return render_template(
        "guide_detail.html",
        title=guide.title,
        nav_active="catalog",
        guide=guide,
        variants=variants,
        variant=selected,
        palette=palette,
        is_favorite=is_favorite,
        in_wishlist=in_wishlist,
        related=_related(guide),
    )


def _palette(guide: Guide, variant: GuideVariant | None):
    """Краски выбранного варианта и место их применения."""
    entries: list[dict] = []
    seen: set[int] = set()
    if variant is None:
        return entries
    for step in variant.steps:
        for link in step.paints:
            if not link.paint or link.paint.id in seen:
                continue
            seen.add(link.paint.id)
            areas = [
                other.area for other in step.paints if other.paint_id == link.paint_id and other.area
            ]
            steps = [
                other.title
                for other in variant.steps
                if any(sp.paint_id == link.paint_id for sp in other.paints)
            ]
            entries.append(
                {
                    "paint": link.paint,
                    "areas": areas,
                    "steps": [title for title in steps if title],
                }
            )
    return entries


def _related(guide: Guide, limit: int = 3):
    stmt = (
        select(Guide)
        .where(
            Guide.published.is_(True),
            Guide.id != guide.id,
            (Guide.country_id == guide.country_id) | (Guide.vehicle_type_id == guide.vehicle_type_id),
        )
        .order_by(Guide.views_count.desc(), Guide.title.asc())
        .limit(limit)
    )
    return list(db.session.scalars(stmt))


@bp.post("/<slug>/favorite")
def toggle_favorite(slug: str):
    from flask_login import current_user

    guide = db.session.scalar(select(Guide).where(Guide.slug == slug))
    if guide is None:
        abort(404)
    favorite = db.session.scalar(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.target_type == "guide",
            Favorite.target_id == guide.id,
        )
    )
    if favorite:
        db.session.delete(favorite)
        flash("Гайд удалён из избранного.", "success")
    else:
        db.session.add(
            Favorite(user_id=current_user.id, target_type="guide", target_id=guide.id)
        )
        flash("Гайд добавлен в избранное.", "success")
    db.session.commit()
    log_action(current_user.id, "guide.favorite", "guide", guide.title)
    return redirect(request.referrer or url_for("guide.guide_detail", slug=slug))


@bp.post("/<slug>/wishlist")
def add_to_wishlist(slug: str):
    from flask_login import current_user

    guide = db.session.scalar(select(Guide).where(Guide.slug == slug))
    if guide is None:
        abort(404)
    existing = db.session.scalar(
        select(WishlistItem).where(
            WishlistItem.user_id == current_user.id,
            WishlistItem.item_type == "guide",
            WishlistItem.item_id == guide.id,
        )
    )
    if existing is None:
        db.session.add(
            WishlistItem(
                user_id=current_user.id,
                item_type="guide",
                item_id=guide.id,
                name=guide.title,
                notes=f"Руководство: /guides/{guide.slug}",
            )
        )
        db.session.commit()
        flash("Руководство добавлено в вишлист.", "success")
    return redirect(request.referrer or url_for("guide.guide_detail", slug=slug))


@bp.post("/<slug>/add-paints")
def add_paints_to_wishlist(slug: str):
    """Добавить все краски выбранного уровня сложности в вишлист."""
    from flask_login import current_user

    guide = db.session.scalar(select(Guide).where(Guide.slug == slug))
    if guide is None:
        abort(404)

    variant = _variant_from_request(guide)
    if variant is None:
        flash("Уровень сложности не найден.", "error")
        return redirect(url_for("guide.guide_detail", slug=slug))

    existing = {
        item.item_id
        for item in db.session.scalars(
            select(WishlistItem).where(
                WishlistItem.user_id == current_user.id,
                WishlistItem.item_type == "paint",
            )
        )
    }

    added = 0
    for paint in _variant_paints(variant):
        if paint.id in existing:
            continue
        db.session.add(
            WishlistItem(
                user_id=current_user.id,
                item_type="paint",
                item_id=paint.id,
                name=f"{paint.brand.name} — {paint.name}",
                notes=f"Оттенок {paint.color_hex} · {guide.title}",
                quantity=1,
            )
        )
        added += 1

    db.session.commit()
    log_action(
        current_user.id,
        "guide.add_paints",
        "guide",
        guide.title,
        f"Добавлено красок: {added}",
    )
    flash(f"В вишлист добавлено красок: {added}.", "success")
    return redirect(url_for("guide.guide_detail", slug=slug, level=request.form.get("level", "")))


def _variant_from_request(guide: Guide) -> GuideVariant | None:
    variant_id = request.form.get("variant_id", type=int)
    if variant_id:
        for variant in guide.variants:
            if variant.id == variant_id:
                return variant
    slug = request.form.get("level", "")
    for variant in guide.variants:
        if variant.difficulty and variant.difficulty.slug == slug:
            return variant
    return guide.default_variant


def _variant_paints(variant: GuideVariant) -> list[Paint]:
    seen: dict[int, Paint] = {}
    for step in variant.steps:
        for link in step.paints:
            if link.paint:
                seen.setdefault(link.paint.id, link.paint)
    return list(seen.values())


def current_user_id():
    from flask_login import current_user

    return current_user.id if current_user.is_authenticated else None
