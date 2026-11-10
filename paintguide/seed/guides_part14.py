"""���� PaintGuide, �? 14: �?�?�>�?�?��, �����?�?��?, �?�?�?�>��? �� �?:��?.

�-��? �? +30 �?��?�, �? �?��?�, �? �?�?� >30 �� ���?�? �? �?�'�?.
�"�?��?� >�'�? <�'�?�? <�?�? �?�'>��?�' �?�>: �? Commons.
"""

from __future__ import annotations

from .guide_kit import G, S, V
from .guides import *  # noqa: F401,F403

PL_FIELD_GREEN = ("70.714", "Field Green")
PL_LIGHT_BLUE = ("70.867", "Japanese Grey")

GUIDES_14 = [
    # ======================= �?�?�>����? ==========================================
    G(
        slug="wz-34",
        title="Samoch�d Pancerny wz. 34",
        subtitle="��� Polish armoured car, 1930s",
        country="poland",
        vtype="armored_car",
        years=(1931, 1939),
        production="Centralne Warsztaty Samochodowe, Warszawa",
        crew="4 crew",
        description="Polish 4x4 armoured car of the 1930s, built on Fiat 621L truck chassis. Armed with 37mm Bofors gun and machine guns. Saw combat in the 1939 campaign.",
        views=60,
        variants=[
            V(
                "easy",
                "Easy: Wz. 34",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply red oxide primer to all surfaces in thin coats.",
                        [(REDOXIDE, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply Polish field grey base coat in two thin layers.",
                        [(AKRC_GERM_GREY, "Корпус"), (BLACK, "Ходовая часть")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply Polish white insignia and tactical numbers.",
                        [(WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust and streaks to lower hull and running gear.",
                        [(EARTH, "Низ и следы"), (DARK_BROWN, "Ходовая часть")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish in two thin coats.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    G(
        slug="wz-29",
        title="Samoch�d Pancerny wz. 29",
        subtitle="Polish armoured car, 1929",
        country="poland",
        vtype="armored_car",
        years=(1929, 1939),
        production="Centralne Warsztaty Samochodowe, Warszawa",
        crew="5 crew",
        description="Polish 6x4 armoured car based on Fiat 621N chassis, armed with Puteaux 37mm gun and Hotchkiss machine guns. Used in the 1939 defensive war.",
        views=55,
        variants=[
            V(
                "easy",
                "Easy: Wz. 29",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply red oxide primer to all surfaces.",
                        [(REDOXIDE, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply grey-green base coat to hull and turret.",
                        [(AKRC_GERM_GREY, "Корпус"), (BLACK, "Ходовая часть")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply white Polish tactical markings.",
                        [(WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust and mud streaks to wheels and lower hull.",
                        [(EARTH, "Низ и следы")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    G(
        slug="c7p",
        title="C7P Artillery Tractor",
        subtitle="Polish half-track artillery tractor",
        country="poland",
        vtype="halftrack",
        years=(1934, 1939),
        production="PZIn��, Warszawa",
        crew="2 crew + 8 soldiers",
        description="Polish half-track artillery tractor designed by Piotr Wilniewczyc, used to tow 75mm and 105mm guns. About 150 built before 1939.",
        views=50,
        variants=[
            V(
                "easy",
                "Easy: C7P",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply red oxide primer to all metal surfaces.",
                        [(REDOXIDE, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply Polish field grey base coat.",
                        [(PL_FIELD_GREEN, "Корпус"), (BLACK, "Ходовая часть")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply white tactical numbers and Polish insignia.",
                        [(WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust to tracks and mud to lower hull.",
                        [(EARTH, "Ходовая часть"), (DARK_BROWN, "Низ и следы")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish in two coats.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    G(
        slug="105mm-wz-29",
        title="105 mm Armata wz. 29",
        subtitle="Polish 105mm field howitzer",
        country="poland",
        vtype="artillery",
        years=(1929, 1939),
        production="Starachowice Works",
        crew="8 crew",
        description="Polish 105mm howitzer based on French Schneider design, main artillery piece of Polish divisions in 1939.",
        views=45,
        variants=[
            V(
                "easy",
                "Easy: 105mm wz. 29",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply red oxide primer to barrel and carriage.",
                        [(REDOXIDE, "Металл и детали")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply field grey base coat to all surfaces.",
                        [(AKRC_GERM_GREY, "Все поверхности")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply white unit markings and serial numbers.",
                        [(WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust and rust streaks to barrel and wheels.",
                        [(EARTH, "Низ и следы"), (RUST, "Металл и детали")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    G(
        slug="tks",
        title="TKS Tankette",
        subtitle="Polish reconnaissance tankette",
        country="poland",
        vtype="tank",
        years=(1931, 1939),
        production="PZIn��, Warszawa",
        crew="2 crew",
        description="Polish tankette based on Carden-Loyd Mk VI, improved with better suspension and armour. About 175 built, used for reconnaissance in 1939.",
        views=50,
        variants=[
            V(
                "easy",
                "Easy: TKS",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply red oxide primer to hull and turret.",
                        [(REDOXIDE, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply Polish field grey base coat.",
                        [(PL_FIELD_GREEN, "Корпус"), (BLACK, "Ходовая часть")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply white Polish tactical markings.",
                        [(WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust and streaks to tracks and hull.",
                        [(EARTH, "Ходовая часть"), (DARK_BROWN, "Низ и следы")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    G(
        slug="tk-3",
        title="TK-3 Tankette",
        subtitle="Polish reconnaissance tankette",
        country="poland",
        vtype="tank",
        years=(1931, 1939),
        production="PZIn��, Warszawa",
        crew="2 crew",
        description="Polish tankette based on Vickers Carden-Loyd Mk VI, early war reconnaissance vehicle. About 100 built.",
        views=45,
        variants=[
            V(
                "easy",
                "Easy: TK-3",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply red oxide primer to all surfaces.",
                        [(REDOXIDE, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply Polish field grey base coat.",
                        [(PL_FIELD_GREEN, "Корпус"), (BLACK, "Ходовая часть")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply white Polish insignia.",
                        [(WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust to tracks and mud streaks.",
                        [(EARTH, "Ходовая часть")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    # ======================= �?��?��? ==========================================
    G(
        slug="cv-33",
        title="Carro Veloce CV-33",
        subtitle="Italian light tankette",
        country="italy",
        vtype="tank",
        years=(1933, 1943),
        production="Ansaldo, Genova",
        crew="2 crew",
        description="Italian light tankette based on Carden-Loyd design, most numerous Italian armoured vehicle of WWII. Used in Spain, North Africa, Balkans and Russia.",
        views=65,
        variants=[
            V(
                "easy",
                "Easy: CV-33",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply red oxide primer to hull and turret.",
                        [(REDOXIDE, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply Italian mottled camouflage base colours.",
                        [(ITALIAN_RED, "Камуфляжные пятна"), (AKRC_GERM_GREY, "Корпус")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply Italian fasces and unit markings.",
                        [(WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add desert dust and sand to hull and tracks.",
                        [(SAND, "Ходовая часть"), (EARTH, "Низ и следы")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    G(
        slug="semovente-75-18",
        title="Semovente 75/18",
        subtitle="Italian 75mm assault gun",
        country="italy",
        vtype="spg",
        years=(1941, 1944),
        production="Ansaldo, Genova",
        crew="4 crew",
        description="Italian self-propelled gun based on M13/40 chassis, armed with 75mm Obice da 75/18 howitzer. Main Italian SPG of WWII.",
        views=70,
        variants=[
            V(
                "easy",
                "Easy: Semovente 75/18",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply red oxide primer to hull and superstructure.",
                        [(REDOXIDE, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply Italian desert camouflage colours.",
                        [(ITALIAN_RED, "Камуфляжные пятна"), (AK_DARK_YELLOW, "Корпус")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply Italian tactical numbers and unit insignia.",
                        [(WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust, sand and exhaust stains to rear hull.",
                        [(SAND, "Низ и следы"), (DARK_BROWN, "Ходовая часть")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    G(
        slug="ab40",
        title="Autoblinda AB40",
        subtitle="Italian armoured car",
        country="italy",
        vtype="armored_car",
        years=(1940, 1943),
        production="Ansaldo, Genova",
        crew="4 crew",
        description="Italian 4x4 armoured car, predecessor of the AB41, armed with two machine guns in turret. Used in North Africa and Balkans.",
        views=50,
        variants=[
            V(
                "easy",
                "Easy: AB40",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply red oxide primer to hull and turret.",
                        [(REDOXIDE, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply Italian desert sand and grey base colours.",
                        [(AK_DARK_YELLOW, "Корпус"), (AKRC_GERM_GREY, "Металл и детали")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply Italian tactical markings and numbers.",
                        [(WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add desert dust and streaks to wheels and hull.",
                        [(SAND, "Ходовая часть"), (EARTH, "Низ и следы")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    G(
        slug="75-27",
        title="Cannone da 75/27",
        subtitle="Italian 75mm field gun",
        country="italy",
        vtype="artillery",
        years=(1927, 1945),
        production="Ansaldo",
        crew="8 crew",
        description="Italian 75mm field gun of WWII, standard artillery piece of Italian divisions. Also used in anti-tank role.",
        views=45,
        variants=[
            V(
                "easy",
                "Easy: 75/27",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply red oxide primer to barrel and carriage.",
                        [(REDOXIDE, "Металл и детали")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply field grey base coat.",
                        [(AKRC_GERM_GREY, "Все поверхности")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply white Italian tactical markings.",
                        [(WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust and rust streaks to barrel and wheels.",
                        [(EARTH, "Низ и следы"), (RUST, "Металл и детали")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    G(
        slug="m11-39",
        title="M11/39",
        subtitle="Italian medium tank",
        country="italy",
        vtype="tank",
        years=(1939, 1942),
        production="Ansaldo, Genova",
        crew="3 crew",
        description="Italian medium tank with hull-mounted 37mm gun, used in North Africa and East Africa. Obsolete by 1941 but saw extensive combat.",
        views=50,
        variants=[
            V(
                "easy",
                "Easy: M11/39",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply red oxide primer to hull and turret.",
                        [(REDOXIDE, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply Italian desert camouflage base colours.",
                        [(AK_DARK_YELLOW, "Корпус"), (ITALIAN_RED, "Камуфляжные пятна")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply Italian fasces and tactical numbers.",
                        [(WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add sand and dust to hull and tracks.",
                        [(SAND, "Ходовая часть"), (EARTH, "Низ и следы")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    # ======================= ������? ==========================================
    G(
        slug="type-4-ho-ro",
        title="Type 4 Ho-Ro",
        subtitle="Japanese 150mm self-propelled gun",
        country="japan",
        vtype="spg",
        years=(1944, 1945),
        production="Mitsubishi Heavy Industries",
        crew="5 crew",
        description="Japanese self-propelled gun based on Type 97 Chi-Ha chassis, armed with 150mm Type 38 howitzer. Late-war infantry support SPG.",
        views=40,
        variants=[
            V(
                "easy",
                "Easy: Type 4 Ho-Ro",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply red oxide primer to hull and superstructure.",
                        [(REDOXIDE, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply Japanese dark green base coat.",
                        [(AK_DARK_GREEN, "Корпус"), (BLACK, "Ходовая часть")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply Japanese tactical markings.",
                        [(INSIGNIA_WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust and mud to hull and tracks.",
                        [(EARTH, "Ходовая часть")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    G(
        slug="type-90-75mm",
        title="Type 90 75mm Field Gun",
        subtitle="Japanese 75mm field artillery",
        country="japan",
        vtype="artillery",
        years=(1930, 1945),
        production="Osaka Arsenal",
        crew="10 crew",
        description="Japanese 75mm field gun, standard artillery piece of Japanese divisions in WWII.",
        views=40,
        variants=[
            V(
                "easy",
                "Easy: Type 90 75mm",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply red oxide primer to barrel and carriage.",
                        [(REDOXIDE, "Металл и детали")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply Japanese field grey base coat.",
                        [(JAP_GREY, "Все поверхности")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply Japanese tactical markings.",
                        [(INSIGNIA_WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust and rust streaks to barrel and wheels.",
                        [(EARTH, "Низ и следы"), (RUST, "Металл и детали")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    G(
        slug="type-94",
        title="Type 94 Tankette",
        subtitle="Japanese reconnaissance tankette",
        country="japan",
        vtype="tank",
        years=(1935, 1943),
        production="Tokyo Gas & Electric",
        crew="2 crew",
        description="Japanese reconnaissance tankette, smallest armoured vehicle of the IJA. Used in China and Pacific islands.",
        views=45,
        variants=[
            V(
                "easy",
                "Easy: Type 94",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply red oxide primer to hull.",
                        [(REDOXIDE, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply Japanese dark green base coat.",
                        [(JAP_GREEN, "Корпус"), (BLACK, "Ходовая часть")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply Japanese hinomaru markings.",
                        [(INSIGNIA_WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust and mud to tracks.",
                        [(EARTH, "Ходовая часть")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    # ======================= �?��?? ==========================================
    G(
        slug="pansarbil-m-39",
        title="Pansarbil m/39",
        subtitle="Swedish armoured car",
        country="sweden",
        vtype="armored_car",
        years=(1939, 1945),
        production="Landsverk",
        crew="4 crew",
        description="Swedish 4x4 armoured car designed by Landsverk, based on Chevrolet chassis. Main Swedish armoured car of WWII.",
        views=50,
        variants=[
            V(
                "easy",
                "Easy: Pansarbil m/39",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply grey primer to hull and turret.",
                        [(AKRC_GERM_GREY, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply Swedish grey-green base coat.",
                        [(GERM_GREY, "Корпус"), (BLACK, "Ходовая часть")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply Swedish yellow-blue insignia.",
                        [(YELLOW, "Знаки"), (BLUE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust to wheels and lower hull.",
                        [(EARTH, "Низ и следы")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    G(
        slug="pansarbil-m-40",
        title="Pansarbil m/40",
        subtitle="Swedish armoured car",
        country="sweden",
        vtype="armored_car",
        years=(1940, 1945),
        production="Landsverk",
        crew="4 crew",
        description="Improved Swedish armoured car with revised turret and armament, based on Chevrolet chassis.",
        views=45,
        variants=[
            V(
                "easy",
                "Easy: Pansarbil m/40",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply grey primer to all surfaces.",
                        [(AKRC_GERM_GREY, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply Swedish grey-green base coat.",
                        [(GERM_GREY, "Корпус"), (BLACK, "Ходовая часть")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply Swedish markings.",
                        [(YELLOW, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust and streaks to hull.",
                        [(EARTH, "Низ и следы")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    G(
        slug="bandkanon-1",
        title="Bandkanon 1",
        subtitle="Swedish 155mm self-propelled artillery",
        country="sweden",
        vtype="spg",
        years=(1967, 1980),
        production="Bofors / Landsverk",
        crew="5 crew",
        description="Swedish self-propelled howitzer on modified Centurion chassis, one of the fastest-firing artillery pieces of its time.",
        views=50,
        variants=[
            V(
                "easy",
                "Easy: Bandkanon 1",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply grey primer to hull and superstructure.",
                        [(AKRC_GERM_GREY, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply Swedish field grey base coat.",
                        [(GERM_GREY, "Корпус"), (BLACK, "Ходовая часть")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply Swedish tactical markings.",
                        [(YELLOW, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust and streaks to tracks.",
                        [(EARTH, "Ходовая часть")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    # ======================= �?����� ==========================================
    G(
        slug="m113-israeli",
        title="M113 (Israel)",
        subtitle="Israeli M113 armoured personnel carrier",
        country="israel",
        vtype="ifv",
        years=(1968, 1990),
        production="FMC / Israel Military Industries",
        crew="2 crew + 11 troops",
        description="Israeli-operated M113 APC, modified with local improvements. Used in Six-Day War, Yom Kippur War and Lebanon operations.",
        views=55,
        variants=[
            V(
                "easy",
                "Easy: M113 (Israel)",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply red oxide primer to hull.",
                        [(REDOXIDE, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply Israeli sand and green camouflage.",
                        [(AK_DARK_YELLOW, "Корпус"), (AK_OLIVE_GREEN, "Камуфляжные пятна")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply Israeli Star of David and tactical numbers.",
                        [(WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add desert dust to hull and tracks.",
                        [(SAND, "Ходовая часть"), (EARTH, "Низ и следы")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    G(
        slug="m50-sherman",
        title="M50 Sherman",
        subtitle="Israeli M50 Super Sherman",
        country="israel",
        vtype="tank",
        years=(1955, 1970),
        production="Israel Military Industries",
        crew="5 crew",
        description="Israeli-upgraded M4 Sherman with French CN-75-50 75mm gun. Main Israeli tank in the 1956 and 1967 wars.",
        views=60,
        variants=[
            V(
                "easy",
                "Easy: M50 Sherman",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply red oxide primer to hull and turret.",
                        [(REDOXIDE, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply Israeli sand base coat.",
                        [(AK_DARK_YELLOW, "Корпус"), (BLACK, "Ходовая часть")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply Israeli insignia and tactical markings.",
                        [(WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add sand and dust to hull.",
                        [(SAND, "Низ и следы")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    # ======================= �?��'���� ==========================================
    G(
        slug="122mm-type-54",
        title="122mm Type 54 Howitzer",
        subtitle="Chinese 122mm field howitzer",
        country="china",
        vtype="artillery",
        years=(1954, 1990),
        production="Norinco, China",
        crew="8 crew",
        description="Chinese-produced copy of the Soviet M-30 122mm howitzer, standard artillery piece of PLA divisions.",
        views=45,
        variants=[
            V(
                "easy",
                "Easy: Type 54 122mm",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply red oxide primer to barrel and carriage.",
                        [(REDOXIDE, "Металл и детали")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply Chinese red-brown base coat.",
                        [(SOVIET_GREEN, "Все поверхности")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply Chinese PLA markings and numbers.",
                        [(WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust and mud to carriage and wheels.",
                        [(EARTH, "Низ и следы")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    G(
        slug="wz-120",
        title="WZ-120",
        subtitle="Chinese main battle tank",
        country="china",
        vtype="tank",
        years=(1970, 1990),
        production="Baoding Machine Factory",
        crew="4 crew",
        description="Chinese main battle tank based on Soviet T-54A design, with 100mm gun. Known as Type 59 in PLA service.",
        views=50,
        variants=[
            V(
                "easy",
                "Easy: WZ-120",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply red oxide primer to hull and turret.",
                        [(REDOXIDE, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply Chinese red-brown base coat.",
                        [(SOVIET_GREEN, "Корпус"), (BLACK, "Ходовая часть")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply Chinese PLA tactical markings.",
                        [(WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust and mud to tracks and hull.",
                        [(EARTH, "Ходовая часть"), (DARK_BROWN, "Низ и следы")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    # ======================= ���?��? ==========================================
    G(
        slug="amr-33",
        title="AMR 33",
        subtitle="French light armoured car",
        country="france",
        vtype="armored_car",
        years=(1933, 1940),
        production="Renault",
        crew="2 crew",
        description="French light armoured car for cavalry reconnaissance, armed with machine gun. Used in the Battle of France 1940.",
        views=45,
        variants=[
            V(
                "easy",
                "Easy: AMR 33",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply grey primer to hull and turret.",
                        [(AKRC_GERM_GREY, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply French dark grey base coat.",
                        [(AK_DARK_GREY, "Корпус"), (BLACK, "Ходовая часть")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply French military markings.",
                        [(WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust to wheels and lower hull.",
                        [(EARTH, "Низ и следы")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    G(
        slug="renault-ue",
        title="Renault UE",
        subtitle="French light tracked tractor",
        country="france",
        vtype="halftrack",
        years=(1932, 1940),
        production="Renault",
        crew="2 crew",
        description="French light tracked armoured tractor used to tow artillery and carry ammunition. Widely used by French and captured German forces.",
        views=45,
        variants=[
            V(
                "easy",
                "Easy: Renault UE",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply grey primer to hull.",
                        [(AKRC_GERM_GREY, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply French grey-blue base coat.",
                        [(AK_LIGHT_GREY, "Корпус"), (BLACK, "Ходовая часть")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply French tactical markings.",
                        [(WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust and mud to tracks.",
                        [(EARTH, "Ходовая часть")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    G(
        slug="r35",
        title="Renault R35",
        subtitle="French light infantry tank",
        country="france",
        vtype="tank",
        years=(1936, 1940),
        production="Renault",
        crew="2 crew",
        description="French light infantry tank, most numerous French tank of 1940. Armed with 37mm gun, used in Battle of France.",
        views=55,
        variants=[
            V(
                "easy",
                "Easy: R35",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply grey primer to hull and turret.",
                        [(AKRC_GERM_GREY, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply French dark grey base coat.",
                        [(AK_DARK_GREY, "Корпус"), (BLACK, "Ходовая часть")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply French military insignia.",
                        [(WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust to tracks and hull.",
                        [(EARTH, "Ходовая часть")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    # ======================= �����?� ==========================================
    G(
        slug="bt-42",
        title="BT-42",
        subtitle="Finnish 114mm self-propelled artillery",
        country="finland",
        vtype="spg",
        years=(1943, 1944),
        production="Finnish Army workshops",
        crew="5 crew",
        description="Finnish self-propelled artillery built on captured Soviet BT-7 chassis, armed with British QF 114mm howitzer. Used against USSR in 1944.",
        views=40,
        variants=[
            V(
                "easy",
                "Easy: BT-42",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply red oxide primer to hull and superstructure.",
                        [(REDOXIDE, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply Finnish olive green base coat.",
                        [(SOVIET_GREEN, "Корпус"), (BLACK, "Ходовая часть")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply Finnish white-blue insignia.",
                        [(WHITE, "Знаки"), (BLUE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add mud and dust to tracks.",
                        [(EARTH, "Ходовая часть"), (DARK_BROWN, "Низ и следы")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    G(
        slug="landsverk-l-180",
        title="Landsverk L-180",
        subtitle="Swedish/Finnish armoured car",
        country="finland",
        vtype="armored_car",
        years=(1935, 1945),
        production="Landsverk",
        crew="4 crew",
        description="Swedish-designed armoured car used by Finnish forces, armed with Madsen 20mm cannon and machine gun.",
        views=40,
        variants=[
            V(
                "easy",
                "Easy: Landsverk L-180",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply grey primer to hull and turret.",
                        [(AKRC_GERM_GREY, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply Finnish olive green base coat.",
                        [(SOVIET_GREEN, "Корпус"), (BLACK, "Ходовая часть")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply Finnish tactical markings.",
                        [(WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust to wheels and hull.",
                        [(EARTH, "Низ и следы")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
    # ======================= �'��>���?�+�?��'���? ==========================================
    G(
        slug="daimler-ac",
        title="Daimler Armoured Car",
        subtitle="British armoured car",
        country="uk",
        vtype="armored_car",
        years=(1941, 1945),
        production="Daimler Company",
        crew="3 crew",
        description="British 4x4 armoured car armed with 2-pounder gun, used in North Africa and NW Europe.",
        views=50,
        variants=[
            V(
                "easy",
                "Easy: Daimler AC",
                "Grunt, base colour, markings, weathering, finish.",
                4,
                default=True,
                steps=[
                    S(
                        "Грунтовка",
                        "Apply grey primer to hull and turret.",
                        [(AKRC_GERM_GREY, "Все поверхности")],
                    ),
                    S(
                        "Базовый цвет",
                        "Apply British desert sand or European grey base coat.",
                        [(BRIT_DARK_KHAKI, "Корпус"), (BLACK, "Ходовая часть")],
                    ),
                    S(
                        "Знаки и надписи",
                        "Apply British tactical markings and squadron insignia.",
                        [(WHITE, "Знаки")],
                    ),
                    S(
                        "Погодные эффекты (износ)",
                        "Add dust and sand to wheels and hull.",
                        [(SAND, "Ходовая часть"), (EARTH, "Низ и следы")],
                    ),
                    S(
                        "Финиш (матовый лак)",
                        "Seal with matt varnish.",
                        (),
                    ),
                ],
            ),
        ],
    ),
]
