"""Общие фикстуры для тестов PaintGuide."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paintguide import create_app  # noqa: E402
from paintguide.extensions import db as _db  # noqa: E402
from paintguide.models import (  # noqa: E402
    Brand,
    Country,
    Difficulty,
    Guide,
    GuideStep,
    GuideVariant,
    Paint,
    PaintLine,
    StepPaint,
    User,
    VehicleType,
    utc_now,
)


@pytest.fixture()
def app():
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        _seed(application)
        yield application
        _db.session.remove()
        _db.drop_all()


def _seed(application) -> None:
    """Минимальный набор данных для тестов."""
    if Country.query.first() is not None:
        return

    country = Country(slug="ussr", name_ru="СССР", name_en="USSR", region="Европа", flag="🇸🇺")
    vehicle_type = VehicleType(slug="tank", name_ru="Танк", name_en="Tank", icon="🛡")
    easy = Difficulty(slug="easy", name_ru="Лёгкая", name_en="Easy", rank=1, badge="easy")
    hard = Difficulty(slug="hard", name_ru="Сложная", name_en="Hard", rank=3, badge="hard")
    brand = Brand(slug="tamiya", name="Tamiya", origin="Япония")
    _db.session.add_all([country, vehicle_type, easy, hard, brand])
    _db.session.flush()

    line = PaintLine(brand_id=brand.id, slug="xf", name="XF", paint_type="acrylic")
    _db.session.add(line)
    _db.session.flush()

    black = Paint(
        brand_id=brand.id,
        line_id=line.id,
        code="XF-1",
        name="Black",
        color_hex="#141414",
        tone=8,
    )
    white = Paint(
        brand_id=brand.id,
        line_id=line.id,
        code="XF-2",
        name="Flat White",
        color_hex="#e9e6dd",
        tone=90,
    )
    _db.session.add_all([black, white])
    _db.session.flush()

    guide = Guide(
        slug="t-34-85",
        title="Т-34-85",
        subtitle="Тестовый гайд",
        country_id=country.id,
        vehicle_type_id=vehicle_type.id,
        year_from=1944,
        year_to=1958,
        description="Описание тестового руководства.",
        published=True,
        views_count=10,
    )
    _db.session.add(guide)
    _db.session.flush()

    variant = GuideVariant(
        guide_id=guide.id, difficulty_id=easy.id, title="Лёгкий вариант", is_default=True
    )
    _db.session.add(variant)
    _db.session.flush()

    step = GuideStep(variant_id=variant.id, position=1, title="Грунтовка", instruction="Покройте грунтом.")
    _db.session.add(step)
    _db.session.flush()
    _db.session.add(
        StepPaint(step_id=step.id, paint_id=black.id, area="Все области", position=0)
    )

    # Почта подтверждена: без этого вход закрыт до подтверждения.
    now = utc_now()
    admin = User(
        email="admin@paintguide.local",
        nickname="Админ",
        role="admin",
        email_verified_at=now,
        terms_accepted_at=now,
    )
    admin.set_password("paintguide")
    user = User(
        email="user@paintguide.local",
        nickname="Моделист",
        role="user",
        email_verified_at=now,
        terms_accepted_at=now,
    )
    user.set_password("paintguide")
    _db.session.add_all([admin, user])
    _db.session.commit()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def logged_in(client):
    client.post(
        "/login",
        data={"email": "user@paintguide.local", "password": "paintguide"},
        follow_redirects=True,
    )
    return client


@pytest.fixture()
def admin_client(client):
    client.post(
        "/login",
        data={"email": "admin@paintguide.local", "password": "paintguide"},
        follow_redirects=True,
    )
    return client
