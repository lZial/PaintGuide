"""Логи действий и статистика посещаемости."""

from __future__ import annotations

from ..extensions import db
from .user import utc_now


class ActionLog(db.Model):
    """Журнал административных и пользовательских действий."""

    __tablename__ = "action_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_label = db.Column(db.String(80), nullable=False, default="")
    action = db.Column(db.String(60), nullable=False, index=True)
    entity_type = db.Column(db.String(40), nullable=False, default="", index=True)
    entity_label = db.Column(db.String(200), nullable=False, default="")
    detail = db.Column(db.String(400), nullable=False, default="")
    ip = db.Column(db.String(60), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, index=True)

    user = db.relationship("User")


class PageView(db.Model):
    """Агрегированная статистика посещений по дням и разделам."""

    __tablename__ = "page_views"

    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(10), nullable=False, index=True)
    path = db.Column(db.String(200), nullable=False, default="/", index=True)
    views = db.Column(db.Integer, nullable=False, default=0)
    unique_visitors = db.Column(db.Integer, nullable=False, default=0)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    __table_args__ = (db.UniqueConstraint("day", "path", name="uq_page_view_day_path"),)


class VisitEvent(db.Model):
    """Событие посещения: позволяет считать уникальных посетителей за день."""

    __tablename__ = "visit_events"

    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(10), nullable=False, index=True)
    path = db.Column(db.String(200), nullable=False, default="/", index=True)
    visitor = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (db.Index("ix_visit_events_day_path_visitor", "day", "path", "visitor"),)
