"""Модель пользователя, избранное, вишлист и инвентарь красок."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db, login_manager


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(320), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    nickname = db.Column(db.String(40), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user", index=True)
    is_blocked = db.Column(db.Boolean, nullable=False, default=False)
    terms_accepted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    # Почта подтверждена: до этого момента аккаунт не считается рабочим.
    email_verified_at = db.Column(db.DateTime(timezone=True), nullable=True)
    # Новый адрес, ещё не подтверждённый: действует только после ссылки
    # из письма, старый при этом остаётся рабочим.
    pending_email = db.Column(db.String(320), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)

    favorites = db.relationship(
        "Favorite", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    wishlist_items = db.relationship(
        "WishlistItem", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    paint_stock = db.relationship(
        "PaintStock", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    tokens = db.relationship(
        "AccountToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_verified(self) -> bool:
        """Подтверждена ли почта."""
        return self.email_verified_at is not None

    @property
    def initials(self) -> str:
        return (self.nickname or self.email or "?")[0].upper()

    def token_for(self, purpose: str) -> "AccountToken | None":
        """Живой токен нужного назначения."""
        now = utc_now()
        for token in self.tokens:
            if token.purpose == purpose and token.is_usable(now):
                return token
        return None

    def __repr__(self) -> str:  # pragma: no cover - отладочное представление
        return f"<User {self.email}>"


class AccountToken(db.Model):
    """Одноразовый токен: подтверждение почты или восстановление пароля.

    В базе лежит только хеш токена: сам токен уходит в письмо и по
    ссылке, поэтому по базе его не восстановить.
    """

    __tablename__ = "account_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purpose = db.Column(db.String(20), nullable=False, index=True)  # verify | reset
    token_hash = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)

    user = db.relationship("User", back_populates="tokens")

    def is_usable(self, now: datetime | None = None) -> bool:
        """Токен ещё можно использовать."""
        moment = now or utc_now()
        if self.used_at is not None:
            return False
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return expires > moment

    def mark_used(self) -> None:
        self.used_at = utc_now()

    @staticmethod
    def lifetime(purpose: str) -> timedelta:
        """Срок действия токена."""
        if purpose == "reset":
            return timedelta(hours=2)
        return timedelta(days=2)

    def __repr__(self) -> str:  # pragma: no cover - отладочное представление
        return f"<AccountToken {self.purpose} user={self.user_id}>"


@login_manager.user_loader
def load_user(user_id: str):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


class Favorite(db.Model):
    """Избранное: модель (гайд)."""

    __tablename__ = "favorites"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_type = db.Column(db.String(10), nullable=False, index=True)  # guide
    target_id = db.Column(db.Integer, nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    user = db.relationship("User", back_populates="favorites")
    __table_args__ = (
        db.UniqueConstraint("user_id", "target_type", "target_id", name="uq_favorite_target"),
    )


class WishlistItem(db.Model):
    """Вишлист: краска, которую планируется купить и применить."""

    __tablename__ = "wishlist_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    item_type = db.Column(db.String(20), nullable=False, default="paint", index=True)
    item_id = db.Column(db.Integer, nullable=True)
    name = db.Column(db.String(180), nullable=False)
    notes = db.Column(db.String(500), nullable=False, default="")
    quantity = db.Column(db.Integer, nullable=False, default=1)
    position = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    user = db.relationship("User", back_populates="wishlist_items")
    __table_args__ = (
        db.UniqueConstraint("user_id", "item_type", "item_id", name="uq_wishlist_target"),
    )


class PaintStock(db.Model):
    """Инвентарь красок: что есть на полке и что планируется купить."""

    __tablename__ = "paint_stock"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    paint_id = db.Column(db.Integer, db.ForeignKey("paints.id", ondelete="CASCADE"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="owned", index=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    notes = db.Column(db.String(300), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    user = db.relationship("User", back_populates="paint_stock")
    paint = db.relationship("Paint", back_populates="stock_entries")
    __table_args__ = (
        db.UniqueConstraint("user_id", "paint_id", name="uq_paint_stock_user_paint"),
    )
