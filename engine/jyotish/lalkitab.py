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
