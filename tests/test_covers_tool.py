"""Тесты инструмента подбора обложек.

Инструмент работает с API Commons: важно, чтобы названия файлов
находились одинаково — с подчёркиваниями и с пробелами.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "fetch_covers", ROOT / "scripts" / "fetch_covers.py"
)
fetch_covers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fetch_covers)


def test_token_normalisation_keeps_both_spellings():
    """Кэш метаданных помнит оба варианта названия файла.

    API отдаёт название с пробелами вместо подчёркиваний, поэтому
    поиск по названию с подчёркиваниями иначе ничего не находит.
    """
    fetch_covers._TITLE_CACHE.clear()
    title = "File:Пример_Файла_(123).jpg"
    item = {
        "title": "File:Пример Файла (123).jpg",
        "width": 800,
        "height": 600,
        "categories": "Тест",
    }
    fetch_covers._TITLE_CACHE[item["title"]] = item
    fetch_covers._TITLE_CACHE[item["title"].replace(" ", "_")] = item

    assert fetch_covers._TITLE_CACHE[title] is item
    assert fetch_covers._TITLE_CACHE[title.replace("_", " ")] is item
    fetch_covers._TITLE_CACHE.clear()


def test_thumb_url_is_built_correctly():
    """Ссылка на миниатюру собирается из адреса оригинала.

    Размер 960 px — из тех, что Wikimedia сейчас принимает; остальные
    отклоняются с кодом 400.
    """
    original = "https://upload.wikimedia.org/wikipedia/commons/0/05/IS-9.jpg"
    url = fetch_covers._thumb_url(original)
    assert url == (
        "https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/960px-IS-9.jpg"
    )
    # Без адреса ссылка не строится.
    assert fetch_covers._thumb_url("") == ""


def test_short_designations_are_detected():
    """Короткие обозначения требуют более строгой проверки."""
    assert fetch_covers._short_designation("m32") is True
    assert fetch_covers._short_designation("t-34-85") is False


def test_match_article_uses_key_words():
    """Сверка статьи идёт по ключевым словам, а не по всей строке."""
    # Число 40 из обозначения совпало, слово «tank» — нет: частичное
    # совпадение, файл всё равно подходит.
    assert fetch_covers.match_article("L6/40 tank", {"title": "Fiat L6 40 05.jpg"}) == 1
    assert fetch_covers.match_article("T-10 tank", {"title": "T-10 tank.jpg"}) == 2
    assert fetch_covers.match_article("SA 201", {"title": "Submarine class.jpg"}) == 0
