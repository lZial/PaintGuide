"""Замена устаревших кодов AK Real Colors на актуальные.

Ручной список красок содержал коды AKRC001…AKRC037 — таких обозначений у
производителя нет: настоящие коды линейки Real Colors выглядят как RCM001…
Скрипт сопоставляет каждую ручную запись с реальным цветом по названию и
переписывает код в paintguide/seed/paints.py.

Запуск:  python scripts/fix_akrc_aliases.py --dry   (только показать)
         python scripts/fix_akrc_aliases.py          (исправить)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTENDED = ROOT / "paintguide" / "seed" / "paints_extended.json"
PAINTS = ROOT / "paintguide" / "seed" / "paints.py"

# Реальные коды линейки AK Real Colors (RCM) вместо выдуманных AKRC.
# Соответствие подобрано по официальным названиям цветов.
WANTED = {
    "Grey Primer": "RCM016",
    "Black Primer": "RCM001",
    "White Primer": "RCM002",
    "Red Oxide Primer": "RCM019",
    "German Grey": "RCM024",
    "Dark Yellow": "RCM018",
    "US Army Olive Drab": "RCM021",
    "Soviet Green": "RCM022",
    "Khaki Green": "RCM023",
    "Japanese Grey": "RCM028",
    "Pale Sand": "RCM008",
    "Sand Grey": "RCM017",
    "Grey Green": "RCM028",
    "Medium Grey": "RCM017",
    "Dark Brown": "RCM020",
}


def main() -> int:
    dry = "--dry" in sys.argv
    if not EXTENDED.exists():
        print("Нет paints_extended.json — сначала выполните fetch_paints.py")
        return 1

    items = json.loads(EXTENDED.read_text(encoding="utf-8"))
    real = [i for i in items if i["brand"] == "ak" and i["code"].startswith("RCM")]
    if not real:
        print("В каталоге нет цветов RCM — дождитесь загрузки красок")
        return 1

    text = PAINTS.read_text(encoding="utf-8")
    changed = 0
    by_code = {item["code"]: item for item in real}
    for label, code in WANTED.items():
        pattern = re.compile(
            r'\("ak", "rc", "AKRC\d{3}", "' + re.escape(label) + r'"\s*,\s*"#[0-9a-fA-F]{6}"',
            re.IGNORECASE,
        )
        if not pattern.search(text):
            continue
        best = by_code.get(code)
        if best is None:
            print(f"  ? {label}: кода {code} нет в каталоге")
            continue
        print(f"  {label:20s} AKRC… → {best['code']} {best['name'][:40]}")
        if not dry:
            replacement = (
                f'("ak", "rc", "{best["code"]}", "{best["name"]}", '
                f'"{best.get("hex") or "#77786d"}"'
            )
            text = pattern.sub(replacement, text, count=1)
            changed += 1

    if not dry and changed:
        PAINTS.write_text(text, encoding="utf-8")
        print(f"\nИсправлено записей: {changed}")
    else:
        print("\nРежим просмотра — файлы не менялись.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
