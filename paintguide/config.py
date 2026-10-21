"""Конфигурация приложения PaintGuide."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.pool import StaticPool

BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Базовая конфигурация."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "paintguide-dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{(INSTANCE_DIR / 'paintguide.db').as_posix()}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    WTF_CSRF_TIME_LIMIT = None
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE")

    PER_PAGE = 24
    PAINTS_PER_PAGE = 40
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024

    # Нужно ли подтверждать адрес при регистрации. По умолчанию нет:
    # письма уходят на почту, которая может не дойти, а без входа
    # человек просто не сможет пользоваться сайтом. Включается
    # переменной окружения, если появится настоящий SMTP.
    EMAIL_VERIFICATION_REQUIRED = _env_bool("EMAIL_VERIFICATION_REQUIRED", False)

    # На хостинге без постоянного диска (Vercel) локальная база
    # исчезает при каждом запуске. Тогда требуем внешнюю базу и
    # честно объясняем, что без неё сайт будет пустым.
    REQUIRE_DATABASE_URL = _env_bool("REQUIRE_DATABASE_URL", False)

    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@paintguide.local").strip().lower()
    DEFAULT_LOCALE = os.environ.get("DEFAULT_LOCALE", "ru")
    SUPPORTED_LOCALES = ("ru", "en")

    # Почта для подтверждения адреса и восстановления пароля.
    # Пустой MAIL_SERVER означает «писать письма в instance/mail».
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "").strip()
    MAIL_PORT = os.environ.get("MAIL_PORT", "587").strip()
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "").strip()
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "").strip()
    MAIL_USE_TLS = _env_bool("MAIL_USE_TLS", True)
    MAIL_FROM = os.environ.get("MAIL_FROM", "PaintGuide <noreply@paintguide.local>").strip()


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", True)


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": False,
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    }
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


CONFIGS = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def resolve_config(name: str | None = None):
    key = (name or os.environ.get("FLASK_CONFIG") or "development").lower()
    return CONFIGS.get(key, DevelopmentConfig)
