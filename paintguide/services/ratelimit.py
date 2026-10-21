"""Ограничение частоты запросов на чувствительные страницы.

Вход, регистрация и восстановление пароля нельзя перебирать: без
ограничения можно перебрать пароль или завалить почту письмами.
Счётчики живут в памяти процесса — этого достаточно для одной копии
приложения, а при нескольких копиях общий Postgres-хранилище можно
подключить позже.
"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

# Сколько попыток за окно и длина окна в секундах.
LIMITS = {
    "login": (10, 300.0),
    "register": (5, 3600.0),
    "verify": (10, 3600.0),
    "reset": (5, 3600.0),
}

_attempts: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def _key(scope: str, identity: str) -> str:
    return f"{scope}:{identity.lower()}"


def check(scope: str, identity: str) -> tuple[bool, int]:
    """Проверить, можно ли выполнить действие.

    Возвращает (можно, сколько секунд ждать).
    """
    limit, window = LIMITS.get(scope, (10, 300.0))
    now = time.monotonic()
    key = _key(scope, identity)
    with _lock:
        moments = [moment for moment in _attempts[key] if now - moment < window]
        if len(moments) >= limit:
            wait = int(window - (now - moments[0])) + 1
            _attempts[key] = moments
            return False, wait
        _attempts[key] = moments
    return True, 0


def hit(scope: str, identity: str) -> None:
    """Отметить попытку."""
    limit, window = LIMITS.get(scope, (10, 300.0))
    now = time.monotonic()
    key = _key(scope, identity)
    with _lock:
        moments = [moment for moment in _attempts[key] if now - moment < window]
        moments.append(now)
        _attempts[key] = moments[-limit:]


def reset(scope: str, identity: str) -> None:
    """Сбросить счётчик — после успешного входа."""
    key = _key(scope, identity)
    with _lock:
        _attempts.pop(key, None)


def clear() -> None:
    """Очистить все счётчики — для тестов."""
    with _lock:
        _attempts.clear()
