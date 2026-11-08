"""Partial planetary strength (a subset of Shadbala, in virupas; 60 virupas = 1 rupa).

Components implemented, all from classical definitions:
  * Uccha bala     : distance from the debilitation point divided by 3 (0-60)
  * Dig bala       : 60 at the planet's directionally strong point, 0 at the opposite point
  * Kendradi bala  : 60 in a kendra, 30 in a panaphara (2,5,8,11), 15 in an apoklima (3,6,9,12)
  * Naisargika bala: fixed natural strength
NOT implemented yet: Kala bala (day/night, tithi, weekday, hora and more), Cheshta bala, Drik bala,
Saptavargaja and Ojayugma bala. So this is NOT the full Shadbala and must not be compared with its
minimum-requirement tables. The strong points use the Lagna and 90-degree steps as an approximation
of the 4th/7th/10th cusps.
"""
from __future__ import annotations

SEVEN = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
EXALT_POINT = {"Sun": 10.0, "Moon": 33.0, "Mars": 298.0, "Mercury": 165.0, "Jupiter": 95.0,
               "Venus": 357.0, "Saturn": 200.0}
STRONG_HOUSE = {"Sun": 10, "Mars": 10, "Jupiter": 1, "Mercury": 1, "Moon": 4, "Venus": 4, "Saturn": 7}
NAISARGIKA = {"Sun": 60.0, "Moon": 51.43, "Venus": 42.86, "Jupiter": 34.29,
              "Mercury": 25.71, "Mars": 17.14, "Saturn": 8.57}


def _arc(a: float, b: float) -> float:
    """Shortest angular distance, 0..180."""
    d = abs(a - b) % 360.0
    return 360.0 - d if d > 180.0 else d


def uccha_bala(planet: str, lon: float) -> float:
    debil = (EXALT_POINT[planet] + 180.0) % 360.0
    return _arc(lon, debil) / 3.0


def dig_bala(planet: str, lon: float, lagna_lon: float) -> float:
    strong_point = (lagna_lon + {1: 0.0, 4: 90.0, 7: 180.0, 10: 270.0}[STRONG_HOUSE[planet]]) % 360.0
    return 60.0 * (180.0 - _arc(lon, strong_point)) / 180.0


def kendradi_bala(house: int) -> float:
    if house in (1, 4, 7, 10):
        return 60.0
    if house in (2, 5, 8, 11):
        return 30.0
    return 15.0


def strength(chart: dict) -> dict:
    lagna_lon = chart["lagna"]["longitude"]
    rows = []
    for p in chart["planets"]:
        n = p["name"]
        if n not in SEVEN:
            continue
        parts = {"uccha": uccha_bala(n, p["longitude"]), "dig": dig_bala(n, p["longitude"], lagna_lon),
                 "kendradi": kendradi_bala(p["house"]), "naisargika": NAISARGIKA[n]}
        rows.append({"name": n, "name_hi": p["name_hi"], **{k: round(v, 2) for k, v in parts.items()},
                     "total": round(sum(parts.values()), 2)})
    order = sorted(rows, key=lambda r: -r["total"])
    for i, r in enumerate(order, 1):
        r["rank"] = i
    return {"planets": rows, "max_possible": 240.0, "unit": "virupa",
            "complete": False,
            "missing_hi": "कालबल, चेष्टाबल, दृग्बल और सप्तवर्गज बल अभी शामिल नहीं हैं, इसलिए यह पूर्ण षड्बल नहीं है।",
            "why_hi": ("उच्चबल: ग्रह अपने उच्च बिंदु से जितना पास, उतना अधिक। दिग्बल: ग्रह अपनी बलवान दिशा "
                       "(सूर्य-मंगल दशम, गुरु-बुध लग्न, चंद्र-शुक्र चतुर्थ, शनि सप्तम) के पास हो तो अधिक। "
                       "केंद्रादि बल: केंद्र में 60, पणफर में 30, आपोक्लिम में 15। नैसर्गिक बल: हर ग्रह का स्थिर बल।"),
            "confidence": "draft"}
