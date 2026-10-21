"""Одноразовые токены для подтверждения почты и восстановления пароля.

В базу кладётся только хеш: сам токен уходит в письмо и по ссылке,
поэтому по содержимому базы его не восстановить. Токен одноразовый
и имеет срок действия.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

TOKEN_BYTES = 32


def generate_token() -> str:
    """Новый токен для ссылки."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Хеш токена для хранения."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_match(token: str, stored_hash: str) -> bool:
    """Сравнить токен с сохранённым хешем."""
    if not token or not stored_hash:
        return False
    return hmac.compare_digest(hash_token(token), stored_hash)
