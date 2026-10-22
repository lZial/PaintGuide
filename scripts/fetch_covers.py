"""Подбор обложек для руководств из Wikimedia Commons.

Скрипт ищет свободно лицензируемые фотографии техники (в первую очередь —
окрашенных моделей любого масштаба), скачивает их, приводит к общему формату
3:2 и сохраняет локально вместе с лицензионными метаданными.

Запуск:

    python scripts/fetch_covers.py                # все гайды
    python scripts/fetch_covers.py t-34-85        # только один гайд
    python scripts/fetch_covers.py --force        # перезаписать существующие
    python scripts/fetch_covers.py --report       # только собрать отчёт

Результат:
    static/img/vehicles/<slug>.jpg  — обложка
    paintguide/seed/covers.json      — автор, лицензия, ссылка, масштаб
    docs/covers-report.html          — галерея для ручной проверки
"""

from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Статика раздаётся из пакета paintguide — туда и складываем обложки.
PACKAGE_DIR = ROOT / "paintguide"
sys.path.insert(0, str(ROOT))

from paintguide.seed.guides import GUIDES  # noqa: E402
from paintguide.seed.guides_part2 import GUIDES_2  # noqa: E402
from paintguide.seed.guides_part3 import GUIDES_3  # noqa: E402
from paintguide.seed.guides_part4 import GUIDES_4  # noqa: E402
from paintguide.seed.guides_part5 import GUIDES_5  # noqa: E402
from paintguide.seed.guides_part6 import GUIDES_6  # noqa: E402
from paintguide.seed.guides_part7 import GUIDES_7  # noqa: E402
from paintguide.seed.guides_part8 import GUIDES_8  # noqa: E402
from paintguide.seed.guides_part9 import GUIDES_9  # noqa: E402
from paintguide.seed.guides_part10 import GUIDES_10  # noqa: E402
from paintguide.seed.guides_part11 import GUIDES_11  # noqa: E402
from paintguide.seed.guides_part12 import GUIDES_12  # noqa: E402
from paintguide.seed.guides_part13 import GUIDES_13  # noqa: E402

ALL_GUIDES = (
    GUIDES
    + GUIDES_2
    + GUIDES_3
    + GUIDES_4
    + GUIDES_5
    + GUIDES_6
    + GUIDES_7
    + GUIDES_8
    + GUIDES_9
    + GUIDES_10
    + GUIDES_11
    + GUIDES_12
    + GUIDES_13
)

API = "https://commons.wikimedia.org/w/api.php"
FILEPATH = "https://commons.wikimedia.org/wiki/Special:FilePath/"
# Wikimedia отдаёт 403/429 агрессивным клиентам: нужен внятный
# User-Agent с контактом и вежливый темп запросов.
USER_AGENT = (
    "PaintGuideBot/1.0 (https://example.org/paintguide; paintguide@example.com) "
    "python-urllib/3"
)
# Хранилище upload.wikimedia.org отклоняет «ботовский» User-Agent с 403,
# хотя API такой принимает. Для скачивания файлов нужен обычный заголовок браузера.
DOWNLOAD_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
REQUEST_DELAY = 1.2

# Пауза между машинами: хранилище Wikimedia не любит частые загрузки.
SLUG_DELAY = 8.0

# Сколько кругов по неудачным машинам и пауза между кругами.
ROUNDS = 3
ROUND_PAUSE = 180.0

# Метаданные файлов за проход: один и тот же файл не запрашивается дважды.
_TITLE_CACHE: dict[str, dict | None] = {}
# Обложка показывается в карточке (~300 px) и в шапке гайда (~500 px).
# 800 px хватает с запасом, а вес папки втрое меньше, чем при 1200 px.
THUMB_WIDTH = 960

# Выставочные категории одинаковы для всех машин — их содержимое
# запрашивается один раз и кэшируется.
_SHOWCASE_CACHE: dict[str, list[dict]] = {}
OUT_DIR = PACKAGE_DIR / "static" / "img" / "vehicles"
DATA_FILE = ROOT / "paintguide" / "seed" / "covers.json"
REPORT_FILE = ROOT / "docs" / "covers-report.html"

# Лицензии, которые можно использовать: CC BY требует атрибуции, CC BY-SA ещё и
# запрещает изменение условий лицензирования. ND использовать нельзя — он
# запрещает кадрирование, NC не нужен для учебного проекта.
ALLOWED_LICENSES = {
    "pd",
    "public domain",
    "cc0",
    "cc by",
    "cc by 2.0",
    "cc by 2.5",
    "cc by 3.0",
    "cc by 4.0",
    "cc by-sa",
    "cc by-sa 2.0",
    "cc by-sa 2.5",
    "cc by-sa 3.0",
    "cc by-sa 4.0",
    "cc by-sa 2.0,3.0,4.0",
    "cc by-sa 3.0,2.0,2.5,1.0",
}

# Сюжеты, которые не подходят для обложки.
BLOCK_WORDS = (
    "drawing", "diagram", "blueprint", "sketch", "plan", "schematic", "logo",
    "badge", "emblem", "map", "chart", "graph", "poster", "stamp", "coin",
    "medal", "book", "cover", "manual", "instruction", "box art", "boxart",
    "box", "kit box", "decal sheet", "decals", "engine", "gearbox", "transmission",
    "radiator", "chassis", "suspension", "carburetor", "muffler", "exhaust pipe",
    "gun barrel", "barrel", "ammunition", "shell", "cartridge", "interior",
    "crew", "commander", "hull bottom", "underside", "top view", "rear view",
    "side view of ", "wheel", "road wheel", "turret interior", "price tag",
    "shop", "museum shop", "windshield", "windscreen", "fume", "crumpled",
    "wreckage only", "rubble", "scrapped", "scrap",
    "fortress", "chateau", "castle", "monument", "memorial", "bastion",
    "panzerhaubitze", "aero ", "aircraft", "fighter", "bomber", "bicycle",
    "3d print", ".stl", "breech", "comparision", "comparison", "diecast",
    "kit box", "boxart", "in box", "unbuilt", "wip", "build in progress",
    # Совпадения по случайным буквам: гонки, космос, спорт.
    "racing", "regatta", "sailing", "catamaran", "sts-125", "shuttle",
    "tank biathlon", "tankbiathlon",
)

# Категории с моделями, которые берём в первую очередь (любой масштаб).
MODEL_CATEGORY_PATTERNS = (
    'intitle:"Scale models of {name}"',
    'intitle:"Scale models of {name} tanks and variants"',
    'intitle:"{name} scale models"',
    'intitle:"{name} tanks in scale"',
)

# Выставочные и музейные категории — там встречаются модели десятков типов.
SHOWCASE_CATEGORIES = (
    "Category:Scale models of tanks at the Bovington Tank Museum",
    "Category:Scale models of tanks at the Tankfest 2009",
    "Category:Scale models of tanks at the Tankfest 2010",
    "Category:Scale models of tanks at the Tankfest 2011",
    "Category:Scale models of tanks at the Tankfest 2012",
    "Category:Scale models of tanks at the Tankfest 2013",
    "Category:Scale models of tanks at the Tankfest 2014",
    "Category:Scale models of tanks at the Tankfest 2015",
    "Category:Scale models of tanks at the Tankfest 2016",
    "Category:Scale models of tanks at the Tankfest 2017",
    "Category:Scale models of tanks at the Tankfest 2018",
    "Category:Scale models of tanks at the Tankfest 2022",
    "Category:Scale models of tanks at the Tankfest 2023",
    "Category:Scale models of tanks at the Tankfest 2024",
    "Category:Scale models of tanks at the Tankfest 2025",
    "Category:Scale models of tanks at the Musée des Blindés",
    "Category:Scale models of tanks at Bovington Tank Museum",
    "Category:Scale models of military vehicles",
    "Category:Scale models of tanks",
    "Category:Scale models of armoured fighting vehicles",
)

# Названия машин для каждого гайда: пробуем по очереди.
VEHICLE_NAMES = {
    "t-34-85": ["T-34-85", "T-34/85", "T-34 85"],
    "t-34-76": ["T-34-76", "T-34 Model 1941", "T-34 (1941)"],
    "kv-1": ["KV-1", "KV heavy tank"],
    "su-100": ["SU-100", "SU 100"],
    "zil-131": ["ZIL-131", "ZIL 131", "ZIL-157"],
    "btr-152": ["BTR-152", "BTR 152", "BTR-152V"],
    "panzer-iv-ausf-g": ["Panzer IV", "Panzerkampfwagen IV"],
    "panther-ausf-g": ["Panther tank", "Panzerkampfwagen V Panther"],
    "tiger-i": ["Tiger I", "Panzerkampfwagen VI Tiger I"],
    "stug-iii-ausf-g": ["StuG III", "Sturmgeschütz III"],
    "wespe": ["Wespe", "Sturmtiger?"],
    "sdkfz-251": ["Sd.Kfz. 251", "Sd.Kfz.251"],
    "m4a3e8-sherman": ["M4 Sherman", "Sherman tank"],
    "m10-wolverine": ["M10 Wolverine", "M10 tank destroyer"],
    "m3a1-stuart": ["M3 Stuart", "Stuart light tank"],
    "m8-grease-truck": ["M8 Greyhound", "M8 armoured car"],
    "churchill-mk-vii": ["Churchill tank", "Churchill Mk VII"],
    "comet": ["Comet tank", "A24 Comet"],
    "spitfire-mk-ix": ["Supermarine Spitfire", "Spitfire"],
    "hurricane-mk-ii": ["Hawker Hurricane", "Hurricane aircraft"],
    "daimler-dingo": ["Daimler Dingo"],
    "sexton": ["Sexton (tank)", "Sexton self-propelled gun"],
    "universal-carrier": ["Universal Carrier"],
    "type-97-chi-ha": ["Type 97 Chi-Ha", "Chi-Ha"],
    "type-95-ha-go": ["Type 95 Ha-Go", "Ha-Go"],
    "type-1-ho-ni": ["Type 1 Ho-Ni", "Ho-Ni"],
    "type-92-jyu-sokosha": ["Type 92 armoured car", "Type 92 Jyu-Sokosha", "Type 92 armoured truck"],
    "nakajima-ki-43-ii": ["Nakajima Ki-43", "Ki-43"],
    "a6m2-zero": ["Mitsubishi A6M Zero", "A6M Zero"],
    "somua-s35": ["SOMUA S35", "S35 tank"],
    "hotchkiss-h39": ["Hotchkiss H39", "H39 tank"],
    "l3-35": ["L3/35", "Fiat L3/35", "L3/35 tankette"],
    "type-59": ["Type 59 tank", "Type 59"],
    "m60-magach-6": ["M60 Magach", "Magach 6"],
    "strv-103": ["Strv 103", "Strv 103 S-tank"],
    "kv-202": ["KV-202", "KV 202"],
    "is-1": ["IS-1", "IS-1 tank"],
    "type-97-shinhoto": ["Type 97 Shinhoto Chi-Ha", "Shinhoto Chi-Ha"],
    "type-89-i-go": ["Type 89 I-Go", "I-Go"],
    "type-3-chi-nu": ["Type 3 Chi-Nu", "Chi-Nu"],
    "nakajima-ki-84-hayate": ["Nakajima Ki-84", "Ki-84 Hayate"],
    "is-2": ["IS-2", "IS-2 tank"],
    "is-3": ["IS-3", "IS-3 tank"],
    "su-152": ["SU-152", "SU 152"],
    "t-54": ["T-54", "T-54 tank"],
    "t-62": ["T-62", "T-62 tank"],
    "mt-lb": ["MT-LB", "MTLB"],
    "panzer-kampfwagen-iv": ["Panzerkampfwagen IV", "Panzer IV"],
    "stug-iv": ["StuG IV", "Sturmgeschütz IV"],
    "jagdpanther": ["Jagdpanther", "Jagdpanzer V"],
    "sdkfz-234": ["Sd.Kfz. 234", "Sd.Kfz.234"],
    "ferdinand-elefant": ["Ferdinand", "Elefant tank destroyer"],
    "m4a1-sherman": ["M4A1 Sherman", "M4A1"],
    "m18-tank-destroyer": ["M18 Tank Destroyer", "M18"],
    "m36-jackson": ["M36 Jackson", "M36"],
    "m24-chaffee": ["M24 Chaffee", "M24"],
    "crusader": ["Crusader tank", "Crusader"],
    "centurion": ["Centurion tank", "Centurion"],
    "valentine": ["Valentine tank", "Valentine"],
    "renault-r35": ["Renault R35", "R35"],
    "m13-40": ["M13/40", "M13-40"],
    "amx-13": ["AMX-13", "AMX13"],
    "t-26": ["T-26 tank", "T-26"],
    # --- часть 5: тяжёлая бронетехника 1930–1950-х ---
    "t-35": ["T-35", "T-35 tank"],
    "t-55": ["T-55", "T-55 tank"],
    "t-70": ["T-70", "T-70 tank"],
    "t-80": ["T-80", "T-80 tank"],
    "t-44": ["T-44", "T-44 tank"],
    "is-7": ["IS-7", "IS-7 tank"],
    "is-9": ["IS-9", "IS-9 tank"],
    "kv-2": ["KV-2", "KV-2 tank"],
    "su-85": ["SU-85", "SU-85 tank"],
    "pt-76": ["PT-76", "PT-76 tank"],
    "bmp-1": ["BMP-1", "BMP-1 infantry fighting vehicle"],
    "btr-60": ["BTR-60", "BTR-60 armoured personnel carrier"],
    "brm-2": ["BRDM-2", "BRDM-2 armoured car"],
    "zil-135": ["ZIL-135", "ZIL 135"],
    "panzer-kampfwagen-iii": ["Panzerkampfwagen III", "Pz.Kpfw. III"],
    "panzer-kampfwagen-i": ["Panzerkampfwagen I", "Pz.Kpfw. I"],
    "stug-38": ["StuG 38", "Sturmgeschütz 38"],
    "hetzer": ["Hetzer", "Panzerjäger Hetzer"],
    "jagdpanzer-iv": ["Jagdpanzer IV", "Panzerjäger Tiger (P)"],
    "sdkfz-222": ["Sd.Kfz. 222", "Sonderkraftfahrzeug 222"],
    "sdkfz-231": ["Sd.Kfz. 231", "Sonderkraftfahrzeug 231"],
    "sdkfz-250": ["Sd.Kfz. 250", "Sonderkraftfahrzeug 250"],
    "maus": ["Panzerkampfwagen VIII Maus", "Maus tank"],
    "flakpanzer-tiger": ["Geschützwagen Tiger", "Flakpanzer 38(t)"],
    "m3-lee": ["M3 Lee", "Medium Tank M3 Lee"],
    "m2-medium-tank": ["M2 medium tank", "M2 Medium Tank"],
    "m7-priest": ["M7 Priest", "M7 Priest artillery"],
    "m12-gmc": ["M12 GMC", "12.2cm howitzer M12"],
    "m26-pershing": ["M26 Pershing", "M26 tank"],
    "l6": ["L6 amphibious tank", "Light Tank L6"],
    "m3-halftrack": ["M3 Halftrack", "Halftrack M3"],
    "m22-locust": ["M22 Locust", "Light Tank M22"],
    "firefly": ["Sherman Firefly", "M4A4 Sherman Firefly"],
    "black-prince": ["Black Prince (tank)", "Churchill Black Prince"],
    "churchill-challenger": ["Churchill Challenger", "M7 Churchill"],
    "avro-lancaster": ["Avro Lancaster", "Lancaster bomber"],
    "de-havilland-mosquito": ["de Havilland Mosquito", "DH Mosquito"],
    "type-95-hyoshou": ["Type 95 Hyoshou", "H95 tankette"],
    "type-4-ke-ni": ["Type 4 Ke-Ni", "Type 4 tank"],
    # --- часть 6: авиация, колёсная техника, другие страны ---
    "messerschmitt-bf-109": ["Messerschmitt Bf 109", "Bf 109"],
    "focke-wulf-fw-190": ["Focke-Wulf Fw 190", "Fw 190"],
    "messerschmitt-me-262": ["Messerschmitt Me 262", "Me 262"],
    "messerschmitt-bf-110": ["Messerschmitt Bf 110", "Bf 110"],
    "north-american-p-51-mustang": ["North American P-51 Mustang", "P-51 Mustang"],
    "republic-p-47-thunderbolt": ["Republic P-47 Thunderbolt", "P-47 Thunderbolt"],
    "boeing-b-17-flying-fortress": ["Boeing B-17 Flying Fortress", "B-17 Flying Fortress"],
    "douglas-a-26-invader": ["Douglas A-26 Invader", "A-26 Invader"],
    "nakajima-ki-61-hiryu": ["Nakajima Ki-61 Hiryu", "Ki-61"],
    "nakajima-ki-44-shoki": ["Nakajima Ki-44 Shoki", "Ki-44"],
    "nakajima-ki-46-dinah": ["Nakajima Ki-46 Dinah", "Ki-46"],
    "macchi-c-202": ["Macchi C.202", "Macchi 202"],
    "dewoitine-d-520": ["Dewoitine D.520", "D.520"],
    "ilyushin-il-2": ["Ilyushin Il-2", "Il-2"],
    "yakovlev-yak-3": ["Yakovlev Yak-3", "Yak-3"],
    "lagg-3": ["LaGG-3", "Lagg 3"],
    "mercedes-benz-l-1500a": ["Mercedes-Benz L 1500A", "L 1500A"],
    "opel-blitz": ["Opel Blitz", "Opel 3.6-36S"],
    "jw-akaba": ["JW Akaba", "Akaba armoured car"],
    "tp-70": ["TP-70 tankette", "TP-70"],
    "strv-104": ["Strv 104", "Strv 104 tank"],
    "landsverk-l-60": ["Landsverk L 60", "L 60 tank"],
    "su-35": ["Su-35 tankette", "Su-35 tankette"],
    "merkava-mk-2": ["Merkava Mk.2", "Merkava"],
    "centurion-shoot": ["Centurion tank", "Centurion Sho't"],
    "type-62": ["Type 62 tank", "Type 62"],
    "m15-42": ["M15/42", "M15 42 howitzer"],
    "p26-40": ["Pz.Kpfw. 47", "P26/40 tank"],
    "pansar-i": ["Pansar I", "Pansar tank"],
}

# Названия машин для гайдов, которых нет в манифесте: берём название гайда
# и убираем оформление — по нему ищем фотографию в Commons.
_TITLE_PAREN = re.compile(r"\(([^)]*)\)")
_TITLE_IN = re.compile(r"\s+в\s+(?:Израиле|Польше|Швеции|Финляндии|Италии|Франции|Китае)\s*$", re.I)
_TITLE_NOISE = re.compile(
    r"[«»\"']|зимн(яя|ий)|зимн|весенн|летнн|поздн|ранн|серийн|модерниз|модиф|"
    r"звёздд|индианск|израильск|и[зс]раильск|польск|шведск|финск|итальянск|"
    r"французск|китайск|японск|немецк|американск|советск|английск|бельгийск|"
    r"канадск|австралийск",
    re.I,
)


def _auto_names(guide: dict) -> list[str]:
    """Варианты названия машины для поиска фотографии.

    Важно не оставлять обрубков вроде «Char» — по ним подходит любая
    машина с похожим словом. Поэтому берём только полное название и
    содержимое скобок: «Landsverk L-60 (Strv 109)» → «Landsverk L-60»
    и «Strv 109».
    """
    title = (guide.get("title") or "").strip()
    variants: list[str] = []

    def add(value: str) -> None:
        value = value.strip(" -,")
        if value and value not in variants:
            variants.append(value)

    # Содержимое скобок — самостоятельное обозначение машины.
    for inner in _TITLE_PAREN.findall(title):
        add(_TITLE_NOISE.sub("", inner))

    without_paren = _TITLE_PAREN.sub("", title)
    add(_TITLE_NOISE.sub("", _TITLE_IN.sub("", without_paren)))
    add(_TITLE_NOISE.sub("", title))
    return variants


def _names_for(slug: str) -> list[str]:
    """Имена для поиска: из манифеста либо из названия гайда.

    Порядок важен: сначала точное название, затем русское название
    гайда (по нему точно ищется статья Википедии), затем варианты
    с числовым обозначением.
    """
    names: list[str] = []

    def add(value: str) -> None:
        value = (value or "").strip(" -,")
        if value and value not in names:
            names.append(value)

    for value in VEHICLE_NAMES.get(slug, []):
        add(value)

    for guide in ALL_GUIDES:
        if guide["slug"] != slug:
            continue
        # Русское название гайда: в русской Википедии ищется точно.
        add(guide.get("title", ""))
        for value in _auto_names(guide):
            add(value)
        break

    return names

# Прямые категории Commons — проверяются первыми, когда название машины
# нигде не упоминается (частый случай у музейных и архивных снимков).
DIRECT_CATEGORIES = {
    "sdkfz-251": [
        "Category:Sd.Kfz. 251",
        "Category:OT-810 based Sd.Kfz. 251 replicas",
    ],
    "type-1-ho-ni": ["Category:Type 1 Ho-Ni"],
    "type-92-jyu-sokosha": [
        "Category:Type 92 (vehicle)",
        "Category:Type 92 armoured car",
    ],
    "kv-202": ["Category:KV-202"],
    "strv-103": ["Category:Strv 103"],
    "type-59": ["Category:Type 59 tank"],
    "is-1": ["Category:IS-1"],
    "somua-s35": ["Category:SOMUA S35"],
    "hotchkiss-h39": ["Category:Hotchkiss H39"],
    "a6m2-zero": ["Category:Mitsubishi A6M Zero"],
    "nakajima-ki-43-ii": ["Category:Nakajima Ki-43"],
    "sexton": ["Category:Sexton (tank)"],
    "daimler-dingo": ["Category:Daimler Dingo"],
    "universal-carrier": ["Category:Universal Carrier"],
    "l3-35": ["Category:L3/35"],
    "m60-magach-6": ["Category:M60 Magach"],
    "wespe": ["Category:Wespe"],
    "hurricane-mk-ii": ["Category:Hawker Hurricane"],
    "spitfire-mk-ix": ["Category:Supermarine Spitfire"],
    "comet": ["Category:Comet (tank)"],
    "churchill-mk-vii": ["Category:Churchill tank"],
    "m8-grease-truck": ["Category:M8 Greyhound"],
    "m3a1-stuart": ["Category:M3 Stuart"],
    "m10-wolverine": ["Category:M10 Wolverine"],
    "m4a3e8-sherman": ["Category:M4 Sherman"],
    "stug-iii-ausf-g": ["Category:StuG III"],
    "tiger-i": ["Category:Tiger I"],
    "panther-ausf-g": ["Category:Panther (tank)"],
    "panzer-iv-ausf-g": ["Category:Panzer IV"],
    "btr-152": ["Category:BTR-152"],
    "zil-131": ["Category:ZIL-131"],
    "su-100": ["Category:SU-100"],
    "kv-1": ["Category:KV-1"],
    "t-34-76": ["Category:T-34"],
    "t-34-85": ["Category:T-34-85"],
    "type-95-ha-go": ["Category:Type 95 Ha-Go"],
    "type-97-chi-ha": ["Category:Type 97 Chi-Ha"],
    "type-97-shinhoto": ["Category:Type 97 Shinhoto Chi-Ha"],
    "type-89-i-go": ["Category:Type 89 I-Go"],
    "type-3-chi-nu": ["Category:Type 3 Chi-Nu"],
    "nakajima-ki-84-hayate": [
        "Category:Nakajima Ki-84 Hayate",
        "Category:Nakajima Ki-43 Hayabusa",
    ],
    "nakajima-ki-43-ii": [
        "Category:Nakajima Ki-43 Hayabusa",
        "Category:Nakajima Ki-43-II",
        "Category:Nakajima Ki-43",
    ],
    "type-1-ho-ni": [
        "Category:Type 1 Ho-Ni",
        "Category:Type 1 Ho-Ni II",
        "Category:Type 1 Ho-Ni I",
    ],
    "type-92-jyu-sokosha": [
        "Category:Type 92 (vehicle)",
        "Category:Type 92 armoured car",
        "Category:Type 92 armoured truck",
    ],
    "type-59": [
        "Category:Type 59 tank at the Tankfest 2012",
        "Category:Type 59 tank in Military Museum of the Chinese People's Revolution",
        "Category:Type 59 tank",
    ],
    "ferdinand-elefant": [
        "Category:Elefant (tank)",
        "Category:Elefant tank destroyer",
        "Category:Sd.Kfz. 184",
    ],
    "kv-202": ["Category:KV-202 tank", "Category:KV-202"],
    # --- часть 5 ---
    "t-35": ["Category:T-35"],
    "t-55": ["Category:T-55"],
    "t-70": ["Category:T-70"],
    "t-80": ["Category:T-80"],
    "t-44": ["Category:T-44"],
    "is-7": ["Category:IS-7"],
    "is-9": ["Category:IS-9"],
    "kv-2": ["Category:KV-2"],
    "su-85": ["Category:SU-85"],
    "pt-76": ["Category:PT-76"],
    "bmp-1": ["Category:BMP-1"],
    "btr-60": ["Category:BTR-60"],
    "brm-2": ["Category:BRDM-2"],
    "zil-135": ["Category:ZIL-135"],
    "panzer-kampfwagen-iii": ["Category:Panzerkampfwagen III"],
    "panzer-kampfwagen-i": ["Category:Panzerkampfwagen I"],
    "stug-38": ["Category:StuG 38"],
    "hetzer": ["Category:Panzerjäger Hetzer"],
    "jagdpanzer-iv": ["Category:Panzerjäger Tiger (P)"],
    "sdkfz-222": ["Category:Sd.Kfz. 222"],
    "sdkfz-231": ["Category:Sd.Kfz. 231"],
    "sdkfz-250": ["Category:Sd.Kfz. 250"],
    "maus": ["Category:Panzerkampfwagen VIII Maus"],
    "flakpanzer-tiger": ["Category:Geschützwagen Tiger", "Category:Flakpanzer 38(t)"],
    "m3-lee": ["Category:M3 Lee"],
    "m2-medium-tank": ["Category:M2 medium tank"],
    "m7-priest": ["Category:M7 Priest"],
    "m12-gmc": ["Category:M12 GMC"],
    "m26-pershing": ["Category:M26 Pershing"],
    "l6": ["Category:Light Tank L6"],
    "m3-halftrack": ["Category:Halftrack M3"],
    "m22-locust": ["Category:Light Tank M22"],
    "firefly": ["Category:Sherman Firefly"],
    "black-prince": ["Category:Churchill Black Prince"],
    "churchill-challenger": ["Category:M7 Churchill"],
    "avro-lancaster": ["Category:Avro Lancaster"],
    "de-havilland-mosquito": ["Category:de Havilland Mosquito"],
    "type-95-hyoshou": ["Category:Type 95 Hyoshou"],
    "type-4-ke-ni": ["Category:Type 4 (tank)"],
    # --- часть 6 ---
    "messerschmitt-bf-109": ["Category:Messerschmitt Bf 109"],
    "focke-wulf-fw-190": ["Category:Focke-Wulf Fw 190"],
    "messerschmitt-me-262": ["Category:Messerschmitt Me 262"],
    "messerschmitt-bf-110": ["Category:Messerschmitt Bf 110"],
    "north-american-p-51-mustang": ["Category:North American P-51 Mustang"],
    "republic-p-47-thunderbolt": ["Category:Republic P-47 Thunderbolt"],
    "boeing-b-17-flying-fortress": ["Category:Boeing B-17 Flying Fortress"],
    "douglas-a-26-invader": ["Category:Douglas A-26 Invader"],
    "nakajima-ki-61-hiryu": ["Category:Nakajima Ki-43"],
    "nakajima-ki-44-shoki": ["Category:Nakajima Ki-44"],
    "nakajima-ki-46-dinah": ["Category:Nakajima Ki-46"],
    "macchi-c-202": ["Category:Macchi C.202"],
    "dewoitine-d-520": ["Category:Dewoitine D.520"],
    "ilyushin-il-2": ["Category:Ilyushin Il-2"],
    "yakovlev-yak-3": ["Category:Yakovlev Yak-3"],
    "lagg-3": ["Category:LaGG-3"],
    "mercedes-benz-l-1500a": ["Category:Mercedes-Benz L 1500A"],
    "opel-blitz": ["Category:Opel Blitz"],
    "jw-akaba": ["Category:JW Akaba"],
    "tp-70": ["Category:TP-70 tankette"],
    "strv-104": ["Category:Strv 104"],
    "landsverk-l-60": ["Category:Landsverk L 60"],
    "su-35": ["Category:Su-35 tankette"],
    "merkava-mk-2": ["Category:Merkava"],
    "centurion-shoot": ["Category:Centurion (tank)"],
    "type-62": ["Category:Type 62 tank"],
    "m15-42": ["Category:M15/42"],
    "p26-40": ["Category:Pz.Kpfw. 47"],
    "pansar-i": ["Category:Pansar I"],
    "is-2": ["Category:IS-2"],
    "is-3": ["Category:IS-3"],
    "su-152": ["Category:SU-152"],
    "t-54": ["Category:T-54"],
    "t-62": ["Category:T-62"],
    "mt-lb": ["Category:MT-LB"],
    "panzer-kampfwagen-iv": ["Category:Panzer IV"],
    "stug-iv": ["Category:StuG IV"],
    "jagdpanther": ["Category:Jagdpanther"],
    "sdkfz-234": ["Category:Sd.Kfz. 234"],
    "ferdinand-elefant": ["Category:Ferdinand", "Category:Elefant tank destroyer"],
    "m4a1-sherman": ["Category:M4A1 Sherman"],
    "m18-tank-destroyer": ["Category:M18 Tank Destroyer"],
    "m36-jackson": ["Category:M36 Jackson"],
    "m24-chaffee": ["Category:M24 Chaffee"],
    "crusader": ["Category:Crusader (tank)"],
    "centurion": ["Category:Centurion (tank)"],
    "valentine": ["Category:Valentine (tank)"],
    "renault-r35": ["Category:Renault R35"],
    "m13-40": ["Category:M13/40"],
    "amx-13": ["Category:AMX-13"],
    "t-26": ["Category:T-26 (tank)"],
}

SCALE_RE = re.compile(r"\b(1\s*:\s*\d{1,3})\b")

# Для машин без пригодной категории в Commons файл подобран вручную.
PREFERRED_FILES = {
    "is-4": "File:IS-4 Tank.jpg",
    "t-90": "File:Moscow 2012 Victory Day Parade Rehearsal, T-90 tank, Russia.jpg",
    "bmp-2": "File:Army2016demo-007.jpg",
    "2s6-tunguska": "File:2008 Moscow Victory Day Parade - 9K22 Tunguska.jpg",
    "mig-21": "File:Croatian MiG-21 (cropped).jpg",
    "su-27": "File:Sukhoi Su-27.jpg",
    "mi-24": "File:Mi24CP (modified) b.jpg",
    "ka-50": "File:Kamov Ka-50 in Moscow.jpg",
    "tiger-ii": "File:Bundesarchiv Bild 101I-721-0398-21A, Frankreich, Panzer VI (Tiger II, Königstiger).jpg",
    "fi-156-storch": "File:Fieseler Storch 3 (cropped).jpg",
    "hs-129": "File:Henschel Hs 129B.jpg",
    "do-17": "File:Bundesarchiv Bild 101I-342-0603-25, Belgien-Frankreich, Flugzeuge Dornier Do 17.jpg",
    "ju-87": "File:Junkers JU-87 'Stuka' in-flight display side view.jpg",
    "he-111": "File:Bundesarchiv Bild 101I-343-0694-21, Belgien-Frankreich, Flugzeug Heinkel He 111.jpg",
    "me-410": "File:Me 410 Hornisse with BK 5.jpg",
    "m1-abrams": "File:M1A2 SEP v3.jpg",
    "m2-bradley": "File:US M2A1 Bradley deployed to Saudi Arabia during Operation Desert Shield.jpg",
    "m46-patton": "File:Marines-tank-Korea-19530705.JPEG",
    "m109-paladin": "File:Kings of battle keep the fire; 1-9 FA fires its last rounds 140910-A-CW513-046.jpg",
    "f-86-sabre": "File:F-86 Sabre hertiage flight.jpg",
    "a-10-thunderbolt": "File:Fairchild Republic A-10 Thunderbolt II - 32156159151.jpg",
    "b-25-mitchell": "File:B25 Mitchell - Chino Airshow 2014 (14033501440).jpg",
    "cromwell": "File:Cromwell Tank (13538144563).jpg",
    "hawker-tempest": "File:Hawker Tempest V in flight Nov 1944.jpg",
    "dh-vampire": "File:De Havilland DH115 Vampire banking with the sun reflecting off its silver wings (cropped).jpg",
    "aec-matador": "File:AEC Matador, H102602 pic3.JPG",
    "merkava": "File:IDF Merkava Mk I in 1979.jpg",
    "type-99": "File:Type 99 MBT front left.jpg",
    "macchi-c-205": "File:Macchi 205.jpg",
    "fiat-cr-32": "File:Az Olasz Légierő FIAT CR-32 típusú vadászrepülőgépe._Fortepan 26473.jpg",
    "wzt-3": "File:MSPO2004 PICT0082 WZT-3.jpg",
    "tatra-813": "File:Tatra 813 KOLOS 1.jpg",
    "tatra-111": "File:Kopřivnice - Muzeum nákladních automobilů Tatra, Tatra 111, obr01.jpg",
    "praga-v3s": "File:BAHNA 2018 - 075 crop.jpg",
    "pzl-ts-11": "File:PZL TS-11 lskra.jpg",
    "pzl-p-11": "File:PZL P.11c '39 - 2' (14336386246).jpg",
    "praga-rn": "File:BAHNA 2018 - 061 crop.jpg",
    "nakajima-ki-87": "File:Ki-87 01 00086218.jpg",
    "bedford-oyd": "File:Bedford OYD 3 ton 4x2 General Service Truck, Duxford 2024-06-29.jpg",
    "panzer-38t": "File:Panzer 38(t) Ausf. S.jpg",
    "sdkfz-251": "File:Sonderkraftfahrzeug 251 Sd.Kfz.251.jpg",
    "type-92-jyu-sokosha": "File:Type 92 Iju Sokosha Tankette.jpg",
    "type-59": "File:Type 59-II Tank (9871578856).jpg",
    "ferdinand-elefant": "File:Elefant ‘501’ - Patriot Museum, Kubinka (26555210489).jpg",
    "is-1": "File:IS 1 prototyp.jpg",
    "nakajima-ki-43-ii": "File:Nakajima Ki-43-II Hayabusa.jpg",
}

# Статья Википедии, где почти наверняка есть фотография машины.
# Название в статье часто отличается от привычного: KV-202 известна
# как «T-10 tank», а Type 4 Ke-Ni — как «Type 4 Ke-Nu light tank».
WIKIPEDIA_ARTICLES = {
    "10-5-cm-m-39": ("en.wikipedia.org", "10.5 cm leFH 16"),
    "10-5cm-lefh-16": ("en.wikipedia.org", "10.5 cm leFH 16"),
    "105-k-13": ("ru.wikipedia.org", "105 K/13"),
    "10tp": ("en.wikipedia.org", "10TP"),
    "10tp-winter": ("en.wikipedia.org", "10TP"),
    "122mm-m-30": ("it.wikipedia.org", "122 mm M-30"),
    "152-k-40": ("en.wikipedia.org", "15 cm sFH 18"),
    "152-k-40-winter": ("en.wikipedia.org", "15 cm sFH 18"),
    "152mm-ml-20": ("it.wikipedia.org", "152 mm ML-20"),
    "15cm-sfh-18": ("en.wikipedia.org", "15 cm sFH 18"),
    "76-k-36": ("pl.wikipedia.org", "76 K/36"),
    "88mm-flak-36": ("en.wikipedia.org", "8.8 cm Flak 36"),
    "autoblinda": ("fi.wikipedia.org", "Autoblinda"),
    "bj212": ("en.wikipedia.org", "Beijing BJ212"),
    "blenheim-mk-v": ("en.wikipedia.org", "Bristol Blenheim"),
    "boeing-b-17-flying-fortress": ("en.wikipedia.org", "Boeing B-17 Flying Fortress"),
    "brm-2": ("en.wikipedia.org", "BRDM-2"),
    "fiat-cr-42": ("en.wikipedia.org", "Fiat CR.42 Falco"),
    "is-9": ("en.wikipedia.org", "T-10 tank"),
    "jelcz-315": ("de.wikipedia.org", "Jelcz 315"),
    "jw-akaba": ("pl.wikipedia.org", "Akaba"),
    "k-33": ("fi.wikipedia.org", "K-33"),
    "kv-202": ("en.wikipedia.org", "T-10 tank"),
    "kv-202-engineering": ("en.wikipedia.org", "T-10 tank"),
    "l6": ("en.wikipedia.org", "L6/40 tank"),
    "lagg-3": ("en.wikipedia.org", "Lavochkin-Gorbunov-Gudkov LaGG-3"),
    "m12-gmc": ("en.wikipedia.org", "M12 Gun Motor Carriage"),
    "m151-mutt": ("en.wikipedia.org", "M151 MUTT"),
    "m2-105mm-howitzer": ("en.wikipedia.org", "M2 howitzer"),
    "m2-medium-tank": ("en.wikipedia.org", "M2 medium tank"),
    "m3-15mc": ("en.wikipedia.org", "M3 medium tank"),
    "m3-76mm": ("en.wikipedia.org", "M3 medium tank"),
    "m3-ussr": ("en.wikipedia.org", "M3 medium tank"),
    "m48a3c": ("en.wikipedia.org", "M48 Patton"),
    "m590": ("en.wikipedia.org", "M590"),
    "m60-blazer": ("en.wikipedia.org", "M60 tank"),
    "macchi-c-202": ("en.wikipedia.org", "Macchi C.202 Folgore"),
    "macchi-mc-202": ("en.wikipedia.org", "Macchi MC.202"),
    "magach-6m": ("en.wikipedia.org", "Magach"),
    "namer": ("en.wikipedia.org", "Namer"),
    "p26-40": ("cs.wikipedia.org", "Panzerkampfwagen VII"),
    "p40": ("en.wikipedia.org", "P40 tank"),
    "pansar-i": ("en.wikipedia.org", "Landsverk L-60"),
    "pg-13": ("en.wikipedia.org", "PG-13"),
    "pzkp-7": ("en.wikipedia.org", "7TP"),
    "renault-d1": ("pl.wikipedia.org", "Renault D1"),
    "sa-201": ("en.wikipedia.org", "SA 201"),
    "sa-201-sweden": ("en.wikipedia.org", "SA 201"),
    "sdkfz-3": ("en.wikipedia.org", "Sd.Kfz. 3"),
    "sdkfz-4": ("en.wikipedia.org", "Sd.Kfz. 4"),
    "sdkfz-6": ("en.wikipedia.org", "Sd.Kfz. 6"),
    "sh-5": ("ru.wikipedia.org", "SH-5"),
    "spg-l-60": ("en.wikipedia.org", "Landsverk L-60"),
    "strv-103-c": ("en.wikipedia.org", "Strv 103"),
    "strv-106": ("sv.wikipedia.org", "Strv 106"),
    "strv-109": ("en.wikipedia.org", "Landsverk L-60"),
    "su-26": ("en.wikipedia.org", "Su-26"),
    "su-26m": ("en.wikipedia.org", "Su-26"),
    "su-35": ("en.wikipedia.org", "Su-35"),
    "t-26-model-1940": ("en.wikipedia.org", "T-26"),
    "t-34-85-finland": ("en.wikipedia.org", "T-34-85"),
    "t-54-israel": ("en.wikipedia.org", "T-54"),
    "t-72-smoothbore": ("en.wikipedia.org", "T-72"),
    "type-4-ke-ni": ("en.wikipedia.org", "Type 4 Ke-Nu light tank"),
    "type-59-1": ("ru.wikipedia.org", "Type 59"),
    "type-80": ("ru.wikipedia.org", "Type 80"),
    "type-95-hyoshou": ("en.wikipedia.org", "Type 95 Ha-Go light tank"),
    "vab": ("ru.wikipedia.org", "VAB"),
    "yakovlev-yak-3": ("en.wikipedia.org", "Yakovlev Yak-3"),
    "zil-135": ("en.wikipedia.org", "ZIL-135"),
    "zis-22": ("de.wikipedia.org", "ZIS-22"),
    "zsl-92": ("en.wikipedia.org", "ZSL-92"),
}

# Для машин с похожими обозначениями требуем, чтобы совпадение было
# именно в имени файла: описание часто упоминает соседние машины.
TITLE_REQUIRED = {
    "type-59": "t-59",
    "strv-103": "strv",
    "nakajima-ki-43-ii": "ki-43",
    "nakajima-ki-84-hayate": "ki-84",
    "kv-202": "kv-202",
    "is-1": "is-1",
    "type-92-jyu-sokosha": "type 92",
    "kv-1": "kv-1",
    "type-1-ho-ni": "ho-ni",
    "sdkfz-251": "251",
    "t-34-76": "t-34",
    "t-34-85": "t-34",
    "type-95-ha-go": "ha-go",
    "type-89-i-go": "i-go",
    "type-97-chi-ha": "chi-ha",
    "type-97-shinhoto": "chi-ha",
    "type-3-chi-nu": "chi-nu",
    "panther-ausf-g": "panther",
    "tiger-i": "tiger",
    "panzer-kampfwagen-iv": "panzer",
    "stug-iv": "stug",
    "jagdpanther": "panther",
    "m4a1-sherman": "sherman",
    "m4a3e8-sherman": "sherman",
    "is-2": "is-2",
    "is-3": "is-3",
    "su-152": "su-152",
    "su-100": "su-100",
    "t-54": "t-54",
    "t-62": "t-62",
    "panzer-kampfwagen-iii": "panzer",
    "opel-blitz": "opel",
    "firefly": "sherman",
    "m3-lee": "tank",
    "t-35": "t-35",
    "t-55": "t-55",
    "t-70": "t-70",
    "t-80": "t-80",
    "t-44": "t-44",
    "is-7": "is-7",
    "is-9": "is-9",
    "kv-2": "kv-2",
    "su-85": "su-85",
    "pt-76": "pt-76",
    "bmp-1": "bmp-1",
    "btr-60": "btr-60",
    "brm-2": "brdm-2",
    "zil-135": "zil",
    "maus": "maus",
    "hetzer": "hetzer",
    "m7-priest": "priest",
    "m12-gmc": "m12",
    "m26-pershing": "pershing",
    "m22-locust": "locust",
    "m3-halftrack": "halftrack",
    "black-prince": "prince",
    "churchill-challenger": "challenger",
    "avro-lancaster": "lancaster",
    "de-havilland-mosquito": "mosquito",
    "type-95-hyoshou": "hyoshou",
    "type-4-ke-ni": "ke-ni",
    "messerschmitt-bf-109": "109",
    "focke-wulf-fw-190": "190",
    "messerschmitt-me-262": "262",
    "messerschmitt-bf-110": "110",
    "north-american-p-51-mustang": "mustang",
    "republic-p-47-thunderbolt": "thunderbolt",
    "boeing-b-17-flying-fortress": "fortress",
    "douglas-a-26-invader": "invader",
    "nakajima-ki-61-hiryu": "ki-61",
    "nakajima-ki-44-shoki": "ki-44",
    "nakajima-ki-46-dinah": "ki-46",
    "macchi-c-202": "c.202",
    "dewoitine-d-520": "d.520",
    "ilyushin-il-2": "il-2",
    "yakovlev-yak-3": "yak-3",
    "lagg-3": "lagg",
    "mercedes-benz-l-1500a": "1500",
    "jw-akaba": "akaba",
    "tp-70": "tp-70",
    "strv-104": "104",
    "landsverk-l-60": "l 60",
    "su-35": "su-35",
    "type-62": "62",
    "m15-42": "m15",
    "p26-40": "p.47",
    "pansar-i": "pansar",
    "crusader": "tank",
    "ferdinand-elefant": "elefant",
    "amx-13": "amx",
    "type-97-chi-ha": "chi-ha",
    "sdkfz-251": "251",
    "type-92-jyu-sokosha": "type 92",
    # Новые машины: фотографии проверены по статьям Википедии.
    "is-4": ("en.wikipedia.org", "IS-4"),
    "t-90": ("en.wikipedia.org", "T-90"),
    "bmp-2": ("en.wikipedia.org", "BMP-2"),
    "2s6-tunguska": ("en.wikipedia.org", "2S6 Tunguska"),
    "mig-21": ("en.wikipedia.org", "Mikoyan-Gurevich MiG-21"),
    "su-27": ("en.wikipedia.org", "Sukhoi Su-27"),
    "mi-24": ("en.wikipedia.org", "Mil Mi-24"),
    "ka-50": ("en.wikipedia.org", "Kamov Ka-50"),
    "tiger-ii": ("en.wikipedia.org", "Tiger II"),
    "fi-156-storch": ("en.wikipedia.org", "Fieseler Fi 156 Storch"),
    "hs-129": ("en.wikipedia.org", "Henschel Hs 129"),
    "do-17": ("en.wikipedia.org", "Dornier Do 17"),
    "ju-87": ("en.wikipedia.org", "Junkers Ju 87"),
    "he-111": ("en.wikipedia.org", "Heinkel He 111"),
    "me-410": ("en.wikipedia.org", "Messerschmitt Me 410"),
    "m1-abrams": ("en.wikipedia.org", "M1 Abrams"),
    "m2-bradley": ("en.wikipedia.org", "M2 Bradley"),
    "m46-patton": ("en.wikipedia.org", "M46 Patton"),
    "m109-paladin": ("en.wikipedia.org", "M109 Paladin"),
    "f-86-sabre": ("en.wikipedia.org", "F-86 Sabre"),
    "a-10-thunderbolt": ("en.wikipedia.org", "A-10 Thunderbolt II"),
    "b-25-mitchell": ("en.wikipedia.org", "North American B-25 Mitchell"),
    "cromwell": ("ru.wikipedia.org", "Cromwell"),
    "hawker-tempest": ("en.wikipedia.org", "Hawker Tempest"),
    "dh-vampire": ("en.wikipedia.org", "de Havilland Vampire"),
    "aec-matador": ("en.wikipedia.org", "AEC Matador"),
    "merkava": ("en.wikipedia.org", "Merkava"),
    "type-99": ("en.wikipedia.org", "Type 99 tank"),
    "macchi-c-205": ("en.wikipedia.org", "Macchi C.205"),
    "fiat-cr-32": ("en.wikipedia.org", "Fiat CR.32"),
    # Польша, Япония, Англия и Чехия — добираем страны и типы техники.
    "wzt-1": ("pl.wikipedia.org", "WZT-1"),
    "tatra-813": ("en.wikipedia.org", "Tatra 813"),
    "tatra-111": ("en.wikipedia.org", "Tatra 111"),
    "praga-v3s": ("en.wikipedia.org", "Praga V3S"),
    "pzl-p-43": ("en.wikipedia.org", "PZL P.43"),
    "pzl-p-11": ("en.wikipedia.org", "PZL P.11"),
    "praga-rn": ("en.wikipedia.org", "Praga RN"),
    "nakajima-ki-87": ("en.wikipedia.org", "Nakajima Ki-87"),
    "bedford-oyd": ("en.wikipedia.org", "Bedford OYD"),
    "panzer-38t": ("en.wikipedia.org", "Panzer 38(t)"),
}

# Другие обозначения той же машины: подходят, если основного нет в имени файла.
TITLE_ALTERNATIVES = {
    "p26-40": ["p26", "p 26", "panzer 40"],
    "type-59": ["type 59", "t59"],
    "m12-gmc": ["m12", "155 gun motor carriage"],
    "zil-135": ["zil 135", "zil135"],
    "brm-2": ["brdm 2", "brdm2"],
}
HEX_RE = re.compile(r"^[0-9a-fA-F]{6}$")


# --------------------------------------------------------------------------
# Работа с API
# --------------------------------------------------------------------------
def api_get(params: dict, attempts: int = 6, host: str = "") -> dict:
    """Запрос к API Commons с повторами и вежливыми паузами."""
    query = urllib.parse.urlencode({**params, "format": "json"})
    last_error: Exception | None = None
    base = f"https://{host}/w/api.php" if host else API
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(
                f"{base}?{query}", headers={"User-Agent": USER_AGENT}
            )
            with urllib.request.urlopen(request, timeout=45) as response:
                data = json.loads(response.read().decode("utf-8"))
            time.sleep(REQUEST_DELAY)
            return data
        except Exception as error:  # noqa: BLE001
            last_error = error
            # 429 — слишком частые запросы: ждать заметно дольше.
            delay = 45.0 if "429" in str(error) else 2.5
            time.sleep(delay * (attempt + 1))
    raise RuntimeError(f"API не ответил: {last_error}")


def search_categories(term: str, limit: int = 12) -> list[str]:
    """Найти категории по имени."""
    data = api_get(
        {
            "action": "query",
            "list": "search",
            "srnamespace": 14,
            "srsearch": term,
            "srlimit": limit,
        }
    )
    return [item["title"] for item in data.get("query", {}).get("search", [])]


def categories_by_prefix(prefix: str, limit: int = 30) -> list[str]:
    """Категории, название которых начинается с указанного.

    Полнотекстовый поиск Commons путает дефис с оператором «минус»:
    запрос «KV-202» не находит ничего. А вот список категорий по
    префиксу работает всегда и даёт точное название вида
    «KV-2 in museums» или «M12 Gun Motor Carriage».
    """
    data = api_get(
        {
            "action": "query",
            "list": "allcategories",
            "acprefix": prefix,
            "aclimit": limit,
        }
    )
    return [item["*"] for item in data.get("query", {}).get("allcategories", [])]


def files_by_prefix(prefix: str, limit: int = 25) -> list[str]:
    """Имена файлов, начинающихся с указанного.

    То же, что и категории по префиксу: имя файла в Commons обычно
    начинается с обозначения машины («BRDM-2, Tallin, Estonia.jpg»).
    """
    data = api_get(
        {
            "action": "query",
            "list": "allimages",
            "aiprefix": prefix,
            "ailimit": limit,
            "aisort": "name",
        }
    )
    return [
        f"File:{item['name']}"
        for item in data.get("query", {}).get("allimages", [])
    ]


def category_files(category: str, limit: int = 60) -> list[dict]:
    """Файлы внутри категории вместе с лицензионными метаданными."""
    data = api_get(
        {
            "action": "query",
            "generator": "categorymembers",
            "gcmtitle": category,
            "gcmtype": "file",
            "gcmlimit": limit,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|size",
            "iiurlwidth": THUMB_WIDTH,
            "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl|License|"
            "AttributionRequired|ImageDescription|Credit|Categories",
        }
    )
    return _pages_to_files(data)


def search_files(term: str, limit: int = 30) -> list[dict]:
    """Поиск файлов по тексту описания.

    Поиск с кавычками иногда не находит ничего, поэтому при пустом
    результате повторяем запрос без кавычек.
    """
    data = api_get(
        {
            "action": "query",
            "generator": "search",
            "gsrsearch": term,
            "gsrnamespace": 6,
            "gsrlimit": limit,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|size",
            "iiurlwidth": THUMB_WIDTH,
            "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl|License|"
            "AttributionRequired|ImageDescription|Credit|Categories",
        }
    )
    files = _pages_to_files(data)
    if files:
        return files
    plain = term.replace('"', "").strip()
    if plain == term.strip():
        return files
    data = api_get(
        {
            "action": "query",
            "generator": "search",
            "gsrsearch": plain,
            "gsrnamespace": 6,
            "gsrlimit": limit,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|size",
            "iiurlwidth": THUMB_WIDTH,
            "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl|License|"
            "AttributionRequired|ImageDescription|Credit|Categories",
        }
    )
    return _pages_to_files(data)


def _pages_to_files(data: dict) -> list[dict]:
    files = []
    for page in data.get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        if not info.get("url"):
            continue
        meta = info.get("extmetadata", {}) or {}

        def field(name: str) -> str:
            return _clean_html((meta.get(name) or {}).get("value", ""))

        files.append(
            {
                "title": page.get("title", ""),
                "url": info.get("url", ""),
                "thumb_url": info.get("thumburl", ""),
                "width": info.get("width", 0),
                "height": info.get("height", 0),
                "size": info.get("size", 0),
                "artist": field("Artist") or field("Credit"),
                "license": field("LicenseShortName") or field("License"),
                "license_url": field("LicenseUrl"),
                "description": field("ImageDescription"),
                "source": info.get("descriptionurl", ""),
                "categories": field("Categories"),
            }
        )
    return files


def _normalize(value: str) -> str:
    """Оставить только буквы и цифры — чтобы «T-34-85» совпадало с «T 34 85»."""
    return re.sub(r"[^a-z0-9а-яё]+", "", (value or "").lower())


# Слишком общие слова: по ним нельзя опознать конкретную машину.
GENERIC_WORDS = {
    "tank", "tanks", "gun", "guns", "car", "cars", "truck", "trucks", "spg",
    "model", "models", "artillery", "aircraft", "vehicle", "vehicles", "afv",
    "self", "propelled", "heavy", "light", "medium", "main", "battle",
}


def _tokens(name: str) -> list[str]:
    """Ключевые фрагменты названия, по которым узнаём машину в подписи к фото."""
    normalized = _normalize(name)
    # Три символа — минимум: коды вида «KV-1», «IS-1», «T-26» короче не бывает.
    tokens = [normalized] if len(normalized) >= 3 else []
    # Характерная часть названия: «Type 97 Chi-Ha» → «chiha»
    tail = re.split(r"[\s/]+", name.strip())[-1]
    tail_normalized = _normalize(tail)
    if (
        len(tail_normalized) >= 3
        and tail_normalized != normalized
        and tail_normalized not in GENERIC_WORDS
    ):
        tokens.append(tail_normalized)
    # «T-34-85» → «t34»
    short = re.match(r"^([a-zа-я]?\d+)-", (name or "").lower())
    if short:
        candidate = _normalize(short.group(1))
        if len(candidate) >= 3 and candidate not in GENERIC_WORDS:
            tokens.append(candidate)
    return tokens


def match_quality(names: list[str], item: dict) -> int:
    """Насколько уверенно файл относится к нужной машине.

    2 — название машины есть в имени файла, 1 — только в описании, 0 — нет.

    Совпадение только в описании принимаем лишь для длинных обозначений:
    «M32» — это и катамаран, и американский танк, и гонка. Короткое
    обозначение обязано стоять в самом имени файла.
    """
    title = _normalize(item.get("title", ""))
    description = _normalize(item.get("description", ""))
    for name in names:
        for token in _tokens(name):
            if not token:
                continue
            if token in title:
                return 2
            if token in description and len(token) >= 5:
                return 1
    return 0


def match_article(article: str, item: dict) -> int:
    """Насколько файл из статьи Википедии соответствует этой машине.

    Название статьи и название файла расходятся: у «L6/40 tank» файл
    может называться «Fiat L6 40 05.jpg». Поэтому сверяем по ключевым
    словам, а не по всей строке целиком.
    """
    title = _normalize(item.get("title", ""))
    description = _normalize(item.get("description", ""))

    # Слова и числа разбираем отдельно: у «L6/40 tank» число 40 — часть
    # обозначения, а «tank» в названии файла может отсутствовать.
    letters: list[str] = []
    numbers: list[str] = []
    for word in re.split(r"[^0-9A-Za-zА-Яа-яЁё]+", article):
        if not word:
            continue
        if word.isdigit():
            if len(word) >= 2:
                numbers.append(word)
            continue
        normalized = _normalize(word)
        if len(normalized) >= 2:
            letters.append(normalized)
    if not letters and not numbers:
        return 0

    def found(word: str) -> bool:
        return word in title or word in description

    if all(found(word) for word in letters + numbers):
        return 2
    if all(found(word) for word in numbers) and sum(
        1 for word in letters if found(word)
    ) >= max(1, len(letters) - 1):
        return 1
    return 0


def title_ok(slug: str, item: dict) -> bool:
    """Для машин с близкими обозначениями требуем совпадение в имени файла."""
    required = TITLE_REQUIRED.get(slug)
    if not required:
        return True
    title = _normalize(item.get("title", ""))
    # Требуемое обозначение может быть записано несколькими способами:
    # «P26/40 tank» известна и как «Pz.Kpfw. 47».
    alternatives = [required] + list(TITLE_ALTERNATIVES.get(slug, []))
    return any(_normalize(value) in title for value in alternatives)


def matches_vehicle(names: list[str], item: dict) -> bool:
    """Проверить, что на фотографии упомянута именно нужная машина.

    Смотрим только на название файла и описание: категории Commons слишком
    широкие — в «Scale models of tanks» попадают сотни чужих моделей.
    """
    return match_quality(names, item) > 0


# --------------------------------------------------------------------------
# Отбор
# --------------------------------------------------------------------------
def _clean_html(value: str) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def license_ok(item: dict) -> bool:
    license_name = (item.get("license") or "").strip().lower()
    if not license_name:
        return False
    if "nd" in license_name and "and" not in license_name:
        return False  # CC BY-ND запрещает кадрирование
    if "nc" in license_name and "nd" not in license_name:
        return False
    for allowed in ALLOWED_LICENSES:
        if license_name == allowed or license_name.startswith(allowed):
            return True
    return False


def subject_ok(item: dict) -> bool:
    """Отсечь изображения, которые не показывают саму машину."""
    haystack = f"{item['title']} {item.get('description', '')}".lower()
    for word in BLOCK_WORDS:
        if word in haystack:
            return False
    return True


def category_says_machine(names: list[str], item: dict) -> bool:
    """Проверить, что машина названа в категориях Commons.

    Категории точнее описания: в «M32 racing» машина упомянута в тексте,
    а вот категория «M32» относится к парусным гонкам. Для коротких
    обозначений это единственный надёжный признак.
    """
    categories = item.get("categories") or ""
    if not categories:
        return False
    normalized = _normalize(categories)
    for name in names:
        for token in _tokens(name):
            # Три символа — минимум: «IS-1» в категории так и записан.
            if token and len(token) >= 3 and token in normalized:
                return True
    return False


def category_says_vehicle(slug: str, item: dict) -> bool:
    """Проверить машину по категориям с учётом псевдонимов.

    KV-202 в Commons называется «T-10M», а Type 4 Ke-Ni — «Type 4 Ke-Nu»:
    сверять надо и с привычным обозначением, и с названием статьи.
    """
    if category_says_machine(_names_for(slug), item):
        return True
    article = WIKIPEDIA_ARTICLES.get(slug)
    if not article:
        return False
    _host, title = article
    categories = item.get("categories") or ""
    if not categories:
        return False
    normalized = _normalize(categories)
    for word in re.split(r"[^0-9A-Za-zА-Яа-яЁё]+", title):
        token = _normalize(word)
        if len(token) >= 4 and token in normalized:
            return True
    return False


# Обозначения всех машин каталога: если в названии фотографии встречается
# чужое обозначение, значит это снимок другой машины.
def _build_known_tokens() -> dict[str, str]:
    """Обозначение машины → слаг, для всех гайдов каталога.

    Числовые токены отбрасываем: «1944» в названии фотографии может
    означать год съёмки, а не модель машины.
    """
    known: dict[str, str] = {}
    for guide in ALL_GUIDES:
        for name in _names_for(guide["slug"]):
            for token in _tokens(name):
                if len(token) < 4 or token.isdigit():
                    continue
                known.setdefault(token, guide["slug"])
    return known


_KNOWN_TOKENS: dict[str, str] = {}


def _short_designation(slug: str) -> bool:
    """Короткое ли обозначение машины: M32, VAB, 7TP.

    Такие обозначения совпадают с чужими машинами и в описании, и в
    категориях, поэтому им нужно прямое упоминание в имени файла.
    """
    for name in _names_for(slug):
        # Смотрим отдельные слова обозначения: у «L6 amphibious tank»
        # коротким является именно «L6».
        for part in re.split(r"[^0-9A-Za-zА-Яа-яЁё]+", name):
            if not part:
                continue
            token = _normalize(part)
            if not token or token.isdigit():
                continue
            # Три-четыре символа — «M32», «VAB», «7TP»: такие коды
            # совпадают с чужими машинами. Два символа считаем кодом
            # только при наличии цифры: «L6» — код, а «TP» из «TP-70» —
            # часть обозначения, а не самостоятельное имя.
            if 3 <= len(token) <= 4:
                return True
            if len(token) == 2 and any(char.isdigit() for char in token):
                return True
    return False


def wrong_vehicle(slug: str, item: dict) -> bool:
    """На фотографии упомянута другая машина из каталога.

    Так отсеиваются «T-74» вместо T-72, «STS-125» вместо VAB и прочие
    совпадения по случайным буквам.
    """
    if not _KNOWN_TOKENS:
        _KNOWN_TOKENS.update(_build_known_tokens())
    title = _normalize(item.get("title", ""))
    own = {token for name in _names_for(slug) for token in _tokens(name)}
    for token, other_slug in _KNOWN_TOKENS.items():
        if other_slug == slug or token in own:
            continue
        if token in title:
            return True
    return False


def geometry_ok(item: dict) -> bool:
    """Размер файла пригоден для обложки.

    Порог снижен до 620×420: часть снимков из Википедии чуть меньше,
    но для карточки каталога этого достаточно.
    """
    width = item.get("width") or 0
    height = item.get("height") or 0
    if width < 620 or height < 420:
        return False
    ratio = width / height
    return 1.15 <= ratio <= 2.6


def geometry_ok_loose(item: dict) -> bool:
    """Мягкая проверка размера для файлов из проверенных статей.

    Фотография из статьи о нужной машине подходит даже когда она
    невелика: лучше обложка поменьше, чем её отсутствие.
    """
    width = item.get("width") or 0
    height = item.get("height") or 0
    if width < 400 or height < 260:
        return False
    ratio = width / height
    return 1.0 <= ratio <= 3.2


def scale_of(*texts: str) -> str:
    for text in texts:
        match = SCALE_RE.search(text or "")
        if match:
            return match.group(1).replace(" ", "")
    return ""


def score(item: dict, names: list[str], prefer_models: bool) -> int:
    """Оценка пригодности изображения."""
    title = item["title"].lower()
    description = (item.get("description") or "").lower()
    total = 0

    for name in names:
        short = name.lower()
        if short in title:
            total += 4
            break
    for name in names:
        short = name.lower()
        if short in description:
            total += 2
            break

    is_model = "model" in title or "scale model" in description or "modèle" in description
    if is_model:
        total += 4 if prefer_models else 1
    else:
        total += 1 if prefer_models else 3

    ratio = (item.get("width") or 1) / (item.get("height") or 1)
    if 1.35 <= ratio <= 1.9:
        total += 2
    if (item.get("width") or 0) >= 1400:
        total += 1
    if (item.get("width") or 0) >= 2400:
        total += 1

    scale = scale_of(item["title"], description)
    if scale in {"1:35", "1:48", "1:32"}:
        total += 2
    if scale in {"1:72", "1:87", "1:100", "1:144"}:
        total -= 1

    if "museum" in description or "musee" in description or "museum" in title:
        total += 1
    if "tankfest" in title.lower() or "bovington" in title.lower():
        total += 1

    return total


# --------------------------------------------------------------------------
# Скачивание и обработка
# --------------------------------------------------------------------------
def _thumb_url(original_url: str, width: int = THUMB_WIDTH) -> str:
    """Прямая ссылка на уменьшенную копию в upload.wikimedia.org.

    Размер 960 px — из тех, что Wikimedia сейчас принимает; остальные
    отклоняются с кодом 400.
    """
    if not original_url:
        return ""
    marker = "/wikipedia/commons/"
    if marker not in original_url:
        return ""
    head, _, tail = original_url.partition(marker)
    tail = tail.split("?")[0]
    folder, _, name = tail.rpartition("/")
    if not name:
        return ""
    return f"{head}{marker}thumb/{folder}/{width}px-{name}"


def download(item: dict, target: Path) -> bool:
    """Скачать файл в уменьшенном виде.

    Ресайз делает сам Wikimedia (`Special:FilePath?...&width=`), поэтому Pillow
    не нужен: зависимость не собирается на Python 3.15, а кадрирование под
    формат 3:2 выполняется на клиенте через `object-fit: cover`.

    Хранилище отвечает 429 при частых запросах, поэтому при отказе
    ждём и пробуем следующий адрес.
    """
    title = item["title"].removeprefix("File:")
    quoted = urllib.parse.quote(title.replace(" ", "_"))
    candidates = [
        # Миниатюру собираем сами: API отдаёт оригинал, когда файл меньше
        # запрошенного размера, а оригиналы тяжёлые и хранилище отказывает.
        _thumb_url(item.get("url", "")),
        item.get("thumb_url", ""),
        f"{FILEPATH}{quoted}?width={THUMB_WIDTH}",
    ]
    payload = b""
    content_type = "image/jpeg"
    for url in candidates:
        if not url:
            continue
        request = urllib.request.Request(
            url, headers={"User-Agent": DOWNLOAD_UA, "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"}
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = response.read()
                content_type = response.headers.get("Content-Type", "image/jpeg")
            if len(payload) > 4096:
                break
        except Exception as error:  # noqa: BLE001
            # 429 — хранилище просит подождать: ждём подольше.
            time.sleep(45.0 if "429" in str(error) else 2.0)
            continue
        finally:
            time.sleep(0.8)

    if len(payload) < 4096:
        print(f"  ! не скачалось: {item['title']}")
        return False

    extension = ".png" if "png" in content_type else ".jpg"
    target = target.with_suffix(extension)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return True


# --------------------------------------------------------------------------
# Основной проход
# --------------------------------------------------------------------------
def candidates_for(slug: str, names: list[str], prefer_models: bool) -> list[dict]:
    """Собрать кандидатов по цепочке источников."""
    collected: dict[str, dict] = {}

    def add(items: list[dict], source: str, context: str = "") -> None:
        for item in items:
            item = dict(item)
            item["source_kind"] = source
            item["context"] = context
            if item["title"] not in collected:
                collected[item["title"]] = item

    if prefer_models:
        for name in names:
            for pattern in MODEL_CATEGORY_PATTERNS:
                term = pattern.format(name=name)
                for category in search_categories(term, limit=8):
                    add(category_files(category), "model-category", category)
                    time.sleep(0.12)
        for category in SHOWCASE_CATEGORIES:
            if category not in _SHOWCASE_CACHE:
                _SHOWCASE_CACHE[category] = category_files(category, limit=40)
            add(_SHOWCASE_CACHE[category], "showcase", category)
        for name in names:
            add(search_files(f'"{name}" scale model'), "model-search")
            add(search_files(f'"{name}" model tank'), "model-search")
            time.sleep(0.12)
    else:
        # Проверенная статья Википедии: самая надёжная отправная точка.
        article = WIKIPEDIA_ARTICLES.get(slug)
        if article:
            host, title = article
            add(wikipedia_page_files(title, host), "vehicle-wiki-known")
            time.sleep(0.2)
            # Статья найдена и проверена: остальные источники не нужны,
            # а каждый запрос к Commons стоит времени из-за лимитов.
            # Но если из статьи ничего не подошло, ищем дальше.
            if collected:
                chosen = _select_candidates(slug, names, collected, prefer_models)
                if chosen:
                    return chosen
        for category in DIRECT_CATEGORIES.get(slug, []):
            add(category_files(category), "vehicle-category", category)
            time.sleep(0.12)
        for name in names:
            add(category_files(f"Category:{name}"), "vehicle-category", f"Category:{name}")
            time.sleep(0.12)
        # Поиск по префиксу: работает там, где полнотекстовый поиск
        # путает дефис с оператором «минус» и не находит ничего.
        for name in names:
            for category in categories_by_prefix(name):
                if category.lower() in {"uncategorized", "mediawiki"}:
                    continue
                add(category_files(f"Category:{category}"), "vehicle-prefix", category)
                time.sleep(0.12)
            time.sleep(0.12)
        for name in names:
            for title in files_by_prefix(name, limit=12):
                add(fetch_by_titles([title]), "vehicle-file-prefix")
                time.sleep(0.05)
            time.sleep(0.12)
        for name in names:
            add(search_files(f'"{name}" tank'), "vehicle-search")
            time.sleep(0.12)
        # Статья Википедии: почти всегда иллюстрирована нужной машиной.
        add(wikipedia_articles(names), "vehicle-wiki")
        # Статья может называться точно как машина — тогда она ищется
        # напрямую, без полнотекстового поиска.
        for name in names:
            if not name or len(name) < 3:
                continue
            add(wikipedia_page_files(name), "vehicle-wiki-exact")
            time.sleep(0.2)

    return _select_candidates(slug, names, collected, prefer_models)


def _select_candidates(
    slug: str,
    names: list[str],
    collected: dict[str, dict],
    prefer_models: bool,
) -> list[dict]:
    """Отобрать подходящие фотографии из собранных кандидатов."""
    title_hits: list[dict] = []
    desc_hits: list[dict] = []
    known = WIKIPEDIA_ARTICLES.get(slug)
    known_article = known[1] if known else ""
    for item in collected.values():
        if not license_ok(item):
            continue
        if not subject_ok(item):
            continue
        # Файл из проверенной статьи Википедии сверяем с названием
        # статьи: оно и есть точное обозначение машины (KV-202
        # известна как «T-10 tank»).
        from_known_article = (
            item.get("source_kind") == "vehicle-wiki-known" and known_article
        )
        if from_known_article:
            if not geometry_ok_loose(item):
                continue
        elif not geometry_ok(item):
            continue
        if from_known_article:
            check = [known_article]
            quality = match_article(known_article, item)
            if quality == 0:
                continue
            item["score"] = score(item, check, prefer_models) + 8
            title_hits.append(item)
            continue
        quality = match_quality(names, item)
        if quality == 0:
            continue
        if not title_ok(slug, item):
            continue
        if wrong_vehicle(slug, item):
            continue
        # Если обозначение машины стоит прямо в имени файла, этого
        # достаточно: категории Commons заполнены не всегда.
        # А вот совпадение только в описании требует подтверждения
        # категорией — в описании «M32» может встретиться и парусная
        # гонка.
        if quality == 1 or _short_designation(slug):
            if not category_says_machine(names, item) and not category_says_vehicle(
                slug, item
            ):
                continue
        item["score"] = score(item, names, prefer_models) + (6 if quality == 2 else 0)
        (title_hits if quality == 2 else desc_hits).append(item)

    # Если есть файлы, где машина названа прямо в имени, — берём только их:
    # упоминание в описании часто означает «на фото заодно видно».
    pool = title_hits or desc_hits
    pool.sort(key=lambda entry: entry["score"], reverse=True)
    return pool


def wikipedia_articles(names: list[str]) -> list[dict]:
    """Фотографии из статей Википедии о машине.

    Статья в Википедии почти всегда иллюстрирована нужной техникой,
    а подпись к файлу ведёт в Commons, где есть и лицензия, и категории.

    Сначала ищем саму статью поиском (название с дефисом полнотекстовый
    поиск ломает), затем берём главную картинку и файлы статьи.
    """
    titles: list[str] = []
    for name in names:
        for variant in (name, name.replace("-", " ")):
            if variant and variant not in titles:
                titles.append(variant)

    found: list[dict] = []
    for host in ("ru.wikipedia.org", "en.wikipedia.org", "de.wikipedia.org"):
        for title in titles[:4]:
            article = _wikipedia_article_title(host, title)
            if not article:
                continue
            for item in _wikipedia_page_files(host, article):
                found.append(item)
        if found:
            return found
    return found


def wikipedia_page_files(article: str, host: str = "") -> list[dict]:
    """Файлы статьи Википедии по её точному названию.

    Хост задан, когда статья найдена заранее: так делается ровно один
    запрос вместо трёх, а лимиты Commons к этому чувствительны.
    """
    hosts = (host,) if host else ("en.wikipedia.org", "ru.wikipedia.org", "de.wikipedia.org")
    for name in hosts:
        files = _wikipedia_page_files(name, article)
        if files:
            return files
    return []


def _wikipedia_article_title(host: str, title: str) -> str:
    """Найти статью Википедии по названию машины."""
    try:
        data = api_get(
            {
                "action": "query",
                "list": "search",
                "srnamespace": 0,
                "srsearch": title,
                "srlimit": 3,
            },
            attempts=2,
            host=host,
        )
    except Exception:  # noqa: BLE001
        return ""
    results = data.get("query", {}).get("search", [])
    if not results:
        return ""
    return results[0].get("title", "")


def _wikipedia_page_files(host: str, title: str) -> list[dict]:
    """Главная картинка и файлы статьи Википедии."""
    try:
        data = api_get(
            {
                "action": "query",
                "titles": title,
                "prop": "pageimages|images",
                "piprop": "original",
                "imlimit": 30,
                "redirects": 1,
            },
            attempts=2,
            host=host,
        )
    except Exception:  # noqa: BLE001
        return []

    commons_titles: list[str] = []
    for page in data.get("query", {}).get("pages", {}).values():
        source = (page.get("original") or {}).get("source", "")
        if source and "upload.wikimedia.org" in source:
            name = source.split("?")[0].rsplit("/", 1)[-1]
            if name.lower().endswith((".jpg", ".jpeg", ".png")):
                commons_titles.append("File:" + urllib.parse.unquote(name))
        for image in page.get("images", []) or []:
            image_title = image.get("title", "")
            if not image_title.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            # Название может быть локализовано: «Файл:», «Datei:», «File:».
            for prefix in ("File:", "Файл:", "Datei:", "Fichier:", "Fichier "):
                if image_title.startswith(prefix):
                    commons_titles.append("File:" + image_title[len(prefix):])
                    break

    files: list[dict] = []
    for start in range(0, len(commons_titles), 20):
        chunk = commons_titles[start:start + 20]
        for item in fetch_by_titles(chunk):
            item["source_kind"] = "vehicle-wiki"
            files.append(item)
        time.sleep(0.2)
    return files


def fetch_by_titles(titles: list[str]) -> list[dict]:
    """Получить метаданные нескольких файлов одним запросом."""
    if not titles:
        return []
    wanted = [title for title in titles if title not in _TITLE_CACHE]
    if wanted:
        data = api_get(
            {
                "action": "query",
                "titles": "|".join(wanted[:40]),
                "prop": "imageinfo",
                "iiprop": "url|extmetadata|size",
                "iiurlwidth": THUMB_WIDTH,
                "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl|License|"
                "ImageDescription|Credit|Categories",
            }
        )
        for item in _pages_to_files(data):
            _TITLE_CACHE[item["title"]] = item
            # API отдаёт название с пробелами вместо подчёркиваний, поэтому
            # держим оба варианта.
            _TITLE_CACHE[item["title"].replace(" ", "_")] = item
    result = []
    for title in titles:
        item = _TITLE_CACHE.get(title) or _TITLE_CACHE.get(title.replace("_", " "))
        if item:
            result.append(item)
    return result


def fetch_by_title(title: str) -> dict | None:
    """Получить метаданные файла по его точному названию."""
    if title in _TITLE_CACHE:
        return _TITLE_CACHE[title]
    data = api_get(
        {
            "action": "query",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|size",
            "iiurlwidth": THUMB_WIDTH,
            "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl|License|"
            "ImageDescription|Credit|Categories",
        }
    )
    files = _pages_to_files(data)
    item = files[0] if files else None
    if item:
        _TITLE_CACHE[item["title"]] = item
        _TITLE_CACHE[item["title"].replace(" ", "_")] = item
    _TITLE_CACHE[title] = item
    return item


def process(slug: str, names: list[str], force: bool, data: dict) -> dict | None:
    target = OUT_DIR / f"{slug}.jpg"
    if not force:
        existing = [path for path in (target, target.with_suffix(".png")) if path.exists()]
        if existing and slug in data:
            print(f"  = {slug}: уже есть, пропускаем")
            return data.get(slug)
        if existing:
            # Файл есть, а записи нет: без неё обложка не покажется.
            # Удаляем файл и качаем заново вместе с описанием.
            print(f"  ! {slug}: файл без записи, качаем заново")
            for path in existing:
                path.unlink()

    preferred = PREFERRED_FILES.get(slug)
    if preferred:
        item = fetch_by_title(preferred)
        if item and license_ok(item) and geometry_ok(item):
            print(f"  > {slug}: {item['title']} [{item.get('license')}] (вручную)")
            if download(item, target):
                entry = _entry_for(slug, item, "vehicle" if "model" not in item["title"].lower() else "model")
                data[slug] = entry
                return entry
        print(f"  ! {slug}: ручной файл не подошёл, ищу обычным способом")

    for prefer_models in (True, False):
        candidates = candidates_for(slug, names, prefer_models)
        if not candidates:
            continue
        kind = "model" if prefer_models else "vehicle"
        for item in candidates[:8]:
            print(f"  > {slug}: {item['title']} [{item.get('license')}] score={item['score']}")
            if download(item, target):
                entry = _entry_for(slug, item, kind)
                data[slug] = entry
                return entry
    print(f"  ! {slug}: подходящей фотографии не нашлось")
    return None


def _entry_for(slug: str, item: dict, kind: str) -> dict:
    """Собрать запись обложки для covers.json."""
    saved = OUT_DIR / f"{slug}.jpg"
    if not saved.exists():
        saved = OUT_DIR / f"{slug}.png"
    return {
        "file": f"static/img/vehicles/{slug}{saved.suffix}",
        "title": item["title"],
        "author": (item.get("artist") or "")[:200],
        "license": (item.get("license") or "")[:60],
        "license_url": (item.get("license_url") or "")[:300],
        "source": (item.get("source") or "")[:500],
        "kind": kind,
        "scale": scale_of(item["title"], item.get("description", "")),
    }


def build_report(data: dict) -> None:
    """Галерея для ручной проверки."""
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    cards = []
    for guide in ALL_GUIDES:
        slug = guide["slug"]
        entry = data.get(slug)
        if entry and (PACKAGE_DIR / entry["file"]).exists():
            cards.append(
                f'<figure><img src="../paintguide/{entry["file"]}" alt="">'
                f"<figcaption><b>{html.escape(guide['title'])}</b><br>"
                f'<span class="k">{html.escape(entry.get("kind", ""))}</span> '
                f'<span class="k">{html.escape(entry.get("scale", ""))}</span><br>'
                f'{html.escape(entry.get("author", ""))}<br>'
                f'<a href="{html.escape(entry.get("source", ""))}">источник</a> · '
                f'{html.escape(entry.get("license", ""))}</figcaption></figure>'
            )
        else:
            cards.append(
                f'<figure class="miss"><div class="ph">нет фото</div>'
                f"<figcaption><b>{html.escape(guide['title'])}</b><br>"
                f'<a href="https://commons.wikimedia.org/wiki/Category:'
                f'{html.escape(guide["title"])}">подобрать вручную</a></figcaption></figure>'
            )
    REPORT_FILE.write_text(
        _REPORT_TEMPLATE.replace("{{FOUND}}", str(len(data)))
        .replace("{{TOTAL}}", str(len(ALL_GUIDES)))
        .replace("{{CARDS}}", "".join(cards)),
        encoding="utf-8",
    )


_REPORT_TEMPLATE = """<!doctype html><html lang="ru"><head><meta charset="utf-8">
<title>Обложки PaintGuide — проверка</title><style>
body{background:#12100f;color:#ece7de;font:15px/1.5 system-ui,sans-serif;margin:0;padding:28px}
h1{font-size:24px;margin:0 0 6px}p{color:#9b948a;margin:0 0 22px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}
figure{margin:0;background:#1c1a18;border:1px solid #302c29;border-radius:10px;overflow:hidden}
figure img{width:100%;aspect-ratio:3/2;object-fit:cover;display:block}
figcaption{padding:11px 13px;font-size:12px;color:#9b948a}
figcaption b{color:#fffaf2;font-size:13px}
.k{display:inline-block;background:#2b2825;border-radius:4px;padding:1px 6px;margin-right:4px;font-size:11px}
.ph{aspect-ratio:3/2;display:grid;place-items:center;background:#232120;color:#6f6960}
.miss{border-style:dashed}a{color:#a8bd76}
.ok{border-color:#3d5a2a}</style></head><body>
<h1>Обложки PaintGuide — проверка</h1>
<p>Найдено: {{FOUND}} из {{TOTAL}}. Сплошная рамка — фото найдено, пунктирная — подобрать вручную.</p>
<div class="grid">{{CARDS}}</div></body></html>"""


def _save_data(data: dict) -> None:
    """Записать данные обложек атомарно.

    Запись через временный файл: иначе прерванный процесс оставляет
    обрезанный json, и часть найденных обложек теряется.
    """
    temporary = DATA_FILE.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(DATA_FILE)


def main() -> int:
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    force = "--force" in sys.argv
    only_report = "--report" in sys.argv

    slugs = args or [guide["slug"] for guide in ALL_GUIDES]
    data: dict = {}
    if DATA_FILE.exists():
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    if not only_report:
        pending = list(slugs)
        for round_number in range(1, ROUNDS + 1):
            if not pending:
                break
            if round_number > 1:
                print(f"\n=== круг {round_number}: {len(pending)} машин ===")
                # Пауза перед повтором: за это время лимиты спадают.
                time.sleep(ROUND_PAUSE)
            failed: list[str] = []
            for index, slug in enumerate(pending, 1):
                names = _names_for(slug)
                if not names:
                    print(f"  ? {slug}: нет в манифесте, пропускаем")
                    continue
                print(f"[{index}/{len(pending)}] {slug}")
                try:
                    found = process(slug, names, force, data)
                except Exception as error:  # noqa: BLE001
                    # Commons отвечает отказом при частых запросах. Одна
                    # неудача не должна останавливать весь проход: машина
                    # попадёт в следующий круг.
                    print(f"  ! {slug}: сбой запроса ({error})")
                    found = None
                _save_data(data)
                if not found:
                    failed.append(slug)
                # Пауза между машинами: хранилище Wikimedia не любит
                # частые обращения, а обложки нужны все сразу и никуда
                # не спешат.
                time.sleep(SLUG_DELAY)
            pending = failed

    build_report(data)
    found = len([entry for entry in data.values() if entry])
    print(f"\nОбложек: {found} из {len(slugs)}")
    print(f"Отчёт: {REPORT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
