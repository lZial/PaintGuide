"""Инвентарь красок: что есть на полке и что планируется купить."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select

from ..extensions import db
from ..models import Paint, PaintStock
from ..services.log import log_action

bp = Blueprint("inventory", __name__, url_prefix="/inventory")


@bp.route("/", methods=["GET", "POST"])
@login_required
def inventory():
    """Список красок на полке и в списке покупок."""
    if request.method == "POST":
        _add_paint()
        return redirect(url_for("inventory.inventory"))

    owned = list(
        db.session.scalars(
            select(PaintStock)
            .where(PaintStock.user_id == current_user.id, PaintStock.status == "owned")
            .order_by(PaintStock.updated_at.desc())
        )
    )
    wanted = list(
        db.session.scalars(
            select(PaintStock)
            .where(PaintStock.user_id == current_user.id, PaintStock.status == "wanted")
            .order_by(PaintStock.updated_at.desc())
        )
    )
    counts = {
        "owned": db.session.scalar(
            select(func.count(PaintStock.id)).where(
                PaintStock.user_id == current_user.id, PaintStock.status == "owned"
            )
        )
        or 0,
        "wanted": db.session.scalar(
            select(func.count(PaintStock.id)).where(
                PaintStock.user_id == current_user.id, PaintStock.status == "wanted"
            )
        )
        or 0,
    }
    return render_template(
        "inventory.html",
        title="Инвентарь красок",
        nav_active="inventory",
        owned=owned,
        wanted=wanted,
        counts=counts,
        all_paints=_all_paints(),
    )


def _all_paints():
    """Список красок для выпадающего списка добавления."""
    from ..models import Paint

    return list(
        db.session.scalars(
            select(Paint).join(Paint.brand).order_by(Paint.brand_id, Paint.name)
        )
    )


def _add_paint() -> None:
    paint_id = request.form.get("paint_id", type=int)
    status = request.form.get("status", "owned")
    quantity = max(1, request.form.get("quantity", default=1, type=int))
    notes = request.form.get("notes", "").strip()[:300]

    if status not in {"owned", "wanted"}:
        status = "owned"
    paint = db.session.get(Paint, paint_id) if paint_id else None
    if paint is None:
        flash("Выберите краску из справочника.", "error")
        return

    stock = db.session.scalar(
        select(PaintStock).where(
            PaintStock.user_id == current_user.id, PaintStock.paint_id == paint.id
        )
    )
    if stock is None:
        db.session.add(
            PaintStock(
                user_id=current_user.id,
                paint_id=paint.id,
                status=status,
                quantity=quantity,
                notes=notes,
            )
        )
    else:
        stock.status = status
        stock.quantity = quantity
        stock.notes = notes
    db.session.commit()
    log_action(current_user.id, "inventory.add", "paint", paint.display_name, status)
    flash("Инвентарь обновлён.", "success")


@bp.post("/<int:stock_id>/toggle")
@login_required
def toggle_status(stock_id: int):
    stock = db.session.scalar(
        select(PaintStock).where(
            PaintStock.id == stock_id, PaintStock.user_id == current_user.id
        )
    )
    if stock is None:
        flash("Запись не найдена.", "error")
        return redirect(url_for("inventory.inventory"))
    stock.status = "wanted" if stock.status == "owned" else "owned"
    db.session.commit()
    flash("Статус краски обновлён.", "success")
    return redirect(url_for("inventory.inventory"))


@bp.post("/<int:stock_id>/delete")
@login_required
def delete_stock(stock_id: int):
    stock = db.session.scalar(
        select(PaintStock).where(
            PaintStock.id == stock_id, PaintStock.user_id == current_user.id
        )
    )
    if stock is None:
        flash("Запись не найдена.", "error")
        return redirect(url_for("inventory.inventory"))
    db.session.delete(stock)
    db.session.commit()
    flash("Краска удалена из инвентаря.", "success")
    return redirect(url_for("inventory.inventory"))
