"""Точка входа для Vercel.

Vercel ищет объект Flask с именем ``app`` в одном из файлов:
``app.py``, ``index.py``, ``server.py``, ``main.py``, ``wsgi.py``, ``asgi.py``.
Наш основной файл — ``run.py``, но его имя в списке нет, поэтому
делимся той же фабрикой приложения.

Запуск локально остаётся прежним:  python run.py
"""

from __future__ import annotations

from run import app  # noqa: F401  (Vercel требует объект с именем app)

__all__ = ["app"]
