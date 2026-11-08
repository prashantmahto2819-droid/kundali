"""Lal Kitab layer (DRAFT): permanent houses, exaltation/debilitation houses and simple traditional remedies.

Two house views are returned because software and schools differ:
  lagna : houses counted from the natal Lagna sign (same as the rest of the app)
  aries : the classical Lal Kitab chart where Mesha is always house 1
Only transparent rules from data/lalkitab.json are used. Texts are tendency language, remedies are
harmless customs, and nothing frightening (debts, curses, doom) is generated.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "lalkitab.json"


@lru_cache(maxsize=1)
def _kb() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def _status(kb: dict, planet: str, house: int) -> str:
    if kb["pakka_ghar"][planet] == house:
        return "pakka"
    if kb["exalt_house"].get(planet) == house:
        return "exalted"
    if kb["debil_house"].get(planet) == house:
        return "debilitated"
    return "other"


def lalkitab(chart: dict) -> dict:
    kb = _kb()
    rows = []
    for p in chart["planets"]:
        n = p["name"]
        views = {}
        for view, house in (("lagna", p["house"]), ("aries", p["sign"] + 1)):
            st = _status(kb, n, house)
            theme = kb["house_theme_hi"][str(house)]
            views[view] = {"house": house, "status": st,
                           "text_hi": kb["status_text_hi"][st].format(p=p["name_hi"], h=house, theme=theme)}
        rows.append({"name": n, "name_hi": p["name_hi"], "pakka_ghar": kb["pakka_ghar"][n],
                     "views": views, "upay_hi": kb["upay_hi"][n]})
    return {"planets": rows, "disclaimer_hi": kb["disclaimer_hi"], "review_status": kb["review_status"],
            "views_note_hi": ("'लग्न' दृश्य में घर जन्म-लग्न से गिने गए हैं; 'मेष' दृश्य में मेष हमेशा पहला घर है "
                              "(लाल किताब की पारंपरिक कुंडली)। दोनों दिखाए गए हैं क्योंकि स्कूलों में मतभेद है.")}


# ---- Varshphal (annual chart) -------------------------------------------------------------------
_VP = Path(__file__).resolve().parents[2] / "data" / "lalkitab_varshphal.json"


def _vp_data() -> dict:
    return json.loads(_VP.read_text(encoding="utf-8"))


def varshphal_house(natal_house: int, year_of_life: int, data: dict | None = None) -> tuple[int, str]:
    """Annual house of a planet for the running year of age (1-120 from the Lal Kitab table; repeats beyond).
    Falls back to the simple rotation only if the table is missing."""
    data = data or _vp_data()
    rows = data.get("rows_by_year") or {}
    y = (year_of_life - 1) % 120 + 1
    row = rows.get(str(y))
    if row and len(row) == 12:
        return int(row[natal_house - 1]), "table"
    return (natal_house - 1 + (year_of_life - 1)) % 12 + 1, "rotation"


def varshphal(chart: dict, year: int | None = None) -> dict:
    """Lal Kitab annual chart for the year of life that starts on the birthday in `year` (default: current)."""
    from datetime import date
    kb = _kb()
    data = _vp_data()
    by = int(chart["input"]["date"][:4])
    bm, bd = int(chart["input"]["date"][5:7]), int(chart["input"]["date"][8:10])
    today = date.today()
    if year is None:
        year = today.year if (today.month, today.day) >= (bm, bd) else today.year - 1
    yol = year - by + 1                                               # year of life beginning on that birthday
    if yol < 1:
        raise ValueError("year is before birth")
    rows, methods = [], set()
    for p in chart["planets"]:
        natal = p["sign"] + 1                                          # Lal Kitab fixed chart: Mesha is always house 1
        h, m = varshphal_house(natal, yol, data)
        methods.add(m)
        st = _status(kb, p["name"], h)
        rows.append({"name": p["name"], "name_hi": p["name_hi"], "natal_house": natal, "annual_house": h, "status": st,
                     "text_hi": kb["status_text_hi"][st].format(p=p["name_hi"], h=h, theme=kb["house_theme_hi"][str(h)]),
                     "upay_hi": kb["upay_hi"][p["name"]]})
    houses = {h: [r["name"] for r in rows if r["annual_house"] == h] for h in range(1, 13)}
    method = "table" if methods == {"table"} else ("mixed" if "table" in methods else "rotation")
    return {"year": year, "year_of_life": yol, "cycle_year": (yol - 1) % 120 + 1, "from": f"{year}-{bm:02d}-{bd:02d}",
            "to": f"{year + 1}-{bm:02d}-{bd:02d}", "planets": rows, "houses": houses, "method": method,
            "review_status": data.get("review_status", "draft") if method == "table" else "unverified",
            "source": data.get("source", ""), "source_typo": data.get("source_typos", {}).get(str((yol - 1) % 120 + 1)),
            "method_note_hi": {"table": "लाल किताब की 120-वर्षीय वर्षफल सारणी से (Astrostudents संकलन; 46वें वर्ष का स्तंभ प्रकाशित उदाहरण से मिलाया गया)।",
                               "mixed": "कुछ ग्रह सत्यापित स्तंभ से, बाक़ी सरल घूर्णन से; मूल सारणी अभी पूरी नहीं भरी।",
                               "rotation": "सरल घूर्णन विधि (हर वर्ष एक घर आगे), जो कई ऑनलाइन कैलकुलेटर उपयोग करते हैं; यह मूल लाल किताब की 35-वर्षीय सारणी नहीं है। मूल सारणी मिलते ही यह बदल दी जाएगी।"}[method],
            "method_note_en": {"table": "From the 120-year Lal Kitab varshphal table (Astrostudents collection; the 46th-year column cross-checked with a published example).",
                               "mixed": "Some planets from a verified column, the rest by simple rotation; the original table is not fully filled yet.",
                               "rotation": "Simple rotation (one house per year) as used by several online calculators; NOT the original Lal Kitab 35-year table. It will be replaced once the original table is entered."}[method],
            "disclaimer_hi": kb["disclaimer_hi"]}
