"""Запуск фоновых заданий без лишних окон.

Скрипты обложек работают долго и запускаются в фоне. Раньше они
открывали окно консоли, а при остановке окно закрывалось с хлопком —
это выглядело как «программы сами закрываются».

Здесь окно не создаётся вовсе (скрытый процесс), а номер процесса
записывается в файл: остановить можно только именно его, не зацепив
чужие процессы.

Запуск:   python scripts/background.py start <команда...>
Остановка: python scripts/background.py stop
Список:   python scripts/background.py list
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "instance" / "background-jobs.json"
LOG_DIR = ROOT / "instance" / "logs"

# Процессы, которые нельзя трогать ни при каких условиях: это сервер
# самого приложения.
PROTECTED = ("run.py", "opencode", "OpenCode", "dlgdiag2", "reshoot_fixed")


def _load() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(data: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _label_for(command: list[str]) -> str:
    """Понятное имя задания: по имени скрипта, а не по интерпретатору."""
    for part in command[1:]:
        if part.endswith(".py"):
            return Path(part).stem
    return Path(command[0]).stem


def start(command: list[str], name: str = "") -> int:
    """Запустить задание в фоне: без окна, с журналом и номером процесса."""
    if not command:
        print("Не указана команда.", flush=True)
        return 2

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    label = name or _label_for(command)
    log_path = LOG_DIR / f"{label}.log"
    handle = log_path.open("w", encoding="utf-8")

    # CREATE_NO_WINDOW: процесс идёт без окна консоли.
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        command,
        cwd=str(ROOT),
        stdout=handle,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        creationflags=creation_flags,
    )
    handle.close()

    data = _load()
    data[label] = {"pid": process.pid, "log": str(log_path), "command": command}
    _save(data)
    print(f"Запущено: {label} (pid {process.pid}), журнал: {log_path}", flush=True)
    return 0


def _processes_for(command: list[str]) -> list[int]:
    """Найти номера процессов по командной строке.

    В Windows виртуальное окружение запускает интерпретатор через
    обёртку: она завершается сразу, а работает потомок. Поэтому
    номер процесса ищем по командной строке, а не по записанному PID.
    """
    if os.name != "nt":
        return []
    needle = " ".join(command).replace('"', "")
    script = (
        "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "
        f"'*{needle}*' }} | ForEach-Object {{ $_.ProcessId }}"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    pids = []
    for line in result.stdout.split():
        if line.isdigit():
            pids.append(int(line))
    return pids


def _is_protected(command: list[str]) -> bool:
    """Задание защищено, если его запускает защищённый процесс.

    Сравниваются только имена скриптов и сам интерпретатор: полный
    путь с аргументами совпадает с чужими словами (например, папка
    «opencode» в пути к плану).
    """
    parts = [Path(part).name for part in command if part]
    return any(part in PROTECTED for part in parts)


def _kill_tree(pid: int) -> bool:
    """Завершить процесс вместе с потомками.

    В Windows виртуальное окружение запускает интерпретатор через
    обёртку: убив только её, настоящий python продолжает работать.
    Поэтому дерево гасится целиком.
    """
    if os.name != "nt":
        try:
            os.kill(pid, 15)
            return True
        except OSError:
            return False
    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return True
    except (OSError, subprocess.SubprocessError):
        try:
            os.kill(pid, 15)
            return True
        except OSError:
            return False


def stop(name: str = "", force: bool = False) -> int:
    """Остановить задание по имени (или все, кроме защищённых).

    `force` снимает защиту: так работает перезапуск сервера — он идёт
    по прямому запросу пользователя.
    """
    data = _load()
    if not data:
        print("Фоновых заданий нет.", flush=True)
        return 0

    targets = [name] if name else list(data)
    stopped = 0
    for label in targets:
        job = data.get(label)
        if not job:
            print(f"  {label}: не найдено", flush=True)
            continue
        pid = int(job.get("pid", 0))
        if not force and _is_protected(job.get("command", [])):
            print(f"  {label}: пропущено (защищённый процесс)", flush=True)
            continue
        pids = _processes_for(job.get("command", [])) or [pid]
        for target in pids:
            _kill_tree(target)
        if pids:
            stopped += 1
            print(f"  {label}: остановлен (pid {', '.join(str(p) for p in pids)})", flush=True)
        else:
            print(f"  {label}: уже не работает", flush=True)
        data.pop(label, None)
    _save(data)
    return 0


def listing() -> int:
    data = _load()
    if not data:
        print("Фоновых заданий нет.", flush=True)
        return 0
    for label, job in data.items():
        pids = _processes_for(job.get("command", []))
        state = "работает" if pids else "завершилось"
        numbers = ", ".join(str(pid) for pid in pids) or str(job.get("pid", ""))
        print(f"  {label}: pid {numbers} — {state}; журнал {job.get('log')}")
    return 0


def restart(name: str = "run") -> int:
    """Перезапустить задание: остановить и запустить заново.

    Сервер приложения запущен без автоперезагрузки (чтобы правка файла
    не дёргала работающий сайт), поэтому после изменений его нужно
    перезапустить — это и делает эта команда.
    """
    data = _load()
    job = data.get(name)
    if not job:
        print(f"Задание «{name}» не найдено.", flush=True)
        return 1
    command = job.get("command", [])
    stop(name, force=True)
    time.sleep(2)
    return start(command, name=name)


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "list"
    if action == "start":
        return start(sys.argv[2:])
    if action == "stop":
        return stop(sys.argv[2] if len(sys.argv) > 2 else "")
    if action == "restart":
        return restart(sys.argv[2] if len(sys.argv) > 2 else "run")
    if action == "list":
        return listing()
    print("Действия: start, stop, restart, list", flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
