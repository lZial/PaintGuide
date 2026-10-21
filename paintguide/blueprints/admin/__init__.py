"""Панель администратора."""

from __future__ import annotations

from functools import wraps

from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required
from sqlalchemy import func, select

from ...extensions import db
from ...models import ActionLog, Country, Guide, Paint, User
from ...services.stats import top_paths, total_views, visits_by_day

bp = Blueprint("admin", __name__)


def admin_required(view):
    """Доступ только для администраторов."""

    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@bp.before_request
@login_required
def restrict_to_admins():
    """Единый шлюз для всех разделов админки."""
    if not current_user.is_admin:
        abort(403)

@bp.get("/")
def dashboard():
    """Сводка: счётчики, посещаемость и последние действия."""
    counts = {
        "guides": db.session.scalar(select(func.count(Guide.id))) or 0,
        "published": db.session.scalar(
            select(func.count(Guide.id)).where(Guide.published.is_(True))
        )
        or 0,
        "paints": db.session.scalar(select(func.count(Paint.id))) or 0,
        "users": db.session.scalar(select(func.count(User.id))) or 0,
        "countries": db.session.scalar(select(func.count(Country.id))) or 0,
    }
    recent = list(
        db.session.scalars(select(ActionLog).order_by(ActionLog.created_at.desc()).limit(12))
    )
    latest_guides = list(
        db.session.scalars(select(Guide).order_by(Guide.created_at.desc()).limit(6))
    )
    return render_template(
        "admin/dashboard.html",
        title="Панель администратора",
        nav_active="admin",
        counts=counts,
        recent=recent,
        latest_guides=latest_guides,
        visits=visits_by_day(14),
        total_views=total_views(14),
        top_paths=top_paths(14, 8),
    )


def register_sub_blueprints(app) -> None:
    """Подключить разделы админки (справочники, гайды, краски, пользователи)."""
    from .guides import bp as guides_bp
    from .paints import bp as paints_bp
    from .reference import bp as reference_bp
    from .users import bp as users_bp

    app.register_blueprint(guides_bp, url_prefix="/admin/guides")
    app.register_blueprint(reference_bp, url_prefix="/admin/reference")
    app.register_blueprint(paints_bp, url_prefix="/admin/paints")
    app.register_blueprint(users_bp, url_prefix="/admin/users")
