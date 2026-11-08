"""Relations between planets: neecha-bhanga (cancellation of debilitation), conjunctions, combustion, aspects.

DRAFT (review_status: draft). Traditions differ on neecha-bhanga conditions; every condition that holds
is reported separately so the reader can see which one applied. Wording is tendency language only.
"""
from __future__ import annotations

from .constants import ASPECTS, DEBILITATION, EXALTATION, PLANETS_HI, SIGN_LORDS, SIGNS_HI
from .vargas import varga_sign

KENDRA = {1, 4, 7, 10}
SEVEN = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
# Combustion orbs in degrees from the Sun (common values; Mercury/Venus smaller when retrograde)
COMBUST_ORB = {"Moon": 12.0, "Mars": 17.0, "Mercury": 14.0, "Jupiter": 11.0, "Venus": 10.0, "Saturn": 15.0}
COMBUST_ORB_RETRO = {"Mercury": 12.0, "Venus": 8.0}
CLOSE_ORB = 10.0


def _arc(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return 360.0 - d if d > 180.0 else d


def _from(a: int, b: int) -> int:
    return (b - a) % 12 + 1


def _in_kendra(chart_p: dict, who: str) -> bool:
    """Is `who` in a kendra from the Lagna or from the Moon?"""
    h = chart_p[who]["house"]
    return h in KENDRA or _from(chart_p["Moon"]["house"], h) in KENDRA


def neecha_bhanga(chart: dict) -> list[dict]:
    p = {x["name"]: x for x in chart["planets"]}
    out = []
    for n in SEVEN:
        if p[n]["dignity"] != "debilitated":
            continue
        sign = p[n]["sign"]
        dispositor = SIGN_LORDS[sign]
        exalt_lord = SIGN_LORDS[EXALTATION[n]]
        raised = next((q for q in SEVEN if EXALTATION[q] == sign), None)    # planet exalted in this sign
        conds = []

        def add(cid, text, text_hi):
            conds.append({"id": cid, "text": text, "text_hi": text_hi})

        if _in_kendra(p, dispositor) and dispositor != n:
            add("dispositor_kendra", f"{dispositor}, lord of the debilitation sign, is in a kendra from the Lagna or Moon.",
                f"नीच राशि के स्वामी {PLANETS_HI[dispositor]} लग्न या चंद्र से केंद्र में हैं।")
        if _in_kendra(p, exalt_lord) and exalt_lord != n:
            add("exaltation_lord_kendra", f"{exalt_lord}, lord of {n}'s exaltation sign, is in a kendra from the Lagna or Moon.",
                f"{PLANETS_HI[n]} की उच्च राशि के स्वामी {PLANETS_HI[exalt_lord]} लग्न या चंद्र से केंद्र में हैं।")
        if raised and raised != n and _in_kendra(p, raised):
            add("raised_planet_kendra", f"{raised}, which is exalted in this sign, is in a kendra from the Lagna or Moon.",
                f"इस राशि में उच्च होने वाला ग्रह {PLANETS_HI[raised]} लग्न या चंद्र से केंद्र में है।")
        if dispositor != n and p[dispositor]["sign"] == sign:
            add("conjunct_dispositor", f"{n} is conjunct {dispositor}, lord of its debilitation sign.",
                f"{PLANETS_HI[n]} अपनी नीच राशि के स्वामी {PLANETS_HI[dispositor]} के साथ युति में है।")
        elif dispositor != n and _from(p[dispositor]["house"], p[n]["house"]) in ASPECTS[dispositor]:
            add("aspected_by_dispositor", f"{n} is aspected by {dispositor}, lord of its debilitation sign.",
                f"{PLANETS_HI[n]} पर नीच राशि के स्वामी {PLANETS_HI[dispositor]} की दृष्टि है।")
        if varga_sign(p[n]["longitude"], "D9") == EXALTATION[n]:
            add("exalted_in_navamsa", f"{n} is exalted in the navamsa chart.",
                f"{PLANETS_HI[n]} नवांश कुंडली में उच्च राशि में है।")
        out.append({"planet": n, "planet_hi": PLANETS_HI[n], "sign_hi": SIGNS_HI[sign],
                    "conditions": conds, "cancelled": bool(conds),
                    "text_hi": (f"{PLANETS_HI[n]} नीच राशि में है, पर {len(conds)} शास्त्रीय शर्त(ें) पूरी होने से नीच-भंग माना जाता है: "
                                "कमज़ोरी का असर घटकर, संघर्ष के बाद फल देने की प्रवृत्ति बताई जाती है।" if conds else
                                f"{PLANETS_HI[n]} नीच राशि में है और नीच-भंग की कोई सामान्य शर्त नहीं मिली: इसके कारकत्व में "
                                "अतिरिक्त मेहनत और धैर्य की ज़रूरत बताई जाती है।"),
                    "why_hi": ("नीच-भंग: नीच ग्रह की कमज़ोरी तब घटती मानी जाती है जब उसकी नीच राशि का स्वामी, उसकी उच्च राशि का स्वामी "
                               "या उस राशि में उच्च होने वाला ग्रह केंद्र में हो, या नीच ग्रह पर/साथ में नीच-राशि स्वामी हो, "
                               "या वह नवांश में उच्च हो। परंपराओं में शर्तें अलग-अलग गिनी जाती हैं, इसलिए हर शर्त अलग दिखाई गई है।"),
                    "review_status": "draft"})
    return out


def conjunctions(chart: dict) -> list[dict]:
    ps = chart["planets"]
    out = []
    for i, a in enumerate(ps):
        for b in ps[i + 1:]:
            if a["sign"] != b["sign"]:
                continue
            orb = _arc(a["longitude"], b["longitude"])
            if orb <= CLOSE_ORB:
                out.append({"planets": [a["name"], b["name"]], "planets_hi": [a["name_hi"], b["name_hi"]],
                            "sign_hi": a["sign_name_hi"], "house": a["house"], "orb": round(orb, 2),
                            "close": orb <= 3.0})
    return sorted(out, key=lambda r: r["orb"])


def combustion(chart: dict) -> list[dict]:
    p = {x["name"]: x for x in chart["planets"]}
    out = []
    for n, orb in COMBUST_ORB.items():
        limit = COMBUST_ORB_RETRO.get(n, orb) if p[n]["retrograde"] else orb
        d = _arc(p[n]["longitude"], p["Sun"]["longitude"])
        if d <= limit:
            out.append({"planet": n, "planet_hi": PLANETS_HI[n], "distance": round(d, 2), "limit": limit,
                        "text_hi": f"{PLANETS_HI[n]} सूर्य से {d:.1f}° पर है (अस्त-सीमा {limit:.0f}°): अस्त ग्रह के कारकत्व "
                                   "कुछ दबे हुए या सूर्य के प्रभाव में बताए जाते हैं।",
                        "review_status": "draft"})
    return out


def aspects(chart: dict) -> dict:
    """Whole-sign graha drishti. -> {'planets': [...], 'houses': {house: [planet, ...]}}"""
    ps = chart["planets"]
    by_house: dict[int, list] = {}
    for p in ps:
        by_house.setdefault(p["house"], []).append(p)
    rows, house_map = [], {h: [] for h in range(1, 13)}
    for p in ps:
        for n in ASPECTS.get(p["name"], [7]):
            target = (p["house"] + n - 2) % 12 + 1
            house_map[target].append(p["name"])
            rows.append({"from": p["name"], "from_hi": p["name_hi"], "from_house": p["house"], "aspect": n,
                         "to_house": target, "on": [q["name"] for q in by_house.get(target, [])],
                         "on_hi": [q["name_hi"] for q in by_house.get(target, [])]})
    return {"planets": rows, "houses": house_map,
            "why_hi": ("दृष्टि: हर ग्रह अपने से 7वें भाव को देखता है; मंगल 4 और 8, गुरु 5 और 9, शनि 3 और 10, राहु-केतु 5 और 9 "
                       "को भी देखते हैं। यहाँ पूरी-राशि दृष्टि गिनी गई है (अंशों के हिसाब से दृष्टि-बल षड्बल के दृग्बल में है)।"),
            "review_status": "draft"}


def relations(chart: dict) -> dict:
    return {"neecha_bhanga": neecha_bhanga(chart), "conjunctions": conjunctions(chart),
            "combustion": combustion(chart), "aspects": aspects(chart)}
