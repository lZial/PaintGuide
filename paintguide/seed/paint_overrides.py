"""Соответствие «краска в гайде» → «позиция каталога».

Ручной список красок описывает их привычными модельными именами
(«Red Oxide», «Field Green»), а в каталоге производителей те же краски
названы иначе, а у части линеек номера перенумерованы: например, AK11008
в каталоге — это «Grimy Grey», тогда как в гайдах им помечен
красно-оксидный грунт.

Здесь задано явное соответствие для цветов, которые используются в гайдах.
Ключ — «код|название» из гайдов, значение — «код|название» из каталога.
Отобраны позиции с близким образцом цвета, чтобы тон не «уехал».
"""

from __future__ import annotations

OVERRIDES: dict[str, str] = {
    # --- Tamiya ---------------------------------------------------------
    # У Tamiya номера XF соответствуют реальным краскам производителя,
    # поэтому «Flat Red» — это XF-7, «Flat Yellow» — XF-3 и так далее.
    "XF-1|Black": "XF-1|Flat black",
    "XF-3|Flat Red": "XF-7|Flat Red",
    "XF-4|Flat Yellow": "XF-3|Flat Yellow",
    "XF-5|Flat Green": "XF-5|Flat Green",
    "XF-6|Flat Orange": "TS-31|Bright Orange",
    "XF-10|Flat Red": "XF-7|Flat Red",
    "XF-15|Flat Green": "XF-4|Yellow Green",
    "XF-16|Flat Green": "XF-4|Yellow Green",
    "XF-17|Gloss Aluminum": "TS-17|Gloss Aluminium",
    "XF-18|Pure Red": "XF-7|Flat Red",
    "XF-19|Pure Blue": "XF-8|Flat Blue",
    "XF-20|Pure Green": "XF-5|Flat Green",
    "XF-22|Pure Yellow": "XF-3|Flat Yellow",
    "XF-23|Flat Black": "XF-1|Flat black",
    "XF-24|Flat Grey": "XF-24|Dark Grey",
    "XF-33|Gun Metal": "XF-33|Gun Metal",
    "XF-49|Khaki": "XF-49|Khaki",
    "XF-56|Flat NATO Green": "XF-67|NATO Green",
    "XF-57|Flat Black Green": "XF-96|Flat Black Green",
    "XF-58|Olive Drab": "XF-62|Olive Drab",
    "XF-60|Flat Red": "XF-7|Flat Red",
    "XF-64|Flat Red-Orange": "XF-28|Dark Copper",
    "XF-66|Flat Light Grey": "XF-66|Light Grey",
    "XF-68|NATO Grey": "XF-25|Light Sea Grey",
    "XF-70|Dark Yellow": "XF-60|Dark Yellow",
    "XF-72|Dark Green": "XF-95|Dark Green",
    "XF-74|Flat Tan": "XF-57|Buff",
    "XF-75|NATO Green": "XF-67|NATO Green",
    "XF-77|Italian Red": "TS-8|Italian Red",
    "XF-78|Flat Sand": "XF-55|Deck Tan",
    "XF-79|Flat Khaki": "XF-49|Khaki",
    "XF-80|Gloss Black": "XF-1|Flat black",
    "XF-81|Gloss Red": "XF-7|Flat Red",
    "XF-84|Gloss Yellow": "XF-3|Flat Yellow",
    "XF-86|Gloss White": "XF-2|Flat White",
    "TS-1|Red Brown": "TS-1|Red Brown",
    "TS-4|German Gray": "TS-4|German Grey",
    "TS-9|British Racing Green": "XF-27|Black Green",
    "TS-17|Gloss Aluminum": "TS-17|Gloss Aluminium",
    "TS-27|Matt Yellow": "TS-16|Yellow",
    "TS-28|Olive Drab": "TS-28|Olive Drab 2",
    "TS-32|Haze Gray": "TS-32|Haze Grey",
    "TS-33|Red": "TS-33|Dull Red",
    "TS-35|Insignia White": "LP-35|Insignia White",
    "TS-36|Insignia Yellow": "TS-16|Yellow",
    "TS-46|Light Gray": "LP-34|Light Gray",
    "TS-51|Mock Sand": "TS-46|Light Sand",
    "TS-52|Flat Earth": "XF-52|Flat Earth",
    "TS-54|Dark Brown": "TS-62|NATO Brown",
    "TS-55|Dark Green": "XF-95|Dark Green",
    "TS-56|Flat White": "XF-2|Flat White",
    # --- Vallejo ---------------------------------------------------------
    # У кодов 70.7xx/70.8xx в выкачанных данных номера смещены: там
    # лежат краски Game Color. Настоящие позиции ищем по смыслу и оттенку.
    "70.601|White": "70.820|Off-White - FS17925",
    "70.602|Black": "70.861|Glossy Black - FS17038",
    "70.606|Pure Red": "70.606|Pure Red",
    "70.608|Pure Yellow": "70.608|Pure Yellow",
    "70.664|Matt Light Olive": "70.664|Matt Light Olive",
    "70.700|British Racing Green": "70.700|British Racing Green",
    "70.703|German Green": "70.703|German Green",
    "70.705|German Grey": "70.705|German Grey",
    "70.706|Russian Green": "70.706|Russian Green",
    "70.708|Light Blue Grey": "70.708|Light Blue Grey",
    "70.709|English Grey": "70.709|English Grey",
    "70.714|Field Green": "70.714|Field Green",
    "70.715|Olive Drab": "70.715|Olive Drab",
    "70.727|NATO Green": "70.727|NATO Green",
    "70.800|Pure Red": "70.606|Pure Red",
    "70.801|US Army Olive Drab": "70.889|USA Olive Drab  - FS34084",
    "70.803|US Army Field Drab": "70.873|US Field Drab - FS30118",
    "70.804|US Army Sand": "70.716|Sand",
    "70.808|US Army Blue Grey": "70.708|Light Blue Grey",
    "70.809|British RTS Dark Khaki": "70.889|USA Olive Drab  - FS34084",
    "70.810|British RTS Field Khaki": "70.873|US Field Drab - FS30118",
    "70.814|British RTS Dark Green": "70.714|Field Green",
    "70.831|German Panzer Grey": "70.705|German Grey",
    "70.833|Soviet Green": "70.706|Russian Green",
    "70.867|Japanese Grey": "70.992|Neutral Grey - FS36173",
    "70.868|Desert Yellow": "70.978|Dark Yellow - FS33440 - RAL 7028",
    "70.878|Dark Yellow": "70.978|Dark Yellow - FS33440 - RAL 7028",
    "70.879|Sand": "70.716|Sand",
    "70.924|Ivory": "70.918|Ivory - FS37855 - RAL 9001",
    "70.947|Red Brown": "70.647|Matt Brown",
    "72.152|Flat White": "70.820|Off-White - FS17925",
    "72.171|Flat Pale Grey": "72.171|Flat Pale Grey",
    # --- AK Interactive ---------------------------------------------------
    # Номера AK 3rd Generation перенумерованы: в каталоге AK11008 —
    # это «Grimy Grey», а красно-оксидный грунт лежит под другим номером.
    "AK11008|Red Oxide": "AK180|Primer Red",
    "AK11009|Yellow Ochre": "AK11118|Ochre - Standard",
    "AK11010|Blue": "AK11179|Ultramarine - Standard",
    "AK11015|Dark Green": "AK11146|Dark Green - Standard",
    "AK11016|Light Green": "AK11141|Light Green - Standard",
    "AK11020|Pale Blue": "AK11161|Pale Blue - Standard",
    "AK11022|Light Grey": "AK11013|Pale Grey - Standard",
    "AK11026|German Dark Yellow": "AK11044|Yellow - Standard",
    "AK11035|Field Green": "AK11875|FIELD GREEN FS 34097",
    "AK11039|Desert Sand": "AK11340|Nº13 Desert Sand (FS30279)",
    "AK11040|Red Brown": "AK11064|Beige Red - Standard",
    "AK11054|Bright Red": "AK11087|Scarlet Red - Standard",
    "AK11059|Brown": "AK11104|Saddle Brown - Standard",
    "AK11080|Dark Brown": "AK11109|Dark Brown - Standard",
    "AK11107|Rust": "AK11107|Dark Rust - Standard",
    "AK11141|Pale Sand": "AK11032|Pale Sand - Standard",
    # --- Lifecolor -------------------------------------------------------
    "LC-11|German Grey": "LC-11|German Grey",
    "LC-14|Russian Green": "LC-14|Russian Green",
    "LC-15|US Army Olive Drab": "LC-15|US Army Olive Drab",
    "LC-21|Gun Metal": "LC-21|Gun Metal",
    "LC-25|Aluminum": "LC-25|Aluminum",
    "LC-30|Rubber Black": "LC-30|Rubber Black",
    "LC-33|Track Steel": "LC-33|Track Steel",
    # --- Scale75 ---------------------------------------------------------
    "SG-001|Russian Green": "SG-001|Russian Green",
    "SG-002|Olive Green": "SG-002|Olive Green",
    "SG-101|German Dark Yellow": "SG-101|German Dark Yellow",
    "SG-103|British Khaki": "SG-103|British Khaki",
    "SG-107|Japanese Green": "SG-107|Japanese Green",
    "SG-115|White": "SG-115|White",
    "SG-116|Black": "SG-116|Black",
    "SG-121|US Army Olive Drab": "SG-121|US Army Olive Drab",
    "SG-133|Italian Red": "SG-133|Italian Red",
    # --- Mr. Color -------------------------------------------------------
    "CMC-10|Khaki Green": "CMC-10|Khaki Green",
    # --- Pacific88 -------------------------------------------------------
    "F-84|Red Oxide": "F-84|Oxide red",
}
