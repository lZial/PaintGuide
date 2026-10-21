"""Тесты: перезагрузка каталога не должна сбрасывать аккаунты."""

from __future__ import annotations

from paintguide.extensions import db
from paintguide.models import AccountToken, Favorite, User, WishlistItem


def _make_extra_user(email: str = "own@paintguide.local") -> User:
    user = User(email=email, nickname="Свой", role="user", email_verified_at=None)
    user.set_password("secret123")
    db.session.add(user)
    db.session.commit()
    return user


def test_seed_reset_keeps_accounts(app):
    """`seed --reset` очищает каталог, но аккаунты остаются.

    Иначе перезагрузка данных обнуляла бы избранное, вишлист и
    инвентарь, заведённые пользователем.
    """
    from paintguide.seed import load_seed_data

    with app.app_context():
        user = User.query.filter_by(email="user@paintguide.local").first()
        assert user is not None
        original_hash = user.password_hash
        original_id = user.id

        # Пользовательские записи, которые обязаны выжить.
        favorite = Favorite(
            user_id=user.id, target_type="guide", target_id=1, created_at=user.created_at
        )
        wish = WishlistItem(
            user_id=user.id, item_type="model", name="Модель", quantity=2
        )
        db.session.add_all([favorite, wish])
        db.session.commit()
        favorite_id = favorite.id
        wish_id = wish.id

        load_seed_data(reset=True)

        # Аккаунт на месте, пароль прежний.
        user = db.session.get(User, original_id)
        assert user is not None
        assert user.email == "user@paintguide.local"
        assert user.password_hash == original_hash
        assert user.check_password("paintguide")
        # Подтверждение почты не сбрасывается.
        assert user.is_verified is True

        # Пользовательские записи тоже на месте.
        assert db.session.get(Favorite, favorite_id) is not None
        assert db.session.get(WishlistItem, wish_id) is not None

        # Демо-входы не пересоздаются с новым паролем.
        admin = User.query.filter_by(email="admin@paintguide.local").first()
        assert admin is not None
        assert admin.is_admin is True
        assert admin.check_password("paintguide")


def test_seed_reset_users_removes_other_accounts(app):
    """Явный флаг --reset-users удаляет аккаунты, кроме демо-входов."""
    from paintguide.seed import load_seed_data

    with app.app_context():
        own = _make_extra_user()
        own_id = own.id
        db.session.add(
            AccountToken(
                user_id=own_id,
                purpose="verify",
                token_hash="a" * 64,
                expires_at=own.created_at,
            )
        )
        db.session.commit()

        load_seed_data(reset_users=True)

        # Свой аккаунт удалён вместе с токенами.
        assert db.session.get(User, own_id) is None
        assert AccountToken.query.count() == 0
        # Демо-входы сид создаёт заново — с ними всё в порядке.
        assert User.query.filter_by(email="admin@paintguide.local").first() is not None
        assert User.query.filter_by(email="admin@paintguide.local").first().is_verified
