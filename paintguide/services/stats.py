"""Статистика посещаемости."""

from __future__ import annotations

import hashlib
from datetime import date, timedelta

from flask import request
from sqlalchemy import func

from ..extensions import db
from ..models import PageView, VisitEvent

_TRACKED_PREFIXES = ("/guides", "/catalog", "/paints", "/", "/admin")


def track_visit(path: str) -> None:
    """Увеличить счётчик посещений текущего пути за сегодня."""
    if not path.startswith(_TRACKED_PREFIXES):
        return
    try:
        day = date.today().isoformat()
        normalized = _normalize(path)
        visitor = _visitor_key()

        row = PageView.query.filter_by(day=day, path=normalized).first()
        if row is None:
            row = PageView(day=day, path=normalized, views=0, unique_visitors=0)
            db.session.add(row)
        row.views += 1

        seen = (
            VisitEvent.query.filter_by(day=day, path=normalized, visitor=visitor).first()
        )
        if seen is None:
            db.session.add(VisitEvent(day=day, path=normalized, visitor=visitor))
            row.unique_visitors += 1

        db.session.commit()
    except Exception:  # pragma: no cover - статистика не должна ломать страницу
        db.session.rollback()


def _normalize(path: str) -> str:
    """Сводит страницы гайдов к общему разделу, чтобы счётчик оставался полезным."""
    if path.startswith("/guides/"):
        return "/guides"
    if path.startswith("/paints/"):
        return "/paints"
    return path


def _visitor_key() -> str:
    """Стабильный, необратимый отпечаток посетителя для подсчёта уникальных."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    raw = forwarded.split(",")[0].strip() if forwarded else (request.remote_addr or "local")
    raw = f"{raw}|{request.headers.get('User-Agent', '')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def visits_by_day(days: int = 14) -> list[tuple[str, int]]:
    """Список (день, просмотры) за последние N дней — для графика в админке."""
    since = (date.today() - timedelta(days=days - 1)).isoformat()
    rows = (
        db.session.query(PageView.day, func.sum(PageView.views))
        .filter(PageView.day >= since)
        .group_by(PageView.day)
        .all()
    )
    buckets = {day: 0 for day in _day_range(days)}
    for day, total in rows:
        buckets[day] = int(total or 0)
    return [(day, buckets[day]) for day in sorted(buckets)]


def _day_range(days: int) -> list[str]:
    today = date.today()
    return [(today - timedelta(days=offset)).isoformat() for offset in range(days - 1, -1, -1)]


def total_views(days: int = 14) -> int:
    since = (date.today() - timedelta(days=days)).isoformat()
    value = (
        db.session.query(func.coalesce(func.sum(PageView.views), 0))
        .filter(PageView.day >= since)
        .scalar()
    )
    return int(value or 0)


def top_paths(days: int = 14, limit: int = 10) -> list[tuple[str, int]]:
    since = (date.today() - timedelta(days=days)).isoformat()
    rows = (
        db.session.query(PageView.path, func.sum(PageView.views))
        .filter(PageView.day >= since)
        .group_by(PageView.path)
        .order_by(func.sum(PageView.views).desc())
        .limit(limit)
        .all()
    )
    return [(path, int(total or 0)) for path, total in rows]
