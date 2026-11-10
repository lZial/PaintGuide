"""Обновить тексты шагов в существующей базе.

Тексты шагов рождаются при загрузке данных из исходников и хранятся
в базе. После правки лестницы техник (`seed/techniques.py`) их нужно
переписать — иначе на сайте останутся старые формулировки.

Скрипт не трогает сами гайды и уровни: их номера остаются прежними,
поэтому избранное и вишлист продолжают указывать на нужные машины.
Пересоздаются только шаги вместе с привязками красок.

Все тексты считаются заранее, до обращения к базе: так соединение
с Neon не простаивает, пока идёт сборка шагов. Каждый гайд пишется
одной короткой транзакцией, при обрыве связи — повтор.

Запуск:

    python scripts/refresh_guide_texts.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, insert, select  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

from paintguide import create_app  # noqa: E402
from paintguide.extensions import db  # noqa: E402
from paintguide.models import (  # noqa: E402
    Guide,
    GuideStep,
    Paint,
    StepPaint,
)
from paintguide.seed import ALL_GUIDES  # noqa: E402
from paintguide.seed.levels import enrich_variants  # noqa: E402
from paintguide.seed.restructure import restructure  # noqa: E402


def build_payload() -> dict[str, dict[str, list[dict]]]:
    """Собрать новые шаги всех гайдов — без обращения к базе."""
    payload: dict[str, dict[str, list[dict]]] = {}
    for guide in ALL_GUIDES:
        levels: dict[str, list[dict]] = {}
        for variant in enrich_variants(guide):
            slug = variant.get("difficulty", "")
            if not slug:
                continue
            levels[slug] = restructure(variant)
        payload[guide["slug"]] = levels
    return payload


def paint_index() -> tuple[dict[tuple[str, str], int], dict[str, int]]:
    """Индекс красок: <код + название> и <код> → id."""
    by_code_name: dict[tuple[str, str], int] = {}
    by_code: dict[str, int] = {}
    for paint in db.session.scalars(select(Paint)):
        by_code_name.setdefault((paint.code, paint.name), paint.id)
        by_code.setdefault(paint.code, paint.id)
    return by_code_name, by_code


def main() -> int:
    payload = build_payload()
    print(f"Собрано гайдов: {len(payload)}", flush=True)

    app = create_app()
    updated = 0
    failed: list[str] = []

    with app.app_context():
        by_code_name, by_code = paint_index()

        for index, guide in enumerate(db.session.scalars(select(Guide)).all(), 1):
            levels = payload.get(guide.slug)
            if not levels:
                continue

            for attempt in range(4):
                try:
                    _refresh_guide(guide, levels, by_code_name, by_code)
                    db.session.commit()
                    updated += 1
                    break
                except OperationalError:
                    db.session.rollback()
                    db.engine.dispose()
                    if attempt == 3:
                        failed.append(guide.slug)
                        break
                    time.sleep(2)

            if index % 25 == 0:
                print(f"  ... {index} гайдов", flush=True)

    print(f"Обновлено гайдов: {updated}", flush=True)
    if failed:
        print(f"Не удалось обновить: {', '.join(failed)}", flush=True)
    return 1 if failed else 0


def _refresh_guide(
    guide: Guide,
    levels: dict[str, list[dict]],
    by_code_name: dict[tuple[str, str], int],
    by_code: dict[str, int],
) -> None:
    """Пересоздать шаги всех уровней одного гайда.

    Пишем пачками: удалить старые шаги одним запросом, вставить новые
    одним запросом, затем одним запросом привязать краски. Иначе на
    удалённой базе уходит по запросу на каждую строку.
    """
    variants = [v for v in guide.variants if levels.get(v.difficulty.slug) is not None]
    if not variants:
        return

    variant_ids = [variant.id for variant in variants]

    # Старые шаги вместе с привязками красок (каскад на уровне базы).
    db.session.execute(delete(GuideStep).where(GuideStep.variant_id.in_(variant_ids)))

    rows: list[dict] = []
    plan: list[tuple[int, int, dict]] = []
    for variant in variants:
        for position, step in enumerate(levels[variant.difficulty.slug], 1):
            rows.append(
                {
                    "variant_id": variant.id,
                    "position": position,
                    "title": step.get("title", ""),
                    "instruction": step.get("instruction", ""),
                    "tip": "",
                    "note": "",
                    "title_en": step.get("title_en", ""),
                    "instruction_en": step.get("instruction_en", ""),
                    "tip_en": "",
                }
            )
            plan.append((variant.id, position, step))
    if not rows:
        return

    db.session.execute(insert(GuideStep), rows)

    stored = db.session.execute(
        select(GuideStep.id, GuideStep.variant_id, GuideStep.position).where(
            GuideStep.variant_id.in_(variant_ids)
        )
    ).all()
    step_ids = {
        (variant_id, position): step_id
        for step_id, variant_id, position in stored
    }

    links: list[dict] = []
    for variant_id, position, step in plan:
        step_id = step_ids.get((variant_id, position))
        if step_id is None:
            continue
        for paint_position, item in enumerate(step.get("paints", [])):
            code, name, area, note = item
            paint_id = by_code_name.get((code, name)) or by_code.get(code)
            if paint_id is None:
                continue
            links.append(
                {
                    "step_id": step_id,
                    "paint_id": paint_id,
                    "area": area,
                    "note": note,
                    "position": paint_position,
                }
            )
    if links:
        db.session.execute(insert(StepPaint), links)

    # Коллекции шагов в сессии устарели — пусть перечитаются при надобности.
    for variant in variants:
        db.session.expire(variant, ["steps"])


if __name__ == "__main__":
    raise SystemExit(main())
