"""Ashtakoota (8-fold, 36-point) kundali matching.

Confidence per koota (shown in the output so nobody over-trusts a number):
  firm   : Varna, Tara, Graha Maitri, Bhakoot, Nadi (widely agreed rules)
  draft  : Vashya, Yoni, Gana (tables differ between sources; verify with a scholar)
Parihara (cancellation) rules for Nadi/Bhakoot are NOT applied automatically.
"""
from __future__ import annotations

from .constants import NAKSHATRAS, SIGNS, SIGN_LORDS
from .core import nakshatra_of, sign_of

# ---- Varna (by Moon sign): Brahmin 4 > Kshatriya 3 > Vaishya 2 > Shudra 1
_VARNA_RANK = {"Brahmin": 4, "Kshatriya": 3, "Vaishya": 2, "Shudra": 1}
_VARNA_OF_SIGN = ["Kshatriya", "Vaishya", "Shudra", "Brahmin", "Kshatriya", "Vaishya",
                  "Shudra", "Brahmin", "Kshatriya", "Vaishya", "Shudra", "Brahmin"]

# ---- Vashya groups
_VASHYA_ORDER = ["Chatushpada", "Manav", "Jalachara", "Vanachara", "Keeta"]
_VASHYA_MATRIX = [  # draft, symmetric
    [2, 1, 1, 0.5, 1],
    [1, 2, 0.5, 0, 1],
    [1, 0.5, 2, 1, 1],
    [0.5, 0, 1, 2, 0],
    [1, 1, 1, 0, 2],
]


def vashya_group(moon_lon: float) -> str:
    s = sign_of(moon_lon)
    deg = moon_lon % 30
    if s in (0, 1):
        return "Chatushpada"
    if s == 8:  # Dhanu: first half human, second half quadruped
        return "Manav" if deg < 15 else "Chatushpada"
    if s == 9:  # Makara: first half quadruped, second half water
        return "Chatushpada" if deg < 15 else "Jalachara"
    if s in (2, 5, 6, 10):
        return "Manav"
    if s in (3, 11):
        return "Jalachara"
    if s == 4:
        return "Vanachara"
    return "Keeta"  # Vrishchika


# ---- Yoni (animal by nakshatra) and compatibility matrix (draft, symmetric)
_YONI_ORDER = ["Horse", "Elephant", "Sheep", "Serpent", "Dog", "Cat", "Rat", "Cow",
               "Buffalo", "Tiger", "Deer", "Monkey", "Mongoose", "Lion"]
_NAK_YONI = ["Horse", "Elephant", "Sheep", "Serpent", "Serpent", "Dog", "Cat", "Sheep",
             "Cat", "Rat", "Rat", "Cow", "Buffalo", "Tiger", "Buffalo", "Tiger", "Deer",
             "Deer", "Dog", "Monkey", "Mongoose", "Monkey", "Lion", "Horse", "Lion",
             "Cow", "Elephant"]
_YONI_MATRIX = [
    [4, 2, 2, 3, 2, 2, 2, 1, 0, 1, 3, 3, 2, 1],
    [2, 4, 3, 3, 2, 2, 2, 2, 3, 1, 2, 3, 2, 0],
    [2, 3, 4, 2, 1, 2, 1, 3, 3, 1, 2, 0, 3, 1],
    [3, 3, 2, 4, 2, 1, 1, 1, 1, 2, 2, 2, 0, 2],
    [2, 2, 1, 2, 4, 2, 1, 2, 2, 1, 0, 2, 1, 1],
    [2, 2, 2, 1, 2, 4, 0, 2, 2, 1, 3, 3, 2, 1],
    [2, 2, 1, 1, 1, 0, 4, 2, 2, 2, 2, 2, 1, 2],
    [1, 2, 3, 1, 2, 2, 2, 4, 3, 0, 3, 2, 2, 1],
    [0, 3, 3, 1, 2, 2, 2, 3, 4, 1, 2, 2, 2, 1],
    [1, 1, 1, 2, 1, 1, 2, 0, 1, 4, 1, 1, 2, 1],
    [3, 2, 2, 2, 0, 3, 2, 3, 2, 1, 4, 2, 2, 1],
    [3, 3, 0, 2, 2, 3, 2, 2, 2, 1, 2, 4, 3, 2],
    [2, 2, 3, 0, 1, 2, 1, 2, 2, 2, 2, 3, 4, 2],
    [1, 0, 1, 2, 1, 1, 2, 1, 1, 1, 1, 2, 2, 4],
]

# ---- Gana by nakshatra index
_GANA = ["Deva", "Manushya", "Rakshasa", "Manushya", "Deva", "Manushya", "Deva", "Deva",
         "Rakshasa", "Rakshasa", "Manushya", "Manushya", "Deva", "Rakshasa", "Deva",
         "Rakshasa", "Deva", "Rakshasa", "Rakshasa", "Manushya", "Manushya", "Deva",
         "Rakshasa", "Rakshasa", "Manushya", "Manushya", "Deva"]
# (bride, groom) -> points. Orientation differs between sources: draft.
_GANA_SCORE = {("Deva", "Deva"): 6, ("Deva", "Manushya"): 5, ("Deva", "Rakshasa"): 1,
               ("Manushya", "Deva"): 6, ("Manushya", "Manushya"): 6, ("Manushya", "Rakshasa"): 0,
               ("Rakshasa", "Deva"): 0, ("Rakshasa", "Manushya"): 0, ("Rakshasa", "Rakshasa"): 6}

# ---- Natural planetary friendship (Parashari)
_FRIEND = {"Sun": {"Moon", "Mars", "Jupiter"}, "Moon": {"Sun", "Mercury"},
           "Mars": {"Sun", "Moon", "Jupiter"}, "Mercury": {"Sun", "Venus"},
           "Jupiter": {"Sun", "Moon", "Mars"}, "Venus": {"Mercury", "Saturn"},
           "Saturn": {"Mercury", "Venus"}}
_ENEMY = {"Sun": {"Venus", "Saturn"}, "Moon": set(), "Mars": {"Mercury"},
          "Mercury": {"Moon"}, "Jupiter": {"Mercury", "Venus"},
          "Venus": {"Sun", "Moon"}, "Saturn": {"Sun", "Moon", "Mars"}}


def _relation(a: str, b: str) -> str:
    if b in _FRIEND[a]:
        return "friend"
    if b in _ENEMY[a]:
        return "enemy"
    return "neutral"


_MAITRI = {("friend", "friend"): 5, ("friend", "neutral"): 4, ("neutral", "friend"): 4,
           ("neutral", "neutral"): 3, ("friend", "enemy"): 1, ("enemy", "friend"): 1,
           ("neutral", "enemy"): 0.5, ("enemy", "neutral"): 0.5, ("enemy", "enemy"): 0}

_NADI = ["Adi", "Madhya", "Antya", "Antya", "Madhya", "Adi"]  # repeats every 6 nakshatras


def _ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _koota(name, name_hi, got, mx, detail, confidence):
    return {"name": name, "name_hi": name_hi, "score": got, "max": mx,
            "detail": detail, "confidence": confidence}


def ashtakoota(boy_moon: float, girl_moon: float) -> dict:
    """``*_moon`` = sidereal Moon longitude of groom and bride."""
    bn, gn = nakshatra_of(boy_moon), nakshatra_of(girl_moon)
    bs, gs = sign_of(boy_moon), sign_of(girl_moon)
    kootas = []

    # 1 Varna
    bv, gv = _VARNA_OF_SIGN[bs], _VARNA_OF_SIGN[gs]
    kootas.append(_koota("Varna", "वर्ण", 1 if _VARNA_RANK[bv] >= _VARNA_RANK[gv] else 0, 1,
                         f"groom {bv}, bride {gv}; points when groom's varna is equal or higher", "firm"))

    # 2 Vashya
    bg, gg = vashya_group(boy_moon), vashya_group(girl_moon)
    kootas.append(_koota("Vashya", "वश्य", _VASHYA_MATRIX[_VASHYA_ORDER.index(gg)][_VASHYA_ORDER.index(bg)], 2,
                         f"groom {bg}, bride {gg}", "draft"))

    # 3 Tara (counted both ways from nakshatra to nakshatra, remainder of count/9)
    def tara_ok(frm: int, to: int) -> bool:
        count = (to - frm) % 27 + 1
        return (count % 9) not in (3, 5, 7)
    t1, t2 = tara_ok(gn["index"], bn["index"]), tara_ok(bn["index"], gn["index"])
    kootas.append(_koota("Tara", "तारा", 3 if t1 and t2 else (1.5 if t1 or t2 else 0), 3,
                         f"bride→groom {'good' if t1 else 'inauspicious'}, groom→bride {'good' if t2 else 'inauspicious'}",
                         "firm"))

    # 4 Yoni
    by, gy = _NAK_YONI[bn["index"]], _NAK_YONI[gn["index"]]
    kootas.append(_koota("Yoni", "योनि", _YONI_MATRIX[_YONI_ORDER.index(by)][_YONI_ORDER.index(gy)], 4,
                         f"groom {by}, bride {gy}", "draft"))

    # 5 Graha Maitri (moon-sign lords)
    bl, gl = SIGN_LORDS[bs], SIGN_LORDS[gs]
    if bl == gl:
        pts, why = 5, f"same lord {bl}"
    else:
        r1, r2 = _relation(bl, gl), _relation(gl, bl)
        pts, why = _MAITRI[(r1, r2)], f"{bl}→{gl}: {r1}; {gl}→{bl}: {r2}"
    kootas.append(_koota("Graha Maitri", "ग्रह मैत्री", pts, 5, why, "firm"))

    # 6 Gana
    bgn, ggn = _GANA[bn["index"]], _GANA[gn["index"]]
    kootas.append(_koota("Gana", "गण", _GANA_SCORE[(ggn, bgn)], 6,
                         f"groom {bgn}, bride {ggn} (orientation of the table varies by source)", "draft"))

    # 7 Bhakoot (Moon-sign distance 2/12, 5/9, 6/8 are inauspicious)
    d = (gs - bs) % 12 + 1
    bad = d in (2, 12, 5, 9, 6, 8)
    kootas.append(_koota("Bhakoot", "भकूट", 0 if bad else 7, 7,
                         f"bride's Moon sign is {_ordinal(d)} from groom's ({SIGNS[bs]} / {SIGNS[gs]})"
                         + ("; inauspicious pair" if bad else ""), "firm"))

    # 8 Nadi
    bnadi, gnadi = _NADI[bn["index"] % 6], _NADI[gn["index"] % 6]
    kootas.append(_koota("Nadi", "नाड़ी", 0 if bnadi == gnadi else 8, 8,
                         f"groom {bnadi}, bride {gnadi}" + ("; same nadi" if bnadi == gnadi else ""), "firm"))

    total = sum(k["score"] for k in kootas)
    if total < 18:
        band_en, band_hi = "below the traditional minimum of 18", "पारंपरिक न्यूनतम 18 से कम"
    elif total < 25:
        band_en, band_hi = "acceptable (18-24)", "स्वीकार्य (18-24)"
    elif total < 33:
        band_en, band_hi = "good (25-32)", "अच्छा (25-32)"
    else:
        band_en, band_hi = "excellent (33+)", "उत्तम (33+)"
    return {
        "total": total, "max": 36, "band_en": band_en, "band_hi": band_hi, "kootas": kootas,
        "groom": {"moon_sign": SIGNS[bs], "nakshatra": bn["name"], "nakshatra_hi": bn["name_hi"], "pada": bn["pada"]},
        "bride": {"moon_sign": SIGNS[gs], "nakshatra": gn["name"], "nakshatra_hi": gn["name_hi"], "pada": gn["pada"]},
        "caution": ("The score is one traditional lens. It ignores the rest of both charts (dashas, 7th house, "
                    "strengths) and auto-applies no parihara. Koota marked 'draft' are pending scholar review."),
    }


def manglik_from(mars_house_lagna: int, mars_sign: int, moon_sign: int) -> dict:
    from_moon = (mars_sign - moon_sign) % 12 + 1
    bad = {1, 4, 7, 8, 12}
    return {"from_lagna": mars_house_lagna in bad, "from_moon": from_moon in bad,
            "mars_house_from_lagna": mars_house_lagna, "mars_house_from_moon": from_moon}


def compare_manglik(boy: dict, girl: dict) -> dict:
    b = boy["from_lagna"] or boy["from_moon"]
    g = girl["from_lagna"] or girl["from_moon"]
    if b == g:
        note = "Both are manglik by at least one count." if b else "Neither is manglik by lagna or Moon count."
        level = "balanced"
    else:
        note = "Only one partner is manglik; traditionally this calls for a closer look at cancellations."
        level = "check"
    return {"boy": boy, "girl": girl, "level": level, "note": note,
            "caution": "Schools differ (2nd house, from Venus, cancellations); this is the simple lagna/Moon count."}
