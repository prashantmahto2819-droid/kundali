"""Life timeline: Vimshottari periods read through the dasha lord's placement in the birth chart.

For each period the engine states WHICH life areas become active (the houses the lord sits in and
owns) and a transparent strength tag. It does not predict events: it says what themes tradition
links to the period, and why. Rahu and Ketu own no house, so only their placement is used.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from .constants import PLANETS_HI, SIGN_LORDS

_HOUSES = Path(__file__).resolve().parents[2] / "data" / "knowledge" / "houses.json"
GOOD_HOUSES = {1, 4, 5, 7, 9, 10}      # kendra and trikona
HARD_HOUSES = {6, 8, 12}               # dusthana
SENSITIVE = ("आयु", "मृत्यु", "रोग", "बीमारी", "दुर्घटना", "शत्रु", "ऋण", "हानि")
MAX_START_AGE = 100.0
TAG_HI = {"favourable": "अनुकूल", "mixed": "मिश्रित", "demanding": "परिश्रम-साध्य"}


@lru_cache(maxsize=1)
def _houses() -> dict:
    return json.loads(_HOUSES.read_text(encoding="utf-8"))["houses"]


def _parse(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def lord_profile(chart: dict, lord: str) -> dict:
    pl = next(p for p in chart["planets"] if p["name"] == lord)
    owned = [h["house"] for h in chart["houses"] if SIGN_LORDS[h["sign"]] == lord] if lord not in ("Rahu", "Ketu") else []
    bindus = None
    if lord in chart["ashtakavarga"]["bav"]:
        bindus = chart["ashtakavarga"]["bav"][lord]["by_sign"][pl["sign"]]
    score, reasons = 0, []
    if pl["dignity"] in ("own", "exalted"):
        score += 1
        reasons.append("स्वराशि/उच्च में" if pl["dignity"] == "own" else "उच्च राशि में")
    elif pl["dignity"] == "debilitated":
        score -= 1
        reasons.append("नीच राशि में")
    if pl["house"] in GOOD_HOUSES:
        score += 1
        reasons.append(f"{pl['house']}वें (केंद्र/त्रिकोण) भाव में")
    elif pl["house"] in HARD_HOUSES:
        score -= 1
        reasons.append(f"{pl['house']}वें (त्रिक) भाव में")
    if bindus is not None:
        if bindus >= 5:
            score += 1
            reasons.append(f"अष्टकवर्ग में {bindus} बिंदु")
        elif bindus <= 3:
            score -= 1
            reasons.append(f"अष्टकवर्ग में {bindus} बिंदु")
    tag = "favourable" if score >= 2 else ("demanding" if score <= -2 else "mixed")
    houses = _houses()
    themes = []
    for h in [pl["house"]] + [x for x in owned if x != pl["house"]]:
        themes.append({"house": h, "name_hi": houses[str(h)]["name_hi"],
                       "themes_hi": [x for x in houses[str(h)]["signifies_hi"] if not any(b in x for b in SENSITIVE)][:3]})
    return {"lord": lord, "lord_hi": PLANETS_HI[lord], "house": pl["house"], "owns": owned,
            "dignity": pl["dignity"], "bindus": bindus, "score": score, "tag": tag, "tag_hi": TAG_HI[tag],
            "reasons_hi": reasons, "themes": themes}


def _sentence(prof: dict, level_hi: str) -> str:
    areas = "; ".join(f"{t['house']}वाँ भाव ({', '.join(t['themes_hi'][:2])})" for t in prof["themes"])
    own = (f" और {', '.join(str(x) for x in prof['owns'])} भाव का स्वामी है" if prof["owns"] else " (छाया ग्रह: कोई भाव स्वामित्व नहीं)")
    why = ("; ".join(prof["reasons_hi"]) or "सामान्य स्थिति")
    return (f"{prof['lord_hi']} जन्म-कुंडली में {prof['house']}वें भाव में है{own}, इसलिए इस {level_hi} में "
            f"{areas} से जुड़े विषय सक्रिय रहते हैं। बल-संकेत: {prof['tag_hi']} ({why})।")


def dasha_timeline(chart: dict, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    birth = _parse(chart["birth_utc"])
    cache: dict[str, dict] = {}

    def prof(l):
        if l not in cache:
            cache[l] = lord_profile(chart, l)
        return cache[l]

    def phase(a, b):
        return "past" if b <= now else ("future" if a > now else "running")

    out = []
    for md in chart["dasha"]["mahadashas"]:
        s, e = _parse(md["start"]), _parse(md["end"])
        p = prof(md["lord"])
        item = {"lord": md["lord"], "lord_hi": p["lord_hi"], "start": md["start"], "end": md["end"],
                "years": round((e - s).days / 365.25, 2), "age_start": round(max(0.0, (s - birth).days / 365.25), 1),
                "age_end": round((e - birth).days / 365.25, 1), "phase": phase(s, e),
                "profile": p, "text_hi": _sentence(p, "महादशा"), "antardashas": []}
        for ad in md.get("children", []):
            sa, ea = _parse(ad["start"]), _parse(ad["end"])
            q = prof(ad["lord"])
            item["antardashas"].append({
                "lord": ad["lord"], "lord_hi": q["lord_hi"], "start": ad["start"], "end": ad["end"],
                "phase": phase(sa, ea), "house": q["house"], "owns": q["owns"], "tag": q["tag"], "tag_hi": q["tag_hi"],
                "themes_hi": [t["themes_hi"][0] for t in q["themes"]]})
        if item["age_start"] <= MAX_START_AGE:
            out.append(item)
    return {"as_of": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "periods": out, "confidence": "draft",
            "note_hi": ("यह समय-रेखा बताती है कि किस दशा में जीवन के कौन-से क्षेत्र सक्रिय रहते हैं, घटनाओं की भविष्यवाणी नहीं। "
                        "बल-संकेत दशेश की स्थिति (गरिमा, भाव, अष्टकवर्ग बिंदु) से बनता है; गोचर, दृष्टियाँ और योग अभी शामिल नहीं हैं।")}


# ---------------------------------------------------------------- year overlay: dasha x slow transits
SAT_ASPECTS = (1, 3, 7, 10)            # houses a planet influences from its sign (occupation + sign aspects)
JUP_ASPECTS = (1, 5, 7, 9)
KEY_HOUSES = {7: ("विवाह / साझेदारी", "marriage / partnership"), 10: ("कर्म / पद", "career / position"), 5: ("संतान / विद्या", "children / studies"),
              4: ("घर / वाहन / माता", "home / vehicle / mother"), 2: ("धन / कुटुंब", "wealth / family"), 11: ("लाभ / इच्छा-पूर्ति", "gains / wishes"), 9: ("भाग्य / यात्रा", "fortune / travel")}


def _influenced(sign: int, lagna_sign: int, offsets) -> set:
    h0 = (sign - lagna_sign) % 12 + 1
    return {(h0 - 1 + o - 1) % 12 + 1 for o in offsets}


def year_overlay(chart: dict, years_after: int = 90) -> dict:
    """One row per year of life: running mahadasha/antardasha, Saturn and Jupiter signs (mid-year), Sade Sati flag,
    and the houses from the Lagna that BOTH Saturn and Jupiter influence that year (double transit, K.N. Rao's rule
    of thumb for timing). Tendency-level; no event prediction."""
    from .transit import _sign_periods
    lagna_sign = chart["lagna"]["sign"]
    moon_sign = next(p["sign"] for p in chart["planets"] if p["name"] == "Moon")
    by = int(chart["input"]["date"][:4])
    sat = _sign_periods("Saturn", 1900, 2100); jup = _sign_periods("Jupiter", 1900, 2100)
    periods = chart.get("dasha", {}).get("mahadashas", [])

    def sign_on(runs, iso):
        return next((s for s, a, b in runs if a <= iso < b), None)

    def running(iso):
        md = next((p for p in periods if p["start"] <= iso < p["end"]), None)
        ad = next((c for c in (md or {}).get("children", []) if c["start"] <= iso < c["end"]), None) if md else None
        return md, ad
    rows = []
    for age in range(0, min(years_after, 2100 - by) + 1):
        y = by + age
        mid = f"{y}-07-01"
        ss, js = sign_on(sat, mid), sign_on(jup, mid)
        if ss is None or js is None:
            continue
        md, ad = running(mid + "T00:00:00Z")
        sat_h = _influenced(ss, lagna_sign, SAT_ASPECTS); jup_h = _influenced(js, lagna_sign, JUP_ASPECTS)
        both = sorted(sat_h & jup_h)
        key = [h for h in both if h in KEY_HOUSES]
        d = (ss - moon_sign) % 12
        rows.append({"age": age, "year": y, "mahadasha": md["lord"] if md else None, "mahadasha_hi": PLANETS_HI.get(md["lord"]) if md else None,
                     "antardasha": ad["lord"] if ad else None, "antardasha_hi": PLANETS_HI.get(ad["lord"]) if ad else None,
                     "saturn_sign": ss, "saturn_house": (ss - lagna_sign) % 12 + 1, "jupiter_sign": js, "jupiter_house": (js - lagna_sign) % 12 + 1,
                     "sade_sati": d in (11, 0, 1), "ashtama_shani": d == 7, "double_transit": both, "key_houses": key,
                     "key_hi": [KEY_HOUSES[h][0] for h in key], "key_en": [KEY_HOUSES[h][1] for h in key]})
    # dasha-lord link: years where a key double-transit house is also owned/occupied by the running mahadasha lord
    pl = {p["name"]: p for p in chart["planets"]}
    for r in rows:
        lord = r["mahadasha"]
        if not lord or lord not in pl:
            r["dasha_supports"] = []; continue
        owns = [h for h in range(1, 13) if SIGN_LORDS[(lagna_sign + h - 1) % 12] == lord]
        r["dasha_supports"] = [h for h in r["key_houses"] if h in owns or h == pl[lord]["house"]]
    return {"rows": rows, "key_houses": {h: {"hi": v[0], "en": v[1]} for h, v in KEY_HOUSES.items()},
            "note_hi": "हर वर्ष (1 जुलाई को) चल रही महादशा-अंतर्दशा, शनि-गुरु की राशि, साढ़ेसाती, और वे भाव जिन्हें शनि (3,7,10 दृष्टि + स्थिति) और गुरु (5,7,9 + स्थिति) दोनों प्रभावित करते हैं — 'दोहरा गोचर'। "
                       "जब वही भाव चल रही महादशा के स्वामी से भी जुड़ा हो, तो परंपरा उस वर्ष को उस भाव के विषय में सक्रिय मानती है। यह समय-संकेत है, घटना की भविष्यवाणी नहीं।",
            "note_en": "For every year (at 1 July): the running mahadasha/antardasha, Saturn's and Jupiter's signs, Sade Sati, and the houses both Saturn (aspects 3,7,10 + occupation) and Jupiter (5,7,9 + occupation) influence — the 'double transit'. "
                       "When that house is also linked to the running mahadasha lord, tradition treats the year as active for that house's matters. A timing hint, not an event prediction."}
