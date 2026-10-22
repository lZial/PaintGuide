"""Регистрация, подтверждение почты, вход, выход и личный профиль.

Порядок работы с аккаунтом:
  1. Регистрация создаёт аккаунт и отправляет письмо со ссылкой.
  2. Ссылка подтверждает адрес — до этого вход невозможен.
  3. Забытый пароль восстанавливается по одноразовой ссылке из письма.
  4. Смена адреса требует подтверждения нового адреса; старый работает
     до этого момента.

Все токены одноразовые и хранятся в базе только в виде хеша.
"""

from __future__ import annotations

import re
from datetime import timedelta

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func, select

from ..extensions import db
from ..models import AccountToken, Favorite, Guide, User, WishlistItem, utc_now
from ..services import ratelimit
from ..services.log import log_action
from ..services.mail import (
    email_change_body,
    password_reset_body,
    send_mail,
    verification_body,
)
from ..services.tokens import generate_token, hash_token

bp = Blueprint("account", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_MIN = 8


def _verification_required() -> bool:
    """Требуется ли подтверждение адреса при регистрации."""
    from flask import current_app

    return bool(current_app.config.get("EMAIL_VERIFICATION_REQUIRED"))


def _safe_next(candidate: str | None) -> str:
    if candidate and candidate.startswith("/") and not candidate.startswith("//"):
        return candidate
    return url_for("main.home")


def _client_identity() -> str:
    """Адрес клиента — по нему ограничиваем попытки."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _issue_token(user: User, purpose: str) -> str:
    """Выдать новый токен, погасив прежние."""
    token = generate_token()
    now = utc_now()
    for existing in list(user.tokens):
        if existing.purpose == purpose:
            db.session.delete(existing)
    db.session.add(
        AccountToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_token(token),
            created_at=now,
            expires_at=now + AccountToken.lifetime(purpose),
        )
    )
    return token


def _absolute_link(endpoint: str, **values) -> str:
    """Абсолютная ссылка для письма."""
    return url_for(endpoint, _external=True, **values)


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Вход в аккаунт."""
    if current_user.is_authenticated:
        return redirect(_safe_next(request.args.get("next")))

    error = None
    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        next_url = _safe_next(request.form.get("next"))
        identity = _client_identity()
        allowed, wait = ratelimit.check("login", identity)
        if not allowed:
            error = f"Слишком много попыток. Повторите через {wait} с."
        else:
            user = db.session.scalar(select(User).where(User.email == email))
            if user is None or not user.check_password(password):
                ratelimit.hit("login", identity)
                error = "Неверная почта или пароль."
            elif user.is_blocked:
                ratelimit.hit("login", identity)
                error = "Аккаунт заблокирован администратором."
            elif _verification_required() and not user.is_verified:
                ratelimit.hit("login", identity)
                error = (
                    "Почта ещё не подтверждена. Проверьте письмо или запросите "
                    "новую ссылку."
                )
            else:
                ratelimit.reset("login", identity)
                # Сессия обнуляется на входе: иначе можно было бы
                # подсадить свой идентификатор сессии.
                session.clear()
                login_user(user, remember=True, fresh=True)
                user.last_login_at = utc_now()
                db.session.commit()
                log_action(user.id, "auth.login", "user", user.email)
                flash(f"С возвращением, {user.nickname}!", "success")
                return redirect(next_url)

    return render_template(
        "auth/login.html",
        title="Вход",
        nav_active="login",
        error=error,
        email=email,
        next_url=request.args.get("next", ""),
    )


@bp.route("/register", methods=["GET", "POST"])
def register():
    """Создание аккаунта моделиста."""
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    error = None
    sent = False
    form = {"email": "", "nickname": ""}
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        nickname = request.form.get("nickname", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("password_confirm", "")
        accepted = request.form.get("terms") == "on"
        form = {"email": email, "nickname": nickname}

        identity = _client_identity()
        allowed, wait = ratelimit.check("register", identity)
        if not allowed:
            error = f"Слишком много попыток регистрации. Повторите через {wait} с."
        elif not EMAIL_RE.match(email):
            error = "Введите корректный адрес электронной почты."
        elif len(nickname) < 2 or len(nickname) > 40:
            error = "Никнейм должен содержать от 2 до 40 символов."
        elif len(password) < PASSWORD_MIN:
            error = f"Пароль должен содержать минимум {PASSWORD_MIN} символов."
        elif password != confirm:
            error = "Пароли не совпадают."
        elif not accepted:
            error = "Необходимо принять пользовательское соглашение."
        elif db.session.scalar(select(User).where(User.email == email)) is not None:
            error = "Этот адрес уже занят."
        else:
            user = User(email=email, nickname=nickname, role="user")
            user.set_password(password)
            user.terms_accepted_at = utc_now()
            _maybe_promote(user)
            if not _verification_required():
                # Подтверждение не требуется — аккаунт готов сразу.
                user.email_verified_at = utc_now()
            db.session.add(user)
            db.session.flush()

            if _verification_required():
                token = _issue_token(user, "verify")
                db.session.commit()

                link = _absolute_link("account.verify_email", token=token)
                send_mail(
                    email,
                    "Подтвердите адрес — PaintGuide",
                    verification_body(link, nickname),
                    user_id=user.id,
                )
                # Адрес держим в сессии: в URL он попал бы в историю
                # браузера и в журнал сервера.
                session["pending_email"] = email
                sent = True
                return redirect(url_for("account.check_email"))

            db.session.commit()
            ratelimit.reset("register", identity)
            log_action(user.id, "auth.register", "user", email)
            # Сразу входим: подтверждение не требуется, ждать письма
            # незачем.
            session.clear()
            login_user(user, remember=True, fresh=True)
            user.last_login_at = utc_now()
            db.session.commit()
            flash("Профиль создан. Добро пожаловать в мастерскую!", "success")
            return redirect(url_for("main.home"))

    return render_template(
        "auth/register.html",
        title="Регистрация",
        nav_active="register",
        error=error,
        form=form,
        sent=sent,
    )


@bp.route("/check-email", methods=["GET"])
def check_email():
    """Страница «проверьте почту»."""
    email = session.pop("pending_email", "") or (
        request.args.get("email") or ""
    ).strip().lower()
    return render_template(
        "auth/check_email.html",
        title="Проверьте почту",
        nav_active="login",
        email=email,
    )


@bp.route("/verify/<token>", methods=["GET"])
def verify_email(token: str):
    """Подтверждение адреса по ссылке из письма."""
    user = _user_by_token("verify", token)
    if user is None:
        flash("Ссылка недействительна или истекла. Запросите новую.", "error")
        return redirect(url_for("account.resend_verification"))

    user.email_verified_at = utc_now()
    for item in list(user.tokens):
        if item.purpose == "verify":
            db.session.delete(item)
    db.session.commit()
    log_action(user.id, "auth.verify", "user", user.email)
    flash("Адрес подтверждён. Теперь можно войти.", "success")
    return redirect(url_for("account.login"))


@bp.route("/resend-verification", methods=["GET", "POST"])
def resend_verification():
    """Отправить письмо с подтверждением ещё раз."""
    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        identity = _client_identity()
        allowed, wait = ratelimit.check("verify", identity)
        if not allowed:
            flash(f"Слишком много запросов. Повторите через {wait} с.", "error")
        else:
            user = db.session.scalar(select(User).where(User.email == email))
            # Ответ одинаковый независимо от того, есть ли такой адрес:
            # иначе можно перебором узнать, какие адреса зарегистрированы.
            if user is not None and not user.is_verified:
                token = _issue_token(user, "verify")
                db.session.commit()
                link = _absolute_link("account.verify_email", token=token)
                send_mail(
                    email,
                    "Подтвердите адрес — PaintGuide",
                    verification_body(link, user.nickname),
                    user_id=user.id,
                )
                log_action(user.id, "auth.verify_resent", "user", email)
            ratelimit.hit("verify", identity)
            flash("Если такой адрес зарегистрирован, мы отправили новое письмо.", "success")
        return redirect(url_for("account.login"))

    return render_template(
        "auth/resend.html",
        title="Отправить письмо ещё раз",
        nav_active="login",
        email=email,
    )


@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Запрос ссылки для восстановления пароля."""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        identity = _client_identity()
        allowed, wait = ratelimit.check("reset", identity)
        if not allowed:
            flash(f"Слишком много запросов. Повторите через {wait} с.", "error")
        else:
            user = db.session.scalar(select(User).where(User.email == email))
            if user is not None and not user.is_blocked:
                token = _issue_token(user, "reset")
                db.session.commit()
                link = _absolute_link("account.reset_password", token=token)
                send_mail(
                    email,
                    "Восстановление пароля — PaintGuide",
                    password_reset_body(link, user.nickname),
                    user_id=user.id,
                )
                log_action(user.id, "auth.reset_requested", "user", email)
            ratelimit.hit("reset", identity)
            # Ответ одинаковый независимо от того, есть ли адрес.
            flash("Если такой адрес зарегистрирован, мы отправили ссылку.", "success")
        return redirect(url_for("account.login"))

    return render_template(
        "auth/forgot.html",
        title="Восстановление пароля",
        nav_active="login",
    )


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    """Задать новый пароль по ссылке из письма."""
    user = _user_by_token("reset", token)
    if user is None:
        flash("Ссылка недействительна или истекла. Запросите новую.", "error")
        return redirect(url_for("account.forgot_password"))

    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("password_confirm", "")
        if len(password) < PASSWORD_MIN:
            error = f"Пароль должен содержать минимум {PASSWORD_MIN} символов."
        elif password != confirm:
            error = "Пароли не совпадают."
        else:
            user.set_password(password)
            for item in list(user.tokens):
                if item.purpose == "reset":
                    item.mark_used()
            db.session.commit()
            log_action(user.id, "auth.password_reset", "user", user.email)
            flash("Пароль обновлён. Теперь можно войти.", "success")
            return redirect(url_for("account.login"))

    return render_template(
        "auth/reset.html",
        title="Новый пароль",
        nav_active="login",
        token=token,
        error=error,
    )


def _user_by_token(purpose: str, token: str) -> User | None:
    """Найти пользователя по действующему токену."""
    from ..services.tokens import tokens_match

    if not token:
        return None
    now = utc_now()
    for item in db.session.scalars(select(AccountToken).where(AccountToken.purpose == purpose)):
        if not item.is_usable(now):
            continue
        if tokens_match(token, item.token_hash):
            return item.user
    return None


def _maybe_promote(user: User) -> None:
    """Пользователь с адресом из ADMIN_EMAIL становится администратором."""
    admin_email = (current_app.config.get("ADMIN_EMAIL") or "").strip().lower()
    if admin_email and user.email == admin_email:
        user.role = "admin"


@bp.post("/logout")
@login_required
def logout():
    log_action(current_user.id, "auth.logout", "user", current_user.email)
    logout_user()
    session.pop("locale", None)
    flash("Вы вышли из аккаунта.", "success")
    return redirect(url_for("main.home"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """Личный кабинет: никнейм, почта, смена пароля и сводка."""
    error = None
    if request.method == "POST":
        action = request.form.get("action", "profile")
        if action == "password":
            error = _change_password()
        elif action == "email":
            error = _change_email()
        else:
            error = _update_profile()
        if error is None:
            flash("Изменения сохранены.", "success")
            return redirect(url_for("account.profile"))

    stats = {
        "guides_saved": db.session.scalar(
            select(func.count(Favorite.id)).where(
                Favorite.user_id == current_user.id, Favorite.target_type == "guide"
            )
        )
        or 0,
        "wishlist_count": db.session.scalar(
            select(func.count(WishlistItem.id)).where(WishlistItem.user_id == current_user.id)
        )
        or 0,
    }

    favorite_guides = list(
        db.session.scalars(
            select(Guide)
            .join(Favorite, Favorite.target_id == Guide.id)
            .where(
                Favorite.user_id == current_user.id,
                Favorite.target_type == "guide",
            )
            .order_by(Favorite.created_at.desc())
        )
    )
    return render_template(
        "profile.html",
        title="Профиль",
        nav_active="profile",
        stats=stats,
        favorite_guides=favorite_guides,
        error=error,
    )


def _update_profile() -> str | None:
    nickname = request.form.get("nickname", "").strip()
    if len(nickname) < 2 or len(nickname) > 40:
        return "Никнейм должен содержать от 2 до 40 символов."
    current_user.nickname = nickname
    db.session.commit()
    log_action(current_user.id, "profile.update", "user", current_user.email)
    return None


def _change_email() -> str | None:
    """Запросить новый адрес: действовать он начнёт после подтверждения."""
    email = request.form.get("email", "").strip().lower()
    if not EMAIL_RE.match(email):
        return "Введите корректный адрес электронной почты."
    if email == current_user.email:
        return "Этот адрес уже используется."
    if db.session.scalar(
        select(User).where(User.email == email, User.id != current_user.id)
    ):
        return "Этот адрес уже занят."

    current_user.pending_email = email
    token = _issue_token(current_user, "verify")
    db.session.commit()
    link = _absolute_link("account.confirm_email", token=token)
    send_mail(
        email,
        "Подтвердите новый адрес — PaintGuide",
        email_change_body(link, current_user.nickname),
        user_id=current_user.id,
    )
    log_action(current_user.id, "auth.email_change", "user", email)
    flash("Письмо с подтверждением отправлено на новый адрес.", "success")
    return None


@bp.route("/confirm-email/<token>", methods=["GET"])
def confirm_email(token: str):
    """Подтверждение нового адреса."""
    user = _user_by_token("verify", token)
    if user is None:
        flash("Ссылка недействительна или истекла.", "error")
        return redirect(url_for("account.profile"))

    if user.pending_email:
        user.email = user.pending_email
        user.pending_email = ""
        user.email_verified_at = utc_now()
    for item in list(user.tokens):
        if item.purpose == "verify":
            db.session.delete(item)
    db.session.commit()
    log_action(user.id, "auth.email_confirmed", "user", user.email)
    flash("Новый адрес подтверждён.", "success")
    return redirect(url_for("account.profile"))


def _change_password() -> str | None:
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm = request.form.get("new_password_confirm", "")
    if not current_user.check_password(current_password):
        return "Текущий пароль указан неверно."
    if len(new_password) < PASSWORD_MIN:
        return f"Новый пароль должен содержать минимум {PASSWORD_MIN} символов."
    if new_password != confirm:
        return "Пароли не совпадают."
    current_user.set_password(new_password)
    # Все прочие сессии гасим: пароль сменился — старые входы недействительны.
    for item in list(current_user.tokens):
        item.mark_used()
    db.session.commit()
    log_action(current_user.id, "profile.password", "user", current_user.email)
    return None


@bp.post("/profile/delete")
@login_required
def delete_account():
    """Удалить аккаунт и всё, что в нём накоплено."""
    password = request.form.get("password", "")
    if not current_user.check_password(password):
        flash("Пароль указан неверно — аккаунт не удалён.", "error")
        return redirect(url_for("account.profile"))
    email = current_user.email
    db.session.delete(current_user)
    db.session.commit()
    logout_user()
    log_action(None, "auth.account_deleted", "user", email)
    flash("Аккаунт удалён.", "success")
    return redirect(url_for("main.home"))
