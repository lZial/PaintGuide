"""Blueprints приложения PaintGuide."""

from __future__ import annotations

from .account import bp as account_bp
from .catalog import bp as catalog_bp
from .favorites import bp as favorites_bp
from .guide import bp as guide_bp
from .inventory import bp as inventory_bp
from .main import bp as main_bp
from .paints import bp as paints_bp
from .wishlist import bp as wishlist_bp

__all__ = [
    "account_bp",
    "catalog_bp",
    "favorites_bp",
    "guide_bp",
    "inventory_bp",
    "main_bp",
    "paints_bp",
    "wishlist_bp",
]
