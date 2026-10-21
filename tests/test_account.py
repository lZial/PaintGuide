"""Тесты авторизации и личного кабинета."""

from __future__ import annotations

from paintguide.extensions import db
from paintguide.models import Favorite, PaintStock, User, WishlistItem


def test_register_creates_user(client, app):
    response = client.post(
        "/register",
        data={
            "nickname": "Новый",
            "email": "new@paintguide.local",
            "password": "secret123",
            "password_confirm": "secret123",
            "terms": "on",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="new@paintguide.local").first()
        assert user is not None
        assert user.role == "user"
        assert user.check_password("secret123")


def test_register_rejects_duplicate_email(client):
    response = client.post(
        "/register",
        data={
            "nickname": "Дубль",
            "email": "user@paintguide.local",
            "password": "secret123",
            "password_confirm": "secret123",
            "terms": "on",
        },
    )
    assert response.status_code == 200
    assert "уже занят" in response.get_data(as_text=True)


def test_register_requires_terms(client):
    response = client.post(
        "/register",
        data={
            "nickname": "Без согласия",
            "email": "noterms@paintguide.local",
            "password": "secret123",
            "password_confirm": "secret123",
        },
    )
    assert "соглашение" in response.get_data(as_text=True)


def test_login_with_wrong_password(client):
    response = client.post(
        "/login", data={"email": "user@paintguide.local", "password": "неверный"}
    )
    assert "Неверная почта или пароль" in response.get_data(as_text=True)


def test_login_and_logout(logged_in, client):
    response = logged_in.get("/profile")
    assert response.status_code == 200
    assert "Моделист" in response.get_data(as_text=True)

    response = logged_in.post("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert logged_in.get("/profile").status_code in (302, 401)


def test_favorite_toggle(logged_in, app):
    response = logged_in.post("/guides/t-34-85/favorite", follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        assert Favorite.query.filter_by(target_type="guide").count() == 1

    logged_in.post("/guides/t-34-85/favorite", follow_redirects=True)
    with app.app_context():
        assert Favorite.query.filter_by(target_type="guide").count() == 0


def test_paint_favorite_toggle(logged_in, app):
    logged_in.post("/paints/1/favorite", follow_redirects=True)
    with app.app_context():
        assert Favorite.query.filter_by(target_type="paint").count() == 1


def test_wishlist_add_and_delete(logged_in, app):
    logged_in.post(
        "/wishlist/",
        data={"name": "Panther Ausf. G", "item_type": "model", "notes": "1:35", "quantity": "1"},
        follow_redirects=True,
    )
    with app.app_context():
        entry = WishlistItem.query.filter_by(name="Panther Ausf. G").first()
        assert entry is not None
        entry_id = entry.id

    logged_in.post(f"/wishlist/{entry_id}/delete", follow_redirects=True)
    with app.app_context():
        assert WishlistItem.query.count() == 0


def test_add_all_paints_from_guide_to_wishlist(logged_in, app):
    logged_in.post("/guides/t-34-85/add-paints", data={"variant_id": "1"}, follow_redirects=True)
    with app.app_context():
        assert WishlistItem.query.filter_by(item_type="paint").count() >= 1


def test_inventory_add_and_toggle(logged_in, app):
    logged_in.post(
        "/inventory/", data={"paint_id": "1", "status": "owned", "quantity": "2"}, follow_redirects=True
    )
    with app.app_context():
        stock = PaintStock.query.first()
        assert stock is not None
        assert stock.quantity == 2
        stock_id = stock.id

    logged_in.post(f"/inventory/{stock_id}/toggle", follow_redirects=True)
    with app.app_context():
        assert PaintStock.query.first().status == "wanted"


def test_profile_updates_nickname(logged_in, app):
    logged_in.post(
        "/profile",
        data={"action": "profile", "nickname": "Новое имя", "email": "user@paintguide.local"},
        follow_redirects=True,
    )
    with app.app_context():
        assert User.query.filter_by(email="user@paintguide.local").first().nickname == "Новое имя"


def test_profile_password_change(logged_in, app):
    logged_in.post(
        "/profile",
        data={
            "action": "password",
            "current_password": "paintguide",
            "new_password": "newsecret",
            "new_password_confirm": "newsecret",
        },
        follow_redirects=True,
    )
    with app.app_context():
        user = User.query.filter_by(email="user@paintguide.local").first()
        assert user.check_password("newsecret")
