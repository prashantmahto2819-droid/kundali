"""Planetary strength: most of Shadbala, in virupas (60 virupas = 1 rupa).  DRAFT, flagged `complete: false`.

Implemented (classical definitions, see why_hi in the output):
  Sthana bala  : uccha, saptavargaja (D1, hora, drekkana, saptamsa, navamsa, dwadasamsa, trimsamsa), ojayugma,
                 kendradi, drekkana
  Dig bala     : directional strength (cusps approximated by the Lagna and 90-degree steps)
  Kala bala    : natonnata, paksha, tribhaga, vara, hora, ayana
  Cheshta bala : ONLY for Sun (= ayana bala) and Moon (= paksha bala), as the classics say
  Naisargika   : fixed
  Drik bala    : (benefic - malefic aspects received) / 4, with the standard virupa aspect formula
NOT implemented: Cheshta bala of Mars..Saturn (needs planetary motion), abda bala, masa bala, yuddha bala.
Because of that, totals must NOT be compared with the classical minimum-requirement tables; use them
only to compare planets within one chart. Assumptions that traditions differ on (benefic/malefic
classification of Mercury, doubling of the Sun's ayana bala, ayana from the ecliptic longitude without
latitude) are listed in `assumptions`.
"""
from __future__ import annotations

import math

from .constants import EXALTATION, OWN_SIGNS, SIGN_LORDS
from .vargas import varga_sign

SEVEN = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
EXALT_POINT = {"Sun": 10.0, "Moon": 33.0, "Mars": 298.0, "Mercury": 165.0, "Jupiter": 95.0,
               "Venus": 357.0, "Saturn": 200.0}
STRONG_HOUSE = {"Sun": 10, "Mars": 10, "Jupiter": 1, "Mercury": 1, "Moon": 4, "Venus": 4, "Saturn": 7}
NAISARGIKA = {"Sun": 60.0, "Moon": 51.43, "Venus": 42.86, "Jupiter": 34.29,
              "Mercury": 25.71, "Mars": 17.14, "Saturn": 8.57}

FRIENDS = {"Sun": {"Moon", "Mars", "Jupiter"}, "Moon": {"Sun", "Mercury"}, "Mars": {"Sun", "Moon", "Jupiter"},
           "Mercury": {"Sun", "Venus"}, "Jupiter": {"Sun", "Moon", "Mars"}, "Venus": {"Mercury", "Saturn"},
           "Saturn": {"Mercury", "Venus"}}
ENEMIES = {"Sun": {"Venus", "Saturn"}, "Moon": set(), "Mars": {"Mercury"}, "Mercury": {"Moon"},
           "Jupiter": {"Mercury", "Venus"}, "Venus": {"Sun", "Moon"}, "Saturn": {"Sun", "Moon", "Mars"}}
# moolatrikona: (sign index, from degree, to degree)
MOOLATRIKONA = {"Sun": (4, 0, 20), "Moon": (1, 3, 30), "Mars": (0, 0, 12), "Mercury": (5, 15, 20),
                "Jupiter": (8, 0, 10), "Venus": (6, 0, 15), "Saturn": (10, 0, 20)}
SAPTA_VARGAS = ("D1", "D2", "D3", "D7", "D9", "D12", "D30")
SAPTA_POINTS = {"moolatrikona": 45, "own": 30, "adhimitra": 20, "mitra": 15, "sama": 10, "shatru": 4, "adhishatru": 2}

DAY_PLANETS = ("Sun", "Jupiter", "Venus")
NIGHT_PLANETS = ("Moon", "Mars", "Saturn")
BENEFICS = ("Jupiter", "Venus", "Mercury", "Moon")
HORA_SEQ = ("Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars")
VARA_LORDS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
DAY_THIRDS = ("Mercury", "Sun", "Saturn")
NIGHT_THIRDS = ("Moon", "Venus", "Mars")


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


# ---- Sthana ---------------------------------------------------------------------------
def trimsamsa_sign(lon: float) -> int:
    sign, deg = int(lon % 360 // 30), lon % 30
    cuts = ((5, 0), (10, 10), (18, 8), (25, 2), (30, 6)) if sign % 2 == 0 else ((5, 1), (12, 5), (20, 11), (25, 9), (30, 7))
    return next(sg for limit, sg in cuts if deg < limit)


def _sign_in(varga: str, lon: float) -> int:
    return trimsamsa_sign(lon) if varga == "D30" else varga_sign(lon, varga)


def _relation(planet: str, other: str, planet_sign: int, other_sign: int) -> str:
    """Compound (natural + temporary) relation of `planet` to `other`, using the rasi positions."""
    nat = 1 if other in FRIENDS[planet] else -1 if other in ENEMIES[planet] else 0
    tmp = 1 if ((other_sign - planet_sign) % 12) in (1, 2, 3, 9, 10, 11) else -1
    return {(1, 1): "adhimitra", (1, -1): "sama", (0, 1): "mitra", (0, -1): "shatru",
            (-1, 1): "sama", (-1, -1): "adhishatru"}[(nat, tmp)]


def saptavargaja_bala(planet: str, lons: dict) -> float:
    total = 0.0
    own_lon = lons[planet]
    mt = MOOLATRIKONA[planet]
    for v in SAPTA_VARGAS:
        sign = _sign_in(v, own_lon)
        if v == "D1" and sign == mt[0] and mt[1] <= own_lon % 30 < mt[2]:
            total += SAPTA_POINTS["moolatrikona"]
            continue
        if sign in OWN_SIGNS[planet]:
            total += SAPTA_POINTS["own"]
            continue
        lord = SIGN_LORDS[sign]
        rel = _relation(planet, lord, int(own_lon % 360 // 30), int(lons[lord] % 360 // 30))
        total += SAPTA_POINTS[rel]
    return total


def ojayugma_bala(planet: str, lon: float) -> float:
    pts = 0.0
    for v in ("D1", "D9"):
        odd = _sign_in(v, lon) % 2 == 0          # index 0 = Mesha = odd sign
        if (planet in ("Moon", "Venus")) != odd:
            pts += 15.0
    return pts


def drekkana_bala(planet: str, lon: float) -> float:
    part = int(lon % 30 // 10)                   # 0,1,2
    want = {"Sun": 0, "Mars": 0, "Jupiter": 0, "Saturn": 1, "Mercury": 1, "Moon": 2, "Venus": 2}[planet]
    return 15.0 if part == want else 0.0


# ---- Kala -----------------------------------------------------------------------------
def _hours(hhmm: str) -> float:
    h, m = hhmm.split(":")[:2]
    return int(h) + int(m) / 60.0


def time_context(chart: dict) -> dict | None:
    """Day/night position of the birth moment (local clock hours), or None if the sun times are unavailable."""
    day = chart.get("day") or {}
    if not day.get("available"):
        return None
    sr, ss = _hours(day["sunrise"]), _hours(day["sunset"])
    t = _hours(chart["input"]["time"])
    if t < sr:
        t += 24.0
    is_day = sr <= t < ss
    vara = day["vedic_vara"]["index"]
    if is_day:
        idx, third = int((t - sr) / ((ss - sr) / 12.0)), int((t - sr) / ((ss - sr) / 3.0))
    else:
        night = sr + 24.0 - ss
        idx, third = 12 + int((t - ss) / (night / 12.0)), int((t - ss) / (night / 3.0))
    noon, midnight = (sr + ss) / 2.0, (sr + ss + 24.0) / 2.0
    return {"is_day": is_day, "vara_lord": VARA_LORDS[vara],
            "hora_lord": HORA_SEQ[(HORA_SEQ.index(VARA_LORDS[vara]) + min(idx, 23)) % 7],
            "third_lord": (DAY_THIRDS if is_day else NIGHT_THIRDS)[min(third, 2)],
            "from_noon": abs(t - noon), "from_midnight": min(abs(t - midnight), 24 - abs(t - midnight))}


def natonnata_bala(planet: str, tc: dict) -> float:
    if planet == "Mercury":
        return 60.0
    d = tc["from_noon"] if planet in DAY_PLANETS else tc["from_midnight"]
    return max(0.0, 60.0 * (12.0 - min(d, 12.0)) / 12.0)


def paksha_bala(planet: str, sun_lon: float, moon_lon: float) -> float:
    x = _arc(moon_lon, sun_lon) / 3.0
    return x if planet in BENEFICS else 60.0 - x


def tribhaga_bala(planet: str, tc: dict) -> float:
    return 60.0 if planet == "Jupiter" or planet == tc["third_lord"] else 0.0


def declination(trop_lon: float, obliquity: float) -> float:
    return math.degrees(math.asin(math.sin(math.radians(obliquity)) * math.sin(math.radians(trop_lon))))


def ayana_bala(planet: str, trop_lon: float, obliquity: float) -> float:
    d = declination(trop_lon, obliquity)
    north = (obliquity + d) / (2 * obliquity) * 60.0
    south = (obliquity - d) / (2 * obliquity) * 60.0
    v = south if planet in ("Saturn", "Moon") else north
    return v * 2.0 if planet == "Sun" else v


# ---- Drik -----------------------------------------------------------------------------
SPECIAL = {"Mars": ((90, 120), (210, 240)), "Jupiter": ((120, 150), (240, 270)), "Saturn": ((60, 90), (270, 300))}


def aspect_virupa(src: str, d: float) -> float:
    """Aspect strength (0-60 virupa) of `src` on a point `d` degrees ahead of it."""
    d %= 360.0
    for lo, hi in SPECIAL.get(src, ()):
        if lo <= d < hi:
            return 60.0
    if d < 30:
        return 0.0
    if d < 60:
        return (d - 30) / 2
    if d < 90:
        return d - 45
    if d < 120:
        return 30 + (120 - d) / 2
    if d < 150:
        return 150 - d
    if d < 180:
        return (d - 150) * 2
    if d < 300:
        return (300 - d) / 2
    return 0.0


def drik_bala(target: str, lons: dict) -> float:
    waxing = ((lons["Moon"] - lons["Sun"]) % 360.0) < 180.0
    total = 0.0
    for src in SEVEN:
        if src == target:
            continue
        v = aspect_virupa(src, lons[target] - lons[src])
        benefic = src in ("Jupiter", "Venus", "Mercury") or (src == "Moon" and waxing)
        total += v if benefic else -v
    return total / 4.0


def strength(chart: dict) -> dict:
    lagna_lon = chart["lagna"]["longitude"]
    lons = {p["name"]: p["longitude"] for p in chart["planets"]}
    houses = {p["name"]: p["house"] for p in chart["planets"]}
    names_hi = {p["name"]: p["name_hi"] for p in chart["planets"]}
    tc = time_context(chart)
    ayan, obl = chart["ayanamsa_value"], chart["obliquity"]
    rows = []
    for n in SEVEN:
        lon = lons[n]
        sthana = {"uccha": uccha_bala(n, lon), "saptavargaja": saptavargaja_bala(n, lons),
                  "ojayugma": ojayugma_bala(n, lon), "kendradi": kendradi_bala(houses[n]),
                  "drekkana": drekkana_bala(n, lon)}
        ay = ayana_bala(n, lon + ayan, obl)
        pk = paksha_bala(n, lons["Sun"], lons["Moon"])
        kala = {"paksha": pk, "ayana": ay}
        if tc:
            kala.update({"natonnata": natonnata_bala(n, tc), "tribhaga": tribhaga_bala(n, tc),
                         "vara": 45.0 if n == tc["vara_lord"] else 0.0,
                         "hora": 60.0 if n == tc["hora_lord"] else 0.0})
        cheshta = ay if n == "Sun" else pk if n == "Moon" else None
        parts = {"sthana": sum(sthana.values()), "dig": dig_bala(n, lon, lagna_lon), "kala": sum(kala.values()),
                 "cheshta": cheshta or 0.0, "naisargika": NAISARGIKA[n], "drik": drik_bala(n, lons)}
        total = sum(parts.values())
        rows.append({"name": n, "name_hi": names_hi[n],
                     "uccha": round(sthana["uccha"], 2), "kendradi": round(sthana["kendradi"], 2),
                     **{k: round(v, 2) for k, v in parts.items()},
                     "detail": {"sthana": {k: round(v, 2) for k, v in sthana.items()},
                                "kala": {k: round(v, 2) for k, v in kala.items()}},
                     "cheshta_known": cheshta is not None,
                     "total": round(total, 2), "rupas": round(total / 60.0, 2),
                     "comparable": round(total - parts["cheshta"], 2)})
    # Rank without cheshta, because it is only known for Sun and Moon (it would unfairly favour them).
    for i, r in enumerate(sorted(rows, key=lambda r: -r["comparable"]), 1):
        r["rank"] = i
    missing = ["cheshta (Mars, Mercury, Jupiter, Venus, Saturn)", "abda", "masa", "yuddha"]
    if not tc:
        missing += ["natonnata", "tribhaga", "vara", "hora (sunrise/sunset unavailable)"]
    return {"planets": rows, "unit": "virupa", "complete": False, "missing": missing,
            "missing_hi": ("चेष्टाबल (सूर्य-चंद्र को छोड़कर), अब्दबल, मासबल और युद्धबल अभी शामिल नहीं हैं, इसलिए यह पूर्ण "
                           "षड्बल नहीं है। कुल अंकों की तुलना शास्त्रीय न्यूनतम-आवश्यकता तालिका से न करें; "
                           "केवल एक ही कुंडली के ग्रहों की आपस में तुलना करें।"),
            "assumptions": ["Mercury counted as benefic in paksha and drik bala",
                            "Moon benefic in drik bala only when waxing",
                            "Sun's ayana bala doubled",
                            "ayana bala uses ecliptic longitude only (planet latitude ignored)",
                            "dig bala cusps approximated by Lagna + 90 degree steps",
                            "moolatrikona counted in D1 only; saptavargaja uses compound friendship from rasi positions"],
            "why_hi": ("स्थानबल: उच्च बिंदु से निकटता, सात वर्गों में मित्र/स्वराशि स्थिति, विषम-सम राशि, केंद्रादि और द्रेष्काण। "
                       "दिग्बल: बलवान दिशा (सूर्य-मंगल दशम, गुरु-बुध लग्न, चंद्र-शुक्र चतुर्थ, शनि सप्तम) के पास। "
                       "कालबल: दिन-रात की स्थिति, पक्ष, त्रिभाग, वार, होरा और अयन। नैसर्गिक बल: हर ग्रह का स्थिर बल। "
                       "दृग्बल: शुभ ग्रहों की दृष्टि जोड़कर और पाप ग्रहों की दृष्टि घटाकर, चौथाई। "
                       "चेष्टाबल: सूर्य के लिए अयनबल और चंद्र के लिए पक्षबल।"),
            "confidence": "draft"}
