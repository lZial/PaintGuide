"""Быстрая проверка всех основных страниц приложения."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paintguide import create_app  # noqa: E402
from paintguide.extensions import db  # noqa: E402
from paintguide.models import User  # noqa: E402


def main() -> int:
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        from paintguide.seed import load_seed_data

        counts = load_seed_data()
        print(
            "Данные: {guides} гайдов, {paints} красок, {steps} шагов".format(**counts)
        )
        user = User.query.filter_by(email="admin@paintguide.local").first()
        if user is None:
            user = User(email="admin@paintguide.local", nickname="Админ", role="admin")
            user.set_password("paintguide")
            db.session.add(user)
            db.session.commit()

    client = app.test_client()
    paths = [
        "/",
        "/catalog",
        "/catalog?country=ussr&vehicle_type=tank&sort=popularity",
        "/catalog?q=%D1%82-34",
        "/guides/t-34-85",
        "/guides/t-34-85?level=medium",
        "/guides/kv-1?level=hard",
        "/paints/",
        "/paints/1",
        "/paints/?brand=tamiya&sort=tone_asc",
        "/login",
        "/register",
        "/terms",
        "/healthz",
    ]
    failures = 0
    for path in paths:
        response = client.get(path)
        status = response.status_code
        flag = "OK " if status < 400 else "FAIL"
        if status >= 400:
            failures += 1
        print(f"{flag} {status} {path}")
        if status >= 400:
            print(response.get_data(as_text=True)[-1200:])

    print("--- авторизованные страницы ---")
    with client:
        client.post(
            "/login",
            data={"email": "admin@paintguide.local", "password": "paintguide"},
            follow_redirects=False,
        )
        admin_paths = [
            "/admin/",
            "/admin/guides/",
            "/admin/guides/new",
            "/admin/guides/1/edit",
            "/admin/paints/",
            "/admin/paints/new",
            "/admin/paints/1/edit",
            "/admin/reference/",
            "/admin/users/",
            "/admin/users/logs",
            "/admin/users/stats",
            "/profile",
            "/favorites/",
            "/wishlist/",
            "/inventory/",
        ]
        for path in admin_paths:
            response = client.get(path)
            status = response.status_code
            flag = "OK " if status < 400 else "FAIL"
            if status >= 400:
                failures += 1
            print(f"{flag} {status} {path}")
            if status >= 400:
                print(response.get_data(as_text=True)[-1500:])

    print(f"\nПровалов: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
