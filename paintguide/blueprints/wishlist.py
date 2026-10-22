"""Вишлист: очередь красок, которые планируется купить и применить.

Модели живут в избранном, а то, что уже куплено, — в инвентаре.
Поэтому вишлист хранит только краски: выбранные из каталога, с
количеством и заметкой.
"""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from ..extensions import db
from ..models import Paint, WishlistItem
from ..services.log import log_action

bp = Blueprint("wishlist", __name__, url_prefix="/wishlist")

ITEM_TYPE = "paint"


@bp.route("/", methods=["GET", "POST"])
@login_required
def wishlist():
    """Список желаемых красок с формой добавления."""
    if request.method == "POST":
        _create_item()
        return redirect(url_for("wishlist.wishlist"))

    entries = list(
        db.session.scalars(
            select(WishlistItem)
            .where(WishlistItem.user_id == current_user.id)
            .order_by(WishlistItem.position, WishlistItem.created_at.desc())
        )
    )
    # Краски достаём пачками: по одному запросу на каждый пункт
    # вишлиста — это медленно, когда база удалённая.
    paint_ids = [e.item_id for e in entries if e.item_id]
    paints = {}
    if paint_ids:
        for paint in db.session.scalars(select(Paint).where(Paint.id.in_(paint_ids))):
            paints[paint.id] = paint

    for entry in entries:
        entry.detail = paints.get(entry.item_id) if entry.item_id else None

    return render_template(
        "wishlist.html",
        title="Вишлист",
        nav_active="wishlist",
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


def _create_item() -> None:
    paint_id = request.form.get("paint_id", type=int)
    notes = request.form.get("notes", "").strip()[:300]
    quantity = max(1, request.form.get("quantity", default=1, type=int))

    if not paint_id:
        flash("Выберите краску из списка.", "error")
        return
    paint = db.session.get(Paint, paint_id)
    if paint is None:
        flash("Эта краска больше недоступна.", "error")
        return

    # Одна и та же краска в списке не нужна дважды: добавляем количество.
    existing = db.session.scalar(
        select(WishlistItem).where(
            WishlistItem.user_id == current_user.id,
            WishlistItem.item_type == ITEM_TYPE,
            WishlistItem.item_id == paint.id,
        )
    )
    if existing is not None:
        existing.quantity += quantity
        if notes:
            existing.notes = notes
        db.session.commit()
        log_action(current_user.id, "wishlist.create", ITEM_TYPE, paint.name)
        flash("Количество увеличено: краска уже была в вишлисте.", "success")
        return

    position = (
        db.session.scalar(
            select(db.func.coalesce(db.func.max(WishlistItem.position), 0)).where(
                WishlistItem.user_id == current_user.id
            )
        )
        or 0
    ) + 1

    db.session.add(
        WishlistItem(
            user_id=current_user.id,
            item_type=ITEM_TYPE,
            item_id=paint.id,
            name=f"{paint.brand.name} — {paint.name}",
            notes=notes,
            quantity=quantity,
            position=position,
        )
    )
    db.session.commit()
    log_action(current_user.id, "wishlist.create", ITEM_TYPE, paint.name)
    flash("Краска добавлена в ваш вишлист.", "success")


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
    db.session.delete(entry)
    db.session.commit()
    log_action(current_user.id, "wishlist.delete", entry.item_type, entry.name)
    flash("Краска убрана из вишлиста.", "success")
    return redirect(url_for("wishlist.wishlist"))
