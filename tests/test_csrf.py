"""Устаревший CSRF-токен и кэширование HTML.

На телефоне форма часто открывается из старой вкладки или из кэша
браузера: токен в ней больше не совпадает с сессией. Раньше такой
запрос заканчивался служебной страницей «Bad Request — The CSRF
tokens do not match». Теперь сервер возвращает пользователя на ту же
страницу с понятным сообщением, а HTML вообще не кэшируется, чтобы
форма всегда была со свежим токеном.
"""

from urllib.parse import urlparse


def test_html_pages_are_not_cached(client):
    """Динамические страницы нельзя кэшировать: иначе устаревает токен."""
    response = client.get("/")
    assert response.status_code == 200
    assert "no-store" in response.headers.get("Cache-Control", "")


def test_static_files_are_still_cached(client):
    """Статика не попадает под запрет кэша — ей нужен свой заголовок."""
    response = client.get("/static/css/site.css")
    assert response.status_code == 200
    assert "no-store" not in response.headers.get("Cache-Control", "")


def test_csrf_failure_returns_to_same_page_with_flash(app, client):
    """POST с мёртвым токеном уходит назад на свою же страницу."""
    app.config["WTF_CSRF_ENABLED"] = True
    response = client.post(
        "/login",
        data={"email": "reader@paintguide.local", "password": "secret"},
        headers={"Referer": "http://localhost/login"},
    )

    assert response.status_code == 303
    assert urlparse(response.headers["Location"]).path == "/login"

    with client.session_transaction() as session:
        flashes = session.get("_flashes", [])
    assert flashes, "после возврата должно всплыть сообщение"
    category, message = flashes[0]
    assert category == "info"
    # Локаль по умолчанию в тестах — русская.
    assert message.startswith("Токен защиты устарел")


def test_csrf_failure_without_referer_shows_friendly_page(app, client):
    """Без referer — та же понятная страница, а не «Bad Request»."""
    app.config["WTF_CSRF_ENABLED"] = True
    response = client.post("/login", data={"email": "reader@paintguide.local"})

    assert response.status_code == 400
    body = response.get_data(as_text=True)
    assert "Форма устарела" in body
    assert "The CSRF tokens do not match" not in body
