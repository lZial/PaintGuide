"""PaintGuide — база руководств по окраске моделей военной техники."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, g, render_template, request

from .config import INSTANCE_DIR, resolve_config
from .extensions import csrf, db, login_manager

BASE_DIR = Path(__file__).resolve().parent.parent

__all__ = ["create_app", "db", "csrf", "login_manager"]


def create_app(config_name: str | None = None) -> Flask:
    load_dotenv(BASE_DIR / ".env")

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        instance_path=str(INSTANCE_DIR),
    )
    app.config.from_object(resolve_config(config_name))
    app.config.from_prefixed_env("PAINTGUIDE")
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

    _init_extensions(app)
    _register_blueprints(app)
    _register_context(app)
    _register_hooks(app)
    _register_errors(app)
    _register_cli(app)
    _register_proxy_fix(app)

    _prepare_database(app)
    _check_production_settings(app)

    return app


def _check_production_settings(app: Flask) -> None:
    """Проверить настройки боевого режима.

    Секретный ключ по умолчанию годится только для разработки: на хостинге
    после каждого деплоя он меняется, и сессии разлогинивают, а токены
    подтверждения почты перестают работать. Лучше сказать об этом при
    старте, чем разбираться позже.
    """
    if not app.config.get("REQUIRE_DATABASE_URL"):
        return

    secret = (os.environ.get("SECRET_KEY") or "").strip()
    if not secret or secret == "paintguide-dev-secret-change-me":
        raise RuntimeError(
            "Задайте постоянный SECRET_KEY: без него при каждом деплое "
            "сессии сбрасываются. Сгенерировать: "
            "python -c \"import secrets; print(secrets.token_hex(32))\""
        )


def _prepare_database(app: Flask) -> None:
    """Подготовить базу к работе.

    На новом хостинге базы ещё нет — создаём таблицы. Но на хостинге
    без постоянного диска (Vercel) локальная база исчезает при каждом
    запуске, поэтому там нужна внешняя: без DATABASE_URL приложение
    поднимется, но страницы окажутся пустыми. О таком случае лучше
    сказать прямо.

    Схему трогаем только когда базы ещё нет: на Vercel приложение
    поднимается при каждом холодном старте, и лишние запросы к базе
    там обходятся дорого.
    """
    from .migrations import drop_obsolete_columns, ensure_schema

    if not app.config.get("REQUIRE_DATABASE_URL"):
        with app.app_context():
            db.create_all()
        ensure_schema(app)
        drop_obsolete_columns(app)
        return

    if not (os.environ.get("DATABASE_URL") or "").strip():
        raise RuntimeError(
            "Для этого хостинга нужна внешняя база: задайте переменную "
            "DATABASE_URL (например, Postgres из Neon)."
        )

    from .models import Guide

    with app.app_context():
        try:
            db.session.scalar(db.select(db.func.count(Guide.id)))
        except Exception:  # noqa: BLE001
            # Таблиц ещё нет — создаём.
            db.session.rollback()
            db.create_all()
            ensure_schema(app)
            drop_obsolete_columns(app)


def _register_proxy_fix(app: Flask) -> None:
    """Учитывать заголовки обратного прокси.

    Нужно, когда приложение открыто через туннель или хостинг: без этого
    Flask считает, что соединение идёт по обычному HTTP, и неверно
    определяет внешний адрес и защищённость cookie.
    """
    from werkzeug.middleware.proxy_fix import ProxyFix

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)


def _init_extensions(app: Flask) -> None:
    app.config["SQLALCHEMY_DATABASE_URI"] = _resolve_database_uri(app)
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = _engine_options(app)
    app.config["ENGINE_OPTIONS"] = _engine_options(app)
    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    _register_sqlite_functions(app)

    from . import models  # noqa: F401  (регистрация моделей в метаданных)


def _register_sqlite_functions(app: Flask) -> None:
    """Научить SQLitelower() работать с кириллицей.

    Встроенная функция SQLite переводит в нижний регистр только ASCII,
    поэтому поиск по русским словам («Проливка» → «проливка») не
    срабатывал. Своя функция решает это на уровне соединения.
    """
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    @event.listens_for(Engine, "connect")
    def _install(dbapi_connection, connection_record):  # pragma: no cover
        if not hasattr(dbapi_connection, "create_function"):
            return
        dbapi_connection.create_function(
            "lower", 1, lambda value: value.lower() if isinstance(value, str) else value
        )
        # Режим WAL: с ним несколько процессов (gunicorn) читают базу
        # одновременно, не блокируя друг друга.
        if dbapi_connection.__class__.__module__.startswith("sqlite3"):
            try:
                dbapi_connection.execute("PRAGMA journal_mode=WAL")
                dbapi_connection.execute("PRAGMA busy_timeout=10000")
            except Exception:
                pass


def _resolve_database_uri(app: Flask) -> str:
    """URI базы: DATABASE_URL из окружения, иначе значение из конфига, иначе локальный SQLite."""
    raw = os.environ.get("DATABASE_URL", "").strip()
    if raw:
        if raw.startswith("postgres://"):
            return raw.replace("postgres://", "postgresql+psycopg://", 1)
        if raw.startswith("postgresql://") and "+psycopg" not in raw:
            return raw.replace("postgresql://", "postgresql+psycopg://", 1)
        return raw
    existing = app.config.get("SQLALCHEMY_DATABASE_URI")
    if existing:
        return existing
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{(INSTANCE_DIR / 'paintguide.db').as_posix()}"


def _engine_options(app: Flask) -> dict:
    """Параметры движка: настройки из конфига имеют приоритет.

    Для внешней базы пул соединений ограничен: на Vercel одновременно
    живёт несколько экземпляров приложения, и каждый держит свой пул.
    Без ограничения они исчерпают лимит соединений у Neon.
    """
    options: dict = dict(app.config.get("SQLALCHEMY_ENGINE_OPTIONS") or {})
    options.setdefault("pool_pre_ping", True)
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        options.setdefault("connect_args", {"check_same_thread": False})
    else:
        options.setdefault("pool_size", 2)
        options.setdefault("max_overflow", 0)
        options.setdefault("pool_recycle", 300)
    return options


def _register_blueprints(app: Flask) -> None:
    from .blueprints.account import bp as account_bp
    from .blueprints.admin import bp as admin_bp
    from .blueprints.admin import register_sub_blueprints
    from .blueprints.catalog import bp as catalog_bp
    from .blueprints.favorites import bp as favorites_bp
    from .blueprints.guide import bp as guide_bp
    from .blueprints.inventory import bp as inventory_bp
    from .blueprints.main import bp as main_bp
    from .blueprints.paints import bp as paints_bp
    from .blueprints.wishlist import bp as wishlist_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(guide_bp)
    app.register_blueprint(paints_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(favorites_bp)
    app.register_blueprint(wishlist_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    register_sub_blueprints(app)


def _register_context(app: Flask) -> None:
    from .i18n import init_app as init_i18n

    init_i18n(app)

    @app.context_processor
    def inject_globals():
        # Справочники не подмешиваются глобально: каждый шаблон получает
        # только те списки, которые ему действительно нужны. Это экономит
        # четыре запроса к базе на каждый просмотр страницы.
        return {"theme": _current_theme()}


def _current_theme() -> str:
    """Текущая тема из cookie; по умолчанию — тёмная."""
    from flask import request

    theme = request.cookies.get("pg_theme")
    return theme if theme in {"dark", "light"} else "dark"


def _register_hooks(app: Flask) -> None:
    from .services.stats import track_visit

    @app.before_request
    def _before():
        g.started_at = None

    @app.after_request
    def _after(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if request.path.startswith("/static/"):
            response.headers.setdefault("Cache-Control", "public, max-age=86400")
        return response

    @app.teardown_appcontext
    def _teardown(exception=None):
        if exception is not None:
            db.session.rollback()

    app.extensions["track_visit"] = track_visit


def _register_errors(app: Flask) -> None:
    from .i18n import translate

    @app.errorhandler(403)
    def forbidden(_error):
        return (
            render_template(
                "error.html",
                code=403,
                title=translate("error.403.title"),
                message=translate("error.403.text"),
            ),
            403,
        )

    @app.errorhandler(404)
    def not_found(_error):
        return (
            render_template(
                "error.html",
                code=404,
                title=translate("error.404.title"),
                message=translate("error.404.text"),
            ),
            404,
        )

    @app.errorhandler(500)
    def server_error(_error):  # pragma: no cover - аварийный сценарий
        db.session.rollback()
        return (
            render_template(
                "error.html",
                code=500,
                title=translate("error.500.title"),
                message=translate("error.500.text"),
            ),
            500,
        )


def _register_cli(app: Flask) -> None:
    import click

    @app.cli.command("init-db")
    def init_db() -> None:
        """Создать схему базы данных."""
        db.create_all()
        click.echo("Схема базы данных готова.")

    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, help="Очистить каталог перед загрузкой данных.")
    @click.option(
        "--reset-users",
        is_flag=True,
        help="Удалить и аккаунты пользователей (по умолчанию они сохраняются).",
    )
    def seed(reset: bool, reset_users: bool) -> None:
        """Загрузить справочники, краски и руководства.

        Аккаунты пользователей при перезагрузке каталога сохраняются:
        избранное, вишлист и инвентарь остаются на месте. Удалить их
        можно только явно, флагом --reset-users.
        """
        from .seed import load_seed_data

        db.create_all()
        created = load_seed_data(reset=reset, reset_users=reset_users)
        click.echo(
            "Загружено: {countries} стран, {vehicles} типов техники, {paints} красок, "
            "{guides} руководств.".format(**created)
        )

    @app.cli.command("create-admin")
    @click.argument("email")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(email: str, password: str) -> None:
        """Создать или повысить пользователя до администратора."""
        from .models import User
        from .services.log import log_action

        normalized = email.strip().lower()
        user = User.query.filter_by(email=normalized).first()
        if user is None:
            user = User(email=normalized, nickname=normalized.split("@")[0], role="admin")
            user.set_password(password)
            db.session.add(user)
        else:
            user.role = "admin"
            user.set_password(password)
        db.session.commit()
        log_action(user.id, "admin.create", "user", user.email, f"Администратор {user.email}")
        click.echo(f"Готово: {user.email} — администратор.")
