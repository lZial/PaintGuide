"""Гайд, уровни сложности, шаги и привязка красок к шагам."""

from __future__ import annotations

from ..extensions import db
from .user import utc_now


class Guide(db.Model):
    """Карточка руководства по окраске единицы техники."""

    __tablename__ = "guides"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(140), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    subtitle = db.Column(db.String(240), nullable=False, default="")
    country_id = db.Column(db.Integer, db.ForeignKey("countries.id"), nullable=False, index=True)
    vehicle_type_id = db.Column(
        db.Integer, db.ForeignKey("vehicle_types.id"), nullable=False, index=True
    )
    year_from = db.Column(db.Integer, nullable=True, index=True)
    year_to = db.Column(db.Integer, nullable=True)
    production = db.Column(db.String(200), nullable=False, default="")
    crew = db.Column(db.String(120), nullable=False, default="")
    description = db.Column(db.Text, nullable=False, default="")
    cover_url = db.Column(db.String(1000), nullable=False, default="")
    cover_credit = db.Column(db.String(200), nullable=False, default="")
    cover_license = db.Column(db.String(60), nullable=False, default="")
    cover_source = db.Column(db.String(500), nullable=False, default="")
    cover_kind = db.Column(db.String(20), nullable=False, default="")
    cover_scale = db.Column(db.String(20), nullable=False, default="")
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    published = db.Column(db.Boolean, nullable=False, default=True, index=True)
    views_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    country = db.relationship("Country", back_populates="guides")
    vehicle_type = db.relationship("VehicleType", back_populates="guides")
    variants = db.relationship(
        "GuideVariant",
        back_populates="guide",
        cascade="all, delete-orphan",
        order_by="GuideVariant.position",
        lazy="selectin",
    )

    @property
    def year_label(self) -> str:
        if self.year_from and self.year_to and self.year_from != self.year_to:
            return f"{self.year_from}–{self.year_to}"
        if self.year_from:
            return str(self.year_from)
        return "—"

    @property
    def meta_line(self) -> str:
        parts = [self.country.name if self.country else "", self.vehicle_type.name if self.vehicle_type else ""]
        parts = [part for part in parts if part]
        parts.append(self.year_label)
        return " · ".join(parts)

    @property
    def default_variant(self) -> "GuideVariant | None":
        if not self.variants:
            return None
        for variant in self.variants:
            if variant.is_default:
                return variant
        return self.variants[0]

    @property
    def difficulty_slugs(self) -> list[str]:
        return [variant.difficulty.slug for variant in self.variants if variant.difficulty]

    @property
    def difficulty_range(self) -> str:
        """Диапазон уровней гайда: «Лёгкая → Экспертная».

        У гайда есть все четыре уровня, поэтому одна метка ничего
        не сообщает: показываем, от чего можно начать и до чего дойти.
        """
        levels = [
            variant.difficulty
            for variant in sorted(
                self.variants,
                key=lambda item: (
                    item.difficulty.rank if item.difficulty else 99,
                    item.position,
                ),
            )
            if variant.difficulty
        ]
        if not levels:
            return "—"
        if len(levels) == 1:
            return levels[0].name
        return f"{levels[0].name} → {levels[-1].name}"

    @property
    def is_hard_guide(self) -> bool:
        """Есть ли у гайда сложные уровни."""
        return any(
            variant.difficulty and variant.difficulty.slug in ("hard", "expert")
            for variant in self.variants
        )

    @property
    def all_paints(self) -> list["Paint"]:
        """Уникальные краски всех вариантов сложности в порядке первого появления."""
        seen: dict[int, Paint] = {}
        for variant in self.variants:
            for step in variant.steps:
                for link in step.paints:
                    if link.paint:
                        seen.setdefault(link.paint.id, link.paint)
        return list(seen.values())

    @property
    def cover_tone(self) -> str:
        """Оттенок карточки-заглушки обложки, если реальной картинки нет."""
        palette = ["#4c5138", "#3f4a3c", "#5a4f37", "#454a4f", "#4d3f38", "#38423f"]
        if self.country_id:
            return palette[self.country_id % len(palette)]
        return palette[0]

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Guide {self.slug}>"


class GuideVariant(db.Model):
    """Конкретный уровень сложности для гайда (лёгкий / средний / сложный)."""

    __tablename__ = "guide_variants"

    id = db.Column(db.Integer, primary_key=True)
    guide_id = db.Column(db.Integer, db.ForeignKey("guides.id", ondelete="CASCADE"), nullable=False)
    difficulty_id = db.Column(
        db.Integer, db.ForeignKey("difficulties.id"), nullable=False, index=True
    )
    title = db.Column(db.String(200), nullable=False, default="")
    summary = db.Column(db.Text, nullable=False, default="")
    time_hours = db.Column(db.Integer, nullable=False, default=0)
    is_default = db.Column(db.Boolean, nullable=False, default=False)
    position = db.Column(db.Integer, nullable=False, default=0)

    guide = db.relationship("Guide", back_populates="variants")
    difficulty = db.relationship("Difficulty", back_populates="variants")
    steps = db.relationship(
        "GuideStep",
        back_populates="variant",
        cascade="all, delete-orphan",
        order_by="GuideStep.position",
        lazy="select",
    )

    @property
    def display_title(self) -> str:
        return self.title or (f"Вариант: {self.difficulty.name_ru}" if self.difficulty else "Вариант")


class GuideStep(db.Model):
    """Один этап покраски."""

    __tablename__ = "guide_steps"

    id = db.Column(db.Integer, primary_key=True)
    variant_id = db.Column(
        db.Integer, db.ForeignKey("guide_variants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position = db.Column(db.Integer, nullable=False, default=0)
    title = db.Column(db.String(160), nullable=False, default="")
    instruction = db.Column(db.Text, nullable=False, default="")
    tip = db.Column(db.Text, nullable=False, default="")
    note = db.Column(db.Text, nullable=False, default="")
    # Английская версия шага: тексты техник переводимы, поэтому
    # английская страница не остаётся русской.
    title_en = db.Column(db.String(160), nullable=False, default="")
    instruction_en = db.Column(db.Text, nullable=False, default="")
    tip_en = db.Column(db.Text, nullable=False, default="")

    variant = db.relationship("GuideVariant", back_populates="steps")
    paints = db.relationship(
        "StepPaint",
        back_populates="step",
        cascade="all, delete-orphan",
        order_by="StepPaint.position",
        lazy="selectin",
    )

    @property
    def local_title(self) -> str:
        from ..i18n import current_locale

        if current_locale() != "ru" and self.title_en:
            return self.title_en
        return self.title

    @property
    def local_instruction(self) -> str:
        from ..i18n import current_locale

        if current_locale() != "ru" and self.instruction_en:
            return self.instruction_en
        return self.instruction

    @property
    def local_tip(self) -> str:
        from ..i18n import current_locale

        if current_locale() != "ru" and self.tip_en:
            return self.tip_en
        return self.tip


class StepPaint(db.Model):
    """Краска, применяемая на шаге, и область нанесения."""

    __tablename__ = "step_paints"

    id = db.Column(db.Integer, primary_key=True)
    step_id = db.Column(db.Integer, db.ForeignKey("guide_steps.id", ondelete="CASCADE"), nullable=False)
    paint_id = db.Column(db.Integer, db.ForeignKey("paints.id", ondelete="CASCADE"), nullable=False)
    area = db.Column(db.String(160), nullable=False, default="")
    note = db.Column(db.String(300), nullable=False, default="")
    position = db.Column(db.Integer, nullable=False, default=0)

    step = db.relationship("GuideStep", back_populates="paints")
    paint = db.relationship("Paint", back_populates="step_links")

    @property
    def local_area(self) -> str:
        """Область нанесения по текущей локали страницы."""
        from ..i18n import current_locale
        from ..seed.mapping import SURFACE_LABELS_EN

        if current_locale() != "ru" and self.area:
            for ru, en in SURFACE_LABELS_EN.items():
                if self.area.startswith(ru):
                    return en
        return self.area
