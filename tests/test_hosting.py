"""Проверки для хостинга: Vercel, Vercel-окружение, только чтение.

Здесь собраны ошибки, которые не видны на локальной машине:
на сервере файловая система только для чтения, а переменная
DATABASE_URL указывает на боевую базу.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paintguide  # noqa: E402
from paintguide import create_app  # noqa: E402


class _ReadOnlyDir:
    """Папка по обычному пути, но создать её нельзя."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def mkdir(self, *args, **kwargs):
        raise OSError(30, "Read-only file system")

    def __str__(self) -> str:
        return str(self._path)

    def __truediv__(self, other):
        return self._path / other


def test_app_starts_on_readonly_filesystem(monkeypatch):
    """Приложение должно подниматься, даже если папку instance не создать.

    На Vercel файловая система функции только для чтения. Если на старте
    попытаться создать папку, приложение падает с ошибкой — и каждая
    страница отдаёт 500.
    """
    monkeypatch.setattr(paintguide, "INSTANCE_DIR", _ReadOnlyDir(paintguide.BASE_DIR / "instance"))
    app = create_app("testing")
    assert app is not None
    assert app.test_client().get("/healthz").status_code == 200


def test_tests_never_touch_live_database(monkeypatch):
    """В тестах используется база из конфига, а не из окружения.

    Тесты создают и удаляют таблицы. Если бы они подхватили
    DATABASE_URL из окружения, то удалили бы таблицы боевой базы.
    """
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@example.invalid/db")
    app = create_app("testing")
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite://"


def test_production_requires_database_url(monkeypatch):
    """Без DATABASE_URL на боевом хостинге приложение не поднимается."""
    app = create_app("testing")
    app.config["REQUIRE_DATABASE_URL"] = True
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with app.app_context():
        with pytest.raises(RuntimeError):
            paintguide._prepare_database(app)


def test_production_requires_secret_key(monkeypatch):
    """Постоянный SECRET_KEY обязателен: иначе после деплоя слетают сессии."""
    app = create_app("testing")
    app.config["REQUIRE_DATABASE_URL"] = True
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError):
        paintguide._check_production_settings(app)


def _count_queries(application, path: str) -> int:
    """Сколько запросов к базе делает страница."""
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    counter = {"n": 0}

    @event.listens_for(Engine, "before_cursor_execute")
    def before(conn, cursor, statement, parameters, context, executemany):
        counter["n"] += 1

    try:
        application.test_client().get(path)
    finally:
        event.remove(Engine, "before_cursor_execute", before)
    return counter["n"]


def test_catalog_does_not_query_every_guide(app):
    """Каталог не должен делать запрос на каждый гайд.

    К удалённой базе каждый запрос — это сеть. Когда карточки тянули
    страну, тип техники и уровни сложности по одному, каталог из
    24 гайдов давал больше сотни запросов и несколько секунд ожидания.
    """
    with app.app_context():
        queries = _count_queries(app, "/catalog")
    assert queries < 30, f"каталог делает {queries} запросов — вернулся N+1"


def test_guide_page_does_not_query_every_paint(app):
    """Страница гайда не должна тянуть краски по одной."""
    with app.app_context():
        queries = _count_queries(app, "/guides/t-34-85")
    assert queries < 30, f"страница гайда делает {queries} запросов — вернулся N+1"


def test_dropped_connection_is_retried(app):
    """Оборванное соединение не должно ронять страницу.

    Neon засыпает при простое и рвёт соединения прямо во время запроса.
    Страница должна открыться со второй попытки, а не отдать 500.
    """
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    from sqlalchemy.exc import OperationalError

    state = {"failed": False}

    @event.listens_for(Engine, "before_cursor_execute")
    def fail_once(conn, cursor, statement, parameters, context, executemany):
        if not state["failed"]:
            state["failed"] = True
            raise OperationalError(
                statement, parameters, Exception("server closed the connection unexpectedly")
            )

    try:
        with app.app_context():
            response = app.test_client().get("/catalog")
    finally:
        event.remove(Engine, "before_cursor_execute", fail_once)

    assert state["failed"], "искусственный обрыв не сработал"
    assert response.status_code == 200, f"страница вернула {response.status_code}"
