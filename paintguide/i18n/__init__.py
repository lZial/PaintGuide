"""Простая i18n-система: словари JSON + helper `t()` для Jinja."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from flask import current_app, g, request, session

LOCALES_DIR = Path(__file__).resolve().parent
DEFAULT_LOCALE = "ru"


@lru_cache(maxsize=8)
def _load(locale: str) -> dict[str, str]:
    path = LOCALES_DIR / f"{locale}.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def available_locales() -> list[str]:
    return sorted(path.stem for path in LOCALES_DIR.glob("*.json"))


def current_locale() -> str:
    """Локаль текущего запроса: сессия → query → поддерживаемые по умолчанию."""
    supported = tuple(current_app.config.get("SUPPORTED_LOCALES", (DEFAULT_LOCALE,)))
    chosen = session.get("locale")
    if chosen in supported:
        return chosen
    requested = request.args.get("lang")
    if requested in supported:
        return requested
    return current_app.config.get("DEFAULT_LOCALE", DEFAULT_LOCALE)


def translate(key: str, **params) -> str:
    """Перевести ключ; при отсутствии вернуть сам ключ."""
    locale = current_locale()
    text = _load(locale).get(key)
    if text is None:
        text = _load(DEFAULT_LOCALE).get(key, key)
    if params:
        try:
            return text.format(**params)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def init_app(app) -> None:
    app.jinja_env.globals["t"] = translate
    app.jinja_env.globals["current_locale"] = current_locale
    app.jinja_env.globals["available_locales"] = available_locales
    app.context_processor(
        lambda: {
            "locale": current_locale(),
            "locale_name": _locale_name(current_locale()),
            # Требуется ли подтверждение адреса: от этого зависит,
            # показывать ли в интерфейсе напоминание о письме.
            "verification_required": bool(
                current_app.config.get("EMAIL_VERIFICATION_REQUIRED")
            ),
        }
    )


def _locale_name(locale: str) -> str:
    return {"ru": "Русский", "en": "English"}.get(locale, locale)
