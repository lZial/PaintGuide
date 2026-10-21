"""Тесты разметки карточки руководства."""

from __future__ import annotations

from html.parser import HTMLParser


class NestedAnchors(HTMLParser):
    """Ищет ссылки внутри ссылок — такой HTML браузер разрывает.

    Если картинка лежит внутри ссылки на гайд, а рядом ещё и ссылка
    «Фото» на источник, браузер закрывает внешнюю ссылку на «Фото»,
    и картинка перестаёт открывать гайд.
    """

    def __init__(self) -> None:
        super().__init__()
        self.depth = 0
        self.problems = 0

    def handle_starttag(self, tag, attrs) -> None:
        if tag == "a":
            if self.depth:
                self.problems += 1
            self.depth += 1

    def handle_endtag(self, tag) -> None:
        if tag == "a" and self.depth:
            self.depth -= 1


def test_guide_card_has_no_nested_links(client):
    """В карточке гайда не должно быть вложенных ссылок."""
    body = client.get("/catalog").get_data(as_text=True)
    parser = NestedAnchors()
    parser.feed(body)
    assert parser.problems == 0


def test_card_image_opens_guide(client):
    """Картинка в карточке ведёт на гайд."""
    body = client.get("/catalog").get_data(as_text=True)
    # Ссылка на гайд лежит отдельным слоем поверх картинки.
    assert 'class="card-art-link"' in body
    assert "card-art-link" in body


def test_photo_credit_stays_separate(app, client):
    """Ссылка «Фото» на источник — отдельная, не внутри ссылки на гайд."""
    from paintguide.extensions import db
    from paintguide.models import Guide

    with app.app_context():
        guide = Guide.query.filter_by(slug="t-34-85").first()
        guide.cover_url = "/static/img/vehicles/t-34-85.jpg"
        guide.cover_source = "https://commons.wikimedia.org/wiki/File:Example.jpg"
        guide.cover_credit = "Автор"
        guide.cover_license = "CC BY-SA 4.0"
        db.session.commit()

    body = client.get("/catalog").get_data(as_text=True)
    assert 'class="card-photo-credit"' in body
    # Обе ссылки существуют независимо друг от друга.
    assert body.count('class="card-art-link"') >= 1
    assert body.count('class="card-photo-credit"') >= 1


def test_no_nested_links_on_main_pages(client):
    """Ни на одной основной странице нет вложенных ссылок."""
    for path in ("/", "/catalog", "/paints/", "/guides/t-34-85", "/login"):
        body = client.get(path).get_data(as_text=True)
        parser = NestedAnchors()
        parser.feed(body)
        assert parser.problems == 0, f"{path}: вложенные ссылки"
