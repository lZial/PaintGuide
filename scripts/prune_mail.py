"""Уборка старых писем.

Когда почтовый сервер не настроен, письма складываются в папку
instance/mail. Их становится много, поэтому старые файлы убираются:
остаются последние, иначе их не найти.

Запуск:  python scripts/prune_mail.py [сколько оставить]
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIL_DIR = ROOT / "instance" / "mail"
KEEP = 50


def prune(keep: int = KEEP) -> int:
    """Удалить лишние письма, оставив последние."""
    if not MAIL_DIR.exists():
        return 0
    files = sorted(MAIL_DIR.glob("*.txt"), key=lambda path: path.stat().st_mtime)
    removed = 0
    for path in files[:-keep] if len(files) > keep else []:
        try:
            path.unlink()
            removed += 1
        except OSError:
            pass
    return removed


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else KEEP
    removed = prune(count)
    left = len(list(MAIL_DIR.glob("*.txt"))) if MAIL_DIR.exists() else 0
    print(f"удалено писем: {removed}; осталось: {left}")
