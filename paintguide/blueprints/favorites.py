"""Избранное: сохранённые гайды и краски."""

from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import select

from ..extensions import db
from ..models import Favorite, Guide, Paint
from ..services.loaders import guide_card_options

bp = Blueprint("favorites", __name__, url_prefix="/favorites")


@bp.get("/")
@login_required
def favorites():
    """Список избранных гайдов и красок."""
    guide_rows = list(
        db.session.scalars(
            select(Guide)
            .join(Favorite, Favorite.target_id == Guide.id)
            .where(
                Favorite.user_id == current_user.id,
                Favorite.target_type == "guide",
            )
            .order_by(Favorite.created_at.desc())
            .options(*guide_card_options())
        )
    )
    paint_rows = list(
        db.session.scalars(
            select(Paint)
            .join(Favorite, Favorite.target_id == Paint.id)
            .where(
                Favorite.user_id == current_user.id,
                Favorite.target_type == "paint",
            )
            .order_by(Favorite.created_at.desc())
        )
    )
    return render_template(
        "favorites.html",
        title="Избранное",
        nav_active="favorites",
        guides=guide_rows,
        paints=paint_rows,
    )
