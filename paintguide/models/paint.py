"""Справочник красок и соответствия между брендами."""

from __future__ import annotations

from ..extensions import db


class PaintLine(db.Model):
    """Линейка красок внутри бренда (3GEN General, Model Color, Real Colors…)."""

    __tablename__ = "paint_lines"

    id = db.Column(db.Integer, primary_key=True)
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False)
    slug = db.Column(db.String(80), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    paint_type = db.Column(db.String(30), nullable=False, default="acrylic")
    sort_order = db.Column(db.Integer, nullable=False, default=100)

    brand = db.relationship("Brand", back_populates="lines")
    paints = db.relationship("Paint", back_populates="line")

    @property
    def full_name(self) -> str:
        return f"{self.brand.name} {self.name}"


class Paint(db.Model):
    """Акриловая краска из справочника."""

    __tablename__ = "paints"

    id = db.Column(db.Integer, primary_key=True)
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id", ondelete="CASCADE"), nullable=False)
    line_id = db.Column(db.Integer, db.ForeignKey("paint_lines.id", ondelete="CASCADE"), nullable=False)
    code = db.Column(db.String(40), nullable=False, default="", index=True)
    name = db.Column(db.String(180), nullable=False, index=True)
    color_hex = db.Column(db.String(7), nullable=False, default="#77786d")
    tone = db.Column(db.Integer, nullable=False, default=50, index=True)
    paint_type = db.Column(db.String(30), nullable=False, default="acrylic")
    description = db.Column(db.Text, nullable=False, default="")

    brand = db.relationship("Brand", back_populates="paints")
    line = db.relationship("PaintLine", back_populates="paints")
    equivalents = db.relationship(
        "PaintEquivalent",
        back_populates="paint",
        cascade="all, delete-orphan",
        foreign_keys="PaintEquivalent.paint_id",
        lazy="select",
    )
    reverse_equivalents = db.relationship(
        "PaintEquivalent",
        back_populates="other_paint",
        cascade="all, delete-orphan",
        foreign_keys="PaintEquivalent.other_paint_id",
        lazy="select",
    )
    stock_entries = db.relationship(
        "PaintStock", back_populates="paint", cascade="all, delete-orphan", lazy="select"
    )
    step_links = db.relationship(
        "StepPaint", back_populates="paint", cascade="all, delete-orphan", lazy="select"
    )

    @property
    def hex(self) -> str:
        return self.color_hex

    @property
    def type_label(self) -> str:
        return {
            "acrylic": "Акрил",
            "enamel": "Эмаль",
            "pigment": "Пигмент",
            "metallic": "Металлик",
            "panzer": "Панцер",
        }.get(self.paint_type, self.paint_type)

    @property
    def display_name(self) -> str:
        return f"{self.brand.name} {self.name}" if self.brand else self.name

    @property
    def all_equivalents(self) -> list["Paint"]:
        seen: dict[int, "Paint"] = {}
        for link in self.equivalents:
            if link.other_paint:
                seen[link.other_paint.id] = link.other_paint
        for link in self.reverse_equivalents:
            if link.paint:
                seen[link.paint.id] = link.paint
        return list(seen.values())

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Paint {self.code} {self.name}>"


class PaintEquivalent(db.Model):
    """Соответствие краски одного бренда краске другого."""

    __tablename__ = "paint_equivalents"

    id = db.Column(db.Integer, primary_key=True)
    paint_id = db.Column(db.Integer, db.ForeignKey("paints.id", ondelete="CASCADE"), nullable=False)
    other_paint_id = db.Column(
        db.Integer, db.ForeignKey("paints.id", ondelete="CASCADE"), nullable=False
    )

    paint = db.relationship("Paint", back_populates="equivalents", foreign_keys=[paint_id])
    other_paint = db.relationship(
        "Paint", back_populates="reverse_equivalents", foreign_keys=[other_paint_id]
    )

    __table_args__ = (
        db.UniqueConstraint("paint_id", "other_paint_id", name="uq_paint_equivalent_pair"),
    )
