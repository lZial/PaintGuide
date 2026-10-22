"""Избранное: сохранённые модели.

По замыслу избранное — про модели: гайды и машины, к которым хочется
вернуться. Краски живут в вишлисте, а учёт того, что уже куплено, — в
инвентаре.
"""

from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import select

from ..extensions import db
from ..models import Favorite, Guide
from ..services.loaders import guide_card_options

bp = Blueprint("favorites", __name__, url_prefix="/favorites")


@bp.get("/")
@login_required
def favorites():
    """Список избранных моделей."""
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
    return render_template(
        "favorites.html",
        title="Избранное",
        nav_active="favorites",
        guides=guide_rows,
    )
