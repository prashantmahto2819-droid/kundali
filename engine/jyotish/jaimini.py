"""Jaimini layer v1: chara karakas (7-karaka scheme with Rahu as the 8th option), arudha padas, karakamsa.

* Chara karakas: planets ranked by degree within sign (highest = Atmakaraka). Default is the 7-karaka
  scheme (Sun..Saturn); the 8-karaka scheme (Rahu included, counted from the end of its sign) is also given.
* Arudha pada of house N: count from the house to its lord, then the same distance again from the lord;
  if the result falls in the same house or the 7th from it, take the 10th from that (standard exception).
* Karakamsa: the navamsa sign of the Atmakaraka. Swamsa chart notes are left for a later version.
Draft: a Jaimini practitioner should check the exception rules and the Rahu convention.
"""
from __future__ import annotations

from .constants import PLANETS_HI, SIGNS, SIGNS_HI, SIGN_LORDS

KARAKAS_7 = ["Atmakaraka", "Amatyakaraka", "Bhratrikaraka", "Matrikaraka", "Putrakaraka", "Gnatikaraka", "Darakaraka"]
KARAKAS_8 = ["Atmakaraka", "Amatyakaraka", "Bhratrikaraka", "Matrikaraka", "Pitrikaraka", "Putrakaraka", "Gnatikaraka", "Darakaraka"]
KARAKA_HI = {"Atmakaraka": "आत्मकारक", "Amatyakaraka": "अमात्यकारक", "Bhratrikaraka": "भ्रातृकारक", "Matrikaraka": "मातृकारक",
             "Pitrikaraka": "पितृकारक", "Putrakaraka": "पुत्रकारक", "Gnatikaraka": "ज्ञातिकारक", "Darakaraka": "दारकारक"}
KARAKA_MEANS = {"Atmakaraka": "self, soul's purpose", "Amatyakaraka": "career, counsel", "Bhratrikaraka": "siblings, guru",
                "Matrikaraka": "mother, home", "Pitrikaraka": "father", "Putrakaraka": "children, students",
                "Gnatikaraka": "relatives, rivals, illness", "Darakaraka": "spouse, partnerships"}
KARAKA_MEANS_HI = {"Atmakaraka": "स्वयं, आत्मा का उद्देश्य", "Amatyakaraka": "कर्म, मंत्रणा", "Bhratrikaraka": "भाई-बहन, गुरु",
                   "Matrikaraka": "माता, घर", "Pitrikaraka": "पिता", "Putrakaraka": "संतान, शिष्य",
                   "Gnatikaraka": "कुटुंब, प्रतिद्वंद्वी, रोग", "Darakaraka": "जीवनसाथी, साझेदारी"}
PADA_HI = {1: "आरूढ़ लग्न (AL)", 2: "धन पद", 3: "विक्रम पद", 4: "मातृ पद", 5: "मंत्र पद", 6: "शत्रु पद", 7: "दार पद",
           8: "मृत्यु पद", 9: "भाग्य पद", 10: "राज्य पद", 11: "लाभ पद", 12: "उपपद (UL)"}
PADA_EN = {1: "Arudha Lagna (AL)", 2: "Dhana pada", 3: "Vikrama pada", 4: "Matri pada", 5: "Mantra pada", 6: "Shatru pada",
           7: "Dara pada", 8: "Mrityu pada", 9: "Bhagya pada", 10: "Rajya pada", 11: "Labha pada", 12: "Upapada (UL)"}


def chara_karakas(planets: list[dict]) -> dict:
    by = {p["name"]: p for p in planets}
    seven = sorted((n for n in by if n not in ("Rahu", "Ketu")), key=lambda n: -by[n]["degree_in_sign"])
    eight_vals = {n: by[n]["degree_in_sign"] for n in seven}
    eight_vals["Rahu"] = 30.0 - by["Rahu"]["degree_in_sign"]          # Rahu counted from the end of its sign
    eight = sorted(eight_vals, key=lambda n: -eight_vals[n])
    mk = lambda names, labels: [{"karaka": k, "karaka_hi": KARAKA_HI[k], "planet": n, "planet_hi": PLANETS_HI[n],
                                 "degree_in_sign": round(by[n]["degree_in_sign"] if n != "Rahu" else eight_vals["Rahu"], 2),
                                 "signifies": KARAKA_MEANS[k], "signifies_hi": KARAKA_MEANS_HI[k]}
                                for k, n in zip(labels, names)]
    return {"scheme7": mk(seven, KARAKAS_7), "scheme8": mk(eight, KARAKAS_8)}


def arudha_padas(lagna_sign: int, planets: list[dict]) -> list[dict]:
    by = {p["name"]: p for p in planets}
    out = []
    for h in range(1, 13):
        hs = (lagna_sign + h - 1) % 12
        lord = SIGN_LORDS[hs]
        ls = by[lord]["sign"]
        dist = (ls - hs) % 12                                    # houses from house to its lord
        pada = (ls + dist) % 12
        exception = pada in (hs, (hs + 6) % 12)
        if exception:
            pada = (pada + 9) % 12                                # 10th from it
        out.append({"house": h, "name_hi": PADA_HI[h], "name": PADA_EN[h], "house_sign": SIGNS[hs], "lord": lord, "lord_sign": SIGNS[ls],
                    "pada_sign": pada, "pada_sign_name": SIGNS[pada], "pada_sign_name_hi": SIGNS_HI[pada],
                    "pada_house": (pada - lagna_sign) % 12 + 1, "exception_applied": exception})
    return out


def jaimini(chart: dict) -> dict:
    planets = chart["planets"]
    ck = chara_karakas(planets)
    ak = ck["scheme7"][0]["planet"]
    akp = next(p for p in planets if p["name"] == ak)
    karakamsa = akp["navamsa_sign"]
    padas = arudha_padas(chart["lagna"]["sign"], planets)
    return {"chara_karakas": ck, "atmakaraka": ak, "atmakaraka_hi": PLANETS_HI[ak],
            "karakamsa": {"sign": karakamsa, "sign_name": SIGNS[karakamsa], "sign_name_hi": SIGNS_HI[karakamsa]},
            "arudha_padas": padas,
            "arudha_lagna": next(x for x in padas if x["house"] == 1), "upapada": next(x for x in padas if x["house"] == 12),
            "review_status": "draft",
            "note_hi": "जैमिनी व्यवस्था v1: चर कारक (7-कारक मुख्य, 8-कारक राहु सहित भी दिए), आरूढ़ पद (एक ही भाव या सप्तम में पड़ने पर दशम लिया), कारकांश। "
                       "ड्राफ़्ट; जैमिनी के जानकार की समीक्षा चाहिए।",
            "note_en": "Jaimini v1: chara karakas (7-karaka main, 8-karaka with Rahu also given), arudha padas (10th taken when the pada falls in "
                       "the same house or its 7th), karakamsa. Draft; needs review by a Jaimini practitioner."}
