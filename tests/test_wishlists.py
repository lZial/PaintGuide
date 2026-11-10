"""Тесты множественных вишлистов и публичного доступа по ссылке."""

from __future__ import annotations

from paintguide.extensions import db
from paintguide.models import User, Wishlist, WishlistItem


def _user(app):
    return User.query.filter_by(email="user@paintguide.local").first()


def test_create_wishlist(logged_in, app):
    response = logged_in.post(
        "/wishlist/lists",
        data={"action": "create", "name": "Для танка"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert Wishlist.query.filter_by(user_id=_user(app).id, name="Для танка").count() == 1


def test_add_paint_to_specific_wishlist(logged_in, app):
    logged_in.post(
        "/wishlist/lists", data={"action": "create", "name": "Заказ"}, follow_redirects=True
    )
    with app.app_context():
        second = Wishlist.query.filter_by(user_id=_user(app).id, name="Заказ").first()
    logged_in.post(
        "/wishlist/add",
        data={"wishlist_id": second.id, "paint_id": "1", "quantity": "2"},
        follow_redirects=True,
    )
    with app.app_context():
        item = WishlistItem.query.filter_by(wishlist_id=second.id, item_id=1).first()
        assert item is not None
        assert item.quantity == 2


def test_same_paint_in_different_wishlists(logged_in, app):
    """Одна краска может быть в разных вишлистах пользователя."""
    logged_in.post("/wishlist/", data={"paint_id": "1"}, follow_redirects=True)
    logged_in.post(
        "/wishlist/lists", data={"action": "create", "name": "Второй"}, follow_redirects=True
    )
    with app.app_context():
        second = Wishlist.query.filter_by(user_id=_user(app).id, name="Второй").first()
    logged_in.post(
        "/wishlist/add",
        data={"wishlist_id": second.id, "paint_id": "1"},
        follow_redirects=True,
    )
    with app.app_context():
        assert WishlistItem.query.filter_by(item_id=1).count() == 2


def test_toggle_public_and_shared_view(logged_in, app):
    logged_in.post(
        "/wishlist/lists", data={"action": "create", "name": "Публичный"}, follow_redirects=True
    )
    with app.app_context():
        wishlist = Wishlist.query.filter_by(user_id=_user(app).id, name="Публичный").first()
        wishlist_id = wishlist.id
    logged_in.post(
        "/wishlist/lists",
        data={"action": "toggle-public", "wishlist_id": wishlist_id},
        follow_redirects=True,
    )
    with app.app_context():
        wishlist = db.session.get(Wishlist, wishlist_id)
        assert wishlist.is_public
        assert wishlist.share_token is not None
        token = wishlist.share_token

    response = logged_in.get(f"/wishlist/share/{token}")
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "Публичный" in text


def test_delete_wishlist(logged_in, app):
    logged_in.post(
        "/wishlist/lists", data={"action": "create", "name": "Удалимый"}, follow_redirects=True
    )
    with app.app_context():
        wishlist_id = Wishlist.query.filter_by(
            user_id=_user(app).id, name="Удалимый"
        ).first().id
    logged_in.post(f"/wishlist/lists/{wishlist_id}/delete", follow_redirects=True)
    with app.app_context():
        assert db.session.get(Wishlist, wishlist_id) is None
