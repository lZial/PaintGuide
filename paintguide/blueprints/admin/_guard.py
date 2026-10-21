"""Общий guard для разделов админ-панели."""

from __future__ import annotations

from flask import abort, redirect, request, url_for
from flask_login import current_user


def restrict_to_admins():
    """Пропустить только администраторов; гостя отправить на страницу входа."""
    if not current_user.is_authenticated:
        return redirect(url_for("account.login", next=request.path))
    if not current_user.is_admin:
        abort(403)
    return None
