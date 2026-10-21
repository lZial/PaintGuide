"""Проверка сайта: обложки, база, скорость, доступность.

Запуск:  python scripts/audit.py
Результат печатается в консоль и складывается в docs/audit-report.md.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from paintguide import create_app  # noqa: E402
from paintguide.extensions import db  # noqa: E402
from paintguide.models import (  # noqa: E402
    Difficulty,
    Guide,
    GuideStep,
    GuideVariant,
    Paint,
    StepPaint,
)
from paintguide.seed import ALL_GUIDES  # noqa: E402

PACKAGE = ROOT / "paintguide"
COVERS_FILE = PACKAGE / "seed" / "covers.json"
REPORT_FILE = ROOT / "docs" / "audit-report.md"

PAGES = [
    "/",
    "/catalog",
    "/catalog?difficulty=medium",
    "/catalog?difficulty=hard",
    "/catalog?difficulty=expert",
    "/catalog?q=проливка",
    "/catalog?q=тонировка",
    "/paints/",
    "/paints/1",
    "/guides/t-34-85",
    "/guides/t-34-85?level=medium",
    "/guides/t-34-85?level=hard",
    "/guides/t-34-85?level=expert",
    "/guides/type-97-chi-ha",
    "/guides/m14-41",
]


def check_covers() -> dict:
    """Обложки: манифест, файлы и соответствие гайдам."""
    covers = json.loads(COVERS_FILE.read_text(encoding="utf-8"))
    files = {
        path.stem: path
        for path in (PACKAGE / "static" / "img" / "vehicles").glob("*")
        if path.suffix in (".jpg", ".png")
    }

    guide_slugs = {guide["slug"] for guide in ALL_GUIDES}
    covered = {slug for slug in guide_slugs if slug in covers}
    without = sorted(guide_slugs - covered)
    orphan_files = sorted(set(files) - set(covers))
    missing_files = sorted(
        slug for slug, entry in covers.items()
        if not (PACKAGE / entry["file"]).exists()
    )
    broken = sorted(slug for slug in covers if slug not in guide_slugs)

    return {
        "covers": covers,
        "total_guides": len(guide_slugs),
        "covered": len(covered),
        "without": without,
        "orphan_files": orphan_files,
        "missing_files": missing_files,
        "broken": broken,
    }


def check_database() -> dict:
    """База: количество записей и согласованность с манифестом."""
    app = create_app()
    with app.app_context():
        guides = db.session.scalar(db.select(db.func.count(Guide.id)))
        variants = db.session.scalar(db.select(db.func.count(GuideVariant.id)))
        steps = db.session.scalar(db.select(db.func.count(GuideStep.id)))
        links = db.session.scalar(db.select(db.func.count(StepPaint.id)))
        paints = db.session.scalar(db.select(db.func.count(Paint.id)))
        with_hex = db.session.scalar(
            db.select(db.func.count(Paint.id)).where(
                Paint.color_hex.notin_(("", "#77786d"))
            )
        )
        with_description = db.session.scalar(
            db.select(db.func.count(Paint.id)).where(Paint.description != "")
        )
        covered = db.session.scalar(
            db.select(db.func.count(Guide.id)).where(Guide.cover_url != "")
        )

        # Сколько гайдов имеют все четыре уровня сложности.
        levels: dict[tuple[str, ...], int] = {}
        for guide in db.session.scalars(db.select(Guide)).all():
            key = tuple(sorted(v.difficulty.slug for v in guide.variants if v.difficulty))
            levels[key] = levels.get(key, 0) + 1

        # Насколько часто встречаются техники в шагах.
        techniques: dict[str, int] = {}
        for title, count in db.session.execute(
            db.select(GuideStep.title, db.func.count()).group_by(GuideStep.title)
        ):
            techniques[title] = count

        return {
            "guides": guides,
            "variants": variants,
            "steps": steps,
            "links": links,
            "paints": paints,
            "paints_with_hex": with_hex,
            "paints_with_description": with_description,
            "guides_with_cover": covered,
            "levels": levels,
            "techniques": techniques,
        }


def check_pages() -> list[dict]:
    """Скорость ответа основных страниц."""
    app = create_app()
    client = app.test_client()
    results = []
    for path in PAGES:
        start = time.perf_counter()
        response = client.get(path)
        elapsed = (time.perf_counter() - start) * 1000
        results.append(
            {"path": path, "status": response.status_code, "ms": round(elapsed, 1)}
        )
    return results


def check_links(app) -> list[dict]:
    """Внутренние ссылки: битых быть не должно."""
    client = app.test_client()
    problems = []
    pages = ["/", "/catalog", "/paints/", "/guides/t-34-85", "/guides/m14-41"]
    seen = set()
    for page in pages:
        response = client.get(page)
        html = response.get_data(as_text=True)
        import re

        for href in re.findall(r'href="([^"#]+)"', html):
            if not href.startswith("/") or href in seen:
                continue
            if href.startswith("/static"):
                continue
            seen.add(href)
            check = client.get(href)
            if check.status_code >= 400:
                problems.append({"from": page, "to": href, "status": check.status_code})
    return problems


def main() -> int:
    app = create_app()
    covers = check_covers()
    database = check_database()
    pages = check_pages()
    links = check_links(app)

    lines: list[str] = []
    lines.append("# Проверка PaintGuide\n")
    lines.append(f"Сгенерировано: {time.strftime('%Y-%m-%d %H:%M')}\n")

    lines.append("## Обложки\n")
    lines.append(f"- Гайдов всего: {covers['total_guides']}")
    lines.append(f"- С обложкой: {covers['covered']}")
    lines.append(f"- Без обложки: {len(covers['without'])}")
    lines.append(f"- Файлов без записи: {len(covers['orphan_files'])}")
    lines.append(f"- Записей без файла: {len(covers['missing_files'])}")
    lines.append(f"- Записей без гайда: {len(covers['broken'])}")
    if covers["without"]:
        lines.append("")
        lines.append("Без обложки: " + ", ".join(covers["without"]))
    lines.append("")

    lines.append("## База\n")
    for key in (
        "guides", "variants", "steps", "links", "paints",
        "paints_with_hex", "paints_with_description", "guides_with_cover",
    ):
        lines.append(f"- {key}: {database[key]}")
    lines.append("")
    lines.append("### Уровни сложности\n")
    for key, count in sorted(database["levels"].items(), key=lambda x: -x[1]):
        lines.append(f"- {key}: {count}")
    lines.append("")
    lines.append("### Техники в шагах\n")
    for title, count in sorted(database["techniques"].items(), key=lambda x: -x[1]):
        lines.append(f"- {title}: {count}")
    lines.append("")

    lines.append("## Скорость\n")
    lines.append("| Страница | Код | мс |")
    lines.append("| --- | --- | --- |")
    for item in pages:
        lines.append(f"| {item['path']} | {item['status']} | {item['ms']} |")
    lines.append("")

    lines.append("## Ссылки\n")
    lines.append(f"- Проверено внутренних ссылок: см. скрипт")
    lines.append(f"- Битых: {len(links)}")
    for problem in links[:20]:
        lines.append(f"  - {problem['from']} → {problem['to']} ({problem['status']})")
    lines.append("")

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nОтчёт: {REPORT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
