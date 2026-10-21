"""Управление справочником красок."""

from __future__ import annotations

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func, or_, select

from ...extensions import db
from ...models import Brand, Paint, PaintEquivalent, PaintLine
from ...services.log import log_action

bp = Blueprint("admin_paints", __name__, url_prefix="/paints")


@bp.before_request
def _guard():
    from ._guard import restrict_to_admins

    return restrict_to_admins()


@bp.get("/")
def index():
    """Список красок с поиском и фильтром по бренду."""
    search = (request.args.get("q") or "").strip()[:100]
    brand_slug = (request.args.get("brand") or "").strip()[:60]

    stmt = select(Paint).join(Paint.brand).join(Paint.line)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(Paint.name.ilike(pattern), Paint.code.ilike(pattern), Brand.name.ilike(pattern))
        )
    if brand_slug:
        stmt = stmt.where(Brand.slug == brand_slug)
    paints = list(
        db.session.scalars(
            stmt.order_by(Brand.sort_order, Brand.name, Paint.name).limit(300)
        )
    )
    return render_template(
        "admin/paints.html",
        title="Краски",
        nav_active="admin",
        paints=paints,
        brands=list(db.session.scalars(select(Brand).order_by(Brand.sort_order, Brand.name))),
        lines=list(db.session.scalars(select(PaintLine).order_by(PaintLine.name))),
        filters={"q": search, "brand": brand_slug},
    )


@bp.route("/new", methods=["GET", "POST"])
def create():
    """Создать запись справочника красок."""
    if request.method == "POST":
        paint = _collect(None)
        if paint is not None:
            db.session.add(paint)
            db.session.commit()
            log_action(current_user.id, "paint.create", "paint", paint.display_name)
            flash("Краска добавлена в справочник.", "success")
            return redirect(url_for("admin_paints.index"))
    return render_template(
        "admin/paint_form.html",
        title="Новая краска",
        nav_active="admin",
        paint=None,
        brands=list(db.session.scalars(select(Brand).order_by(Brand.sort_order, Brand.name))),
        lines=list(db.session.scalars(select(PaintLine).order_by(PaintLine.name))),
        equivalents=[],
        error=None,
    )


@bp.route("/<int:paint_id>/edit", methods=["GET", "POST"])
def edit(paint_id: int):
    """Редактировать краску."""
    paint = db.get_or_404(Paint, paint_id)
    if request.method == "POST":
        updated = _collect(paint)
        if updated is not None:
            _collect_equivalents(paint)
            db.session.commit()
            log_action(current_user.id, "paint.update", "paint", paint.display_name)
            flash("Краска сохранена.", "success")
            return redirect(url_for("admin_paints.index"))
    equivalents = [link.other_paint_id for link in paint.equivalents]
    return render_template(
        "admin/paint_form.html",
        title="Редактирование краски",
        nav_active="admin",
        paint=paint,
        brands=list(db.session.scalars(select(Brand).order_by(Brand.sort_order, Brand.name))),
        lines=list(db.session.scalars(select(PaintLine).order_by(PaintLine.name))),
        equivalents=equivalents,
        error=None,
    )


@bp.post("/<int:paint_id>/delete")
def delete(paint_id: int):
    paint = db.get_or_404(Paint, paint_id)
    label = paint.display_name
    db.session.delete(paint)
    db.session.commit()
    log_action(current_user.id, "paint.delete", "paint", label)
    flash("Краска удалена из справочника.", "success")
    return redirect(url_for("admin_paints.index"))


@bp.post("/import")
def import_paints():
    """Массовый импорт красок из JSON."""
    raw = request.form.get("payload", "").strip()
    if not raw:
        flash("Вставьте JSON с красками.", "error")
        return redirect(url_for("admin_paints.index"))
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        flash(f"Не удалось разобрать JSON: {error}", "error")
        return redirect(url_for("admin_paints.index"))
    if not isinstance(payload, list):
        flash("Ожидается массив объектов.", "error")
        return redirect(url_for("admin_paints.index"))

    created = 0
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        code = str(entry.get("code", "")).strip()
        name = str(entry.get("name", "")).strip()
        brand_slug = str(entry.get("brand", "")).strip()
        if not code or not name or not brand_slug:
            continue
        brand = db.session.scalar(select(Brand).where(Brand.slug == brand_slug))
        if brand is None:
            continue
        line_slug = str(entry.get("line") or "general").strip()
        line = db.session.scalar(
            select(PaintLine).where(PaintLine.brand_id == brand.id, PaintLine.slug == line_slug)
        )
        if line is None:
            line = PaintLine(
                brand_id=brand.id,
                slug=line_slug,
                name=line_slug.replace("-", " ").title(),
                paint_type=str(entry.get("type", "acrylic")),
            )
            db.session.add(line)
            db.session.flush()
        existing = db.session.scalar(
            select(Paint).where(
                Paint.brand_id == brand.id, Paint.code == code, Paint.name == name
            )
        )
        if existing is not None:
            continue
        db.session.add(
            Paint(
                brand_id=brand.id,
                line_id=line.id,
                code=code,
                name=name,
                color_hex=_normalize_hex(str(entry.get("hex", "#77786d"))),
                tone=_tone(str(entry.get("hex", "#77786d"))),
                paint_type=str(entry.get("type", "acrylic")),
                description=str(entry.get("description", "")),
            )
        )
        created += 1
    db.session.commit()
    log_action(current_user.id, "paint.import", "paint", f"Импортировано: {created}")
    flash(f"Импортировано красок: {created}.", "success")
    return redirect(url_for("admin_paints.index"))


def _collect(paint: Paint | None) -> Paint | None:
    code = request.form.get("code", "").strip()[:40]
    name = request.form.get("name", "").strip()[:180]
    hex_value = _normalize_hex(request.form.get("color_hex", "#77786d"))
    paint_type = request.form.get("paint_type", "acrylic").strip()[:30] or "acrylic"
    description = request.form.get("description", "").strip()
    brand_id = request.form.get("brand_id", type=int)
    line_id = request.form.get("line_id", type=int)

    if not code or not name:
        flash("Код и название обязательны.", "error")
        return None
    brand = db.session.get(Brand, brand_id) if brand_id else None
    line = db.session.get(PaintLine, line_id) if line_id else None
    if brand is None or line is None:
        flash("Выберите бренд и линейку.", "error")
        return None
    if line.brand_id != brand.id:
        flash("Линейка должна принадлежать выбранному бренду.", "error")
        return None

    if paint is None:
        paint = Paint()
        db.session.add(paint)
    paint.brand_id = brand.id
    paint.line_id = line.id
    paint.code = code
    paint.name = name
    paint.color_hex = hex_value
    paint.tone = _tone(hex_value)
    paint.paint_type = paint_type
    paint.description = description
    return paint


def _collect_equivalents(paint: Paint) -> None:
    raw = request.form.get("equivalents", "")
    ids = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if chunk.isdigit():
            value = int(chunk)
            if value not in ids:
                ids.append(value)
    existing = {link.other_paint_id: link for link in paint.equivalents}
    for other_id, link in existing.items():
        if other_id not in ids:
            db.session.delete(link)
    for other_id in ids:
        if other_id in existing:
            continue
        if other_id == paint.id:
            continue
        other = db.session.get(Paint, other_id)
        if other is None:
            continue
        db.session.add(PaintEquivalent(paint_id=paint.id, other_paint_id=other.id))


def _normalize_hex(value: str) -> str:
    value = (value or "").strip().lstrip("#")
    if len(value) == 3:
        value = "".join(char * 2 for char in value)
    if len(value) != 6 or any(char not in "0123456789abcdefABCDEF" for char in value):
        return "#77786d"
    return f"#{value.lower()}"


def _tone(hex_value: str) -> int:
    """Тон (0–100) из HEX: средневзвешенная яркость с поправкой на насыщенность."""
    value = hex_value.lstrip("#")
    if len(value) != 6:
        return 50
    try:
        r, g, b = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return 50
    luminance = (0.299 * r + 0.587 * g + 0.114 * b)
    return max(0, min(100, round(luminance / 255 * 100)))
