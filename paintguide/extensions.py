"""Расширения Flask, инициализируются в фабрике приложения."""

from __future__ import annotations

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

# expire_on_commit=False: по умолчанию после коммита все загруженные
# объекты становятся «протухшими», и каждое обращение к их полям
# снова идёт в базу. Счётчик посещений коммитится посреди страницы —
# и каталог из 24 гайдов превращался в 109 запросов вместо десятка.
# К удалённой базе каждый запрос — это сеть, поэтому это было очень
# заметно.
db = SQLAlchemy(session_options={"expire_on_commit": False})
csrf = CSRFProtect()
login_manager = LoginManager()

login_manager.login_view = "account.login"
login_manager.login_message = "Войдите в аккаунт, чтобы сохранять материалы."
login_manager.login_message_category = "info"
login_manager.session_protection = "strong"
