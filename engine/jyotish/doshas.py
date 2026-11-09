"""Doshas (Kaal Sarp, Pitru, Mangal with its classical cancellations, Sade Sati status) and remedy pointers
(gemstone by lagna lord / 5th-9th lords, rudraksha by lagna lord, Ishta Devata from the Jaimini karakamsa's 12th).

Classical bases, simplified and labelled as such:
- Kaal Sarp: all seven planets (Sun..Saturn) lie within the arc from Rahu forward to Ketu (or Ketu to Rahu — the "anti" form,
  flagged separately). Twelve names by Rahu's house from the Lagna (Anant .. Shesh Nag). Partial (one planet outside) is reported
  as "partial", which many astrologers do not count.
- Pitru dosha (one common reading): Sun or Moon conjunct Rahu/Ketu, or Rahu/Saturn in the 9th, or the 9th lord in 6/8/12 with Rahu.
- Mangal dosha from Lagna, Moon and Venus (houses 1, 2*, 4, 7, 8, 12; the 2nd by the South Indian school), with the usual
  cancellations: Mars in own/exalted sign, Mars in Mesha (1st), Vrishchika (4th), Makara (7th), Karka (8th), Dhanu (12th),
  Mars aspected by Jupiter, Mars with Jupiter or Moon, Mars in Simha/Kumbha lagna.
Gemstones follow the common "lagna-lord stone, plus stones of the 5th and 9th lords when they are friends" convention, and the
text says plainly that stones for malefic lords (6, 8, 12 lords) are avoided. Nothing here is a prescription.
"""
from __future__ import annotations

from .constants import PLANETS_HI, SIGN_LORDS, SIGNS, SIGNS_HI

KAAL_SARP = ["Anant", "Kulik", "Vasuki", "Shankhpal", "Padma", "Mahapadma", "Takshak", "Karkotak", "Shankhachud", "Ghatak", "Vishdhar", "Shesh Nag"]
KAAL_SARP_HI = ["अनंत", "कुलिक", "वासुकि", "शंखपाल", "पद्म", "महापद्म", "तक्षक", "कर्कोटक", "शंखचूड़", "घातक", "विषधर", "शेषनाग"]
GEMS = {"Sun": ("माणिक्य", "Ruby", "रविवार", "अनामिका"), "Moon": ("मोती", "Pearl", "सोमवार", "कनिष्ठा"), "Mars": ("मूँगा", "Red coral", "मंगलवार", "अनामिका"),
        "Mercury": ("पन्ना", "Emerald", "बुधवार", "कनिष्ठा"), "Jupiter": ("पुखराज", "Yellow sapphire", "गुरुवार", "तर्जनी"), "Venus": ("हीरा / ओपल", "Diamond / opal", "शुक्रवार", "मध्यमा"),
        "Saturn": ("नीलम", "Blue sapphire", "शनिवार", "मध्यमा"), "Rahu": ("गोमेद", "Hessonite", "शनिवार", "मध्यमा"), "Ketu": ("लहसुनिया", "Cat's eye", "मंगलवार", "अनामिका")}
RUDRAKSHA = {"Sun": (12, "बारह मुखी"), "Moon": (2, "दो मुखी"), "Mars": (3, "तीन मुखी"), "Mercury": (4, "चार मुखी"), "Jupiter": (5, "पाँच मुखी"), "Venus": (6, "छह मुखी"),
             "Saturn": (7, "सात मुखी"), "Rahu": (8, "आठ मुखी"), "Ketu": (9, "नौ मुखी")}
ISHTA = {"Sun": ("शिव / सूर्य", "Shiva / Surya"), "Moon": ("गौरी / पार्वती", "Gauri / Parvati"), "Mars": ("हनुमान / कार्तिकेय", "Hanuman / Kartikeya"), "Mercury": ("विष्णु", "Vishnu"),
         "Jupiter": ("ब्रह्मा / दत्तात्रेय", "Brahma / Dattatreya"), "Venus": ("लक्ष्मी", "Lakshmi"), "Saturn": ("शनि / हनुमान", "Shani / Hanuman"), "Rahu": ("दुर्गा", "Durga"), "Ketu": ("गणेश", "Ganesha")}
# karakamsa 12th-house occupant/lord → devata (Jaimini Upadesha Sutras 1.2, common renderings)
FRIEND = {"Sun": {"Moon", "Mars", "Jupiter"}, "Moon": {"Sun", "Mercury"}, "Mars": {"Sun", "Moon", "Jupiter"}, "Mercury": {"Sun", "Venus"}, "Jupiter": {"Sun", "Moon", "Mars"},
          "Venus": {"Mercury", "Saturn"}, "Saturn": {"Mercury", "Venus"}}
SEVEN = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]


def _arc_in(lon: float, start: float, end: float) -> bool:
    return (lon - start) % 360.0 <= (end - start) % 360.0


def kaal_sarp(chart: dict) -> dict:
    p = {x["name"]: x for x in chart["planets"]}
    rahu, ketu = p["Rahu"]["longitude"], p["Ketu"]["longitude"]
    inside_rk = [n for n in SEVEN if _arc_in(p[n]["longitude"], rahu, ketu)]
    inside_kr = [n for n in SEVEN if _arc_in(p[n]["longitude"], ketu, rahu)]
    full = len(inside_rk) == 7 or len(inside_kr) == 7
    partial = (len(inside_rk) == 6 or len(inside_kr) == 6) and not full
    direction = "rahu_to_ketu" if len(inside_rk) >= len(inside_kr) else "ketu_to_rahu"
    h = p["Rahu"]["house"]
    name, name_hi = KAAL_SARP[h - 1], KAAL_SARP_HI[h - 1]
    outside = [n for n in SEVEN if n not in (inside_rk if direction == "rahu_to_ketu" else inside_kr)]
    status = "full" if full else "partial" if partial else "none"
    hi = {"full": f"कालसर्प योग ({name_hi}) — सातों ग्रह राहु-केतु अक्ष के {'राहु से केतु' if direction == 'rahu_to_ketu' else 'केतु से राहु'} की ओर एक ही तरफ़ हैं; राहु लग्न से {h}वें भाव में।",
          "partial": f"आंशिक कालसर्प ({name_hi}) — {PLANETS_HI[outside[0]] if outside else ''} अक्ष से बाहर है; कई विद्वान इसे दोष नहीं गिनते।",
          "none": "कालसर्प योग नहीं है।"}[status]
    en = {"full": f"Kaal Sarp yoga ({name}) — all seven planets lie on one side of the Rahu–Ketu axis ({'Rahu to Ketu' if direction == 'rahu_to_ketu' else 'Ketu to Rahu'}); Rahu in house {h} from the Lagna.",
          "partial": f"Partial Kaal Sarp ({name}) — {outside[0] if outside else ''} is outside the axis; many astrologers do not count this.",
          "none": "No Kaal Sarp yoga."}[status]
    return {"present": full, "partial": partial, "status": status, "type": name if status != "none" else None, "type_hi": name_hi if status != "none" else None,
            "rahu_house": h, "direction": direction, "outside": outside, "text_hi": hi, "text_en": en,
            "note_hi": "कालसर्प शास्त्रीय योग-ग्रंथों में नहीं, बाद की परंपरा में है; इसका फल पूरी कुंडली के साथ देखा जाता है।",
            "note_en": "Kaal Sarp is a later tradition, not in the classical yoga texts; it is weighed with the whole chart."}


def pitru(chart: dict) -> dict:
    p = {x["name"]: x for x in chart["planets"]}
    lagna_sign = chart["lagna"]["sign"]
    ninth_sign = (lagna_sign + 8) % 12
    ninth_lord = SIGN_LORDS[ninth_sign]
    reasons_hi, reasons_en = [], []
    for lum in ("Sun", "Moon"):
        for node in ("Rahu", "Ketu"):
            if p[lum]["sign"] == p[node]["sign"]:
                reasons_hi.append(f"{PLANETS_HI[lum]} {PLANETS_HI[node]} के साथ ({SIGNS_HI[p[lum]['sign']]})"); reasons_en.append(f"{lum} with {node} ({SIGNS[p[lum]['sign']]})")
    for m in ("Rahu", "Saturn", "Ketu"):
        if p[m]["house"] == 9:
            reasons_hi.append(f"{PLANETS_HI[m]} नवम भाव में"); reasons_en.append(f"{m} in the 9th house")
    if p[ninth_lord]["house"] in (6, 8, 12):
        reasons_hi.append(f"नवमेश {PLANETS_HI[ninth_lord]} {p[ninth_lord]['house']}वें भाव में"); reasons_en.append(f"9th lord {ninth_lord} in house {p[ninth_lord]['house']}")
    if p["Sun"]["house"] == 9 and any(p[m]["sign"] == p["Sun"]["sign"] for m in ("Saturn", "Rahu", "Ketu")):
        reasons_hi.append("नवम भाव में सूर्य पाप-ग्रह के साथ"); reasons_en.append("Sun in the 9th with a malefic")
    present = len(reasons_hi) >= 1
    strong = len(reasons_hi) >= 2
    return {"present": present, "strong": strong, "reasons_hi": reasons_hi, "reasons_en": reasons_en,
            "text_hi": ("पितृ दोष के संकेत: " + "; ".join(reasons_hi) + "।" if present else "पितृ दोष के सामान्य संकेत नहीं मिले।"),
            "text_en": ("Pitru dosha indications: " + "; ".join(reasons_en) + "." if present else "No usual Pitru dosha indication."),
            "note_hi": "पितृ दोष की परिभाषा ग्रंथों में एक नहीं; यहाँ सूर्य/चंद्र-राहु/केतु युति, नवम भाव और नवमेश की स्थिति देखी गई है। परंपरागत उपाय: पितृ पक्ष में तर्पण/श्राद्ध।",
            "note_en": "Pitru dosha has no single textual definition; this checks Sun/Moon with the nodes, the 9th house and its lord. Traditional remedy: tarpana/shraddha in Pitru Paksha."}


def mangal(chart: dict) -> dict:
    p = {x["name"]: x for x in chart["planets"]}
    mars = p["Mars"]
    lagna_sign = chart["lagna"]["sign"]
    def house_from(ref_sign: int) -> int:
        return (mars["sign"] - ref_sign) % 12 + 1
    counts = {"lagna": house_from(lagna_sign), "moon": house_from(p["Moon"]["sign"]), "venus": house_from(p["Venus"]["sign"])}
    DOSHA = {1, 4, 7, 8, 12}
    flags = {k: v in DOSHA for k, v in counts.items()}
    second = {k: v == 2 for k, v in counts.items()}
    cancels_hi, cancels_en = [], []
    ms = mars["sign"]
    if mars.get("dignity") in ("own", "exalted"):
        cancels_hi.append("मंगल स्वराशि/उच्च में"); cancels_en.append("Mars in own/exalted sign")
    hl = counts["lagna"]
    if (hl, ms) in ((1, 0), (4, 7), (7, 9), (8, 3), (12, 8)):
        cancels_hi.append(f"{SIGNS_HI[ms]} का मंगल {hl}वें भाव में (परिहार-स्थान)"); cancels_en.append(f"Mars in {SIGNS[ms]} in house {hl} (exempt placement)")
    if lagna_sign in (4, 10):
        cancels_hi.append("सिंह/कुंभ लग्न"); cancels_en.append("Simha or Kumbha lagna")
    if p["Jupiter"]["sign"] == ms or (ms - p["Jupiter"]["sign"]) % 12 in (4, 6, 8):
        cancels_hi.append("गुरु की युति/दृष्टि मंगल पर"); cancels_en.append("Jupiter conjunct or aspecting Mars")
    if p["Moon"]["sign"] == ms:
        cancels_hi.append("मंगल चंद्र के साथ"); cancels_en.append("Mars with the Moon")
    present_any = any(flags.values())
    level = "none" if not present_any else ("low" if cancels_hi else ("high" if sum(flags.values()) >= 2 else "medium"))
    where_hi = ", ".join(f"{ {'lagna': 'लग्न', 'moon': 'चंद्र', 'venus': 'शुक्र'}[k]} से {counts[k]}" for k in counts if flags[k])
    where_en = ", ".join(f"{counts[k]} from {k.capitalize()}" for k in counts if flags[k])
    return {"present": present_any, "level": level, "houses": counts, "flags": flags, "second_house": second, "cancellations_hi": cancels_hi, "cancellations_en": cancels_en,
            "text_hi": (f"मंगल दोष ({where_hi}वें भाव में मंगल)" + (f"; परिहार: {', '.join(cancels_hi)}" if cancels_hi else "") + "।") if present_any else "लग्न, चंद्र और शुक्र — तीनों से मंगल दोष नहीं।",
            "text_en": (f"Mangal dosha (Mars in house {where_en})" + (f"; cancellations: {', '.join(cancels_en)}" if cancels_en else "") + ".") if present_any else "No Mangal dosha from Lagna, Moon or Venus.",
            "note_hi": "दक्षिण परंपरा दूसरा भाव भी गिनती है (यहाँ अलग दिखाया)। मिलान में दोनों कुंडलियों की तुलना करें।",
            "note_en": "The South Indian school also counts the 2nd house (shown separately). In matching, compare both charts."}


def remedies(chart: dict) -> dict:
    p = {x["name"]: x for x in chart["planets"]}
    lagna_sign = chart["lagna"]["sign"]
    lord = SIGN_LORDS[lagna_sign]
    fifth, ninth = SIGN_LORDS[(lagna_sign + 4) % 12], SIGN_LORDS[(lagna_sign + 8) % 12]
    avoid = {SIGN_LORDS[(lagna_sign + h - 1) % 12] for h in (6, 8, 12)} - {lord}
    stones = []
    def stone(pl, role_hi, role_en, primary):
        g = GEMS[pl]
        stones.append({"planet": pl, "planet_hi": PLANETS_HI[pl], "gem_hi": g[0], "gem_en": g[1], "day_hi": g[2], "finger_hi": g[3], "role_hi": role_hi, "role_en": role_en, "primary": primary,
                       "weak": p[pl].get("dignity") == "debilitated" or p[pl]["house"] in (6, 8, 12)})
    stone(lord, "लग्नेश (जीवन-रत्न)", "Lagna lord (life stone)", True)
    for pl, role_hi, role_en in ((ninth, "नवमेश (भाग्य-रत्न)", "9th lord (fortune stone)"), (fifth, "पंचमेश (बुद्धि/संतान)", "5th lord (intellect/children)")):
        if pl != lord and pl not in avoid and (pl in FRIEND.get(lord, set()) or pl == lord):
            stone(pl, role_hi, role_en, False)
    r = RUDRAKSHA[lord]
    j = chart.get("jaimini") or {}
    ishta = None
    if j.get("karakamsa"):
        k12 = (j["karakamsa"]["sign"] + 11) % 12
        occupants = [x["name"] for x in chart["planets"] if x.get("navamsa_sign") == k12 and x["name"] not in ("Rahu", "Ketu")]
        dev_pl = occupants[0] if occupants else SIGN_LORDS[k12]
        ishta = {"planet": dev_pl, "planet_hi": PLANETS_HI[dev_pl], "devata_hi": ISHTA[dev_pl][0], "devata_en": ISHTA[dev_pl][1], "via": "karakamsa_12th", "karakamsa_sign_hi": j["karakamsa"]["sign_name_hi"],
                 "text_hi": f"कारकांश ({j['karakamsa']['sign_name_hi']}) से 12वें भाव के {'ग्रह' if occupants else 'स्वामी'} {PLANETS_HI[dev_pl]} से इष्ट देवता का संकेत: {ISHTA[dev_pl][0]}।",
                 "text_en": f"From the {'occupant' if occupants else 'lord'} ({dev_pl}) of the 12th from the karakamsa ({j['karakamsa']['sign_name']}): Ishta Devata pointer {ISHTA[dev_pl][1]}."}
    return {"gemstones": stones, "avoid_planets": sorted(avoid), "avoid_planets_hi": [PLANETS_HI[x] for x in sorted(avoid)],
            "rudraksha": {"planet": lord, "mukhi": r[0], "mukhi_hi": r[1], "text_hi": f"लग्नेश {PLANETS_HI[lord]} के अनुसार {r[1]} रुद्राक्ष।", "text_en": f"{r[0]}-mukhi rudraksha for the Lagna lord {lord}."},
            "ishta_devata": ishta,
            "mantra_hi": {"Sun": "ॐ घृणिः सूर्याय नमः", "Moon": "ॐ सोम सोमाय नमः", "Mars": "ॐ अं अंगारकाय नमः", "Mercury": "ॐ बुं बुधाय नमः", "Jupiter": "ॐ बृं बृहस्पतये नमः",
                         "Venus": "ॐ शुं शुक्राय नमः", "Saturn": "ॐ शं शनैश्चराय नमः", "Rahu": "ॐ रां राहवे नमः", "Ketu": "ॐ कें केतवे नमः"}[lord],
            "note_hi": "रत्न/रुद्राक्ष/इष्ट परंपरागत संकेत हैं (लग्नेश, त्रिकोणेश, कारकांश); रत्न धारण से पहले योग्य ज्योतिषी से पूरी कुंडली दिखाएँ — 6, 8, 12 भावों के स्वामियों के रत्न टाले जाते हैं।",
            "note_en": "Gem/rudraksha/Ishta pointers follow convention (lagna lord, trine lords, karakamsa); consult a qualified astrologer before wearing a stone — stones of the 6th, 8th and 12th lords are avoided."}


def layer(chart: dict) -> dict:
    return {"kaal_sarp": kaal_sarp(chart), "pitru": pitru(chart), "mangal": mangal(chart), "remedies": remedies(chart), "review_status": "draft"}
