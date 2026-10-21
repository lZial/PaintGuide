"""Вишлист: очередь моделей, гайдов, красок и идей."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from ..extensions import db
from ..models import Guide, Paint, WishlistItem
from ..services.log import log_action

bp = Blueprint("wishlist", __name__, url_prefix="/wishlist")

ITEM_TYPES = {"model", "guide", "paint", "idea"}


@bp.route("/", methods=["GET", "POST"])
@login_required
def wishlist():
    """Список желаемого с формой добавления."""
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
    for entry in entries:
        entry.detail = None
        if entry.item_type == "paint" and entry.item_id:
            entry.detail = db.session.get(Paint, entry.item_id)
        elif entry.item_type == "guide" and entry.item_id:
            entry.detail = db.session.get(Guide, entry.item_id)

    return render_template(
        "wishlist.html",
        title="Вишлист",
        nav_active="wishlist",
        entries=entries,
    )


def _create_item() -> None:
    name = request.form.get("name", "").strip()
    item_type = request.form.get("item_type", "model").strip().lower()
    notes = request.form.get("notes", "").strip()
    item_id = request.form.get("item_id", type=int)
    quantity = max(1, request.form.get("quantity", default=1, type=int))

    if not name:
        flash("Введите название пункта вишлиста.", "error")
        return
    if len(name) > 180 or len(notes) > 500:
        flash("Название или заметка слишком длинные.", "error")
        return
    if item_type not in ITEM_TYPES:
        item_type, item_id = "model", None

    if item_type == "paint" and item_id:
        paint = db.session.get(Paint, item_id)
        if paint is None:
            flash("Эта краска больше недоступна.", "error")
            return
        name = f"{paint.brand.name} — {paint.name}"
    elif item_type == "guide" and item_id:
        guide = db.session.get(Guide, item_id)
        if guide is None or not guide.published:
            flash("Это руководство больше недоступно.", "error")
            return
        name = guide.title
    else:
        item_id = None

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
            item_type=item_type,
            item_id=item_id,
            name=name,
            notes=notes,
            quantity=quantity,
            position=position,
        )
    )
    db.session.commit()
    log_action(current_user.id, "wishlist.create", item_type, name)
    flash("Добавлено в ваш вишлист.", "success")


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
    flash("Пункт удалён из вишлиста.", "success")
    return redirect(url_for("wishlist.wishlist"))
