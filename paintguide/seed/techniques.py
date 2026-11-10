"""Лестница техник окраски — каркас, по которому собираются все гайды.

За образец взят разбор проекта Warhammer Colour: шаг гайда — это одна
техника окраски, а внутри шага краски привязаны к поверхностям. Одни и те же
поверхности повторяются от шага к шагу: база, тень, проливка и высветление
красят одну и ту же деталь, — поэтому по краске видно, где её искать.

Каждой технике соответствуют:
  * название шага — так его называют в мастерской;
  * текст инструкции — что и в какой последовательности делать, какой
    пропорцией разводить, какой кистью работать и где ошибаются чаще
    всего.

Названия красок в текстах — реальные серии производителей: акрил AK
Interactive 3rd Generation и Real Colors, Model Color и Surface Color
Vallejo, Art Color Pacific88, Mr. Weathering, Scale75, LifeColor. Окраска
должна идти краской одного типа: смешивать 3rd Generation с Model Color
нельзя — они различаются по связующему и по времени высыхания.

Поверхности заданы единым словарём (см. ZONES), чтобы в разных гайдах
одна и та же деталь называлась одинаково.
"""

from __future__ import annotations

# --- Поверхности ------------------------------------------------------------
# Единый словарь: одна и та же деталь во всех гайдах называется одинаково.
ZONES = [
    "Все поверхности",
    "Корпус",
    "Верхние плоскости",
    "Нижние плоскости",
    "Стыки и углубления",
    "Камуфляжные пятна",
    "Кромки деталей",
    "Ходовая часть",
    "Низ и следы",
    "Металл и детали",
    "Дерево и тенты",
    "Оптика и приборы",
    "Знаки",
]

# --- Техники ----------------------------------------------------------------
TECHNIQUES: dict[str, dict[str, str]] = {
    "primer": {
        "title": "Грунт",
        "instruction": (
            "Нанесите {paints} {zones} в два-три тонких слоя, разбавив примерно 1:1 "
            "водой с каплей разбавителя (для акрила — вода и акриловый разбавитель 1:10, "
            "для эмали — растворитель). Дайте высохнуть сутки и при необходимости "
            "зашкурьте наждачной бумагой 800–1200, чтобы убрать пыль и поднять адгезию."
        ),
        "tip": (
            "Грунт кладут тонким слоем: он должен дать адгезию и показать рельеф, "
            "но не залить его. Для современной техники берут серый грунт, для "
            "тевоньих машин — красно-оксидный (AK 3rd Generation, RAL 8012), "
            "для ходовой части — чёрный."
        ),
    },
    "base": {
        "title": "База",
        "instruction": (
            "Нанесите {paints} {zones} в два-три тонких слоя, каждый полностью "
            "просушив (20–30 минут). Слой должен быть как на бумаге: тонкий даёт "
            "ровный цвет, толстый — потёки и «шагрень». Краску разводите водой с "
            "каплей разбавителя, работайте кистью № 6–8 без нажима."
        ),
        "tip": (
            "Красьте краской одного типа: AK Real Colors (RAL, FS) для точного "
            "соответствия оригиналу, Model Color или Art Color — для общего тона. "
            "Проверяйте тон на куске пластика и всегда красьте одну деталь целиком, "
            "не отвлекаясь на другую."
        ),
    },
    "camo": {
        "title": "Камуфляж",
        "instruction": (
            "Нанесите {paints} {zones} поверх высохшей основы: пятна рисуют аэрографом "
            "через трафарет либо жёсткой кистью № 6–8, ведя её «на сухую» и подбирая "
            "цвет в тон. Пятно должно быть чуть больше оригинала — по краям его "
            "подрежут тень и смывка."
        ),
        "tip": (
            "Чёрного контура не делайте: его дадут тень и проливка. Пятна "
            "разбивают по форме деталей, а не «по сетке», и обязательно оставляют "
            "фрагменты базового цвета. Тёплый и холодный оттенки одного цвета "
            "чередуются — так камуфляж читается объёмным."
        ),
    },
    "shade": {
        "title": "Тень (затемнение)",
        "instruction": (
            "Затемните {paints} {zones} в стыках, у приборов наблюдения, под козырьками "
            "и навесами. Держите тон 1:2–1:3 и работайте кистью № 2–4, втягивая "
            "краску в углубления и снимая излишки о край баночки."
        ),
        "tip": (
            "Тень наносится по сухой базе. Классический приём — прешэдинг: чёрный "
            "или тёмно-коричневый разводят 1:5 и кладут заранее, до базы, тогда "
            "тень оказывается под краской и края получаются «мягкими». Второй приём — "
            "тень поверх базы кистью. На металле тень не кладут вовсе: его красят "
            "металликом и сухой кистью."
        ),
    },
    "wash": {
        "title": "Проливка",
        "instruction": (
            "Приготовьте {paints} и разбавьте 1:5–1:10 (для акрила — вода с каплей "
            "разбавителя, для эмали — растворитель). Проведите кистью № 1–2 по швам, "
            "заклёпкам, козырькам и литью, давая краске стечь в углубления. Поверх "
            "засохшей смывки проливку не повторяют."
        ),
        "tip": (
            "Проливка идёт по полностью высохшей базе — минимум сутки, иначе она "
            "размоет краску. Цвет берите тот же тип, что и база, но темнее в "
            "полтора-два раза. Альтернатива — жидкий пигментный фильтр (AK "
            "Weathering Set, Pacific88 Filter, Scale75): он работает по сухой базе "
            "сразу и не требует подбора цвета."
        ),
    },
    "drybrush": {
        "title": "Сухое крашение (драйбраш)",
        "instruction": (
            "Сухой кистью № 4–6, на ворсе которой осталось лишь немного {paints}, "
            "пройдитесь лёгкими движениями {zones}, ловя верхние плоскости и кромки "
            "деталей. Двигайтесь вдоль детали, почти не касаясь её."
        ),
        "tip": (
            "Это техника «наброс»: сухой ворс забирает пигмент только с "
            "выступающих мест. Перед сеансом промойте кисть, оботрите её о "
            "салфетку и слегка смажьте краской — ворс должен быть сухим, а "
            "краска — только на кончике. Тот же приём с мягкой кистью называется "
            "«статинг»."
        ),
    },
    "overbrush": {
        "title": "Овербраш",
        "instruction": (
            "Наложите {paints} {zones} вторым слоем поверх сухой основы — овербраш "
            "выравнивает тон и закрывает пропуски. Работайте полусухой кистью № 6 "
            "с лёгким нажимом, ведя её в одну сторону."
        ),
        "tip": (
            "Слой кладут по сухому грунту или по первой базе, а не «по мокрому»: "
            "второй слой разбавляют сильнее первого (1:2), иначе проступят "
            "запятые. Овербраш — это ещё и способ выровнять разные оттенки "
            "одинаковых деталей, собранных из разных наборов."
        ),
    },
    "tone": {
        "title": "Тонировка (глазурь)",
        "instruction": (
            "Наложите {paints} {zones} общим полупрозрачным тоном, разбавив 1:5–1:8: "
            "глазурь связывает камуфляж в один цвет, но не перекрывает рисунок. "
            "Дайте слою высохнуть и только потом кладите следующий шаг."
        ),
        "tip": (
            "Тон — это прозрачная краска, а не разбавленная база: берите краску "
            "той же серии, но на два-три тона темнее, и разводите сильнее, чем "
            "смывку. Он снимает «пластиковую» яркость и добавляет глубины. "
            "После тонировки камуфляж читается как единый цвет, и наносить "
            "смывку поверх уже не нужно."
        ),
    },
    "highlight": {
        "title": "Контраст (высветление)",
        "instruction": (
            "Осветлите {paints} по центрам крупных плоскостей: смесь базового цвета "
            "с белой в пропорции 1:3–1:5 нанесите полусухой кистью вразброс, "
            "затрагивая середину панели и не заходя в углубления."
        ),
        "tip": (
            "Контраст читается как свет сверху: светлее — верхние плоскости, темнее — "
            "нижние. Второй приём — зенитальное освещение: сначала лёгкий контраст "
            "по всей поверхности, потом основной цвет, а в конце тонкий слой базы "
            "по краям панелей. Работайте мягкой кистью № 8, почти сухой."
        ),
    },
    "edge": {
        "title": "Кромки",
        "instruction": (
            "Подчеркните острые кромки деталей {paints}: возьмите кисть № 00, "
            "слегка смочите её и оботрите о край баночки, чтобы на ворсе осталось "
            "минимум краски. Проведите по грани одним движением, не растирая."
        ),
        "tip": (
            "Кромки работают только на настоящих гранях: плоские участки трогать "
            "нельзя. Сначала высветлите плоскости, потом кромки — иначе свет "
            "съест край. На мелких деталях (болты, петли, фары) кромки не делают "
            "вовсе, иначе деталь рассыпается."
        ),
    },
    "markings": {
        "title": "Знаки и надписи",
        "instruction": (
            "Нанесите {paints} {zones}: тонкие элементы — номера, звёзды, кокарды, "
            "белые полосы — удобнее рисовать кистью № 0 тонким слоем по трафарету "
            "из маскировочной плёнки или по выкройке, крупные — аэрографом через "
            "трафарет. Красьте после матового лака."
        ),
        "tip": (
            "Для белых знаков берите Insignia White (TS-35) — обычная белая краска "
            "желтеет. Номера и надписи удобнее ставить по трафарету, чем рисовать "
            "от руки, и дать им высохнуть, прежде чем браться за следы и пыль: "
            "декали, наоборот, клеят последними, поверх износа."
        ),
    },
    "weathering": {
        "title": "Погодные эффекты (износ)",
        "instruction": (
            "Добавьте {paints} {zones}: пыль и грязь кладите пигментами (AK "
            "Weathering Set, Scale75) или жидкими фильтрами (Mr. Weathering WX, "
            "Pacific88 Filter), потёки тяните вниз кистью № 0, сколы делайте "
            "жёсткой кистью по кромке, ржавчину — только там, где металл "
            "действительно ржавеет."
        ),
        "tip": (
            "Износ читается по вертикали: грязь стекает сверху вниз, пыль садится "
            "на горизонтальных плоскостях, следы от выхлопа тянутся назад по "
            "корме. Проверяйте себя по фотографиям машины в том климате и в том "
            "состоянии, которое вы копируете: у пустынной техники светлая пыль, "
            "у зимней — снег и побелка, у лесной — грязь и мох. Зимние сколы "
            "показывают грунт, летние — ещё и металл."
        ),
    },
    "finish": {
        "title": "Финиш (матовый лак)",
        "instruction": (
            "Закрепите результат матовым лаком (AK Interactive, Vallejo) в два "
            "тонких слоя с расстояния 25–30 см, предварительно убрав пыль мягкой "
            "кистью. Дайте лаку высохнуть, не трогая модель."
        ),
        "tip": (
            "Матовая плёнка гасит блеск пластика и делает цвет глубже — после "
            "лака краска выглядит иначе, поэтому лак кладут до финальной пыли и "
            "последних потёков. Полуглянцевый лак оставляют для оптики, стекла "
            "и резервуаров, а для матовых машин берут именно матовый."
        ),
    },
}

# --- Техники по-английски -----------------------------------------------------
# Названия и тексты шагов переводимы: без них английская версия страницы
# осталась бы русской, хотя интерфейс переведён.
TECHNIQUES_EN: dict[str, dict[str, str]] = {
    "primer": {
        "title": "Primer",
        "instruction": (
            "Apply {paints} {zones} in two or three thin coats, thinned roughly 1:1 "
            "with water and a drop of thinner (for enamels use the matching solvent). "
            "Let it cure for a day and sand back with 800–1200 grit if needed."
        ),
        "tip": (
            "Primer gives adhesion but must not fill the detail: keep the coat thin. "
            "Grey primer for modern vehicles, red oxide (AK 3rd Generation, RAL 8012) "
            "for the interwar and Soviet kits, black for the running gear."
        ),
    },
    "base": {
        "title": "Base coat",
        "instruction": (
            "Apply {paints} {zones} in two or three thin coats, each fully dry "
            "(20–30 minutes). The coat should be paper-thin: thin layers give an "
            "even colour, thick ones give runs and orange peel. Work with a size 6–8 "
            "brush and no pressure."
        ),
        "tip": (
            "Stick to one paint type: AK Real Colors (RAL, FS) for an exact match, "
            "Model Color or Art Color for a general tone. Test the mix on a scrap "
            "of plastic, and always finish one part before starting another."
        ),
    },
    "camo": {
        "title": "Camouflage",
        "instruction": (
            "Apply {paints} {zones} over the dry base coat: airbrush the patches "
            "through a stencil or stipple them with a stiff size 6–8 brush, keeping "
            "the colour close in tone. Make the patches slightly larger than the "
            "original — the shade and wash will trim them back."
        ),
        "tip": (
            "No black outlines: the shade and the wash provide them. Break the "
            "patches up along the shape of the panels rather than on a grid, and "
            "always leave some of the base colour showing. Alternate the warm and "
            "the cool version of a colour so the pattern reads as volume."
        ),
    },
    "shade": {
        "title": "Shade (pre-shading)",
        "instruction": (
            "Darken {paints} {zones} in the panel lines, around the sights, under "
            "the canopies and along the overhangs. Keep the mix at 1:2–1:3 and work "
            "with a size 2–4 brush, letting the colour sink into the recesses and "
            "wiping the surplus off the edge of the jar."
        ),
        "tip": (
            "Shading goes onto a dry base coat. The classic method is pre-shading: "
            "black or dark brown thinned 1:5 and laid down before the base coat, so "
            "the shade ends up under the paint and the edges stay soft. The second "
            "method is to shade over the base coat. Never shade bare metal: it is "
            "painted in metallics and finished with a drybrush."
        ),
    },
    "wash": {
        "title": "Wash",
        "instruction": (
            "Mix {paints} and dilute them 1:5–1:10 (water plus a drop of thinner for "
            "acrylics, solvent for enamels). Run a size 1–2 brush along the seams, "
            "rivets, canopies and castings and let the colour sink into the "
            "recesses. Do not wash twice over a dry wash."
        ),
        "tip": (
            "Wash a fully cured base coat — at least a day, otherwise it washes the "
            "paint back off. Take the colour from the same series as the base, half "
            "to twice as dark. A liquid pigment filter (AK Weathering Set, Pacific88 "
            "Filter, Scale75) is the alternative: it works straight onto a dry base "
            "and takes the guesswork out of the colour."
        ),
    },
    "drybrush": {
        "title": "Drybrush",
        "instruction": (
            "With a dry size 4–6 brush carrying only a trace of {paints}, stroke "
            "gently along {zones} to catch the top surfaces and the edges of the "
            "details. Work along the part, barely touching it."
        ),
        "tip": (
            "This is the stipple technique: dry bristles pick up pigment only on the "
            "raised surfaces. Before you start, wash the brush, wipe it on a tissue "
            "and load just the tip. The same effect with a soft brush is called "
            "stumping."
        ),
    },
    "overbrush": {
        "title": "Overbrush",
        "instruction": (
            "Lay {paints} {zones} as a second coat over the dry base — the "
            "overbrush evens the tone out and closes the gaps. Work with a semi-dry "
            "size 6 brush and light pressure, in one direction."
        ),
        "tip": (
            "The coat goes onto dry primer or onto the first base coat, never onto a "
            "wet one, and it is thinned harder than the base (1:2) or the joins "
            "will show. An overbrush is also the way to match parts from different "
            "kits that came in slightly different shades."
        ),
    },
    "tone": {
        "title": "Glaze",
        "instruction": (
            "Apply {paints} {zones} as a single translucent glaze, thinned 1:5–1:8: "
            "the glaze pulls the camouflage together without hiding the pattern. "
            "Let it dry before the next step."
        ),
        "tip": (
            "A glaze is transparent paint, not thinned base coat: take a colour from "
            "the same series two or three shades darker and thin it far more than "
            "you would a wash. It takes the plastic look off the colours and adds "
            "depth. Once glazed, the camouflage reads as one colour and you no "
            "longer need a wash on top."
        ),
    },
    "highlight": {
        "title": "Contrast (highlight)",
        "instruction": (
            "Lighten {paints} along the centres of the larger panels: mix the base "
            "colour with white at 1:3–1:5 and stipple it on with a semi-dry brush, "
            "staying off the recesses."
        ),
        "tip": (
            "Contrast reads as light from above: lighter on the top surfaces, "
            "darker below. The second method is zenithal lighting — a light contrast "
            "over the whole surface, then the base colour, then a thin coat of base "
            "along the panel edges. Use a soft size 8 brush, nearly dry."
        ),
    },
    "edge": {
        "title": "Edge highlights",
        "instruction": (
            "Pick out the sharp edges of the details with {paints}: take a size 00 "
            "brush, wet it slightly and wipe it on the rim of the jar so that only a "
            "trace of colour is left. Draw the edge in a single stroke, without "
            "rubbing."
        ),
        "tip": (
            "Edge highlights only work on real edges — leave flat areas alone. "
            "Highlight the panels first and the edges afterwards, or the light will "
            "eat the edge. Skip them on small parts (bolts, hinges, headlights), "
            "where they would break the part up."
        ),
    },
    "markings": {
        "title": "Markings",
        "instruction": (
            "Apply {paints} {zones}: thin elements — numbers, stars, roundels, white "
            "stripes — are easier with a size 0 brush on a stencil cut from masking "
            "tape or from the original artwork, large ones with an airbrush through "
            "a stencil. Paint them over matt varnish."
        ),
        "tip": (
            "Use Insignia White (TS-35) for white markings: ordinary white paint "
            "yellows. Stencils beat freehand for numbers and lettering. Let the "
            "markings dry before you add any dust or streaks; decals, on the other "
            "hand, go on last, over the weathering."
        ),
    },
    "weathering": {
        "title": "Weathering",
        "instruction": (
            "Add {paints} {zones}: lay dust and grime with pigments (AK Weathering "
            "Set, Scale75) or liquid filters (Mr. Weathering WX, Pacific88 Filter), "
            "pull the streaks down with a size 0 brush, chip the edges with a stiff "
            "brush and put rust only where the metal really corrodes."
        ),
        "tip": (
            "Weathering reads vertically: dirt runs down, dust settles on horizontal "
            "surfaces, exhaust trails run backwards along the hull. Check yourself "
            "against photographs of the vehicle in the climate and the condition you "
            "are copying: light dust in the desert, snow and whitewash in winter, "
            "mud and moss in the forests. Winter chips show the primer, summer "
            "chips show bare metal as well."
        ),
    },
    "finish": {
        "title": "Finish (matt varnish)",
        "instruction": (
            "Seal the result with matt varnish (AK Interactive, Vallejo) in two thin "
            "coats from 25–30 cm away, after removing the dust with a soft brush. "
            "Let the varnish dry without touching the model."
        ),
        "tip": (
            "The matt film takes the shine off the plastic and makes the colour "
            "deeper — the paint looks different after varnish, so apply the varnish "
            "before the final dust and the last streaks. Keep a satin varnish for "
            "optics, glazing and fuel tanks, and use matt on matt surfaces."
        ),
    },
}

# --- Порядок шагов -----------------------------------------------------------
# Строгая последовательность: грунт → база → камуфляж → тень → проливка →
# сухое крашение → овербраш → тонировка → высветление → кромки → знаки →
# погода → финиш.
#
# Порядок не случаен: сначала закрывают цвет, потом добавляют объём, потом
# износ и в последнюю очередь лак. Нарушать его нельзя — смывка размоет
# невысохшую базу, а пыль ляжет на лак.
TECHNIQUE_ORDER = [
    "primer",
    "base",
    "camo",
    "shade",
    "wash",
    "drybrush",
    "overbrush",
    "tone",
    "highlight",
    "edge",
    "markings",
    "weathering",
    "finish",
]

# Сколько техник показывать на каждом уровне сложности.
DIFFICULTY_TECHNIQUES = {
    "easy": ["primer", "base", "shade", "highlight", "markings", "finish"],
    "medium": [
        "primer", "base", "camo", "shade", "wash", "overbrush", "highlight",
        "markings", "weathering", "finish",
    ],
    "hard": [
        "primer", "base", "camo", "shade", "wash", "drybrush", "overbrush",
        "highlight", "edge", "markings", "weathering", "finish",
    ],
    "expert": [
        "primer", "base", "camo", "shade", "wash", "drybrush", "overbrush",
        "tone", "highlight", "edge", "markings", "weathering", "finish",
    ],
}
