"""Tajika layer for the varshaphal (annual chart) v1: panchavargiya bala, panchadhikaris and varshesha,
sahams, mudda dasha and Tajika (orb-based) aspects.

Conventions (draft, pending scholar review against Tajika Neelakanthi / B.V. Raman's "Varshaphal"):
- Panchavargiya bala: kshetra 30, uchcha 20, hadda 15 (Egyptian terms), drekkana 10 (Parashari 1/5/9 lords),
  navamsa 5; own sign full, friend 3/4, neutral 1/2, enemy 1/4 (natural friendship); uchcha proportional to
  distance from the deep debilitation point.
- Panchadhikaris: muntha lord, birth-lagna lord, varsha-lagna lord, trirashi lord, dina/ratri lord.
  Varshesha = the strongest of these that aspects the varsha lagna by sign (3,5,9,11 friendly; 4,10 half;
  7 full); if none aspects, the strongest overall.
- Sahams: A - B + Lagna for a day return, B - A + Lagna for a night return (not reversed when the formula
  itself contains the Lagna); +30 deg when the Lagna does not lie between B and A.
- Mudda dasha: Vimshottari order from the varsha Moon's nakshatra lord, the 120-year cycle squeezed into the
  365.25-day year, balance from the Moon's position in the nakshatra.
- Tajika aspects: 0/60/90/120/180 within the mean of the two deeptamshas (Sun 15, Moon 12, Mars 8, Mercury 7,
  Jupiter 9, Venus 7, Saturn 9); applying (ithasala) when the separation is closing, else separating (ishrafa).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .constants import DASHA_ORDER, DASHA_YEARS, DEBILITATION, EXALTATION, PLANETS_HI, SIGN_LORDS, SIGNS, SIGNS_HI
from .core import nakshatra_of, navamsa_sign, sign_of
from .strength import ENEMIES, FRIENDS

SEVEN = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
DEEP_EXALT = {"Sun": 10.0, "Moon": 33.0, "Mars": 298.0, "Mercury": 165.0, "Jupiter": 95.0, "Venus": 357.0, "Saturn": 200.0}
DEEPTAMSHA = {"Sun": 15, "Moon": 12, "Mars": 8, "Mercury": 7, "Jupiter": 9, "Venus": 7, "Saturn": 9}
# Egyptian terms (hadda): list of (upper degree bound, lord) per sign
HADDA = [
    [(6, "Jupiter"), (12, "Venus"), (20, "Mercury"), (25, "Mars"), (30, "Saturn")],
    [(8, "Venus"), (14, "Mercury"), (22, "Jupiter"), (27, "Saturn"), (30, "Mars")],
    [(6, "Mercury"), (12, "Jupiter"), (17, "Venus"), (24, "Mars"), (30, "Saturn")],
    [(7, "Mars"), (13, "Venus"), (19, "Mercury"), (26, "Jupiter"), (30, "Saturn")],
    [(6, "Jupiter"), (11, "Venus"), (18, "Saturn"), (24, "Mercury"), (30, "Mars")],
    [(7, "Mercury"), (17, "Venus"), (21, "Jupiter"), (28, "Mars"), (30, "Saturn")],
    [(6, "Saturn"), (14, "Mercury"), (21, "Jupiter"), (28, "Venus"), (30, "Mars")],
    [(7, "Mars"), (11, "Venus"), (19, "Mercury"), (24, "Jupiter"), (30, "Saturn")],
    [(12, "Jupiter"), (17, "Venus"), (21, "Mercury"), (26, "Saturn"), (30, "Mars")],
    [(7, "Mercury"), (14, "Jupiter"), (22, "Venus"), (26, "Saturn"), (30, "Mars")],
    [(7, "Mercury"), (13, "Venus"), (20, "Jupiter"), (25, "Mars"), (30, "Saturn")],
    [(12, "Venus"), (16, "Jupiter"), (19, "Mercury"), (28, "Mars"), (30, "Saturn")],
]
# trirashi lords: element -> (day lord, night lord)
TRIRASHI = {0: ("Sun", "Jupiter"), 1: ("Venus", "Moon"), 2: ("Saturn", "Mercury"), 3: ("Venus", "Mars")}
# sahams: name, hi, A, B, reversed at night?  ("Lagna" and "LagnaLord" are allowed tokens; "Punya" = the punya saham)
SAHAMS = [
    ("Punya", "पुण्य", "Moon", "Sun", True), ("Vidya", "विद्या", "Sun", "Moon", True), ("Yasha", "यश", "Jupiter", "Punya", True),
    ("Mahatmya", "माहात्म्य", "Punya", "Mars", True), ("Asha", "आशा", "Saturn", "Mars", True), ("Samarthya", "सामर्थ्य", "Mars", "LagnaLord", False),
    ("Bhratri", "भ्रातृ", "Jupiter", "Saturn", True), ("Pitri", "पितृ", "Saturn", "Sun", True), ("Matri", "मातृ", "Moon", "Venus", True),
    ("Putra", "पुत्र", "Jupiter", "Moon", True), ("Vivaha", "विवाह", "Venus", "Saturn", True), ("Karma", "कर्म", "Mars", "Mercury", True),
]
ASPECTS = {0: ("conjunction", "युति", "neutral"), 60: ("sextile", "तृतीय-एकादश (60°)", "friendly"), 90: ("square", "चतुर्थ-दशम (90°)", "inimical"),
           120: ("trine", "पंचम-नवम (120°)", "friendly"), 180: ("opposition", "सप्तम (180°)", "inimical")}


def _rel(planet: str, lord: str) -> float:
    if planet == lord:
        return 1.0
    if lord in FRIENDS[planet]:
        return 0.75
    if lord in ENEMIES[planet]:
        return 0.25
    return 0.5


def hadda_lord(lon: float) -> str:
    deg = lon % 30
    for upper, lord in HADDA[sign_of(lon)]:
        if deg < upper:
            return lord
    return HADDA[sign_of(lon)][-1][1]


def drekkana_lord(lon: float) -> str:
    s = sign_of(lon)
    part = int((lon % 30) // 10)
    return SIGN_LORDS[(s + 4 * part) % 12]


def panchavargiya(planet: str, lon: float) -> dict:
    s = sign_of(lon)
    kshetra = 30 * _rel(planet, SIGN_LORDS[s])
    dist = abs((lon - (DEEP_EXALT[planet] + 180.0) + 180.0) % 360.0 - 180.0)   # distance from deep debilitation
    uchcha = 20 * dist / 180.0
    hadda = 15 * _rel(planet, hadda_lord(lon))
    drek = 10 * _rel(planet, drekkana_lord(lon))
    nav = 5 * _rel(planet, SIGN_LORDS[navamsa_sign(lon)])
    total = kshetra + uchcha + hadda + drek + nav
    return {"kshetra": round(kshetra, 2), "uchcha": round(uchcha, 2), "hadda": round(hadda, 2), "drekkana": round(drek, 2), "navamsa": round(nav, 2),
            "total": round(total, 2), "grade": "very strong" if total >= 60 else "strong" if total >= 45 else "medium" if total >= 30 else "weak",
            "grade_hi": "अति बली" if total >= 60 else "बली" if total >= 45 else "मध्यम" if total >= 30 else "निर्बल"}


def _sign_aspect(from_sign: int, to_sign: int) -> str | None:
    d = (to_sign - from_sign) % 12 + 1
    return "full" if d == 7 else "friendly" if d in (3, 5, 9, 11) else "half" if d in (4, 10) else None


def _is_day(sun_lon: float, lagna_lon: float) -> bool:
    """Day when the Sun is above the horizon: in houses 7..12 counted from the Lagna degree."""
    return 180.0 <= (sun_lon - lagna_lon) % 360.0 < 360.0


def _between(x: float, start: float, end: float) -> bool:
    return (x - start) % 360.0 <= (end - start) % 360.0


def sahams(lons: dict, lagna_lon: float, day: bool) -> list[dict]:
    H = lambda n: PLANETS_HI.get(n, n)
    values = {}
    out = []
    lagna_lord = SIGN_LORDS[sign_of(lagna_lon)]
    for name, hi, a, b, rev in SAHAMS:
        def val(tok):
            if tok == "Lagna": return lagna_lon
            if tok == "LagnaLord": return lons[lagna_lord]
            if tok == "Punya": return values["Punya"]
            return lons[tok]
        A, B = val(a), val(b)
        if rev and not day:
            A, B = B, A
        x = (A - B + lagna_lon) % 360.0
        plus30 = not _between(lagna_lon, B, A)
        if plus30:
            x = (x + 30.0) % 360.0
        values[name] = x
        label = lambda t: "लग्न" if t == "Lagna" else "लग्नेश" if t == "LagnaLord" else "पुण्य-सहम" if t == "Punya" else H(t)
        out.append({"name": name, "name_hi": hi, "longitude": round(x, 4), "sign": sign_of(x), "sign_name": SIGNS[sign_of(x)], "sign_name_hi": SIGNS_HI[sign_of(x)],
                    "degree_in_sign": round(x % 30, 2), "formula": f"{a} - {b} + Lagna" + (" (reversed at night)" if rev else ""),
                    "formula_hi": f"{label(a)} − {label(b)} + लग्न" + (" (रात्रि में उलट)" if rev else ""), "plus_30": plus30, "night": not day})
    return out


def mudda_dasha(moon_lon: float, start_utc: datetime, year_days: float = 365.25) -> list[dict]:
    nak = nakshatra_of(moon_lon)
    lord, frac = nak["lord"], nak["fraction"]
    unit = year_days / 120.0
    i0 = DASHA_ORDER.index(lord)
    cur = start_utc
    out = []
    for k in range(10):                       # balance of the first lord, 8 full periods, then the first lord's remainder
        p = DASHA_ORDER[(i0 + k) % 9]
        days = DASHA_YEARS[p] * unit * ((1 - frac) if k == 0 else frac if k == 9 else 1.0)
        if days <= 0.01:
            continue
        end = cur + timedelta(days=days)
        subs, c2 = [], cur
        j0 = DASHA_ORDER.index(p)
        for j in range(9):
            q = DASHA_ORDER[(j0 + j) % 9]
            d2 = days * DASHA_YEARS[q] / 120.0
            subs.append({"lord": q, "lord_hi": PLANETS_HI[q], "start": c2.strftime("%Y-%m-%d"), "end": (c2 + timedelta(days=d2)).strftime("%Y-%m-%d")})
            c2 += timedelta(days=d2)
        out.append({"lord": p, "lord_hi": PLANETS_HI[p], "start": cur.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d"), "days": round(days, 1), "children": subs})
        cur = end
    return out


def tajika_aspects(lons: dict, speeds: dict) -> list[dict]:
    out = []
    for i, a in enumerate(SEVEN):
        for b in SEVEN[i + 1:]:
            sep = abs((lons[a] - lons[b] + 180.0) % 360.0 - 180.0)
            orb = (DEEPTAMSHA[a] + DEEPTAMSHA[b]) / 2.0
            for angle, (name, hi, nature) in ASPECTS.items():
                if abs(sep - angle) <= orb:
                    sep_next = abs((lons[a] + speeds[a] - lons[b] - speeds[b] + 180.0) % 360.0 - 180.0)
                    applying = abs(sep_next - angle) < abs(sep - angle)
                    out.append({"planets": [a, b], "planets_hi": [PLANETS_HI[a], PLANETS_HI[b]], "aspect": name, "aspect_hi": hi, "angle": angle,
                                "nature": nature, "orb": round(abs(sep - angle), 2), "max_orb": orb,
                                "phase": "ithasala" if applying else "ishrafa", "phase_hi": "इत्थशाल (बनता हुआ)" if applying else "ईसराफ (बीतता हुआ)"})
                    break
    return sorted(out, key=lambda x: x["orb"])


def tajika(varsha_chart: dict, natal_lagna_sign: int, muntha_sign: int, speeds: dict, return_utc: datetime) -> dict:
    lons = {p["name"]: p["longitude"] for p in varsha_chart["planets"]}
    lagna_lon = varsha_chart["lagna"]["longitude"]
    lagna_sign = sign_of(lagna_lon)
    day = _is_day(lons["Sun"], lagna_lon)
    bala = {p: panchavargiya(p, lons[p]) for p in SEVEN}
    element = lagna_sign % 4
    cands = {"muntha_lord": SIGN_LORDS[muntha_sign], "birth_lagna_lord": SIGN_LORDS[natal_lagna_sign], "varsha_lagna_lord": SIGN_LORDS[lagna_sign],
             "trirashi_lord": TRIRASHI[element][0 if day else 1], "dina_ratri_lord": SIGN_LORDS[sign_of(lons["Sun"])] if day else SIGN_LORDS[sign_of(lons["Moon"])]}
    ROLE_HI = {"muntha_lord": "मुन्थेश", "birth_lagna_lord": "जन्म-लग्नेश", "varsha_lagna_lord": "वर्ष-लग्नेश", "trirashi_lord": "त्रिराशीश", "dina_ratri_lord": "दिन/रात्रि-पति"}
    rows = []
    for role, p in cands.items():
        asp = _sign_aspect(sign_of(lons[p]), lagna_sign)
        rows.append({"role": role, "role_hi": ROLE_HI[role], "planet": p, "planet_hi": PLANETS_HI[p], "bala": bala[p]["total"], "aspects_lagna": asp})
    aspecting = [r for r in rows if r["aspects_lagna"]]
    pool = aspecting or rows
    best = max(pool, key=lambda r: r["bala"])
    varshesha = best["planet"]
    H = PLANETS_HI
    why_hi = (f"पंचाधिकारी: {', '.join(f'{r['role_hi']} {H[r['planet']]} ({r['bala']})' for r in rows)}। "
              + (f"लग्न को देखने वालों में सबसे बली {H[varshesha]} → वर्षेश।" if aspecting else f"कोई लग्न को नहीं देखता; सबसे बली {H[varshesha]} → वर्षेश।"))
    why_en = (f"Office-bearers: {', '.join(f'{r['role']} {r['planet']} ({r['bala']})' for r in rows)}. "
              + (f"Strongest among those aspecting the Lagna: {varshesha} → year lord." if aspecting else f"None aspects the Lagna; strongest overall {varshesha} → year lord."))
    rule_hi = "पंचाधिकारियों में से, लग्न को देखने वालों में सबसे बली ग्रह वर्षेश है।" if aspecting else "कोई पंचाधिकारी लग्न को नहीं देखता; सबसे बली ग्रह वर्षेश लिया गया।"
    rule_en = "Among the office-bearers, the strongest that aspects the Lagna is the year lord." if aspecting else "No office-bearer aspects the Lagna; the strongest overall is taken as year lord."
    return {"day_return": day, "panchavargiya": bala, "panchadhikaris": rows, "varshesha": varshesha, "varshesha_hi": H[varshesha],
            "varshesha_why_hi": why_hi, "varshesha_why_en": why_en, "varshesha_rule_hi": rule_hi, "varshesha_rule_en": rule_en,
            "sahams": sahams(lons, lagna_lon, day), "mudda_dasha": mudda_dasha(lons["Moon"], return_utc),
            "aspects": tajika_aspects(lons, speeds), "review_status": "draft",
            "note_hi": "ताजिक परत (ड्राफ़्ट): पंचवर्गीय बल, पंचाधिकारी व वर्षेश, 12 सहम, मुद्दा दशा और इत्थशाल/ईसराफ दृष्टियाँ। "
                       "16 ताजिक योग (इक्कबाल, इंदुवार आदि) अभी नहीं जोड़े गए; सूत्र समीक्षा के लिए साथ दिखाए गए हैं।",
            "note_en": "Tajika layer (draft): panchavargiya bala, office-bearers and year lord, 12 sahams, mudda dasha and ithasala/ishrafa aspects. "
                       "The 16 Tajika yogas (Ikkavala, Induvara etc.) are not yet included; formulas are shown for review."}
