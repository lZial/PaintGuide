"""Справочники: страны, типы техники, уровни сложности, бренды и линейки красок."""

from __future__ import annotations

from ..extensions import db


def _localized(ru: str, en: str) -> str:
    """Имя справочника по текущей локали страницы."""
    from ..i18n import current_locale

    if current_locale() != "ru" and en:
        return en
    return ru


class Country(db.Model):
    __tablename__ = "countries"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(60), unique=True, nullable=False, index=True)
    name_ru = db.Column(db.String(80), nullable=False)
    name_en = db.Column(db.String(80), nullable=False, default="")
    region = db.Column(db.String(60), nullable=False, default="")
    flag = db.Column(db.String(16), nullable=False, default="")
    sort_order = db.Column(db.Integer, nullable=False, default=100)

    guides = db.relationship("Guide", back_populates="country")

    @property
    def name(self) -> str:
        return _localized(self.name_ru, self.name_en)

    @property
    def english_name(self) -> str:
        return self.name_en or self.name_ru


class VehicleType(db.Model):
    __tablename__ = "vehicle_types"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(60), unique=True, nullable=False, index=True)
    name_ru = db.Column(db.String(80), nullable=False)
    name_en = db.Column(db.String(80), nullable=False, default="")
    icon = db.Column(db.String(40), nullable=False, default="")
    sort_order = db.Column(db.Integer, nullable=False, default=100)

    guides = db.relationship("Guide", back_populates="vehicle_type")

    @property
    def name(self) -> str:
        return _localized(self.name_ru, self.name_en)


class Difficulty(db.Model):
    """Уровень сложности покраски: от лёгкого до экспертного."""

    __tablename__ = "difficulties"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(30), unique=True, nullable=False, index=True)
    name_ru = db.Column(db.String(60), nullable=False)
    name_en = db.Column(db.String(60), nullable=False, default="")
    rank = db.Column(db.Integer, nullable=False, default=1)
    badge = db.Column(db.String(20), nullable=False, default="easy")
    description_ru = db.Column(db.String(300), nullable=False, default="")

    variants = db.relationship("GuideVariant", back_populates="difficulty")

    @property
    def name(self) -> str:
        return _localized(self.name_ru, self.name_en)


class Brand(db.Model):
    """Производитель красок."""

    __tablename__ = "brands"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(60), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    origin = db.Column(db.String(60), nullable=False, default="")
    sort_order = db.Column(db.Integer, nullable=False, default=100)

    lines = db.relationship(
        "PaintLine", back_populates="brand", cascade="all, delete-orphan", lazy="selectin"
    )
    paints = db.relationship("Paint", back_populates="brand")

    @property
    def paint_count(self) -> int:
        return len(self.paints)
