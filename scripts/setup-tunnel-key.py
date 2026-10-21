"""Подготовка постоянного адреса для туннеля.

localhost.run и serveo.net выдают случайный поддомен на каждое соединение.
Если зарегистрировать SSH-ключ у провайдера туннеля, можно зарезервировать
имя — тогда адрес перестаёт меняться при переподключении.

Скрипт создаёт ключевую пару и печатает публичный ключ, который нужно
один раз добавить в личном кабинете провайдера.

Запуск:

    python scripts/setup-tunnel-key.py          # создать ключ и показать инструкцию
    python scripts/setup-tunnel-key.py --done   # ключ добавлен — включить постоянный адрес
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY_DIR = ROOT / ".tunnel"
KEY = KEY_DIR / "id_ed25519"
FLAG = KEY_DIR / "registered"

STEPS = """
  Что сделать один раз
  ──────────────────────────────────────────────────────────────
  1. Откройте https://console.serveo.net/settings
     (или https://admin.localhost.run/ — для варианта localhost.run)
  2. Зарегистрируйтесь и добавьте публичный ключ ниже
     (раздел SSH keys / Public keys).
  3. Зарезервируйте имя поддомена — например paintguide
     (раздел Add a domain → Serveo subdomain).
  4. Сообщите скрипту, что ключ добавлен:
        python scripts/setup-tunnel-key.py --done
  5. Перезапустите туннель — адрес станет постоянным:
        https://paintguide.serveo.net

  Ключ лежит в файле:
    {key}
  Публичный ключ:
{public}
"""


def main() -> int:
    if "--done" in sys.argv:
        FLAG.write_text("ok\n", encoding="utf-8")
        print("Готово: туннель будет использовать постоянный адрес.")
        print("Перезапустите туннель: python scripts/tunnel.py")
        return 0

    KEY_DIR.mkdir(exist_ok=True)
    if KEY.exists():
        print("Ключ уже создан:", KEY)
    else:
        result = subprocess.run(
            [
                "ssh-keygen",
                "-t",
                "ed25519",
                "-f",
                str(KEY),
                "-N",
                "",
                "-C",
                "paintguide",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("! не удалось создать ключ:", result.stderr.strip(), file=sys.stderr)
            return 1
        print("Ключ создан:", KEY)

    public = (KEY.with_suffix(".pub")).read_text(encoding="utf-8").strip()
    print(STEPS.format(key=KEY, public=public))
    print("  Приватный ключ никому не передавайте.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
