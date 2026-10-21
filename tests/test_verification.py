"""Тесты подтверждения почты, восстановления пароля и защиты аккаунтов."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from paintguide.extensions import db
from paintguide.models import AccountToken, Favorite, User, utc_now
from paintguide.services import ratelimit
from paintguide.services.tokens import generate_token, hash_token, tokens_match


@pytest.fixture(autouse=True)
def _clean_limits(app):
    """Счётчики попыток и письма живут вне теста — чистим перед каждым."""
    ratelimit.clear()
    directory = Path(app.instance_path) / "mail"
    if directory.exists():
        for item in directory.glob("*.txt"):
            item.unlink()
    yield
    ratelimit.clear()


@pytest.fixture()
def verification_on(app):
    """Включить обязательное подтверждение адреса.

    Сама механика проверки в приложении остаётся: её включают
    переменной окружения, когда появится настоящий SMTP.
    """
    app.config["EMAIL_VERIFICATION_REQUIRED"] = True
    return app


def _register(client, email="new@paintguide.local", password="secret123"):
    return client.post(
        "/register",
        data={
            "nickname": "Новый",
            "email": email,
            "password": password,
            "password_confirm": password,
            "terms": "on",
        },
        follow_redirects=True,
    )


def _mail_links(app) -> list[str]:
    """Ссылки из писем, сохранённых на диск.

    Письма складываются по строкам (стандарт MIME), поэтому длинная
    ссылка разрывается переносом — разворачиваем его обратно.
    """
    directory = Path(app.instance_path) / "mail"
    links: list[str] = []
    for path in sorted(directory.glob("*.txt")):
        body = path.read_text(encoding="utf-8").replace("\n ", "")
        links.extend(re.findall(r"https?://[^\s<>]+/verify/[^\s<>]+", body))
        links.extend(re.findall(r"https?://[^\s<>]+/reset-password/[^\s<>]+", body))
        links.extend(re.findall(r"https?://[^\s<>]+/confirm-email/[^\s<>]+", body))
    return links


def test_register_requires_email_confirmation(client, app, verification_on):
    """После регистрации аккаунт создан, но почта ещё не подтверждена."""
    _register(client)
    with app.app_context():
        user = User.query.filter_by(email="new@paintguide.local").first()
        assert user is not None
        assert user.is_verified is False
        assert user.token_for("verify") is not None


def test_unverified_user_cannot_log_in(client, app, verification_on):
    """До подтверждения почты вход закрыт."""
    _register(client)
    response = client.post(
        "/login",
        data={"email": "new@paintguide.local", "password": "secret123"},
        follow_redirects=True,
    )
    assert "не подтверждена" in response.get_data(as_text=True)


def test_verification_link_confirms_email(client, app, verification_on):
    """Ссылка из письма подтверждает адрес, и после неё можно войти."""
    _register(client)
    links = _mail_links(app)
    assert links, "письмо с подтверждением не сохранено"

    token = links[0].rsplit("/", 1)[-1]
    response = client.get(f"/verify/{token}", follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email="new@paintguide.local").first()
        assert user.is_verified is True
        assert user.token_for("verify") is None

    response = client.post(
        "/login",
        data={"email": "new@paintguide.local", "password": "secret123"},
        follow_redirects=True,
    )
    assert "С возвращением" in response.get_data(as_text=True)


def test_verification_token_is_single_use(client, app, verification_on):
    """Ссылка не работает второй раз."""
    _register(client)
    token = _mail_links(app)[0].rsplit("/", 1)[-1]
    client.get(f"/verify/{token}")
    response = client.get(f"/verify/{token}", follow_redirects=True)
    assert "недействительна" in response.get_data(as_text=True)


def test_invalid_verification_token_is_rejected(client):
    response = client.get("/verify/совсем-не-верный-токен", follow_redirects=True)
    assert "недействительна" in response.get_data(as_text=True)


def test_resend_verification_sends_new_link(client, app, verification_on):
    """Письмо с подтверждением можно запросить повторно."""
    _register(client)
    before = len(_mail_links(app))
    client.post(
        "/resend-verification",
        data={"email": "new@paintguide.local"},
        follow_redirects=True,
    )
    assert len(_mail_links(app)) > before


def test_resend_does_not_leak_account_existence(client, app, verification_on):
    """Ответ одинаков для существующего и несуществующего адреса."""
    _register(client)
    first = client.post(
        "/resend-verification",
        data={"email": "new@paintguide.local"},
        follow_redirects=True,
    ).get_data(as_text=True)
    second = client.post(
        "/resend-verification",
        data={"email": "нет-такого@paintguide.local"},
        follow_redirects=True,
    ).get_data(as_text=True)
    assert "если такой адрес" in first.lower() or "если такой адрес" in second.lower()


def test_forgot_password_creates_reset_link(client, app):
    """По заявке отправляется ссылка для смены пароля."""
    client.post(
        "/forgot-password",
        data={"email": "user@paintguide.local"},
        follow_redirects=True,
    )
    links = _mail_links(app)
    assert any("/reset-password/" in link for link in links)


def test_password_reset_changes_password(client, app):
    """По ссылке можно задать новый пароль, после чего вход работает."""
    client.post(
        "/forgot-password",
        data={"email": "user@paintguide.local"},
        follow_redirects=True,
    )
    links = [link for link in _mail_links(app) if "/reset-password/" in link]
    assert links
    token = links[0].rsplit("/", 1)[-1]

    response = client.post(
        f"/reset-password/{token}",
        data={"password": "новыйпароль123", "password_confirm": "новыйпароль123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="user@paintguide.local").first()
        assert user.check_password("новыйпароль123")
        assert not user.check_password("paintguide")


def test_reset_password_rejects_short_password(client, app):
    """Слишком короткий пароль не принимается."""
    client.post(
        "/forgot-password",
        data={"email": "user@paintguide.local"},
        follow_redirects=True,
    )
    links = [link for link in _mail_links(app) if "/reset-password/" in link]
    token = links[0].rsplit("/", 1)[-1]
    response = client.post(
        f"/reset-password/{token}",
        data={"password": "123", "password_confirm": "123"},
    )
    assert "минимум" in response.get_data(as_text=True)


def test_email_change_requires_confirmation(client, app):
    """Новый адрес действует только после подтверждения."""
    client.post(
        "/login",
        data={"email": "user@paintguide.local", "password": "paintguide"},
        follow_redirects=True,
    )
    response = client.post(
        "/profile",
        data={"action": "email", "email": "novy@paintguide.local"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="user@paintguide.local").first()
        assert user is not None
        assert user.pending_email == "novy@paintguide.local"
        assert user.email == "user@paintguide.local"

    links = _mail_links(app)
    confirm_links = [link for link in links if "/confirm-email/" in link]
    assert confirm_links
    token = confirm_links[0].rsplit("/", 1)[-1]
    client.get(f"/confirm-email/{token}", follow_redirects=True)

    with app.app_context():
        user = User.query.filter_by(email="novy@paintguide.local").first()
        assert user is not None
        assert user.pending_email == ""


def test_login_is_rate_limited(client):
    """После серии неудачных входов дальше пускать перестаёт."""
    for _ in range(12):
        client.post(
            "/login",
            data={"email": "user@paintguide.local", "password": "неверный"},
        )
    response = client.post(
        "/login",
        data={"email": "user@paintguide.local", "password": "неверный"},
    )
    assert "Слишком много попыток" in response.get_data(as_text=True)


def test_account_can_be_deleted(client, app):
    """Аккаунт удаляется вместе с накопленным."""
    client.post(
        "/login",
        data={"email": "user@paintguide.local", "password": "paintguide"},
        follow_redirects=True,
    )
    response = client.post(
        "/profile/delete",
        data={"password": "paintguide"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        assert User.query.filter_by(email="user@paintguide.local").first() is None


def test_token_helpers_work():
    """Токен хранится только в виде хеша."""
    token = generate_token()
    assert len(token) >= 32
    stored = hash_token(token)
    assert stored != token
    assert tokens_match(token, stored)
    assert not tokens_match("другой", stored)


def test_expired_token_is_not_usable(app):
    """Просроченный токен не работает."""
    with app.app_context():
        user = User.query.filter_by(email="user@paintguide.local").first()
        token = AccountToken(
            user_id=user.id,
            purpose="verify",
            token_hash=hash_token("что-то"),
            expires_at=utc_now() - __import__("datetime").timedelta(hours=1),
        )
        db.session.add(token)
        db.session.commit()
        assert token.is_usable() is False

def test_registration_without_confirmation_allows_login(client, app):
    """По умолчанию подтверждение не требуется.

    Так сайт остаётся рабочим там, где письма не доходят: человек
    регистрируется и сразу оказывается в своём кабинете.
    """
    app.config["EMAIL_VERIFICATION_REQUIRED"] = False
    response = _register(client)
    assert "Добро пожаловать" in response.get_data(as_text=True)

    with app.app_context():
        user = User.query.filter_by(email="new@paintguide.local").first()
        assert user is not None
        assert user.is_verified is True

    # Кабинет доступен сразу после регистрации.
    profile = client.get("/profile")
    assert profile.status_code == 200
    assert "new@paintguide.local" in profile.get_data(as_text=True)


def test_registration_without_confirmation_sends_no_mail(client, app):
    """Без подтверждения письма не отправляются."""
    app.config["EMAIL_VERIFICATION_REQUIRED"] = False
    _register(client)
    assert _mail_links(app) == []


def test_profile_hides_confirmation_badge_without_verification(client, app):
    """В профиле нет напоминания о подтверждении, если оно не нужно."""
    app.config["EMAIL_VERIFICATION_REQUIRED"] = False
    client.post(
        "/login",
        data={"email": "user@paintguide.local", "password": "paintguide"},
        follow_redirects=True,
    )
    body = client.get("/profile").get_data(as_text=True)
    assert "Адрес не подтверждён" not in body

def test_registration_logs_user_in_immediately(client, app):
    """После регистрации пользователь уже вошёл.

    Без этого человек оказывается на странице, где все его кнопки
    требуют входа, — и он решает, что регистрация не сработала.
    """
    app.config["EMAIL_VERIFICATION_REQUIRED"] = False
    response = _register(client, email="vhod@paintguide.local")
    body = response.get_data(as_text=True)
    assert "Добро пожаловать" in body
    # Личный кабинет доступен без повторного входа.
    profile = client.get("/profile")
    assert profile.status_code == 200
    assert "vhod@paintguide.local" in profile.get_data(as_text=True)


def test_registration_with_existing_email_creates_no_duplicate(client, app):
    """Повторная регистрация того же адреса не создаёт второй аккаунт."""
    app.config["EMAIL_VERIFICATION_REQUIRED"] = False
    _register(client, email="двойной@paintguide.local")

    # Тот же адрес ещё раз: аккаунт должен остаться один.
    client.get("/register")
    client.post("/register", data={
        "nickname": "Двойной",
        "email": "двойной@paintguide.local",
        "password": "secret123",
        "password_confirm": "secret123",
        "terms": "on",
    })

    with app.app_context():
        same = db.session.scalars(
            db.select(User).where(User.email == "двойной@paintguide.local")
        ).all()
        assert len(same) == 1


def test_duplicate_email_is_reported_for_guest(client, app):
    """Гостю, пришедшему на регистрацию, сообщают, что адрес занят."""
    app.config["EMAIL_VERIFICATION_REQUIRED"] = False
    _register(client, email="занятый@paintguide.local")

    # Выходим из аккаунта, чтобы страница регистрации открылась
    # заново, как у нового посетителя.
    client.post("/logout", follow_redirects=True)
    response = client.post("/register", data={
        "nickname": "Третий",
        "email": "занятый@paintguide.local",
        "password": "secret123",
        "password_confirm": "secret123",
        "terms": "on",
    })
    assert "уже занят" in response.get_data(as_text=True)
