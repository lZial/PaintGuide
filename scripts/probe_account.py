"""Живая проверка системы аккаунтов на работающем сервере.

Регистрация → письмо → подтверждение → вход → профиль → смена адреса
→ подтверждение адреса → удаление аккаунта.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

BASE = "http://127.0.0.1:5000"
MAIL_DIR = Path(r"D:\PaintGuide\instance\mail")
EMAIL = "живой-тест@paintguide.local"
PASSWORD = "оченьхорошийпароль"


class Session:
    """Клиент с cookie-jar и CSRF-токеном."""

    def __init__(self):
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )
        self.token = ""

    def get(self, path: str) -> str:
        request = urllib.request.Request(BASE + path, headers={"User-Agent": "probe"})
        with self.opener.open(request, timeout=45) as response:
            body = response.read().decode("utf-8", "replace")
        match = re.search(r'name="csrf_token" value="([^"]+)"', body)
        if match:
            self.token = match.group(1)
        return body

    def post(self, path: str, data: dict) -> str:
        payload = dict(data)
        payload["csrf_token"] = self.token
        request = urllib.request.Request(
            BASE + path,
            data=urllib.parse.urlencode(payload).encode("utf-8"),
            headers={"User-Agent": "probe"},
        )
        with self.opener.open(request, timeout=45) as response:
            body = response.read().decode("utf-8", "replace")
        match = re.search(r'name="csrf_token" value="([^"]+)"', body)
        if match:
            self.token = match.group(1)
        return body


def latest_link(kind: str) -> str:
    """Ссылка из самого свежего письма нужного типа."""
    links: list[str] = []
    for path in sorted(MAIL_DIR.glob("*.txt")):
        body = path.read_text(encoding="utf-8")
        links += re.findall(rf"https?://[^\s<>]+/{kind}/[^\s<>]+", body)
    return links[-1] if links else ""


def step(title: str, ok: bool, extra: str = "") -> None:
    mark = "OK  " if ok else "!!  "
    print(f"  {mark}{title}{(' — ' + extra) if extra else ''}")


def main() -> int:
    for item in MAIL_DIR.glob("*.txt"):
        if EMAIL.replace("@", "_") in item.name:
            item.unlink()

    session = Session()
    print("1. Регистрация")
    session.get("/register")
    body = session.post(
        "/register",
        {
            "nickname": "Живой тест",
            "email": EMAIL,
            "password": PASSWORD,
            "password_confirm": PASSWORD,
            "terms": "on",
        },
    )
    step("аккаунт создан", "Проверьте почту" in body)
    step("письмо отправлено", bool(latest_link("verify")), latest_link("verify")[-40:])

    print("2. Вход до подтверждения")
    session.get("/login")
    body = session.post("/login", {"email": EMAIL, "password": PASSWORD})
    step("вход закрыт", "не подтверждена" in body)

    print("3. Подтверждение адреса")
    link = latest_link("verify")
    token = link.rsplit("/", 1)[-1]
    body = session.get(f"/verify/{token}")
    step("адрес подтверждён", "Адрес подтверждён" in body)

    print("4. Вход после подтверждения")
    session.get("/login")
    body = session.post("/login", {"email": EMAIL, "password": PASSWORD})
    step("вход выполнен", "С возвращением" in body)

    print("5. Профиль")
    body = session.get("/profile")
    step("профиль открыт", "Живой тест" in body)
    step("статус подтверждения", "Адрес подтверждён" in body)

    print("6. Смена адреса")
    session.get("/profile")
    body = session.post("/profile", {"action": "email", "email": "живой-тест-2@paintguide.local"})
    confirm = latest_link("confirm-email")
    step("письмо с подтверждением", bool(confirm))
    if confirm:
        body = session.get(f"/confirm-email/{confirm.rsplit('/', 1)[-1]}")
        step("новый адрес подтверждён", "Новый адрес подтверждён" in body)

    print("7. Восстановление пароля")
    anonymous = Session()
    anonymous.get("/forgot-password")
    body = anonymous.post("/forgot-password", {"email": "живой-тест-2@paintguide.local"})
    step("запрос принят", "отправили ссылку" in body.lower())
    reset = latest_link("reset-password")
    step("письмо со сбросом", bool(reset))
    if reset:
        anonymous.get(f"/reset-password/{reset.rsplit('/', 1)[-1]}")
        body = anonymous.post(
            f"/reset-password/{reset.rsplit('/', 1)[-1]}",
            {"password": "совсемновыйпароль", "password_confirm": "совсемновыйпароль"},
        )
        step("пароль изменён", "Пароль обновлён" in body)

    print("8. Удаление аккаунта")
    session.get("/profile")
    body = session.post("/profile/delete", {"password": "совсемновыйпароль"})
    step("аккаунт удалён", "Аккаунт удалён" in body)

    print("9. Служебные страницы")
    for path in ("/verify/неверный-токен", "/reset-password/неверный-токен"):
        quoted = urllib.parse.quote(path, safe="/")
        body = Session().get(quoted)
        step(f"{path} — понятная ошибка", "недействительна" in body)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
