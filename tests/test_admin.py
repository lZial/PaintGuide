"""Тесты админ-панели: права доступа, CRUD, справочники, статистика."""

from __future__ import annotations

from paintguide.extensions import db
from paintguide.models import ActionLog, Country, Guide, Paint, User


def test_admin_area_is_closed_for_guests(client):
    for path in ("/admin/", "/admin/guides/", "/admin/paints/", "/admin/users/"):
        response = client.get(path)
        assert response.status_code in (302, 401)


def test_admin_area_is_closed_for_regular_user(logged_in):
    response = logged_in.get("/admin/")
    assert response.status_code == 403


def test_admin_dashboard_is_available_for_admin(admin_client):
    response = admin_client.get("/admin/")
    assert response.status_code == 200
    assert "Панель администратора" in response.get_data(as_text=True)


def test_admin_can_create_guide(admin_client, app):
    response = admin_client.post(
        "/admin/guides/new",
        data={
            "title": "Новый гайд",
            "slug": "novyy-gayd",
            "country": "ussr",
            "vehicle_type": "tank",
            "year_from": "1943",
            "year_to": "1945",
            "description": "Описание",
            "published": "on",
            "variant_difficulty": ["easy"],
            "step_title_easy_0": "Грунтовка",
            "step_instruction_easy_0": "Нанесите грунт",
            "step_paint1_easy_0": "1",
            "step_area1_easy_0": "Все области",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        guide = Guide.query.filter_by(slug="novyy-gayd").first()
        assert guide is not None
        assert guide.variants
        assert guide.variants[0].steps
        assert guide.variants[0].steps[0].paints


def test_admin_can_edit_guide(admin_client, app):
    admin_client.post(
        "/admin/guides/1/edit",
        data={
            "title": "Т-34-85 (обновлено)",
            "slug": "t-34-85",
            "country": "ussr",
            "vehicle_type": "tank",
            "description": "Новое описание",
            "published": "on",
            "variant_difficulty": ["easy"],
            "step_title_easy_0": "Обновлённая грунтовка",
        },
        follow_redirects=True,
    )
    with app.app_context():
        guide = Guide.query.filter_by(slug="t-34-85").first()
        assert guide.title == "Т-34-85 (обновлено)"
        assert guide.variants[0].steps[0].title == "Обновлённая грунтовка"


def test_admin_can_delete_guide(admin_client, app):
    admin_client.post("/admin/guides/1/delete", follow_redirects=True)
    with app.app_context():
        assert Guide.query.count() == 0


def test_admin_toggle_publish(admin_client, app):
    admin_client.post("/admin/guides/1/publish", follow_redirects=True)
    with app.app_context():
        assert Guide.query.first().published is False


def test_admin_can_create_paint(admin_client, app):
    admin_client.post(
        "/admin/paints/new",
        data={
            "brand_id": "1",
            "line_id": "1",
            "code": "XF-99",
            "name": "Test Colour",
            "color_hex": "#123456",
            "paint_type": "acrylic",
            "description": "Тест",
        },
        follow_redirects=True,
    )
    with app.app_context():
        paint = Paint.query.filter_by(code="XF-99").first()
        assert paint is not None
        assert paint.tone >= 0


def test_admin_can_edit_paint_and_equivalents(admin_client, app):
    admin_client.post(
        "/admin/paints/1/edit",
        data={
            "brand_id": "1",
            "line_id": "1",
            "code": "XF-1",
            "name": "Black",
            "color_hex": "#101010",
            "paint_type": "acrylic",
            "equivalents": "2",
        },
        follow_redirects=True,
    )
    with app.app_context():
        paint = Paint.query.filter_by(code="XF-1").first()
        assert paint.color_hex == "#101010"
        assert len(paint.equivalents) == 1


def test_admin_reference_crud(admin_client, app):
    admin_client.post(
        "/admin/reference/countries",
        data={"slug": "testland", "name_ru": "Тестландия", "name_en": "Testland", "sort_order": "99"},
        follow_redirects=True,
    )
    with app.app_context():
        item = Country.query.filter_by(slug="testland").first()
        assert item is not None
        item_id = item.id

    admin_client.post(f"/admin/reference/countries/{item_id}/delete", follow_redirects=True)
    with app.app_context():
        assert Country.query.filter_by(slug="testland").first() is None


def test_admin_reference_delete_is_blocked_when_in_use(admin_client, app):
    response = admin_client.post(
        "/admin/reference/countries/1/delete", follow_redirects=True
    )
    assert response.status_code == 200
    with app.app_context():
        assert Country.query.count() == 1


def test_admin_can_change_user_role(admin_client, app):
    response = admin_client.post("/admin/users/2/role", follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="user@paintguide.local").first()
        assert user.role == "admin"


def test_admin_can_block_user(admin_client, app):
    admin_client.post("/admin/users/2/block", follow_redirects=True)
    with app.app_context():
        assert User.query.filter_by(email="user@paintguide.local").first().is_blocked is True


def test_admin_logs_and_stats_pages(admin_client):
    assert admin_client.get("/admin/users/logs").status_code == 200
    assert admin_client.get("/admin/users/stats").status_code == 200


def test_actions_are_logged(admin_client, app):
    admin_client.post(
        "/admin/reference/countries",
        data={"slug": "logged", "name_ru": "Лог", "sort_order": "1"},
        follow_redirects=True,
    )
    with app.app_context():
        assert ActionLog.query.count() >= 1
