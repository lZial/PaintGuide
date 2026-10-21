"""Отправка писем: подтверждение почты и восстановление пароля.

Если SMTP настроен, письмо уходит настоящей почтой. Если нет — оно
пишется в instance/mail файлом .eml, а ссылка из письма попадает в
журнал приложения. Так систему можно развернуть и проверить без
почтового сервера, а для боевого режима достаточно задать MAIL_*.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

from flask import current_app

from .log import log_action


def _config(name: str, default: str = "") -> str:
    return (current_app.config.get(name) or default).strip()


def _mail_dir() -> Path | None:
    """Папка для писем, если её можно создать.

    На некоторых хостингах файловая система только для чтения. Тогда
    письмо не сохранится, но отправка не должна из-за этого падать.
    """
    directory = Path(current_app.instance_path) / "mail"
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    return directory


def _message(to: str, subject: str, body: str, cte: str = "") -> EmailMessage:
    message = EmailMessage()
    message["From"] = _config("MAIL_FROM", "PaintGuide <noreply@paintguide.local>")
    message["To"] = to
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain="paintguide.local")
    if cte:
        # Для файла на диске текст оставляем читаемым, без base64.
        message.set_content(body, charset="utf-8", cte=cte)
    else:
        message.set_content(body)
    return message


def _write_to_disk(to: str, subject: str, body: str) -> Path:
    """Сохранить письмо на диск — запасной путь без SMTP.

    Письмо кладём обычным текстом, а не в формате .eml с base64:
    когда почтового сервера нет, ссылку из письма нужно прочитать
    глазами.
    """
    import time

    # Имя файла должно быть безопасным для любой системы: только
    # буквы, цифры и дефис.
    # Микросекунды нужны, чтобы два письма, отправленные в одну
    # секунду, не затёрли друг друга.
    directory = _mail_dir()
    if directory is None:
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S") + f"-{time.time_ns() % 1000000:06d}"
    safe = "".join(char if char.isalnum() or char in "-_." else "_" for char in to)
    path = directory / f"{stamp}-{safe}.txt"
    text = (
        f"Кому: {to}\n"
        f"Тема: {subject}\n"
        f"Дата: {formatdate(localtime=True)}\n"
        f"{'-' * 68}\n\n"
        f"{body}\n"
    )
    try:
        path.write_text(text, encoding="utf-8")
    except OSError:
        return None
    return path


def _send_smtp(message: EmailMessage) -> None:
    server = _config("MAIL_SERVER")
    port = int(_config("MAIL_PORT", "25") or 25)
    with smtplib.SMTP(server, port, timeout=30) as client:
        if _config("MAIL_USE_TLS").lower() in {"1", "true", "yes", "on"}:
            client.starttls()
        username = _config("MAIL_USERNAME")
        if username:
            client.login(username, _config("MAIL_PASSWORD"))
        client.send_message(message)


def _prune_old_mails(keep: int = 50) -> None:
    """Убрать старые письма: без почтового сервера их копится много."""
    directory = _mail_dir()
    if directory is None:
        return
    try:
        files = sorted(directory.glob("*.txt"), key=lambda path: path.stat().st_mtime)
        for path in files[:-keep] if len(files) > keep else []:
            path.unlink()
    except OSError:
        # Уборка не должна мешать отправке письма.
        pass


def send_mail(to: str, subject: str, body: str, user_id: int | None = None) -> bool:
    """Отправить письмо. Возвращает False, если письмо не ушло."""
    message = _message(to, subject, body)
    server = _config("MAIL_SERVER")
    if server:
        try:
            _send_smtp(message)
        except Exception as error:  # noqa: BLE001
            path = _write_to_disk(to, subject, body)
            current_app.logger.warning(
                "Письмо не отправлено (%s), сохранено в %s", error, path
            )
            if user_id:
                log_action(user_id, "auth.mail_failed", "user", to, str(error)[:200])
            _prune_old_mails()
            return False
        if user_id:
            log_action(user_id, "auth.mail_sent", "user", to)
        return True

    path = _write_to_disk(to, subject, body)
    current_app.logger.info("Письмо сохранено без SMTP: %s", path)
    if user_id:
        log_action(user_id, "auth.mail_saved", "user", to)
    _prune_old_mails()
    return True


def verification_body(link: str, nickname: str = "") -> str:
    """Текст письма с подтверждением почты."""
    greeting = f", {nickname}" if nickname else ""
    return (
        f"Здравствуйте{greeting}!\n\n"
        "Подтвердите адрес электронной почты, чтобы аккаунт заработал:\n\n"
        f"{link}\n\n"
        "Ссылка действует двое суток. Если вы не регистрировались, "
        "просто проигнорируйте письмо.\n"
    )


def password_reset_body(link: str, nickname: str = "") -> str:
    """Текст письма со сменой пароля."""
    greeting = f", {nickname}" if nickname else ""
    return (
        f"Здравствуйте{greeting}!\n\n"
        "По вашему запросу можно задать новый пароль:\n\n"
        f"{link}\n\n"
        "Ссылка действует два часа. Если вы не просили сменить пароль, "
        "ничего не делайте — текущий пароль останется в силе.\n"
    )


def email_change_body(link: str, nickname: str = "") -> str:
    """Текст письма с подтверждением нового адреса."""
    greeting = f", {nickname}" if nickname else ""
    return (
        f"Здравствуйте{greeting}!\n\n"
        "Подтвердите новый адрес электронной почты:\n\n"
        f"{link}\n\n"
        "Пока адрес не подтверждён, аккаунт работает со старой почтой.\n"
    )
