"""Лёгкие миграции схемы.

В проекте не используется Alembic: набор таблиц стабилен, а переход на полноценный
инструмент добавил бы зависимость и риск. Вместо этого недостающие колонки
добавляются обычным `ALTER TABLE` — этого достаточно для эволюции модели.
"""

from __future__ import annotations

from sqlalchemy import inspect, select, text

from .extensions import db


def _column_ddl(column) -> str:
    """Собрать DDL для добавления колонки в существующую таблицу."""
    type_sql = column.type.compile(dialect=db.engine.dialect)
    default_sql = ""
    default = column.default
    if default is not None and getattr(default, "is_scalar", False):
        value = default.arg
        if isinstance(value, str):
            default_sql = f" DEFAULT '{value}'"
        elif isinstance(value, bool):
            default_sql = f" DEFAULT {1 if value else 0}"
        elif isinstance(value, (int, float)):
            default_sql = f" DEFAULT {value}"
    not_null = " NOT NULL" if not column.nullable and default_sql else ""
    return f"{column.name} {type_sql}{default_sql}{not_null}"


def ensure_schema(app) -> list[str]:
    """Добавить в существующие таблицы колонки, которых ещё нет.

    Возвращает список применённых изменений.
    """
    applied: list[str] = []
    with app.app_context():
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
        for model in db.metadata.sorted_tables:
            if model.name not in tables:
                continue
            existing = {column["name"] for column in inspector.get_columns(model.name)}
            for column in model.columns:
                if column.name in existing:
                    continue
                ddl = _column_ddl(column)
                db.session.execute(text(f"ALTER TABLE {model.name} ADD COLUMN {ddl}"))
                applied.append(f"{model.name}.{column.name}")
        if applied:
            db.session.commit()
    return applied


def migrate_wishlists(app) -> list[str]:
    """Перенести вишлисты на схему с несколькими списками.

    Добавляет таблицу wishlists, колонку wishlist_id в wishlist_items,
    создаёт каждому пользователю базовый вишлист и меняет уникальность
    с «одна краска на пользователя» на «одна краска в вишлисте».
    """
    applied: list[str] = []
    with app.app_context():
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())

        if "wishlists" not in tables:
            db.create_all()
            applied.append("table wishlists")

        if "wishlist_items" in tables:
            existing = {column["name"] for column in inspector.get_columns("wishlist_items")}
            if "wishlist_id" not in existing:
                db.session.execute(
                    text(
                        "ALTER TABLE wishlist_items "
                        "ADD COLUMN wishlist_id INTEGER "
                        "REFERENCES wishlists(id) ON DELETE CASCADE"
                    )
                )
                applied.append("wishlist_items.wishlist_id")
        if applied:
            db.session.commit()

        # Каждому пользователю — базовый вишлист, а записи без списка — в него.
        from .models.user import User, Wishlist

        for user in db.session.scalars(select(User)).all():
            default = db.session.scalar(
                select(Wishlist).where(Wishlist.user_id == user.id).order_by(Wishlist.created_at.asc())
            )
            if default is None:
                default = Wishlist(
                    user_id=user.id,
                    name="Вишлист",
                    slug=f"wishlist-{user.id}",
                    position=0,
                )
                db.session.add(default)
                db.session.flush()
                applied.append(f"wishlist {user.id}")
            db.session.execute(
                text(
                    "UPDATE wishlist_items SET wishlist_id = :wid "
                    "WHERE user_id = :uid AND wishlist_id IS NULL"
                ),
                {"wid": default.id, "uid": user.id},
            )
        db.session.commit()

        # Уникальность теперь внутри вишлиста, а не на всю базу пользователя.
        if "wishlist_items" in tables:
            try:
                db.session.execute(
                    text("ALTER TABLE wishlist_items DROP CONSTRAINT IF EXISTS uq_wishlist_target")
                )
                db.session.commit()
                applied.append("drop uq_wishlist_target")
            except Exception:  # noqa: BLE001 - SQLite не поддерживает IF EXISTS для констрейнтов
                db.session.rollback()
            try:
                db.session.execute(
                    text(
                        "ALTER TABLE wishlist_items "
                        "ADD CONSTRAINT uq_wishlist_target UNIQUE (wishlist_id, item_type, item_id)"
                    )
                )
                db.session.commit()
                applied.append("uq_wishlist_target(wishlist_id, item_type, item_id)")
            except Exception:  # noqa: BLE001 - уже существует или дубликаты
                db.session.rollback()
    return applied


# Колонки, которые убрали из моделей. Список явный: удалять что-либо из базы
# наугад нельзя, поэтому здесь только те поля, что выведены из интерфейса.
OBSOLETE_COLUMNS = {
    "guides": ("scale", "youtube_url"),
}


def drop_obsolete_columns(app) -> list[str]:
    """Удалить колонки, которых больше нет в моделях.

    Вызывается при старте приложения, поэтому старые базы не требуют
    ручной правки после обновления схемы.
    """
    applied: list[str] = []
    with app.app_context():
        inspector = inspect(db.engine)
        tables = set(inspector.get_table_names())
        for table, columns in OBSOLETE_COLUMNS.items():
            if table not in tables:
                continue
            existing = {column["name"] for column in inspector.get_columns(table)}
            for column in columns:
                if column not in existing:
                    continue
                db.session.execute(text(f"ALTER TABLE {table} DROP COLUMN {column}"))
                applied.append(f"{table}.{column}")
        if applied:
            db.session.commit()
    return applied
