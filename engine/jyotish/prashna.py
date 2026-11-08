"""Prashna (horary) v1 in the KP way.

The chart of the moment of the question (or of a KP number 1-249 that the querent gives, which fixes the
Lagna at the start of that sub) is read for one topic: the sub-lord of the topic's cusp is checked for
whether it signifies the houses that favour the matter (e.g. marriage 2-7-11) or the ones that deny it
(e.g. 1-6-10 for marriage). The Moon's sub-lord shows the querent's mind, and the ruling planets are given
for timing. Wording is tendency only; health, legal and lifespan questions are not offered.
Draft: a KP practitioner should check the house groups and the verdict rules.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .constants import PLANETS_HI, SIGNS, SIGNS_HI
from .kp import _house_of, _lords, kp_ayanamsa, placidus_cusps, ruling_planets
from .ephemeris import mean_node, norm360
from .timeutil import delta_t, julian_day, year_fraction
from .constants import DASHA_ORDER, DASHA_YEARS

TOPICS = {
    "marriage":  {"hi": "विवाह", "en": "Marriage", "house": 7, "favour": [2, 7, 11], "deny": [1, 6, 10]},
    "job":       {"hi": "नौकरी", "en": "Job", "house": 10, "favour": [2, 6, 10, 11], "deny": [5, 9, 12]},
    "business":  {"hi": "व्यापार", "en": "Business", "house": 7, "favour": [2, 7, 10, 11], "deny": [5, 8, 12]},
    "money":     {"hi": "धन / वसूली", "en": "Money / recovery", "house": 11, "favour": [2, 6, 11], "deny": [5, 8, 12]},
    "property":  {"hi": "संपत्ति / मकान", "en": "Property / house", "house": 4, "favour": [4, 11, 12], "deny": [3, 5, 10]},
    "education": {"hi": "शिक्षा / परीक्षा", "en": "Education / exam", "house": 4, "favour": [4, 9, 11], "deny": [3, 8, 12]},
    "children":  {"hi": "संतान", "en": "Children", "house": 5, "favour": [2, 5, 11], "deny": [1, 4, 10]},
    "travel":    {"hi": "विदेश / यात्रा", "en": "Travel / abroad", "house": 9, "favour": [3, 9, 12], "deny": [2, 4, 11]},
    "lost_item": {"hi": "खोई वस्तु", "en": "Lost item", "house": 2, "favour": [2, 6, 11], "deny": [3, 5, 8, 12]},
    "general":   {"hi": "सामान्य प्रश्न (सफलता)", "en": "General question (success)", "house": 11, "favour": [1, 10, 11], "deny": [6, 8, 12]},
}


def lagna_from_kp_number(n: int) -> float:
    """Longitude at the start of the n-th sub (1-249) in zodiacal order: 27 stars x 9 subs."""
    if not 1 <= n <= 249:
        raise ValueError("KP number must be 1-249")
    k, lon = 0, 0.0
    span = 360.0 / 27.0
    for nak in range(27):
        star = DASHA_ORDER[nak % 9]
        order = DASHA_ORDER[DASHA_ORDER.index(star):] + DASHA_ORDER[:DASHA_ORDER.index(star)]
        for p in order:
            k += 1
            if k == n:
                return lon
            lon += span * DASHA_YEARS[p] / 120.0
    return lon


def _signifies(planet: str, houses: dict, star_of: dict, owners: dict, sign_lords: dict) -> set:
    """Houses a planet signifies in KP: house of its star lord, its own house, houses owned by star lord, own houses."""
    out = set()
    sl = star_of[planet]
    out.add(houses[sl]); out.add(houses[planet])
    out |= owners.get(sl, set()); out |= owners.get(planet, set())
    return out


def prashna(topic: str, when_utc: datetime, lat: float, lon_east: float, backend, tz: str = "Asia/Kolkata",
            kp_number: int | None = None) -> dict:
    if topic not in TOPICS:
        raise ValueError(f"unknown topic '{topic}' (choose {', '.join(TOPICS)})")
    T = TOPICS[topic]
    jd_ut = julian_day(when_utc)
    jd_tt = jd_ut + delta_t(year_fraction(when_utc)) / 86400.0
    ayan = kp_ayanamsa(jd_tt)
    pos = backend.positions(jd_tt)
    pos["Rahu"] = mean_node(jd_tt)
    pos["Ketu"] = norm360(pos["Rahu"] + 180.0)
    lons = {p: norm360(v - ayan) for p, v in pos.items()}
    if kp_number:
        asc = lagna_from_kp_number(kp_number)
        # keep the chart's angular shape from the moment but anchor cusp 1 at the number's Lagna: equal shift of all cusps
        base = placidus_cusps(jd_ut, jd_tt, lat, lon_east)
        shift = asc - norm360(base[0] - ayan)
        cusps = [norm360(c - ayan + shift) for c in base]
    else:
        cusps = [norm360(c - ayan) for c in placidus_cusps(jd_ut, jd_tt, lat, lon_east)]
    planets = {p: {**_lords(l), "longitude": l, "house": _house_of(l, cusps)} for p, l in lons.items()}
    cusp_rows = [{"house": i + 1, **_lords(c)} for i, c in enumerate(cusps)]
    houses = {p: v["house"] for p, v in planets.items()}
    star_of = {p: v["star_lord"] for p, v in planets.items()}
    owners: dict[str, set] = {}
    for i, c in enumerate(cusp_rows):
        owners.setdefault(c["sign_lord"], set()).add(i + 1)
    # Rahu/Ketu represent the lord of their sign (KP agency) for ownership
    for node in ("Rahu", "Ketu"):
        owners.setdefault(node, set()).update(owners.get(planets[node]["sign_lord"], set()))
    sig = {p: _signifies(p, houses, star_of, owners, None) for p in planets}
    qc = cusp_rows[T["house"] - 1]
    sub = qc["sub_lord"]
    sub_sig = sig[sub]
    fav = sorted(sub_sig & set(T["favour"])); den = sorted(sub_sig & set(T["deny"]))
    if fav and not den:
        verdict, v_hi = "favourable", "अनुकूल"
    elif den and not fav:
        verdict, v_hi = "unfavourable", "प्रतिकूल"
    elif fav and den:
        verdict, v_hi = "mixed", "मिश्रित (देरी या शर्तों के साथ)"
    else:
        verdict, v_hi = "unclear", "अस्पष्ट"
    moon = planets["Moon"]
    moon_sub_sig = sig[moon["sub_lord"]]
    moon_ok = bool(moon_sub_sig & set(T["favour"]))
    rp = ruling_planets(when_utc, lat, lon_east, backend, tz)
    H = lambda n: PLANETS_HI.get(n, n)
    why_hi = [f"{T['hi']} का भाव {T['house']}; उसके भाव-स्पष्ट का उप-स्वामी {H(sub)} है।",
              f"{H(sub)} भाव {', '.join(map(str, sorted(sub_sig))) or '—'} का कारक है: अनुकूल भाव {', '.join(map(str, fav)) or 'कोई नहीं'}, प्रतिकूल भाव {', '.join(map(str, den)) or 'कोई नहीं'}।",
              f"चंद्र (प्रश्नकर्ता का मन) {moon['sign_name_hi']} में, उप-स्वामी {H(moon['sub_lord'])}: " + ("प्रश्न विषय से जुड़ा है।" if moon_ok else "प्रश्न विषय से सीधा जुड़ाव नहीं दिखता।")]
    why_en = [f"House {T['house']} rules {T['en'].lower()}; the sub-lord of its cusp is {sub}.",
              f"{sub} signifies houses {', '.join(map(str, sorted(sub_sig))) or '—'}: favouring {', '.join(map(str, fav)) or 'none'}, denying {', '.join(map(str, den)) or 'none'}.",
              f"The Moon (the querent's mind) in {moon['sign_name']}, sub-lord {moon['sub_lord']}: " + ("connected to the matter." if moon_ok else "no direct connection to the matter.")]
    return {"topic": topic, "topic_hi": T["hi"], "topic_en": T["en"], "at": when_utc.strftime("%Y-%m-%dT%H:%M:%SZ"), "tz": tz,
            "kp_number": kp_number, "ayanamsa": ayan, "verdict": verdict, "verdict_hi": v_hi,
            "question_house": T["house"], "cusp_sub_lord": sub, "cusp_sub_lord_hi": H(sub), "sub_lord_signifies": sorted(sub_sig),
            "favour_hit": fav, "deny_hit": den, "moon": {"sign_name": moon["sign_name"], "sign_name_hi": moon["sign_name_hi"], "sub_lord": moon["sub_lord"], "connected": moon_ok},
            "lagna": {"sign_name": SIGNS[cusp_rows[0]["sign"]], "sign_name_hi": SIGNS_HI[cusp_rows[0]["sign"]], "degree_in_sign": round(cusp_rows[0]["degree_in_sign"], 2)},
            "cusps": cusp_rows, "planets": {p: {"sign_name_hi": v["sign_name_hi"], "house": v["house"], "star_lord": v["star_lord"], "sub_lord": v["sub_lord"]} for p, v in planets.items()},
            "ruling_planets": rp, "reasons_hi": why_hi, "reasons_en": why_en, "review_status": "draft",
            "disclaimer_hi": "प्रश्न कुंडली प्रवृत्ति बताती है, निश्चित उत्तर नहीं। स्वास्थ्य, क़ानून या आयु के प्रश्न यहाँ नहीं लिए जाते। KP विशेषज्ञ की समीक्षा बाकी है।",
            "disclaimer_en": "A prashna chart shows a tendency, not a certain answer. Health, legal and lifespan questions are not taken here. Pending review by a KP practitioner."}
