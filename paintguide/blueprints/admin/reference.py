"""Управление справочниками: страны, типы техники, сложности, бренды и линейки."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func, select

from ...extensions import db
from ...models import Brand, Country, Difficulty, Guide, GuideVariant, Paint, PaintLine, VehicleType
from ...services.log import log_action

bp = Blueprint("admin_reference", __name__, url_prefix="/reference")


@bp.before_request
def _guard():
    from ._guard import restrict_to_admins

    return restrict_to_admins()

RESOURCES = {
    "countries": {
        "model": Country,
        "title": "Страны",
        "fields": (
            ("slug", "Код (slug)", True),
            ("name_ru", "Название (RU)", True),
            ("name_en", "Название (EN)", False),
            ("region", "Регион", False),
            ("flag", "Флаг (эмодзи)", False),
            ("sort_order", "Порядок", False),
        ),
    },
    "vehicle-types": {
        "model": VehicleType,
        "title": "Типы техники",
        "fields": (
            ("slug", "Код (slug)", True),
            ("name_ru", "Название (RU)", True),
            ("name_en", "Название (EN)", False),
            ("sort_order", "Порядок", False),
        ),
    },
    "difficulties": {
        "model": Difficulty,
        "title": "Уровни сложности",
        "fields": (
            ("slug", "Код (slug)", True),
            ("name_ru", "Название (RU)", True),
            ("name_en", "Название (EN)", False),
            ("rank", "Ранг (1–4)", False),
            ("badge", "Метка бейджа", False),
            ("description_ru", "Описание", False),
        ),
    },
    "brands": {
        "model": Brand,
        "title": "Бренды",
        "fields": (
            ("slug", "Код (slug)", True),
            ("name", "Название", True),
            ("origin", "Страна производства", False),
            ("sort_order", "Порядок", False),
        ),
    },
    "lines": {
        "model": PaintLine,
        "title": "Линейки красок",
        "fields": (
            ("slug", "Код (slug)", True),
            ("name", "Название", True),
            ("brand_id", "Бренд (ID)", True),
            ("paint_type", "Тип", False),
            ("sort_order", "Порядок", False),
        ),
    },
}


@bp.get("/")
def index():
    """Сводная страница справочников."""
    return render_template(
        "admin/reference.html",
        title="Справочники",
        nav_active="admin",
        countries=_all(Country, Country.sort_order),
        vehicle_types=_all(VehicleType, VehicleType.sort_order),
        difficulties=_all(Difficulty, Difficulty.rank),
        brands=_all(Brand, Brand.sort_order),
        lines=_all(PaintLine, PaintLine.sort_order),
        usage={
            "countries": _usage_counts(Guide, Guide.country_id),
            "vehicle_types": _usage_counts(Guide, Guide.vehicle_type_id),
            "difficulties": _usage_counts(GuideVariant, GuideVariant.difficulty_id),
            "brands": _usage_counts(Paint, Paint.brand_id),
            "lines": _usage_counts(Paint, Paint.line_id),
        },
        brands_list=_all(Brand, Brand.sort_order),
    )


def _all(model, order):
    return list(db.session.scalars(select(model).order_by(order)))


def _usage_counts(model, foreign_key):
    """Сколько записей ссылается на каждый элемент справочника."""
    counts = dict(
        db.session.execute(
            select(foreign_key, func.count(model.id)).group_by(foreign_key)
        ).all()
    )
    return {key: value for key, value in counts.items() if key is not None}


@bp.post("/countries")
def save_country():
    return _save(Country, "countries", ("slug", "name_ru", "name_en", "region", "flag", "sort_order"))


@bp.post("/vehicle-types")
def save_vehicle_type():
    return _save(
        VehicleType,
        "vehicle-types",
        ("slug", "name_ru", "name_en", "sort_order"),
    )


@bp.post("/difficulties")
def save_difficulty():
    return _save(
        Difficulty,
        "difficulties",
        ("slug", "name_ru", "name_en", "rank", "badge", "description_ru"),
    )


@bp.post("/brands")
def save_brand():
    return _save(Brand, "brands", ("slug", "name", "origin", "sort_order"))


@bp.post("/lines")
def save_line():
    return _save(PaintLine, "lines", ("slug", "name", "brand_id", "paint_type", "sort_order"))


def _save(model, resource: str, fields: tuple[str, ...]):
    """Создать или обновить запись справочника."""
    item_id = request.form.get("id", type=int)
    item = db.session.get(model, item_id) if item_id else None
    if item is None:
        item = model()
        db.session.add(item)

    for field in fields:
        raw = request.form.get(field)
        if raw is None:
            continue
        column = model.__table__.columns.get(field)
        if column is None:
            continue
        if hasattr(column.type, "python_type") and column.type.python_type is int:
            try:
                setattr(item, field, int(raw.strip() or 0))
            except (TypeError, ValueError):
                setattr(item, field, 0)
        else:
            setattr(item, field, raw.strip())

    slug = getattr(item, "slug", "")
    if slug:
        # no_autoflush: иначе новая запись успела бы попасть в базу и «конфликтовала» сама с собой.
        with db.session.no_autoflush:
            clash = db.session.scalar(
                select(model).where(model.slug == slug, model.id != (item.id or -1))
            )
        if clash is not None:
            db.session.rollback()
            flash("Такой код уже используется в справочнике.", "error")
            return redirect(url_for("admin_reference.index"))

    db.session.commit()
    log_action(
        current_user.id,
        "reference.save",
        resource,
        getattr(item, "name_ru", None) or getattr(item, "name", slug),
    )
    flash("Справочник обновлён.", "success")
    return redirect(url_for("admin_reference.index"))


@bp.post("/<resource>/<int:item_id>/delete")
def delete(resource: str, item_id: int):
    """Удалить запись справочника, если её не используют другие данные."""
    config = RESOURCES.get(resource)
    if config is None:
        flash("Неизвестный справочник.", "error")
        return redirect(url_for("admin_reference.index"))
    model = config["model"]
    item = db.get_or_404(model, item_id)
    label = getattr(item, "name_ru", None) or getattr(item, "name", str(item_id))

    if _is_in_use(model, item):
        flash("Запись используется в каталоге — сначала перенесите связанные материалы.", "error")
        return redirect(url_for("admin_reference.index"))

    db.session.delete(item)
    db.session.commit()
    log_action(current_user.id, "reference.delete", resource, label)
    flash("Запись удалена из справочника.", "success")
    return redirect(url_for("admin_reference.index"))


def _is_in_use(model, item) -> bool:
    if model is Country:
        return db.session.scalar(
            select(func.count(Guide.id)).where(Guide.country_id == item.id)
        ) > 0
    if model is VehicleType:
        return db.session.scalar(
            select(func.count(Guide.id)).where(Guide.vehicle_type_id == item.id)
        ) > 0
    if model is Difficulty:
        from ...models import GuideVariant

        return db.session.scalar(
            select(func.count(GuideVariant.id)).where(GuideVariant.difficulty_id == item.id)
        ) > 0
    if model is Brand:
        return db.session.scalar(
            select(func.count(Paint.id)).where(Paint.brand_id == item.id)
        ) > 0
    if model is PaintLine:
        return db.session.scalar(
            select(func.count(Paint.id)).where(Paint.line_id == item.id)
        ) > 0
    return False
