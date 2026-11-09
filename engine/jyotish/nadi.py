"""Nadi layer — Bhrigu Nandi Nadi (BNN) style reading of the Rashi chart, as popularised by R. G. Rao.

BNN reads planets, not houses: each planet is a karaka (Jupiter = the native / jeeva, Saturn = karma / profession, Venus = spouse,
Mars = property / siblings / energy, Mercury = speech / trade / learning, Sun = father / authority, Moon = mother / mind,
Rahu = foreign / unconventional, Ketu = moksha / sudden). The reading is built from planets that are *together*, *opposite*
(7th), in *trine* (5th / 9th), or *adjacent* (2nd / 12th) to a karaka, and from what is *ahead* of Saturn (profession field).
Nadi also moves Jupiter's transit as the age clock (12 years per cycle): the sign Jupiter occupies in a given year "activates"
the planets there and in trines to it.

Also attached: the native's nadi (Adi / Madhya / Antya from the Moon's nakshatra — the kuta used in matching) and the
nadi-amsha number (1..150 within the sign), which some Nadi schools use to index leaves. Interpretive texts are the
tradition's tendency language, labelled draft for scholar review.
"""
from __future__ import annotations

from datetime import date

from .constants import NAKSHATRAS, PLANETS_HI, SIGNS, SIGNS_HI

KARAKA = {"Jupiter": ("जीव (जातक स्वयं), धन, ज्ञान", "the native (jeeva), wealth, wisdom"), "Saturn": ("कर्म, व्यवसाय, श्रम", "karma, profession, toil"),
          "Venus": ("जीवनसाथी, सुख, कला", "spouse, comforts, arts"), "Mars": ("भूमि-भवन, भाई, ऊर्जा, तकनीक", "land/property, siblings, energy, engineering"),
          "Mercury": ("वाणी, व्यापार, शिक्षा, लेखन", "speech, trade, education, writing"), "Sun": ("पिता, अधिकार, सरकार", "father, authority, government"),
          "Moon": ("माता, मन, जनता, यात्रा", "mother, mind, public, travel"), "Rahu": ("विदेश, अपरंपरागत, छाया", "foreign, unconventional, shadow"),
          "Ketu": ("मोक्ष, आकस्मिक, अध्यात्म, गणित", "moksha, sudden events, spirituality, mathematics")}
# profession hints from planets that join / sit ahead of Saturn (BNN convention, simplified)
PROF = {"Jupiter": ("शिक्षा, वित्त, परामर्श, धर्म-क्षेत्र", "teaching, finance, advisory, religious field"), "Venus": ("कला, फ़ैशन, वाहन, विलासिता, मनोरंजन", "arts, fashion, vehicles, luxury, entertainment"),
        "Mars": ("इंजीनियरिंग, भूमि-भवन, पुलिस/सेना, शल्य", "engineering, real estate, police/defence, surgery"), "Mercury": ("लेखा, व्यापार, संचार, लेखन, IT", "accounts, trade, communication, writing, IT"),
        "Sun": ("सरकार, प्रशासन, चिकित्सा, नेतृत्व", "government, administration, medicine, leadership"), "Moon": ("जनसंपर्क, पर्यटन, तरल/खाद्य, नर्सिंग", "public dealing, tourism, liquids/food, nursing"),
        "Rahu": ("विदेशी कंपनी, आयात-निर्यात, तकनीक, राजनीति", "foreign firms, import-export, technology, politics"), "Ketu": ("गणित, शोध, आध्यात्म, चिकित्सा-निदान", "mathematics, research, spirituality, diagnostics")}
SIGN_FIELD = {0: ("सैन्य/पुलिस, खेल, अग्नि-धातु", "defence, sports, fire & metals"), 1: ("कृषि, वित्त, भोजन, सौंदर्य", "agriculture, finance, food, beauty"), 2: ("संचार, लेखन, व्यापार", "communication, writing, trade"),
              3: ("जल, पर्यटन, देखभाल, घर", "water, hospitality, care, home"), 4: ("सरकार, प्रबंधन, मनोरंजन", "government, management, entertainment"), 5: ("लेखा, सेवा, स्वास्थ्य", "accounts, service, health"),
              6: ("न्याय, कला, साझेदारी", "law, arts, partnership"), 7: ("शोध, रसायन, गुप्त विद्या", "research, chemistry, occult"), 8: ("शिक्षा, धर्म, विदेश", "teaching, religion, abroad"),
              9: ("उद्योग, निर्माण, प्रशासन", "industry, construction, administration"), 10: ("तकनीक, समाज-सेवा, नवाचार", "technology, social work, innovation"), 11: ("जल, औषधि, आध्यात्म, कला", "water, medicine, spirituality, arts")}
NADI_KUTA = ["Adi", "Madhya", "Antya"]
NADI_HI = {"Adi": "आदि (वात)", "Madhya": "मध्य (पित्त)", "Antya": "अंत्य (कफ)"}
_NADI_SEQ = [0, 1, 2, 2, 1, 0]      # repeats every 6 nakshatras


def nadi_of_nakshatra(idx: int) -> str:
    return NADI_KUTA[_NADI_SEQ[idx % 6]]


def nadi_amsha(longitude: float) -> int:
    """1..150 within the sign (each amsha = 12 arc-minutes)."""
    return int((longitude % 30.0) / 0.2) + 1


def _rel(a: int, b: int) -> str | None:
    d = (b - a) % 12
    return {0: "with", 6: "opposite", 4: "trine", 8: "trine", 1: "next", 11: "previous"}.get(d)


def relations(planets: dict) -> list[dict]:
    out = []
    names = [p for p in KARAKA if p in planets]
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            r = _rel(planets[a]["sign"], planets[b]["sign"])
            if r:
                out.append({"a": a, "b": b, "relation": r, "a_hi": PLANETS_HI[a], "b_hi": PLANETS_HI[b],
                            "relation_hi": {"with": "युति", "opposite": "सम्मुख (7वें)", "trine": "त्रिकोण", "next": "अगली राशि", "previous": "पिछली राशि"}[r]})
    return out


def _strength_words(rel: str, hi: bool) -> str:
    return {"with": ("प्रबल, जीवन-भर का विषय", "strong, a lifelong theme"), "opposite": ("प्रभाव स्पष्ट", "a clear influence"),
            "trine": ("सहज सहयोग", "easy support"), "next": ("आगे चलकर फलित", "unfolds later in life"),
            "previous": ("पूर्व-अर्जित, पृष्ठभूमि में", "carried from before, in the background")}[rel][0 if hi else 1]


def reading(chart: dict) -> dict:
    p = {x["name"]: x for x in chart["planets"]}
    rels = relations(p)
    jup, sat, ven = p["Jupiter"], p["Saturn"], p["Venus"]
    lines = []
    # 1. the native (Jupiter) and his company
    comp = [r for r in rels if "Jupiter" in (r["a"], r["b"])]
    for r in comp:
        other = r["b"] if r["a"] == "Jupiter" else r["a"]
        lines.append({"topic": "jeeva", "topic_hi": "जीव (जातक)", "planets": ["Jupiter", other], "relation": r["relation"],
                      "hi": f"गुरु (जीव) का {PLANETS_HI[other]} से {r['relation_hi']}: जीवन में {KARAKA[other][0]} का विषय प्रमुख — {_strength_words(r['relation'], True)}।",
                      "en": f"Jupiter (the native) {r['relation']} {other}: {KARAKA[other][1]} is a prominent theme — {_strength_words(r['relation'], False)}."})
    if not comp:
        lines.append({"topic": "jeeva", "topic_hi": "जीव (जातक)", "planets": ["Jupiter"], "relation": None,
                      "hi": f"गुरु {SIGNS_HI[jup['sign']]} में अकेला — स्वतंत्र, अपने बल पर बढ़ने वाला जीव; {SIGN_FIELD[jup['sign']][0]} से जुड़ाव।",
                      "en": f"Jupiter alone in {SIGNS[jup['sign']]} — a self-reliant native; links with {SIGN_FIELD[jup['sign']][1]}."})
    # 2. profession from Saturn: planets with / next to / opposite Saturn, else the sign field
    sat_comp = [r for r in rels if "Saturn" in (r["a"], r["b"]) and r["relation"] in ("with", "next", "opposite", "trine")]
    prof_pl = [(r["b"] if r["a"] == "Saturn" else r["a"], r["relation"]) for r in sat_comp]
    if prof_pl:
        for other, rel in prof_pl:
            lines.append({"topic": "karma", "topic_hi": "कर्म / व्यवसाय", "planets": ["Saturn", other], "relation": rel,
                          "hi": f"शनि (कर्म) के साथ {PLANETS_HI[other]} ({ {'with': 'युति', 'next': 'अगली राशि में', 'opposite': 'सम्मुख', 'trine': 'त्रिकोण में'}[rel]}): कार्य-क्षेत्र {PROF[other][0]} की ओर; {SIGNS_HI[sat['sign']]} राशि से {SIGN_FIELD[sat['sign']][0]}।",
                          "en": f"Saturn (karma) {rel} {other}: work leans to {PROF[other][1]}; the sign {SIGNS[sat['sign']]} adds {SIGN_FIELD[sat['sign']][1]}."})
    else:
        lines.append({"topic": "karma", "topic_hi": "कर्म / व्यवसाय", "planets": ["Saturn"], "relation": None,
                      "hi": f"शनि {SIGNS_HI[sat['sign']]} में बिना साथी — कर्म-क्षेत्र राशि से: {SIGN_FIELD[sat['sign']][0]}; श्रम से धीरे-धीरे बनने वाला करियर।",
                      "en": f"Saturn alone in {SIGNS[sat['sign']]} — the field comes from the sign: {SIGN_FIELD[sat['sign']][1]}; a career built slowly by effort."})
    # 3. spouse from Venus
    ven_comp = [r for r in rels if "Venus" in (r["a"], r["b"]) and r["relation"] in ("with", "opposite", "trine")]
    for r in ven_comp:
        other = r["b"] if r["a"] == "Venus" else r["a"]
        if other in ("Jupiter", "Saturn"):
            continue
        lines.append({"topic": "kalatra", "topic_hi": "जीवनसाथी", "planets": ["Venus", other], "relation": r["relation"],
                      "hi": f"शुक्र (जीवनसाथी) का {PLANETS_HI[other]} से {r['relation_hi']}: साथी में {KARAKA[other][0]} के गुण/पृष्ठभूमि; {_strength_words(r['relation'], True)}।",
                      "en": f"Venus (spouse) {r['relation']} {other}: the partner carries {KARAKA[other][1]} traits/background; {_strength_words(r['relation'], False)}."})
    if ven["sign"] == jup["sign"] or (ven["sign"] - jup["sign"]) % 12 == 6:
        lines.append({"topic": "kalatra", "topic_hi": "जीवनसाथी", "planets": ["Venus", "Jupiter"], "relation": "with/opposite",
                      "hi": "शुक्र-गुरु युति/सम्मुख: विवाह और साथी जीवन का केंद्रीय विषय; परंपरा में सुखद दांपत्य का संकेत।", "en": "Venus with/opposite Jupiter: marriage is central; tradition reads a supportive partnership."})
    # 4. Rahu / Ketu colour
    for node, lbl_hi, lbl_en in (("Rahu", "राहु", "Rahu"), ("Ketu", "केतु", "Ketu")):
        for r in rels:
            if node in (r["a"], r["b"]) and r["relation"] == "with":
                other = r["b"] if r["a"] == node else r["a"]
                if other in ("Rahu", "Ketu"):
                    continue
                lines.append({"topic": "chhaya", "topic_hi": "छाया ग्रह", "planets": [node, other], "relation": "with",
                              "hi": f"{lbl_hi} के साथ {PLANETS_HI[other]}: {KARAKA[other][0]} के विषय में {'विदेशी/अपरंपरागत रंग, उतार-चढ़ाव' if node == 'Rahu' else 'वैराग्य, अचानक मोड़, सूक्ष्म बुद्धि'}।",
                              "en": f"{lbl_en} with {other}: {KARAKA[other][1]} takes on {'a foreign/unconventional colour with ups and downs' if node == 'Rahu' else 'detachment, sudden turns, subtle intellect'}."})
    # 5. Jupiter's transit clock — which natal planets are activated this year and next
    clock = []
    try:
        from .transit import positions_at
        from .ephemeris import AnalyticBackend
        from datetime import datetime, timezone
        for y in (date.today().year, date.today().year + 1):
            pos = positions_at(datetime(y, 7, 1, tzinfo=timezone.utc), AnalyticBackend())
            js = pos["Jupiter"]["sign"]
            act = [n for n, x in p.items() if (x["sign"] - js) % 12 in (0, 4, 8)]
            clock.append({"year": y, "jupiter_sign": js, "jupiter_sign_hi": SIGNS_HI[js], "activates": act, "activates_hi": [PLANETS_HI[n] for n in act],
                          "hi": f"{y}: गोचर गुरु {SIGNS_HI[js]} में — " + (f"{', '.join(PLANETS_HI[n] for n in act)} के विषय ({'; '.join(KARAKA[n][0] for n in act)}) सक्रिय।" if act else "जन्म-ग्रहों में से कोई सीधे सक्रिय नहीं; शांत वर्ष।"),
                          "en": f"{y}: transit Jupiter in {SIGNS[js]} — " + (f"activates {', '.join(act)} ({'; '.join(KARAKA[n][1] for n in act)})." if act else "no natal planet directly activated; a quieter year.")})
    except Exception:
        pass
    moon = p["Moon"]
    nak_idx = NAKSHATRAS.index(moon["nakshatra"])
    nk = nadi_of_nakshatra(nak_idx)
    return {"system": "bhrigu_nandi_nadi", "review_status": "draft", "karakas": {k: {"hi": v[0], "en": v[1], "sign_hi": SIGNS_HI[p[k]["sign"]]} for k, v in KARAKA.items() if k in p},
            "relations": rels, "lines": lines, "jupiter_clock": clock,
            "nadi_kuta": {"name": nk, "name_hi": NADI_HI[nk], "nakshatra_hi": moon["nakshatra_hi"]},
            "nadi_amsha": {"moon": nadi_amsha(moon["longitude"]), "lagna": nadi_amsha(chart["lagna"]["longitude"])},
            "note_hi": "भृगु नंदी नाड़ी (BNN) पद्धति का सरलीकृत पाठ: ग्रह-कारक और उनकी युति/सम्मुख/त्रिकोण/आगे-पीछे की राशि से विषय; गुरु का गोचर वर्ष-घड़ी। यह पत्र-आधारित नाड़ी (ताड़पत्र) नहीं है; प्रवृत्ति-संकेत मात्र।",
            "note_en": "A simplified Bhrigu Nandi Nadi reading: planet-karakas and their conjunction/opposition/trine/adjacent-sign links; Jupiter's transit as the year clock. Not leaf-based Nadi; tendency pointers only."}
