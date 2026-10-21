"""Сопоставление красок из гайдов с реальным каталогом.

Ручной список красок описывает их привычными модельными именами
(«Red Oxide», «Field Green»), а производители называют те же краски иначе
(«Primer Red», «FIELD GREEN FS 34097»). Номера у AK Interactive менялись,
поэтому искать по коду ненадёжно: AK11008 в каталоге — это «Grimy Grey»,
хотя в гайдах им помечен красно-оксидный грунт.

Здесь подбор идёт по итоговому каталогу (выкачанные данные плюс ручной
список). Если краска есть в каталоге под своим кодом и названием — она
остаётся как есть. Если номер занят другой краской, подыскивается
настоящая: сперва по явным правилам, затем по смыслу названия.

Результат — таблица соответствий paintguide/seed/paint_map.json.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from paintguide.seed.catalog import build_catalog  # noqa: E402
from paintguide.seed.paint_overrides import OVERRIDES  # noqa: E402
from paintguide.seed.paints import EQUIVALENTS, PAINTS  # noqa: E402

MAP_FILE = ROOT / "paintguide" / "seed" / "paint_map.json"

# Слова, которые не несут смысла при сравнении названий.
STOP_WORDS = {
    "paint", "color", "colour", "acrylic", "enamel", "matt", "matte", "gloss",
    "satin", "standard", "intense", "series", "real", "the", "and", "for",
    "model", "toy", "hobby", "mr", "tamiya", "vallejo", "humbrol", "ak", "lifecolor",
    "gen", "generation", "3rd", "no", "n", "fs", "ral", "rlm", "mil", "ml",
}


def tokens(text: str) -> set[str]:
    words = re.split(r"[^a-z0-9а-яё]+", (text or "").lower())
    return {word for word in words if len(word) > 2 and word not in STOP_WORDS}


def similarity(left: str, right: str) -> float:
    """Сходство по значимым словам.

    Важно: значимые слова ручного названия не должны теряться в
    каталоговом. Иначе «Soviet Green» нашёлся бы в «Lime Green» — по
    одному общему слову «green». Поэтому, если в ручном названии есть
    слово, которого нет в каталоговом, совпадение засчитывается лишь
    частично.
    """
    a, b = tokens(left), tokens(right)
    if not a or not b:
        return 0.0
    if a <= b or b <= a:
        score = len(a & b) / len(a | b)
    else:
        common = a & b
        if not common:
            return 0.0
        score = 0.5 * len(common) / len(a | b)
    first_a = (left or "").lower().split(" ")[0]
    first_b = (right or "").lower().split(" ")[0]
    if first_a and first_a == first_b:
        score += 0.25
    return score


def main() -> int:
    catalog = build_catalog()

    by_brand: dict[str, list[dict]] = {}
    for item in catalog:
        by_brand.setdefault(item["brand"], []).append(item)

    # Коды и названия, которые в каталоге уже есть под своим именем.
    exact_keys = {
        (item["brand"], item["code"], item["name"])
        for item in catalog
    }

    mapping: dict[str, dict] = {}
    unresolved: list[str] = []
    conflicts: list[str] = []

    for brand, _line, code, name, _hex, _type, _description in PAINTS:
        key = f"{code}|{name}"

        # Краска есть в каталоге под своим кодом и названием — всё в порядке.
        if (brand, code, name) in exact_keys:
            mapping[key] = {"code": code, "name": name, "score": 1.0}
            continue

        # Явные правила: у части линеек номера перенумерованы, и по названию
        # найти нужную краску невозможно.
        forced = OVERRIDES.get(key)
        if forced:
            forced_code, forced_name = forced.split("|", 1)
            mapping[key] = {
                "code": forced_code,
                "name": forced_name,
                "score": 1.0,
            }
            continue

        conflicts.append(key)

        # Иначе ищем настоящую краску по смыслу названия, в пределах бренда.
        pool = by_brand.get(brand, [])
        best = None
        best_score = 0.0
        for item in pool:
            score = similarity(name, item["name"])
            if score > best_score:
                best_score = score
                best = item
        if best is not None and best_score >= 0.34:
            mapping[key] = {
                "code": best["code"],
                "name": best["name"],
                "score": round(best_score, 2),
            }
        else:
            unresolved.append(key)

    # Соответствия между брендами — резолвим обе стороны.
    resolved_equivalents: list[list[str]] = []
    for code_a, name_a, code_b, name_b in EQUIVALENTS:
        first = mapping.get(f"{code_a}|{name_a}")
        second = mapping.get(f"{code_b}|{name_b}")
        if first and second:
            resolved_equivalents.append(
                [first["code"], first["name"], second["code"], second["name"]]
            )

    MAP_FILE.write_text(
        json.dumps(
            {"paints": mapping, "equivalents": resolved_equivalents},
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"Сопоставлено: {len(mapping)} из {len(PAINTS)}")
    print(f"Номер занят другой краской: {len(conflicts)}")
    print(f"Не найдено: {len(unresolved)}")
    for key in unresolved[:20]:
        print("   ?", key)
    print(f"Соответствий между брендами сохранено: {len(resolved_equivalents)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
