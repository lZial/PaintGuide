"""Управление пользователями и просмотр журнала действий."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func, or_, select

from ...extensions import db
from ...models import ActionLog, User, utc_now
from ...services.log import log_action
from ...services.stats import top_paths, total_views, visits_by_day

bp = Blueprint("admin_users", __name__, url_prefix="/users")


@bp.before_request
def _guard():
    from ._guard import restrict_to_admins

    return restrict_to_admins()


@bp.get("/")
def index():
    """Список пользователей с поиском."""
    search = (request.args.get("q") or "").strip()[:100]
    stmt = select(User)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(User.email.ilike(pattern), User.nickname.ilike(pattern)))
    users = list(db.session.scalars(stmt.order_by(User.created_at.desc()).limit(200)))
    return render_template(
        "admin/users.html",
        title="Пользователи",
        nav_active="admin",
        users=users,
        search=search,
    )


@bp.post("/<int:user_id>/role")
def toggle_role(user_id: int):
    """Выдать или снять права администратора."""
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("Нельзя изменить собственные права.", "error")
        return redirect(url_for("admin_users.index"))
    user.role = "user" if user.is_admin else "admin"
    db.session.commit()
    log_action(
        current_user.id,
        "user.role",
        "user",
        user.email,
        f"Новая роль: {user.role}",
    )
    flash(f"Роль пользователя {user.email} изменена.", "success")
    return redirect(url_for("admin_users.index"))


@bp.post("/<int:user_id>/block")
def toggle_block(user_id: int):
    """Заблокировать или разблокировать пользователя."""
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("Нельзя заблокировать самого себя.", "error")
        return redirect(url_for("admin_users.index"))
    user.is_blocked = not user.is_blocked
    db.session.commit()
    log_action(
        current_user.id,
        "user.block" if user.is_blocked else "user.unblock",
        "user",
        user.email,
    )
    flash(f"Статус пользователя {user.email} обновлён.", "success")
    return redirect(url_for("admin_users.index"))


@bp.post("/<int:user_id>/verify")
def verify_user(user_id: int):
    """Подтвердить адрес пользователя вручную.

    Иногда письмо теряется: тогда подтверждение делает администратор.
    """
    user = db.get_or_404(User, user_id)
    if user.is_verified:
        flash(f"Адрес {user.email} уже подтверждён.", "info")
        return redirect(url_for("admin_users.index"))
    user.email_verified_at = utc_now()
    # Незавершённые токены больше не нужны.
    for token in list(user.tokens):
        if token.purpose == "verify":
            token.mark_used()
    db.session.commit()
    log_action(
        current_user.id,
        "user.verified",
        "user",
        user.email,
        "Адрес подтверждён администратором",
    )
    flash(f"Адрес {user.email} подтверждён.", "success")
    return redirect(url_for("admin_users.index"))


@bp.get("/logs")
def logs():
    """Журнал действий с фильтром по типу."""
    action = (request.args.get("action") or "").strip()[:60]
    stmt = select(ActionLog)
    if action:
        stmt = stmt.where(ActionLog.action == action)
    rows = list(db.session.scalars(stmt.order_by(ActionLog.created_at.desc()).limit(300)))
    actions = list(
        db.session.scalars(select(ActionLog.action).distinct().order_by(ActionLog.action))
    )
    return render_template(
        "admin/logs.html",
        title="Логи действий",
        nav_active="admin",
        logs=rows,
        actions=actions,
        action_filter=action,
    )


@bp.get("/stats")
def stats():
    """Статистика посещаемости."""
    return render_template(
        "admin/stats.html",
        title="Статистика",
        nav_active="admin",
        visits=visits_by_day(30),
        total=total_views(30),
        top=top_paths(30, 12),
    )
