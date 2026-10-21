"""Публикация PaintGuide в интернете по временной ссылке.

Поднимает SSH-туннель: приложение остаётся на этом компьютере, а по ссылке
https://<домен> к нему открывается доступ с телефона, планшета или из-за
пределов вуза.

Запуск:

    python scripts/tunnel.py                  # против http://127.0.0.1:5000
    python scripts/tunnel.py --port 8000      # другой порт
    python scripts/tunnel.py --provider local # только localhost.run
    python scripts/tunnel.py --once           # не переподключаться при обрыве

Что происходит:
  * туннель поднимается через serveo.net (или localhost.run);
  * текущая ссылка печатается в консоль и пишется в файл tunnel-url.txt;
  * при обрыве соединения скрипт переподключается сам — ссылка может смениться.

Чтобы адрес не менялся, зарегистрируйте SSH-ключ (одноразовая настройка,
нужна бесплатная учётная запись у провайдера туннеля) — см. README.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY_DIR = ROOT / ".tunnel"
URL_FILE = ROOT / "tunnel-url.txt"

# Провайдеры туннелей: имя → (хост, шаблон удалённой переадресации, регулярка адреса)
PROVIDERS = {
    "serveo": ("serveo.net", "80:{host}:{port}", r"https://[^\s]*serveousercontent\.com[^\s]*"),
    "local": ("localhost.run", "80:{host}:{port}", r"https://[a-z0-9\-]+\.lhr\.life"),
}

BANNER = """
  PaintGuide — публичный адрес
  ───────────────────────────────────────────────
  Приложение должно работать на {port}.
  Ссылка печатается ниже и пишется в tunnel-url.txt.
  Соединение может оборваться — скрипт переподключится сам.
  Остановить: Ctrl+C
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Публичный туннель для PaintGuide")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--provider", choices=("serveo", "local"), default="serveo")
    parser.add_argument("--once", action="store_true", help="не переподключаться при обрыве")
    args = parser.parse_args()

    print(BANNER.format(port=args.port), flush=True)
    attempt = 0
    while True:
        attempt += 1
        print(f"  Подключение #{attempt}…", flush=True)
        code = _run_tunnel(args)
        if args.once:
            return code
        print(
            f"  Соединение закрыто (код {code}). Переподключаюсь через 4 с…", flush=True
        )
        time.sleep(4)


def _run_tunnel(args) -> int:
    host, forward_template, url_pattern = PROVIDERS[args.provider]
    command = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ServerAliveInterval=20",
        "-o", "ServerAliveCountMax=6",
        "-o", "TCPKeepAlive=yes",
        "-o", "ExitOnForwardFailure=yes",
    ]
    key = KEY_DIR / "id_ed25519"
    # Ключ используем только после того, как он зарегистрирован в аккаунте:
    # иначе провайдер не признает зарезервированное имя.
    if key.exists() and (KEY_DIR / "registered").exists():
        # С зарегистрированным ключом провайдер выдаёт постоянный поддомен.
        # Имя резервируется за аккаунтом, а ключ его подтверждает.
        command += [
            "-i",
            str(key),
            "-R",
            f"paintguide:{forward_template.format(host=args.host, port=args.port)}",
        ]
        target = f"plan@{host}" if args.provider == "local" else host
    else:
        command += ["-R", forward_template.format(host=args.host, port=args.port)]
        target = f"nokey@{host}"
    command.append(target)

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except FileNotFoundError:
        print("  ! ssh не найден. Проверьте: ssh -V", flush=True)
        return 1

    pattern = re.compile(url_pattern)
    try:
        for line in process.stdout:
            match = pattern.search(line)
            if match:
                url = match.group(0).rstrip(".,)")
                _announce(url)
    except KeyboardInterrupt:
        print("\n  Останавливаю туннель…", flush=True)
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    return process.returncode or 0


def _announce(url: str) -> None:
    try:
        URL_FILE.write_text(url + "\n", encoding="utf-8")
    except OSError:
        pass
    print("\n  ╔════════════════════════════════════════╗", flush=True)
    print(f"  ║  {url:<38} ║", flush=True)
    print("  ╚════════════════════════════════════════╝", flush=True)
    print("  Откройте ссылку на телефоне или другом компьютере.\n", flush=True)


if __name__ == "__main__":
    sys.exit(main())
