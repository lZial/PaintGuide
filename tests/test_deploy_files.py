"""Тесты файлов публикации: точка входа, сборка, настройки хостинга."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_entrypoint_exposes_app():
    """Vercel ищет объект Flask с именем app.

    Имя файла должно быть из списка Vercel: app.py, index.py,
    server.py, main.py, wsgi.py, asgi.py.
    """
    import main

    assert hasattr(main, "app")
    assert main.app.name == "paintguide"
    assert main.__file__.endswith(("main.py", "wsgi.py", "app.py", "server.py", "index.py"))


def test_vercel_config_is_valid():
    """vercel.json — корректный JSON с нужными полями."""
    data = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    assert data["framework"] == "flask"
    assert data["buildCommand"] == "python build.py"
    assert data["env"]["REQUIRE_DATABASE_URL"] == "1"
    assert data["env"]["FLASK_CONFIG"] == "production"
    # Подтверждение адреса по умолчанию выключено: письма не всегда
    # доходят, а человек без входа не сможет пользоваться сайтом.
    assert data["env"]["EMAIL_VERIFICATION_REQUIRED"] == "0"


def test_build_script_copies_static():
    """Сборка кладёт статику в public/static.

    На Vercel папка static_folder Flask не раздаётся — файлы кладутся
    в public/**, и Vercel отдаёт их через CDN.
    """
    source = (ROOT / "build.py").read_text(encoding="utf-8")
    assert "paintguide/static" in source or "STATIC_SOURCE" in source
    assert "public" in source
    assert "create_all" not in source  # таблицы создаёт приложение


def test_gitignore_excludes_local_data():
    """Локальная база и собранная статика не попадают в репозиторий."""
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "instance/" in text
    assert "public/" in text
    assert ".env" in text
    assert "*.db" in text


def test_requirements_contain_server_and_driver():
    """Нужны gunicorn (на Linux) и драйвер Postgres."""
    text = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "gunicorn" in text
    assert "psycopg" in text


def test_production_requires_secret_and_database():
    """В боевом режиме нужны SECRET_KEY и внешняя база."""
    source = (ROOT / "paintguide" / "__init__.py").read_text(encoding="utf-8")
    assert "SECRET_KEY" in source
    assert "DATABASE_URL" in source
    assert "REQUIRE_DATABASE_URL" in source


def test_readme_has_publication_guide():
    """В README есть пошаговое руководство по публикации."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Как опубликовать на Vercel" in text
    assert "DATABASE_URL" in text
    assert "SECRET_KEY" in text
    assert "neon.tech" in text
