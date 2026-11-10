"""Вишлисты: именованные списки красок.

Модели живут в избранном, а то, что уже куплено, — в инвентаре.
Поэтому вишлист хранит только краски: выбранные из каталога, с
количеством и заметкой.

Каждый пользователь может держать несколько вишлистов, например
«Для раскраски танка» и «Заказы на следующую неделю». Краску можно
добавить в любой из них — при добавлении всплывает выбор списка.
Вишлист можно сделать публичным и делиться им по ссылке.
"""

from __future__ import annotations

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import select

from ..extensions import db
from ..models import Guide, Paint, User, Wishlist, WishlistItem
from ..services.log import log_action

bp = Blueprint("wishlist", __name__, url_prefix="/wishlist")

ITEM_TYPE = "paint"


# --- Внутренние помощники ---------------------------------------------------


def _user_wishlists() -> list[Wishlist]:
    """Все вишлисты текущего пользователя по позициям."""
    return list(
        db.session.scalars(
            select(Wishlist)
            .where(Wishlist.user_id == current_user.id)
            .order_by(Wishlist.position, Wishlist.created_at)
        )
    )


def _default_wishlist() -> Wishlist:
    """Базовый вишлист пользователя, создавая его при необходимости."""
    wishlists = _user_wishlists()
    if wishlists:
        return wishlists[0]
    wishlist = Wishlist(
        user_id=current_user.id,
        name="Вишлист",
        slug=f"wishlist-{current_user.id}",
        position=0,
    )
    db.session.add(wishlist)
    db.session.flush()
    return wishlist


def _find_paint(paint_id: int) -> Paint | None:
    return db.session.get(Paint, paint_id)


def _add_to_wishlist(
    wishlist: Wishlist,
    paint: Paint,
    quantity: int,
    notes: str,
) -> WishlistItem:
    """Добавить краску в вишлист, объединяя с существующей записью."""
    quantity = max(1, quantity)
    existing = db.session.scalar(
        select(WishlistItem).where(
            WishlistItem.wishlist_id == wishlist.id,
            WishlistItem.item_type == ITEM_TYPE,
            WishlistItem.item_id == paint.id,
        )
    )
    if existing is not None:
        existing.quantity += quantity
        if notes:
            existing.notes = notes
        db.session.commit()
        log_action(
            current_user.id, "wishlist.add", ITEM_TYPE, f"{wishlist.name}: {paint.name}"
        )
        flash(f"Количество увеличено: «{paint.name}» уже было в «{wishlist.name}».", "success")
        return existing

    position = (
        db.session.scalar(
            select(db.func.coalesce(db.func.max(WishlistItem.position), 0)).where(
                WishlistItem.wishlist_id == wishlist.id
            )
        )
        or 0
    ) + 1

    item = WishlistItem(
        wishlist_id=wishlist.id,
        user_id=current_user.id,
        item_type=ITEM_TYPE,
        item_id=paint.id,
        name=f"{paint.brand.name} — {paint.name}",
        notes=notes.strip()[:300],
        quantity=quantity,
        position=position,
    )
    db.session.add(item)
    db.session.commit()
    log_action(
        current_user.id, "wishlist.add", ITEM_TYPE, f"{wishlist.name}: {paint.name}"
    )
    flash(f"Краска добавлена в «{wishlist.name}».", "success")
    return item


# --- Маршруты ---------------------------------------------------------------


@bp.route("/", methods=["GET", "POST"])
@login_required
def wishlist():
    """Мои вишлисты и выбранный из них.

    GET — показываем список вишлистов и содержимое выбранного (по
    умолчанию — базового). POST — добавить краску в выбранный вишлист.
    """
    wishlists = _user_wishlists()
    if not wishlists:
        wishlist = _default_wishlist()
        wishlists = [wishlist]
    else:
        wishlist = wishlists[0]

    selected_id = request.args.get("list", type=int)
    if selected_id:
        wishlist = db.session.get(Wishlist, selected_id)
        if wishlist is None or wishlist.user_id != current_user.id:
            abort(404)

    if request.method == "POST":
        paint_id = request.form.get("paint_id", type=int)
        notes = request.form.get("notes", "").strip()[:300]
        quantity = max(1, request.form.get("quantity", default=1, type=int))
        target_id = request.form.get("wishlist_id", type=int)
        if target_id:
            target = db.session.get(Wishlist, target_id)
            if target is None or target.user_id != current_user.id:
                abort(404)
            wishlist = target

        paint = _find_paint(paint_id) if paint_id else None
        if not paint:
            flash("Выберите краску из списка.", "error")
            return redirect(url_for("wishlist.wishlist"))
        _add_to_wishlist(wishlist, paint, quantity, notes)
        return redirect(url_for("wishlist.wishlist", list=wishlist.id))

    entries = list(
        wishlist.items
    )
    # Краски достаём пачками: один запрос на все пункты вишлиста.
    paint_ids = [e.item_id for e in entries if e.item_id]
    paints = {}
    if paint_ids:
        for paint in db.session.scalars(select(Paint).where(Paint.id.in_(paint_ids))):
            paints[paint.id] = paint

    for entry in entries:
        entry.detail = paints.get(entry.item_id) if entry.item_id else None

    return render_template(
        "wishlist.html",
        title="Вишлисты",
        nav_active="wishlist",
        wishlists=wishlists,
        wishlist=wishlist,
        entries=entries,
        all_paints=_all_paints(),
    )


def _all_paints():
    """Список красок для выпадающего списка добавления."""
    return list(
        db.session.scalars(
            select(Paint).join(Paint.brand).order_by(Paint.brand_id, Paint.name)
        )
    )


@bp.post("/add")
@login_required
def add_item():
    """Единая точка добавления: краска или весь уровень гайда в вишлист.

    Используется всплывающей панелью выбора списка. Принимает либо
    paint_id, либо guide_slug (+ variant_id), и wishlist_id.
    """
    wishlist_id = request.form.get("wishlist_id", type=int)
    quantity = max(1, request.form.get("quantity", default=1, type=int))
    notes = request.form.get("notes", "").strip()[:300]
    next_url = request.form.get("next") or request.referrer or url_for("wishlist.wishlist")

    wishlist = db.session.get(Wishlist, wishlist_id)
    if wishlist is None or wishlist.user_id != current_user.id:
        flash("Вишлист не найден.", "error")
        return redirect(next_url)

    paint_id = request.form.get("paint_id", type=int)
    guide_slug = request.form.get("guide_slug", "").strip()
    variant_id = request.form.get("variant_id", type=int)

    if paint_id:
        paint = _find_paint(paint_id)
        if paint is None:
            flash("Эта краска больше недоступна.", "error")
            return redirect(next_url)
        _add_to_wishlist(wishlist, paint, quantity, notes)
        return redirect(next_url)

    if guide_slug:
        from ..blueprints.guide import _variant_paints

        guide = db.session.scalar(select(Guide).where(Guide.slug == guide_slug))
        if guide is None:
            abort(404)
        variant = None
        if variant_id:
            for v in guide.variants:
                if v.id == variant_id:
                    variant = v
                    break
        if variant is None:
            variant = guide.default_variant
        if variant is None:
            flash("Уровень сложности не найден.", "error")
            return redirect(next_url)
        added = 0
        for paint in _variant_paints(variant):
            existing = db.session.scalar(
                select(WishlistItem).where(
                    WishlistItem.wishlist_id == wishlist.id,
                    WishlistItem.item_type == ITEM_TYPE,
                    WishlistItem.item_id == paint.id,
                )
            )
            if existing is None:
                position = (
                    db.session.scalar(
                        select(db.func.coalesce(db.func.max(WishlistItem.position), 0)).where(
                            WishlistItem.wishlist_id == wishlist.id
                        )
                    )
                    or 0
                ) + 1
                db.session.add(
                    WishlistItem(
                        wishlist_id=wishlist.id,
                        user_id=current_user.id,
                        item_type=ITEM_TYPE,
                        item_id=paint.id,
                        name=f"{paint.brand.name} — {paint.name}",
                        notes=f"Оттенок {paint.color_hex} · {guide.title}",
                        quantity=1,
                        position=position,
                    )
                )
                added += 1
        db.session.commit()
        log_action(
            current_user.id,
            "guide.add_paints",
            "guide",
            guide.title,
            f"Вишлист {wishlist.name}: добавлено красок {added}",
        )
        flash(f"В «{wishlist.name}» добавлено красок: {added}.", "success")
        return redirect(next_url)

    flash("Не указано, что добавить.", "error")
    return redirect(next_url)


@bp.route("/lists", methods=["GET", "POST"])
@login_required
def lists():
    """Управление вишлистами: создать, переименовать, 공개/удалить."""
    if request.method == "POST":
        action = request.form.get("action", "create")
        wishlist_id = request.form.get("wishlist_id", type=int)
        wishlist = None
        if wishlist_id:
            wishlist = db.session.get(Wishlist, wishlist_id)
            if wishlist is None or wishlist.user_id != current_user.id:
                abort(404)

        if action == "create":
            name = (request.form.get("name") or "").strip()[:120] or "Вишлист"
            base_slug = (
                "".join(ch for ch in name.lower() if ch.isalnum() or ch == "-") or "wishlist"
            )
            slug = base_slug
            counter = 1
            while db.session.scalar(
                select(Wishlist).where(
                    Wishlist.user_id == current_user.id, Wishlist.slug == slug
                )
            ):
                slug = f"{base_slug}-{counter}"
                counter += 1
            position = (
                db.session.scalar(
                    select(db.func.coalesce(db.func.max(Wishlist.position), 0)).where(
                        Wishlist.user_id == current_user.id
                    )
                )
                or 0
            ) + 1
            db.session.add(
                Wishlist(
                    user_id=current_user.id,
                    name=name,
                    slug=slug,
                    position=position,
                )
            )
            db.session.commit()
            log_action(current_user.id, "wishlist.create", "wishlist", name)
            flash(f'Вишлист «{name}» создан.', "success")

        elif action == "rename" and wishlist is not None:
            name = (request.form.get("name") or "").strip()[:120]
            if not name:
                flash("Название не может быть пустым.", "error")
            else:
                wishlist.name = name
                db.session.commit()
                log_action(current_user.id, "wishlist.rename", "wishlist", wishlist.name)
                flash("Вишлист переименован.", "success")

        elif action == "toggle-public" and wishlist is not None:
            wishlist.is_public = not wishlist.is_public
            if wishlist.is_public and not wishlist.share_token:
                import secrets

                wishlist.share_token = secrets.token_urlsafe(24)
            db.session.commit()
            log_action(
                current_user.id,
                "wishlist.toggle-public",
                "wishlist",
                wishlist.name,
                f"public={wishlist.is_public}",
            )
            flash(
                "Вишлист открыт по ссылке."
                if wishlist.is_public
                else "Вишлист снова приватный.",
                "success",
            )

        elif action == "delete" and wishlist is not None:
            name = wishlist.name
            db.session.delete(wishlist)
            db.session.commit()
            log_action(current_user.id, "wishlist.delete", "wishlist", name)
            flash(f'Вишлист «{name}» удалён.', "success")

        return redirect(url_for("wishlist.lists"))

    wishlists = _user_wishlists()
    for wishlist in wishlists:
        wishlist.item_count = len(wishlist.items)
    return render_template(
        "wishlists.html",
        title="Мои вишлисты",
        nav_active="wishlist",
        wishlists=wishlists,
    )


@bp.post("/lists/<int:wishlist_id>/delete")
@login_required
def delete_list(wishlist_id: int):
    wishlist = db.session.get(Wishlist, wishlist_id)
    if wishlist is None or wishlist.user_id != current_user.id:
        abort(404)
    name = wishlist.name
    db.session.delete(wishlist)
    db.session.commit()
    log_action(current_user.id, "wishlist.delete", "wishlist", name)
    flash(f'Вишлист «{name}» удалён.', "success")
    return redirect(url_for("wishlist.lists"))


@bp.post("/<int:entry_id>/delete")
@login_required
def delete_entry(entry_id: int):
    entry = db.session.scalar(
        select(WishlistItem).where(
            WishlistItem.id == entry_id, WishlistItem.user_id == current_user.id
        )
    )
    if entry is None:
        flash("Запись не найдена.", "error")
        return redirect(url_for("wishlist.wishlist"))
    list_id = entry.wishlist_id
    db.session.delete(entry)
    db.session.commit()
    log_action(current_user.id, "wishlist.delete", entry.item_type, entry.name)
    flash("Краска убрана из вишлиста.", "success")
    return redirect(url_for("wishlist.wishlist", list=list_id))


@bp.get("/share/<token>")
def shared(token: str):
    """Публичный просмотр чужого вишлиста по ссылке."""
    wishlist = db.session.scalar(select(Wishlist).where(Wishlist.share_token == token))
    if wishlist is None or not wishlist.is_public:
        abort(404)

    entries = list(wishlist.items)
    paint_ids = [e.item_id for e in entries if e.item_id]
    paints = {}
    if paint_ids:
        for paint in db.session.scalars(select(Paint).where(Paint.id.in_(paint_ids))):
            paints[paint.id] = paint

    for entry in entries:
        entry.detail = paints.get(entry.item_id) if entry.item_id else None

    owner = db.session.get(User, wishlist.user_id)
    return render_template(
        "wishlist_shared.html",
        title=f"Вишлист «{wishlist.name}»",
        wishlist=wishlist,
        owner=owner,
        entries=entries,
    )
