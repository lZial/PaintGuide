"""Загрузка демонстрационных данных: справочники, краски и руководства.

Команды:

    python run.py seed            # добавить недостающее
    python run.py seed --reset    # очистить базу и загрузить заново
"""

from __future__ import annotations

from sqlalchemy import func, insert, select, text

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


def _next_id(model) -> int:
    """Первый свободный id в таблице."""
    return (db.session.scalar(select(func.max(model.id))) or 0) + 1


def _default_value(column):
    """Значение по умолчанию для столбца.

    SQLAlchemy оборачивает вызываемое значение так, что оно ждёт
    контекст выполнения, поэтому исходную функцию достаём из обёртки.
    """
    default = column.default
    if default is None:
        return None
    value = default.arg
    if not callable(value):
        return value
    original = getattr(value, "__wrapped__", None)
    if original is not None:
        return original()
    try:
        return value()
    except TypeError:
        return value(None)


def _insert_rows(model, rows: list[dict]) -> int:
    """Вставить строки одной пачкой.

    Обычная вставка через ORM отправляет по одному запросу на строку.
    К удалённой базе (Neon) это тысячи сетевых запросов, поэтому
    собираем строки в список и вставляем за один вызов.

    Значения по умолчанию берём у самой модели, чтобы не забыть ни
    одного столбца: у колонок значения по умолчанию заданы на стороне
    Python, и обычная вставка их не подставит.
    """
    if not rows:
        return 0
    columns = list(model.__table__.columns)
    prepared = []
    for row in rows:
        item = {}
        for column in columns:
            name = column.name
            if name in row:
                item[name] = row[name]
                continue
            if column.default is not None:
                item[name] = _default_value(column)
            elif column.nullable:
                item[name] = None
            else:
                raise ValueError(f"Не задан столбец {model.__name__}.{name}")
        prepared.append(item)
    db.session.execute(insert(model), prepared)
    return len(prepared)


def _sync_sequences() -> None:
    """Подогнать счётчики id под загруженные данные.

    Строки вставляются с явными id — так вставка идёт одной пачкой, —
    поэтому счётчик в Postgres об этом не знает и может выдать занятый
    id при следующей вставке.
    """
    if db.engine.dialect.name != "postgresql":
        return
    for table in (
        "paints",
        "paint_equivalents",
        "guides",
        "guide_variants",
        "guide_steps",
        "step_paints",
    ):
        # Имя таблицы берётся из списка выше, а не извне.
        db.session.execute(
            text(
                "SELECT setval(pg_get_serial_sequence('" + table + "', 'id'), "
                "COALESCE((SELECT MAX(id) FROM " + table + "), 1)) "
                "WHERE pg_get_serial_sequence('" + table + "', 'id') IS NOT NULL"
            )
        )


def load_seed_data(reset: bool = False, reset_users: bool = False) -> dict:
    """Загрузить справочники, краски и руководства в базу.

    `reset` очищает только каталог, `reset_users` — ещё и аккаунты.
    """
    import time

    if reset:
        _wipe()
    if reset_users:
        _wipe_users()

    def phase(label: str, function) -> None:
        """Выполнить этап и показать, сколько он занял.

        Замеры нужны, чтобы по логу сборки было видно, где именно
        идёт работа: к удалённой базе каждый запрос — это сеть.
        """
        start = time.perf_counter()
        function()
        print(f"  {label}: {time.perf_counter() - start:.1f} с", flush=True)

    print("Загрузка данных в базу:", flush=True)
    phase("справочники", _seed_reference)
    phase("краски", _seed_paints)
    db.session.commit()
    phase("гайды, уровни, шаги", _seed_guides)
    db.session.commit()
    phase("счётчики id", _sync_sequences)
    db.session.commit()
    phase("обложки", _seed_covers)
    phase("демо-аккаунты", _seed_users)

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
    # Справочники и уже загруженные краски берём один раз: к удалённой
    # базе каждый запрос — это сетевой запрос, а на каждую краску их
    # уходило по три.
    brands = {brand.slug: brand for brand in db.session.scalars(select(Brand))}
    lines = {
        (line.brand_id, line.slug): line
        for line in db.session.scalars(select(PaintLine))
    }
    existing_paints = {
        (paint.brand_id, paint.code)
        for paint in db.session.scalars(select(Paint))
    }

    next_id = _next_id(Paint)
    rows = []
    for item in catalog:
        brand = brands.get(item["brand"])
        if brand is None:
            continue
        line = lines.get((brand.id, item["line"]))
        if line is None:
            continue
        if (brand.id, item["code"]) in existing_paints:
            continue
        existing_paints.add((brand.id, item["code"]))
        rows.append(
            {
                "id": next_id + len(rows),
                "brand_id": brand.id,
                "line_id": line.id,
                "code": item["code"],
                "name": item["name"],
                "color_hex": item.get("hex") or "#77786d",
                "tone": _tone(item.get("hex") or "#77786d"),
                "paint_type": item.get("type") or "acrylic",
                "description": item.get("description") or "",
            }
        )
    _insert_rows(Paint, rows)
    # Индекс строится после вставки, чтобы в нём были и новые краски.
    _paint_index(rebuild=True)

    existing_links = {
        (link.paint_id, link.other_paint_id)
        for link in db.session.scalars(select(PaintEquivalent))
    }
    next_link_id = _next_id(PaintEquivalent)
    link_rows = []
    for code_a, name_a, code_b, name_b in EQUIVALENTS:
        first = _find_paint(code_a, name_a)
        second = _find_paint(code_b, name_b)
        if first is None or second is None or first.id == second.id:
            continue
        if (first.id, second.id) in existing_links:
            continue
        existing_links.add((first.id, second.id))
        link_rows.append(
            {
                "id": next_link_id + len(link_rows),
                "paint_id": first.id,
                "other_paint_id": second.id,
            }
        )
    _insert_rows(PaintEquivalent, link_rows)

def _paint_map() -> dict:
    """Таблица соответствий «ручное название → реальный код производителя»."""
    import json
    from pathlib import Path

    if getattr(_paint_map, "store", None) is None:
        path = Path(__file__).resolve().parent / "paint_map.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        _paint_map.store = data.get("paints", {})
    return _paint_map.store


def _paint_index(rebuild: bool = False) -> tuple[dict, dict]:
    """Индекс всех красок в памяти: «код+название» и «код» → краска.

    Один запрос вместо тысячи. К удалённой базе каждый запрос — это
    сетевой запрос, а ссылок на краски в гайдах больше десяти тысяч.
    """
    if rebuild or getattr(_paint_index, "store", None) is None:
        by_code_name: dict = {}
        by_code: dict = {}
        for paint in db.session.scalars(select(Paint)):
            by_code_name.setdefault((paint.code, paint.name), paint)
            by_code.setdefault(paint.code, paint)
        _paint_index.store = (by_code_name, by_code)
    return _paint_index.store


def _find_paint(code: str, name: str = "") -> "Paint | None":
    """Найти краску по коду, при совпадении кодов — по названию.

    Сначала ищем точное совпадение «код + название»: так ручные ссылки
    работают даже после уточнения названий по данным производителя.
    """
    if not code:
        return None
    by_code_name, by_code = _paint_index()
    mapped = _paint_map().get(f"{code}|{name}")
    if mapped:
        code = mapped["code"]
        name = mapped["name"]
    if name:
        found = by_code_name.get((code, name))
        if found is not None:
            return found
    return by_code.get(code)


def _seed_guides() -> None:
    """Создать руководства с уровнями сложности, шагами и красками."""
    # Справочники — один раз: к удалённой базе каждый запрос обходится
    # в сетевой запрос, а гайдов 297.
    countries = {item.slug: item for item in db.session.scalars(select(Country))}
    vehicle_types = {
        item.slug: item for item in db.session.scalars(select(VehicleType))
    }
    difficulties = {
        item.slug: item for item in db.session.scalars(select(Difficulty))
    }
    existing_guides = set(db.session.scalars(select(Guide.slug)))
    # После коммита объекты в сессии становятся «протубшими», поэтому
    # индекс красок строим заново.
    _paint_index(rebuild=True)

    # Строки вставляются пачками, поэтому id задаём сами: иначе ORM
    # отправлял бы по одному запросу на каждый шаг.
    guide_id = _next_id(Guide)
    variant_id = _next_id(GuideVariant)
    step_id = _next_id(GuideStep)
    link_id = _next_id(StepPaint)

    guide_rows: list[dict] = []
    variant_rows: list[dict] = []
    step_rows: list[dict] = []
    link_rows: list[dict] = []

    for item in ALL_GUIDES:
        if item["slug"] in existing_guides:
            continue
        country = countries.get(item["country"])
        vehicle_type = vehicle_types.get(item["vehicle_type"])
        if country is None or vehicle_type is None:
            continue

        this_guide_id = guide_id + len(guide_rows)
        guide_rows.append(
            {
                "id": this_guide_id,
                "slug": item["slug"],
                "title": item["title"],
                "subtitle": item.get("subtitle", ""),
                "country_id": country.id,
                "vehicle_type_id": vehicle_type.id,
                "year_from": item.get("year_from"),
                "year_to": item.get("year_to"),
                "production": item.get("production", ""),
                "crew": item.get("crew", ""),
                "description": item.get("description", ""),
                "cover_url": item.get("cover_url", ""),
                "published": item.get("published", True),
                "views_count": item.get("views", 0),
            }
        )

        for position, variant_item in enumerate(enrich_variants(item)):
            difficulty = difficulties.get(variant_item["difficulty"])
            if difficulty is None:
                continue
            this_variant_id = variant_id + len(variant_rows)
            variant_rows.append(
                {
                    "id": this_variant_id,
                    "guide_id": this_guide_id,
                    "difficulty_id": difficulty.id,
                    "title": variant_item.get("title", ""),
                    "summary": variant_item.get("summary", ""),
                    "time_hours": variant_item.get("hours", 0),
                    "is_default": variant_item.get("default", position == 0),
                    "position": position,
                }
            )

            for step_position, step_item in enumerate(steps_of(variant_item)):
                this_step_id = step_id + len(step_rows)
                english = _english_step(step_item)
                step_rows.append(
                    {
                        "id": this_step_id,
                        "variant_id": this_variant_id,
                        "position": step_position + 1,
                        "title": step_item.get("title", ""),
                        "instruction": step_item.get("instruction", ""),
                        "tip": step_item.get("tip", ""),
                        "note": step_item.get("note", ""),
                        "title_en": english["title_en"],
                        "instruction_en": english["instruction_en"],
                        "tip_en": english["tip_en"],
                    }
                )

                for paint_position, paint_item in enumerate(step_item.get("paints", [])):
                    code, name, area, note = _parse_paint_ref(paint_item)
                    paint = _find_paint(code, name)
                    if paint is None:
                        continue
                    link_rows.append(
                        {
                            "id": link_id + len(link_rows),
                            "step_id": this_step_id,
                            "paint_id": paint.id,
                            "area": area,
                            "note": note,
                            "position": paint_position,
                        }
                    )

    _insert_rows(Guide, guide_rows)
    _insert_rows(GuideVariant, variant_rows)
    _insert_rows(GuideStep, step_rows)
    _insert_rows(StepPaint, link_rows)


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

    from sqlalchemy import update

    path = Path(__file__).resolve().parent / "covers.json"
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    # Все гайды одним запросом и одной пачкой обновлений: к удалённой
    # базе каждый запрос — это сетевой запрос.
    guides = {guide.slug: guide for guide in db.session.scalars(select(Guide))}
    rows = []
    for slug, entry in data.items():
        guide = guides.get(slug)
        if guide is None:
            continue
        file_path = entry.get("file", "")
        if not file_path:
            continue
        rows.append(
            {
                "id": guide.id,
                "cover_url": "/" + file_path.replace("\\", "/"),
                "cover_credit": (entry.get("author") or "")[:200],
                "cover_license": (entry.get("license") or "")[:60],
                "cover_source": (entry.get("source") or "")[:500],
                "cover_kind": (entry.get("kind") or "")[:20],
                "cover_scale": (entry.get("scale") or "")[:20],
            }
        )
    if rows:
        db.session.execute(
            update(Guide),
            rows,
            execution_options={"synchronize_session": False},
        )
    db.session.commit()
    print(f"Обложки проставлены: {len(rows)}.")


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
