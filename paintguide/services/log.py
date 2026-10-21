"""Журнал действий пользователей и администраторов."""

from __future__ import annotations

from ..extensions import db
from ..models import ActionLog

MAX_DETAIL = 400


def log_action(
    user_id: int | None,
    action: str,
    entity_type: str = "",
    entity_label: str = "",
    detail: str = "",
    ip: str = "",
) -> ActionLog:
    """Записать действие в журнал. Ошибки логирования не должны ломать запрос."""
    try:
        entry = ActionLog(
            user_id=user_id,
            user_label=_user_label(user_id),
            action=action,
            entity_type=entity_type,
            entity_label=(entity_label or "")[:200],
            detail=(detail or "")[:MAX_DETAIL],
            ip=(ip or "")[:60],
        )
        db.session.add(entry)
        db.session.commit()
        return entry
    except Exception:  # pragma: no cover - журнал не критичен
        db.session.rollback()
        return None


def _user_label(user_id: int | None) -> str:
    if not user_id:
        return "гость"
    from ..models import User

    user = db.session.get(User, user_id)
    if user is None:
        return "гость"
    return user.nickname or user.email
