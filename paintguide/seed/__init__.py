"""Загрузка демонстрационных данных: справочники, краски и руководства.

Команды:

    python run.py seed            # добавить недостающее
    python run.py seed --reset    # очистить базу и загрузить заново
"""

from __future__ import annotations

from sqlalchemy import select

from ..extensions import db
from ..models import (
    Brand,
    Country,
    Difficulty,
    Guide,
    GuideStep,
    GuideVariant,
    Paint,
    PaintEquivalent,
    PaintLine,
    StepPaint,
    VehicleType,
    utc_now,
)
from .guides import GUIDES
from .guides_part2 import GUIDES_2
from .guides_part3 import GUIDES_3
from .guides_part4 import GUIDES_4
from .guides_part5 import GUIDES_5
from .guides_part6 import GUIDES_6
from .guides_part7 import GUIDES_7
from .guides_part8 import GUIDES_8
from .guides_part9 import GUIDES_9
from .guides_part10 import GUIDES_10
from .levels import enrich_variants
from .paints import EQUIVALENTS, PAINTS
from .reference import BRANDS, COUNTRIES, DIFFICULTIES, LINES, VEHICLE_TYPES
from .restructure import restructure as _restructure

ALL_GUIDES = (
    GUIDES
    + GUIDES_2
    + GUIDES_3
    + GUIDES_4
    + GUIDES_5
    + GUIDES_6
    + GUIDES_7
    + GUIDES_8
    + GUIDES_9
    + GUIDES_10
)


def steps_of(variant: dict) -> list[dict]:
    """Шаги варианта в техническом виде: одна техника — один шаг."""
    return _restructure(variant)


def load_seed_data(reset: bool = False, reset_users: bool = False) -> dict:
    """Загрузить справочники, краски и руководства в базу.

    `reset` очищает только каталог, `reset_users` — ещё и аккаунты.
    """
    if reset:
        _wipe()
    if reset_users:
        _wipe_users()

    _seed_reference()
    _seed_paints()
    db.session.commit()
    _seed_guides()
    db.session.commit()
    _seed_covers()
    _seed_users()

    return {
        "countries": db.session.scalar(select(db.func.count(Country.id))) or 0,
        "vehicles": db.session.scalar(select(db.func.count(VehicleType.id))) or 0,
        "paints": db.session.scalar(select(db.func.count(Paint.id))) or 0,
        "guides": db.session.scalar(select(db.func.count(Guide.id))) or 0,
        "variants": db.session.scalar(select(db.func.count(GuideVariant.id))) or 0,
        "steps": db.session.scalar(select(db.func.count(GuideStep.id))) or 0,
    }


def _wipe() -> None:
    """Очистить содержимое каталога (для полной перезагрузки).

    Учётные записи пользователей и всё, что в них накоплено —
    избранное, вишлист, инвентарь, — намеренно не трогаются:
    перезагрузка каталога не должна сбрасывать аккаунты. Полная
    очистка делается отдельной командой `flask seed --reset-users`.
    """
    for model in (
        StepPaint,
        GuideStep,
        GuideVariant,
        Guide,
        PaintEquivalent,
        Paint,
        PaintLine,
        Brand,
        VehicleType,
        Difficulty,
        Country,
    ):
        db.session.execute(db.delete(model))
    db.session.commit()


def _wipe_users() -> None:
    """Удалить аккаунты вместе с тем, что в них накоплено.

    Вызывается только по явному требованию: `flask seed --reset-users`.
    """
    from ..models import AccountToken, Favorite, PaintStock, User, WishlistItem

    for model in (AccountToken, Favorite, WishlistItem, PaintStock, User):
        db.session.execute(db.delete(model))
    db.session.commit()


def _seed_reference() -> None:
    """Создать справочники, если их ещё нет."""
    for slug, name_ru, name_en, region, flag, order in COUNTRIES:
        if db.session.scalar(select(Country).where(Country.slug == slug)) is None:
            db.session.add(
                Country(
                    slug=slug,
                    name_ru=name_ru,
                    name_en=name_en,
                    region=region,
                    flag=flag,
                    sort_order=order,
                )
            )

    for slug, name_ru, name_en, icon, order in VEHICLE_TYPES:
        existing = db.session.scalar(select(VehicleType).where(VehicleType.slug == slug))
        if existing is None:
            db.session.add(
                VehicleType(
                    slug=slug,
                    name_ru=name_ru,
                    name_en=name_en,
                    icon=icon,
                    sort_order=order,
                )
            )
        elif existing.icon != icon:
            # Иконки типов техники из справочника пустые: в интерфейсе
            # эмодзи-иконки не используются. Синхронизируем старое значение.
            existing.icon = icon

    for slug, name_ru, name_en, rank, badge, description in DIFFICULTIES:
        if db.session.scalar(select(Difficulty).where(Difficulty.slug == slug)) is None:
            db.session.add(
                Difficulty(
                    slug=slug,
                    name_ru=name_ru,
                    name_en=name_en,
                    rank=rank,
                    badge=badge,
                    description_ru=description,
                )
            )

    for slug, name, origin, order in BRANDS:
        if db.session.scalar(select(Brand).where(Brand.slug == slug)) is None:
            db.session.add(Brand(slug=slug, name=name, origin=origin, sort_order=order))
    db.session.flush()

    for brand_slug, slug, name, paint_type, order in LINES:
        brand = db.session.scalar(select(Brand).where(Brand.slug == brand_slug))
        if brand is None:
            continue
        existing = db.session.scalar(
            select(PaintLine).where(PaintLine.slug == slug, PaintLine.brand_id == brand.id)
        )
        if existing is None:
            db.session.add(
                PaintLine(
                    brand_id=brand.id,
                    slug=slug,
                    name=name,
                    paint_type=paint_type,
                    sort_order=order,
                )
            )
    db.session.flush()


def _seed_paints() -> None:
    """Создать краски и соответствия между брендами."""
    from .catalog import build_catalog

    catalog = build_catalog()
    for item in catalog:
        brand = db.session.scalar(select(Brand).where(Brand.slug == item["brand"]))
        if brand is None:
            continue
        line = db.session.scalar(
            select(PaintLine).where(
                PaintLine.slug == item["line"], PaintLine.brand_id == brand.id
            )
        )
        if line is None:
            continue
        existing = db.session.scalar(
            select(Paint).where(
                Paint.brand_id == brand.id, Paint.code == item["code"]
            )
        )
        if existing is not None:
            continue
        db.session.add(
            Paint(
                brand_id=brand.id,
                line_id=line.id,
                code=item["code"],
                name=item["name"],
                color_hex=item.get("hex") or "#77786d",
                tone=_tone(item.get("hex") or "#77786d"),
                paint_type=item.get("type") or "acrylic",
                description=item.get("description") or "",
            )
        )
    db.session.flush()

    for code_a, name_a, code_b, name_b in EQUIVALENTS:
        first = _find_paint(code_a, name_a)
        second = _find_paint(code_b, name_b)
        if first is None or second is None or first.id == second.id:
            continue
        link = db.session.scalar(
            select(PaintEquivalent).where(
                PaintEquivalent.paint_id == first.id,
                PaintEquivalent.other_paint_id == second.id,
            )
        )
        if link is None:
            db.session.add(PaintEquivalent(paint_id=first.id, other_paint_id=second.id))

def _paint_map() -> dict:
    """Таблица соответствий «ручное название → реальный код производителя»."""
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parent / "paint_map.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("paints", {})


def _find_paint(code: str, name: str = "") -> "Paint | None":
    """Найти краску по коду, при совпадении кодов — по названию.

    Сначала ищем точное совпадение «код + название»: так ручные ссылки
    работают даже после уточнения названий по данным производителя.
    """
    if not code:
        return None
    mapped = _paint_map().get(f"{code}|{name}")
    if mapped:
        code = mapped["code"]
        name = mapped["name"]
    if name:
        exact = db.session.scalar(
            select(Paint).where(Paint.code == code, Paint.name == name)
        )
        if exact is not None:
            return exact
    return db.session.scalar(select(Paint).where(Paint.code == code).limit(1))


def _seed_guides() -> None:
    """Создать руководства с уровнями сложности, шагами и красками."""
    for item in ALL_GUIDES:
        if db.session.scalar(select(Guide).where(Guide.slug == item["slug"])) is not None:
            continue
        country = db.session.scalar(select(Country).where(Country.slug == item["country"]))
        vehicle_type = db.session.scalar(
            select(VehicleType).where(VehicleType.slug == item["vehicle_type"])
        )
        if country is None or vehicle_type is None:
            continue

        guide = Guide(
            slug=item["slug"],
            title=item["title"],
            subtitle=item.get("subtitle", ""),
            country_id=country.id,
            vehicle_type_id=vehicle_type.id,
            year_from=item.get("year_from"),
            year_to=item.get("year_to"),
            production=item.get("production", ""),
            crew=item.get("crew", ""),
            description=item.get("description", ""),
            cover_url=item.get("cover_url", ""),
            published=item.get("published", True),
            views_count=item.get("views", 0),
        )
        db.session.add(guide)
        db.session.flush()

        for position, variant_item in enumerate(enrich_variants(item)):
            difficulty = db.session.scalar(
                select(Difficulty).where(Difficulty.slug == variant_item["difficulty"])
            )
            if difficulty is None:
                continue
            variant = GuideVariant(
                guide_id=guide.id,
                difficulty_id=difficulty.id,
                title=variant_item.get("title", ""),
                summary=variant_item.get("summary", ""),
                time_hours=variant_item.get("hours", 0),
                is_default=variant_item.get("default", position == 0),
                position=position,
            )
            db.session.add(variant)
            db.session.flush()

            for step_position, step_item in enumerate(steps_of(variant_item)):
                step = GuideStep(
                    variant_id=variant.id,
                    position=step_position + 1,
                    title=step_item.get("title", ""),
                    instruction=step_item.get("instruction", ""),
                    tip=step_item.get("tip", ""),
                    note=step_item.get("note", ""),
                    **_english_step(step_item),
                )
                db.session.add(step)
                db.session.flush()

                for paint_position, paint_item in enumerate(step_item.get("paints", [])):
                    code, name, area, note = _parse_paint_ref(paint_item)
                    paint = _find_paint(code, name)
                    if paint is None:
                        continue
                    db.session.add(
                        StepPaint(
                            step_id=step.id,
                            paint_id=paint.id,
                            area=area,
                            note=note,
                            position=paint_position,
                        )
                    )


def _english_step(step_item: dict) -> dict:
    """Английский текст шага.

    Тексты техник переводимы, поэтому английский шаг собирается вместе
    с русским: в нём те же краски и те же поверхности, но по-английски.
    """
    return {
        "title_en": step_item.get("title_en", ""),
        "instruction_en": step_item.get("instruction_en", ""),
        "tip_en": step_item.get("tip_en", ""),
    }


def _parse_paint_ref(item) -> tuple[str, str, str, str]:
    """Разобрать ссылку на краску.

    Поддерживаются два формата:
      ("XF-1", "Black")              — только краска
      ("XF-1", "Black", "Корпус")   — краска и область
      [("XF-1", "Black"), "Корпус", "заметка"] — алиас + область + заметка
    """
    first = item[0]
    if isinstance(first, (tuple, list)):
        code = first[0]
        name = first[1]
        area = item[1] if len(item) > 1 else ""
        note = item[2] if len(item) > 2 else ""
    else:
        code = first
        name = item[1] if len(item) > 1 else ""
        area = item[2] if len(item) > 2 else ""
        note = item[3] if len(item) > 3 else ""
    return code, name, area, note


def _seed_covers() -> None:
    """Проставить обложки и данные об авторе/лицензии из covers.json."""
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parent / "covers.json"
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    applied = 0
    for slug, entry in data.items():
        guide = db.session.scalar(select(Guide).where(Guide.slug == slug))
        if guide is None:
            continue
        file_path = entry.get("file", "")
        if not file_path:
            continue
        guide.cover_url = "/" + file_path.replace("\\", "/")
        guide.cover_credit = (entry.get("author") or "")[:200]
        guide.cover_license = (entry.get("license") or "")[:60]
        guide.cover_source = (entry.get("source") or "")[:500]
        guide.cover_kind = (entry.get("kind") or "")[:20]
        guide.cover_scale = (entry.get("scale") or "")[:20]
        applied += 1
    db.session.commit()


def _seed_users() -> None:
    """Создать демонстрационные учётные записи.

    Существующие аккаунты не трогаем: пароль не меняется, почта не
    трогается. Иначе перезагрузка каталога сбрасывала бы учётные
    записи, которые завели живые пользователи.
    """
    from ..models import User

    accounts = [
        ("admin@paintguide.local", "Администратор", "admin", "paintguide"),
        ("modelist@paintguide.local", "Моделист", "user", "paintguide"),
    ]
    for email, nickname, role, password in accounts:
        user = db.session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                nickname=nickname,
                role=role,
                email_verified_at=utc_now(),
                terms_accepted_at=utc_now(),
            )
            user.set_password(password)
            db.session.add(user)
            continue
        if role == "admin" and not user.is_admin:
            user.role = "admin"
        # Демонстрационные записи считаем подтверждёнными, иначе вход
        # для них был бы закрыт.
        if user.email_verified_at is None:
            user.email_verified_at = utc_now()
    db.session.commit()


def _tone(hex_value: str) -> int:
    """Тон (0–100) из HEX: средневзвешенная яркость."""
    value = (hex_value or "").lstrip("#")
    if len(value) != 6:
        return 50
    try:
        r, g, b = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return 50
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return max(0, min(100, round(luminance / 255 * 100)))
