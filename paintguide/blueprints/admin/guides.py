"""Управление руководствами: список, создание, редактирование, удаление."""

from __future__ import annotations

import re

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user
from sqlalchemy import func, select

from ...extensions import db
from ...models import (
    Country,
    Difficulty,
    Guide,
    GuideStep,
    GuideVariant,
    Paint,
    StepPaint,
    VehicleType,
)
from ...services.log import log_action

bp = Blueprint("admin_guides", __name__, url_prefix="/guides")


@bp.before_request
def _guard():
    from ._guard import restrict_to_admins

    return restrict_to_admins()

CYRILLIC_SLUGS = str.maketrans(
    {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }
)


def slugify(value: str) -> str:
    normalized = value.lower().translate(CYRILLIC_SLUGS)
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")[:140]


@bp.get("/")
def index():
    """Список всех руководств с фильтром по публикации."""
    published = request.args.get("published", "")
    stmt = select(Guide)
    if published == "yes":
        stmt = stmt.where(Guide.published.is_(True))
    elif published == "no":
        stmt = stmt.where(Guide.published.is_(False))
    guides = list(db.session.scalars(stmt.order_by(Guide.created_at.desc())))
    return render_template(
        "admin/guides.html",
        title="Руководства",
        nav_active="admin",
        guides=guides,
        published_filter=published,
    )


@bp.route("/new", methods=["GET", "POST"])
def create():
    """Создать руководство."""
    if request.method == "POST":
        guide = _collect_guide(None)
        if guide is not None:
            db.session.add(guide)
            db.session.flush()
            _collect_variants(guide)
            db.session.commit()
            log_action(current_user.id, "guide.create", "guide", guide.title)
            flash("Руководство создано.", "success")
            return redirect(url_for("admin_guides.edit", guide_id=guide.id))
    return render_template(
        "admin/guide_form.html",
        title="Новое руководство",
        nav_active="admin",
        guide=None,
        countries=_countries(),
        vehicle_types=_vehicle_types(),
        difficulties=_difficulties(),
        paint_index=_paint_index(),
        error=None,
    )


@bp.route("/<int:guide_id>/edit", methods=["GET", "POST"])
def edit(guide_id: int):
    """Редактировать руководство вместе с уровнями сложности и шагами."""
    guide = db.get_or_404(Guide, guide_id)
    error = None
    if request.method == "POST":
        updated = _collect_guide(guide)
        if updated is not None:
            _collect_variants(guide)
            db.session.commit()
            log_action(current_user.id, "guide.update", "guide", guide.title)
            flash("Руководство сохранено.", "success")
            return redirect(url_for("admin_guides.edit", guide_id=guide.id))
    return render_template(
        "admin/guide_form.html",
        title="Редактирование руководства",
        nav_active="admin",
        guide=guide,
        countries=_countries(),
        vehicle_types=_vehicle_types(),
        difficulties=_difficulties(),
        paint_index=_paint_index(),
        error=error,
    )


def _paint_index():
    """Компактный индекс красок для клиентского скрипта.

    Списки «краска → вариант» отрисовываются на клиенте из одного JSON,
    иначе страница редактора раздувается до нескольких мегабайт.
    Ключи короткие: в справочнике около двух тысяч красок.
    """
    paints = list(
        db.session.scalars(
            select(Paint).join(Paint.brand).order_by(Paint.brand_id, Paint.name)
        )
    )
    brands: dict[int, str] = {}
    entries = []
    for paint in paints:
        brands[paint.brand_id] = paint.brand.name
        entries.append(
            {
                "i": paint.id,
                "b": paint.brand_id,
                "c": paint.code,
                "n": paint.name,
            }
        )
    return {"brands": brands, "paints": entries}


@bp.post("/<int:guide_id>/publish")
def toggle_publish(guide_id: int):
    guide = db.get_or_404(Guide, guide_id)
    guide.published = not guide.published
    db.session.commit()
    log_action(
        current_user.id,
        "guide.publish" if guide.published else "guide.unpublish",
        "guide",
        guide.title,
    )
    flash("Статус публикации обновлён.", "success")
    return redirect(request.referrer or url_for("admin_guides.index"))


@bp.post("/<int:guide_id>/delete")
def delete(guide_id: int):
    guide = db.get_or_404(Guide, guide_id)
    title = guide.title
    db.session.delete(guide)
    db.session.commit()
    log_action(current_user.id, "guide.delete", "guide", title)
    flash("Руководство удалено.", "success")
    return redirect(url_for("admin_guides.index"))


def _collect_guide(guide: Guide | None) -> Guide | None:
    """Собрать и проверить основные поля руководства."""
    title = request.form.get("title", "").strip()
    subtitle = request.form.get("subtitle", "").strip()
    country_slug = request.form.get("country", "").strip()
    vehicle_type_slug = request.form.get("vehicle_type", "").strip()
    description = request.form.get("description", "").strip()
    production = request.form.get("production", "").strip()
    crew = request.form.get("crew", "").strip()
    cover_url = request.form.get("cover_url", "").strip()
    published = request.form.get("published") == "on"

    year_from = _int_or_none(request.form.get("year_from"))
    year_to = _int_or_none(request.form.get("year_to"))

    if not title:
        flash("Укажите название руководства.", "error")
        return None
    if len(title) > 200:
        flash("Название слишком длинное.", "error")
        return None

    country = db.session.scalar(select(Country).where(Country.slug == country_slug))
    vehicle_type = db.session.scalar(
        select(VehicleType).where(VehicleType.slug == vehicle_type_slug)
    )
    if country is None or vehicle_type is None:
        flash("Выберите страну и тип техники.", "error")
        return None

    if cover_url and not _valid_http_url(cover_url):
        flash("Для обложки нужна корректная ссылка http или https.", "error")
        return None
    if year_from and year_to and year_to < year_from:
        flash("Конец периода выпуска не может быть раньше начала.", "error")
        return None

    slug = slugify(request.form.get("slug", "").strip() or title)
    if not slug:
        slug = f"guide-{abs(hash(title)) % 100000}"
    with db.session.no_autoflush:
        clash = db.session.scalar(
            select(Guide).where(Guide.slug == slug, Guide.id != (guide.id if guide else -1))
        )
    if clash is not None:
        flash("Такой адрес уже занят другим руководством.", "error")
        return None

    if guide is None:
        guide = Guide(slug=slug, author_id=current_user.id)
        db.session.add(guide)

    guide.title = title
    guide.subtitle = subtitle[:240]
    guide.country_id = country.id
    guide.vehicle_type_id = vehicle_type.id
    guide.year_from = year_from
    guide.year_to = year_to or year_from
    guide.production = production[:200]
    guide.crew = crew[:120]
    guide.description = description
    guide.cover_url = cover_url[:1000]
    guide.published = published
    return guide


def _collect_variants(guide: Guide) -> None:
    """Пересобрать уровни сложности и шаги из формы."""
    difficulties = _difficulties()
    by_slug = {item.slug: item for item in difficulties}

    existing = {variant.difficulty_id: variant for variant in guide.variants}
    selected_slugs = request.form.getlist("variant_difficulty")
    if not selected_slugs:
        selected_slugs = [item.slug for item in difficulties]

    for slug in selected_slugs:
        difficulty = by_slug.get(slug)
        if difficulty is None:
            continue
        variant = existing.get(difficulty.id)
        if variant is None:
            variant = GuideVariant(guide_id=guide.id, difficulty_id=difficulty.id)
            db.session.add(variant)
        variant.position = difficulty.rank
        variant.title = request.form.get(f"variant_title_{slug}", "").strip()[:200]
        variant.summary = request.form.get(f"variant_summary_{slug}", "").strip()
        variant.time_hours = request.form.get(f"variant_hours_{slug}", default=0, type=int)
        variant.is_default = request.form.get(f"variant_default_{slug}") == "on"
        db.session.flush()
        _collect_steps(variant, slug)

    for difficulty_id, variant in existing.items():
        if variant.difficulty and variant.difficulty.slug not in selected_slugs:
            db.session.delete(variant)

    if guide.variants and not any(variant.is_default for variant in guide.variants):
        guide.variants[0].is_default = True


MAX_STEPS = 12
PAINT_SLOTS = 3


def _collect_steps(variant: GuideVariant, slug: str) -> None:
    """Пересобрать шаги варианта: заголовки, советы и краски с областями."""
    existing = {step.id: step for step in variant.steps}
    keep_ids: set[int] = set()

    for index in range(MAX_STEPS):
        title = request.form.get(f"step_title_{slug}_{index}", "").strip()[:160]
        instruction = request.form.get(f"step_instruction_{slug}_{index}", "").strip()
        tip = request.form.get(f"step_tip_{slug}_{index}", "").strip()
        if not title and not instruction:
            continue

        step = GuideStep(variant_id=variant.id, position=index + 1)
        db.session.add(step)
        db.session.flush()

        for slot in range(1, PAINT_SLOTS + 1):
            paint_id = request.form.get(f"step_paint{slot}_{slug}_{index}", type=int)
            if not paint_id:
                continue
            paint = db.session.get(Paint, paint_id)
            if paint is None:
                continue
            area = request.form.get(f"step_area{slot}_{slug}_{index}", "").strip()[:160]
            note = request.form.get(f"step_paint_note{slot}_{slug}_{index}", "").strip()[:300]
            db.session.add(
                StepPaint(
                    step_id=step.id,
                    paint_id=paint.id,
                    area=area,
                    note=note,
                    position=slot - 1,
                )
            )

        step.title = title
        step.instruction = instruction
        step.tip = tip
        keep_ids.add(step.id)

    for step_id, step in existing.items():
        if step_id not in keep_ids:
            db.session.delete(step)


def _int_or_none(raw: str | None) -> int | None:
    try:
        value = int((raw or "").strip())
    except (TypeError, ValueError):
        return None
    if 1850 <= value <= 2100:
        return value
    return None


def _valid_http_url(value: str) -> bool:
    from urllib.parse import urlparse

    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _countries():
    return list(db.session.scalars(select(Country).order_by(Country.sort_order, Country.name_ru)))


def _vehicle_types():
    return list(
        db.session.scalars(select(VehicleType).order_by(VehicleType.sort_order, VehicleType.name_ru))
    )


def _difficulties():
    return list(db.session.scalars(select(Difficulty).order_by(Difficulty.rank)))
