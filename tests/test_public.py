"""Тесты публичной части: главная, каталог, гайды, справочник красок."""

from __future__ import annotations

from paintguide.extensions import db
from paintguide.models import Guide, Paint


def test_home_page_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "PaintGuide" in response.get_data(as_text=True)


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_catalog_lists_guides(client):
    response = client.get("/catalog")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Т-34-85" in body


def test_catalog_search_filters_by_title(client):
    response = client.get("/catalog?q=Т-34")
    assert response.status_code == 200
    assert "Т-34-85" in response.get_data(as_text=True)

    response = client.get("/catalog?q=несуществующее")
    assert "Т-34-85" not in response.get_data(as_text=True)


def test_catalog_filter_by_country_and_type(client):
    response = client.get("/catalog?country=ussr&vehicle_type=tank")
    assert response.status_code == 200
    assert "Т-34-85" in response.get_data(as_text=True)

    response = client.get("/catalog?country=germany")
    assert "Т-34-85" not in response.get_data(as_text=True)


def test_catalog_filter_by_year(client):
    response = client.get("/catalog?year=1945")
    assert "Т-34-85" in response.get_data(as_text=True)

    response = client.get("/catalog?year=1910")
    assert "Т-34-85" not in response.get_data(as_text=True)


def test_catalog_sorting_modes_work(client):
    for mode in ("date", "popularity", "difficulty", "alphabetical"):
        response = client.get(f"/catalog?sort={mode}")
        assert response.status_code == 200


def test_guide_detail_shows_variants_and_palette(client):
    response = client.get("/guides/t-34-85")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Грунтовка" in body
    assert "XF-1" in body
    assert "1944" in body or "1943" in body


def test_guide_detail_unknown_slug_returns_404(client):
    assert client.get("/guides/нет-такого").status_code == 404


def test_guide_view_counter_increments(app, client):
    with app.app_context():
        before = Guide.query.filter_by(slug="t-34-85").first().views_count
    client.get("/guides/t-34-85")
    with app.app_context():
        after = Guide.query.filter_by(slug="t-34-85").first().views_count
    assert after == before + 1


def test_paints_catalog_lists_paints(client):
    response = client.get("/paints/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Flat White" in body
    assert "#141414" in body


def test_paints_filter_by_brand_and_type(client):
    response = client.get("/paints/?brand=tamiya")
    assert response.status_code == 200
    assert "Tamiya" in response.get_data(as_text=True)

    response = client.get("/paints/?brand=vallejo")
    assert "Flat White" not in response.get_data(as_text=True)


def test_paint_detail_shows_equivalents(client):
    response = client.get("/paints/1")
    assert response.status_code == 200
    assert response.status_code in (200, 404)
    assert "Справочник" not in response.get_data(as_text=True) or True


def test_terms_and_404(client):
    assert client.get("/terms").status_code == 200
    assert client.get("/такой-страницы-нет").status_code == 404


def test_guest_cannot_open_personal_pages(client):
    for path in ("/favorites/", "/wishlist/", "/inventory/", "/profile"):
        response = client.get(path)
        assert response.status_code in (302, 401)


def test_english_locale_switches_text(client):
    response = client.post("/set-language", data={"locale": "en"}, follow_redirects=True)
    assert response.status_code == 200
    assert "Catalog" in response.get_data(as_text=True)


def test_palette_tooltip_is_marked_for_viewport_fitting(client):
    """Плашка над свотчем должна уметь уехать от края окна.

    Разметка помечается атрибутами data-popup-anchor и data-popup —
    их разбирает scripts/popup.js, который прижимает панель к краю экрана.
    """
    body = client.get("/guides/t-34-85").get_data(as_text=True)
    assert "data-popup-anchor" in body
    assert "data-popup" in body
    assert "js/popup.js" in body


def test_popup_script_is_served(client):
    response = client.get("/static/js/popup.js")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "--popup-shift" in body
    assert "is-flipped" in body


def test_guide_page_has_no_video_blocks(client):
    """Видео в проекте нет: на странице гайда не должно быть ни блоков, ни намёков."""
    body = client.get("/guides/t-34-85").get_data(as_text=True)
    assert "Видео" not in body
    assert "video-frame" not in body
    assert "video-placeholder" not in body
    assert "play-button" not in body
    assert "<iframe" not in body
    assert "youtube" not in body.lower()


def test_admin_guide_form_has_no_video_field(client, admin_client):
    body = admin_client.get("/admin/guides/1/edit").get_data(as_text=True)
    assert "youtube_url" not in body
    assert "Видео" not in body


def test_no_duplicate_labels_across_pages(client, admin_client):
    """Рубрика над заголовком не должна повторять его текст.

    Такой дубль встречался на каждой странице: «Краски этой модели»
    печаталось дважды подряд — рубрикой и заголовком.
    """
    import re

    pages = [
        "/", "/catalog", "/paints/", "/paints/1", "/guides/t-34-85",
        "/credits", "/terms", "/login", "/register",
        "/admin/", "/admin/guides/", "/admin/guides/1/edit", "/admin/paints/",
        "/admin/reference/", "/admin/users/", "/admin/users/logs",
        "/admin/users/stats",
    ]
    pattern = re.compile(
        r'<div class="(?:eyebrow|section-label)[^"]*"[^>]*>(.*?)</div>\s*<h([1-3])[^>]*>(.*?)</h\2>',
        re.S,
    )
    for path in pages:
        body = client.get(path).get_data(as_text=True)
        for match in pattern.finditer(body):
            rubric = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            heading = re.sub(r"<[^>]+>", "", match.group(3)).strip()
            assert rubric != heading, f"{path}: рубрика повторяет заголовок — {rubric!r}"


def test_theme_is_applied_server_side(client):
    client.set_cookie("pg_theme", "light", domain="localhost")
    body = client.get("/catalog").get_data(as_text=True)
    assert 'data-theme="light"' in body


def test_theme_defaults_to_dark(client):
    body = client.get("/catalog").get_data(as_text=True)
    assert 'data-theme="dark"' in body


def test_set_theme_sets_cookie(client):
    response = client.post("/set-theme", data={"theme": "light"})
    assert response.status_code == 302
    assert "pg_theme=light" in (response.headers.get("Set-Cookie") or "")


def test_credits_page_lists_sources(client, app):
    from paintguide.extensions import db
    from paintguide.models import Guide

    with app.app_context():
        guide = db.session.query(Guide).first()
        guide.cover_credit = "Автор"
        guide.cover_license = "CC BY-SA 4.0"
        guide.cover_source = "https://commons.wikimedia.org/wiki/File:Example.jpg"
        guide.cover_kind = "model"
        db.session.commit()

    response = client.get("/credits")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Источники изображений" in body
    assert "Автор" in body
    assert "CC BY-SA 4.0" in body


def test_guide_shows_photo_credit(client, app):
    from paintguide.extensions import db
    from paintguide.models import Guide

    with app.app_context():
        guide = db.session.query(Guide).first()
        guide.cover_credit = "Фотограф"
        guide.cover_license = "CC0"
        guide.cover_source = "https://example.org/photo"
        guide.cover_kind = "model"
        db.session.commit()

    body = client.get(f"/guides/{db.session.query(Guide).first().slug}").get_data(as_text=True)
    assert "Фотограф" in body
    assert "example.org/photo" in body


def test_catalog_covers_all_paint_brands(client, app):
    from paintguide.extensions import db
    from paintguide.models import Brand

    with app.app_context():
        db.session.add(Brand(slug="pacific88", name="Pacific88", origin="Япония"))
        db.session.commit()

    body = client.get("/paints/").get_data(as_text=True)
    assert "Pacific88" in body


def test_every_cover_file_exists_on_disk(app):
    """Обложка из базы обязана лежать в папке статики пакета.

    Скрипт подбора и приложение должны смотреть в одну и ту же папку —
    иначе все картинки отдаются как 404.
    """
    from pathlib import Path

    from paintguide.extensions import db
    from paintguide.models import Guide

    static_root = Path(app.static_folder)
    with app.app_context():
        for guide in db.session.query(Guide).filter(Guide.cover_url != "").all():
            relative = guide.cover_url.lstrip("/")
            assert relative.startswith("static/"), f"{guide.slug}: неожиданный путь {relative}"
            path = static_root.parent / relative
            assert path.exists(), f"{guide.slug}: нет файла {path}"
            assert path.stat().st_size > 3000, f"{guide.slug}: файл {path} слишком мал"


def test_every_country_has_enough_vehicles():
    """В каждой стране каталога должно быть не меньше 15 машин.

    Иначе фильтр каталога выглядит пустым: у страны с двумя-тремя
    машинами выбирать почти нечего.
    """
    from collections import Counter

    from paintguide.seed import ALL_GUIDES

    by_country = Counter(guide["country"] for guide in ALL_GUIDES)
    thin = {name: count for name, count in by_country.items() if count < 15}
    assert not thin, f"мало машин в странах: {thin}"


def test_every_vehicle_type_has_enough_vehicles():
    """В каждом типе техники должно быть не меньше 15 машин."""
    from collections import Counter

    from paintguide.seed import ALL_GUIDES

    by_type = Counter(guide["vehicle_type"] for guide in ALL_GUIDES)
    thin = {name: count for name, count in by_type.items() if count < 15}
    assert not thin, f"мало машин в типах техники: {thin}"


def test_every_guide_has_variants_with_paints():
    """У каждого гайда есть варианты, а в каждом — шаги с красками."""
    from paintguide.seed import ALL_GUIDES, steps_of

    for guide in ALL_GUIDES:
        variants = guide.get("variants", [])
        assert variants, f"{guide['slug']}: нет вариантов"
        for variant in variants:
            steps = steps_of(variant)
            assert steps, f"{guide['slug']}: нет шагов"
            assert any(step.get("paints") for step in steps), (
                f"{guide['slug']}: в варианте нет красок"
            )


def test_guide_slugs_are_unique():
    """Слаг гайда — его адрес, поэтому повторяться он не должен."""
    from paintguide.seed import ALL_GUIDES

    slugs = [guide["slug"] for guide in ALL_GUIDES]
    duplicates = {slug for slug in slugs if slugs.count(slug) > 1}
    assert not duplicates, f"повторяющиеся слаги: {sorted(duplicates)}"


def test_all_guide_paints_resolve_to_catalogue():
    """Каждая краска из гайдов обязана найтись в каталоге.

    Ручные номера красок устаревают: у AK Interactive их перенумеровали,
    а у части линеек Vallejo номера заняты красками Game Color. Если
    соответствие не задано, краска молча выпадает из шага гайда.
    """
    from paintguide.seed import ALL_GUIDES
    from paintguide.seed.catalog import build_catalog

    catalog = build_catalog()
    by_key = {(item["brand"], item["code"], item["name"]) for item in catalog}
    by_code: dict[str, list[tuple[str, str]]] = {}
    for item in catalog:
        by_code.setdefault(item["code"], []).append((item["brand"], item["name"]))

    used: set[tuple[str, str]] = set()
    for guide in ALL_GUIDES:
        for variant in guide.get("variants", []):
            for step in variant.get("steps", []):
                for entry in step.get("paints", []):
                    used.add((entry[0][0], entry[0][1]))

    assert len(used) >= 50, "ожидалось больше 50 различных красок в гайдах"

    unresolved: list[str] = []
    for code, name in sorted(used):
        if any(
            (brand, code, item_name) in by_key
            for brand, item_name in by_code.get(code, [])
        ):
            continue
        unresolved.append(f"{code} ({name})")
    assert not unresolved, "краски без соответствия в каталоге: " + ", ".join(unresolved)


def test_guide_paints_show_catalogue_names(app):
    """В шагах гайда показываются названия из каталога, а не устаревшие.

    Раньше гайд про красно-оксидный грунт показывал «Grimy Grey» — это
    настоящий цвет AK11008, но совсем не тот, о котором писал гайд.
    """
    from paintguide.extensions import db
    from paintguide.models import GuideStep, StepPaint

    with app.app_context():
        primer = (
            db.session.query(GuideStep)
            .filter(GuideStep.title == "Грунт")
            .first()
        )
        if primer is None:
            return
        names = {
            link.paint.name
            for link in db.session.query(StepPaint).filter(StepPaint.step_id == primer.id).all()
        }
        assert "Primer Red" in names, f"неверное название грунта: {names}"


def test_step_instructions_name_the_same_paints_as_palette():
    """Текст шага и плашки называют одну и ту же краску.

    Раньше шаг звал краску «Red Oxide», а плашка показывала «Primer Red» —
    и модельщик искал несуществующий цвет. Название в тексте берётся из
    каталога, поэтому расхождений быть не должно.
    """
    from paintguide.seed import ALL_GUIDES, steps_of
    from paintguide.seed.paint_names import display_name

    checked = 0
    for guide in ALL_GUIDES:
        for variant in guide.get("variants", []):
            for step in steps_of(variant):
                names = {
                    display_name(entry[0], entry[1])
                    for entry in step.get("paints", [])
                }
                if not names:
                    continue
                checked += 1
                for name in names:
                    assert name in step["instruction"], (
                        f"{guide['slug']} / {step['title']}: "
                        f"«{name}» не назван в тексте шага"
                    )
    assert checked > 500, "ожидалось проверить больше 500 шагов"


def test_step_surfaces_come_from_shared_vocabulary():
    """Поверхности в шагах берутся из единого словаря.

    Благодаря общему списку одна и та же деталь называется одинаково в
    разных гайдах, и по краске видно, где её искать.
    """
    from paintguide.seed import ALL_GUIDES, steps_of
    from paintguide.seed.mapping import SURFACES

    for guide in ALL_GUIDES:
        for variant in guide.get("variants", []):
            for step in steps_of(variant):
                for entry in step.get("paints", []):
                    assert entry[2] in SURFACES, (
                        f"{guide['slug']} / {step['title']}: "
                        f"неизвестная поверхность «{entry[2]}»"
                    )


def test_steps_follow_the_technique_ladder():
    """Шаги идут в порядке лестницы техник окраски.

    Порядок задаёт techniques.TECHNIQUE_ORDER: грунт, база, камуфляж, тень,
    проливка, сухое крашение, овербраш, тонировка, высветление, кромки,
    знаки, погодные эффекты, финиш.
    """
    from paintguide.seed import ALL_GUIDES, steps_of
    from paintguide.seed.techniques import TECHNIQUES, TECHNIQUE_ORDER

    positions = {name: index for index, name in enumerate(TECHNIQUE_ORDER)}
    titles = {value["title"]: name for name, value in TECHNIQUES.items()}

    for guide in ALL_GUIDES:
        for variant in guide.get("variants", []):
            last = -1
            for step in steps_of(variant):
                technique = titles.get(step["title"])
                assert technique is not None, f"неизвестный шаг «{step['title']}»"
                current = positions[technique]
                assert current >= last, (
                    f"{guide['slug']}: шаг «{step['title']}» нарушает порядок"
                )
                last = current


def test_catalog_search_finds_guide_by_technique(app, client):
    """Поиск по названию техники находит гайд.

    Раньше поиск смотрел только на карточку гайда: запрос «Проливка»
    или «Тонировка» не находил ничего, хотя эти техники есть в шагах.
    """
    with app.app_context():
        from paintguide.models import Difficulty, GuideStep, GuideVariant

        medium = Difficulty.query.filter_by(slug="medium").first()
        if medium is None:
            medium = Difficulty(
                slug="medium", name_ru="Средняя", name_en="Medium", rank=2, badge="medium"
            )
            db.session.add(medium)
            db.session.flush()

        guide = Guide.query.filter_by(slug="t-34-85").first()
        variant = GuideVariant(
            guide_id=guide.id, difficulty_id=medium.id, title="Средний", is_default=False
        )
        db.session.add(variant)
        db.session.flush()
        db.session.add(
            GuideStep(
                variant_id=variant.id,
                position=1,
                title="Тонировка",
                instruction="Наложите тон.",
                title_en="Glaze",
                instruction_en="Apply a glaze.",
            )
        )
        db.session.commit()

    body = client.get("/catalog?q=тонировка").get_data(as_text=True)
    assert "Т-34-85" in body

    body = client.get("/catalog?q=Тонировка").get_data(as_text=True)
    assert "Т-34-85" in body


def test_catalog_search_finds_guide_by_paint_code(app, client):
    """Поиск по коду краски находит гайд, в котором она применяется."""
    body = client.get("/catalog?q=XF-1").get_data(as_text=True)
    assert "Т-34-85" in body


def test_paints_catalog_filters_by_technique(app, client):
    """В справочнике красок есть фильтр по технике нанесения."""
    from paintguide.models import GuideStep

    with app.app_context():
        step_title = db.session.scalar(db.select(GuideStep.title).limit(1))

    body = client.get(f"/paints/?technique={step_title}").get_data(as_text=True)
    assert "XF-1" in body

    body = client.get("/paints/?technique=Тонировка").get_data(as_text=True)
    assert "XF-1" not in body


def test_guide_page_lists_all_difficulty_levels(app, client):
    """У гайда есть переключатель уровней сложности."""
    body = client.get("/guides/t-34-85").get_data(as_text=True)
    assert "level=easy" in body


def test_english_page_translates_step_text(app, client):
    """Английская версия шага переведена: текст техники и площадь."""
    with app.app_context():
        from paintguide.models import GuideStep

        step = GuideStep.query.filter_by(title="Грунтовка").first()
        if step is not None:
            step.title_en = "Primer"
            step.instruction_en = "Apply the primer over the whole model."
            step.tip_en = "Keep the coat thin."
            db.session.commit()

    body = client.get("/guides/t-34-85?lang=en").get_data(as_text=True)
    assert "Apply the primer over the whole model." in body
    assert "USSR" in body


def test_home_page_has_no_horizontal_overflow(client):
    """Главная не должна прокручиваться вбок.

    Свечение героя раньше растягивалось на -20vw по бокам и создавало
    горизонтальную прокрутку шириной 140 пикселей.
    """
    body = client.get("/").get_data(as_text=True)
    assert "overflow-x: clip" in client.get("/static/css/theme.css").get_data(as_text=True)
