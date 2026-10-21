"""Тесты порядка уровней сложности."""

from __future__ import annotations

import re

from paintguide.seed import ALL_GUIDES
from paintguide.seed.levels import enrich_variants


def test_levels_are_ordered_from_easy_to_expert():
    """У каждого гайда уровни идут: лёгкая → средняя → сложная → экспертная.

    Достроенные уровни добавлялись в конец списка, и порядок на
    странице получался случайным.
    """
    for guide in ALL_GUIDES:
        levels = [item["difficulty"] for item in enrich_variants(guide)]
        assert levels == ["easy", "medium", "hard", "expert"], guide["slug"]


def test_easiest_level_is_default():
    """Открывается самый простой уровень."""
    for guide in ALL_GUIDES:
        variants = enrich_variants(guide)
        defaults = [item for item in variants if item.get("default")]
        assert len(defaults) == 1, guide["slug"]
        assert defaults[0]["difficulty"] == "easy", guide["slug"]


def test_guide_page_shows_levels_in_order(client):
    """На странице гайда вкладки уровней идут по порядку."""
    body = client.get("/guides/t-34-85").get_data(as_text=True)
    block = re.search(r'<div class="variant-tabs".*?</div>', body, re.S)
    assert block is not None
    order = re.findall(r'href="[^"]*level=([a-z]+)"', block.group(0))
    assert order == sorted(
        order, key=lambda level: ["easy", "medium", "hard", "expert"].index(level)
    )


def test_first_tab_is_active_by_default(client):
    """По умолчанию открыт первый уровень — лёгкая."""
    body = client.get("/guides/t-34-85").get_data(as_text=True)
    block = re.search(r'<div class="variant-tabs".*?</div>', body, re.S)
    assert block is not None
    first = re.search(r'class="variant-tab ([^"]*)"', block.group(0))
    assert first is not None
    assert "active" in first.group(1)
