"""Build data/i18n_en.json (Hindi -> English dictionary used by the web page and the report).

    python tools/build_i18n.py

Sources, in order of trust:
  1. Hindi/English pairs already present in data/knowledge/*.json and data/rules/*.json (keys `x_hi` + `x`/`x_en`,
     tarot `hi` + `name`, and every rule's text_hi -> text_en)
  2. constants (planet, sign, nakshatra, weekday, tithi, yoga, karana names)
  3. UI labels written by hand below
Unknown Hindi stays Hindi; the translation is therefore PARTIAL and says so in the UI.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from jyotish import constants as C  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PHRASES: dict[str, str] = {}   # substring replacement, longest first
EXACT: dict[str, str] = {}     # whole-text-node replacement only (short/ambiguous strings)


def put(hi: str, en: str):
    hi, en = str(hi).strip(), str(en).strip()
    if not hi or not en or hi == en:
        return
    (PHRASES if len(hi) >= 3 else EXACT).setdefault(hi, en)


def harvest(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.endswith("_hi"):
                base = k[:-3]
                en = obj.get(base + "_en", obj.get(base))
                if isinstance(v, str) and isinstance(en, str):
                    put(v, en)
                elif isinstance(v, list) and isinstance(en, list) and len(v) == len(en):
                    for a, b in zip(v, en):
                        if isinstance(a, str) and isinstance(b, str):
                            put(a, b)
            harvest(v)
        if isinstance(obj.get("hi"), str) and isinstance(obj.get("name"), str):
            put(obj["hi"], obj["name"])
        if isinstance(obj.get("hi"), str) and isinstance(obj.get("en"), str):
            put(obj["hi"], obj["en"])
    elif isinstance(obj, list):
        for v in obj:
            harvest(v)


for f in (ROOT / "data" / "knowledge").glob("*.json"):
    harvest(json.loads(f.read_text(encoding="utf-8")))
lk = json.loads((ROOT / "data" / "lalkitab.json").read_text(encoding="utf-8"))
LK_THEMES_EN = {"1": "self, personality and beginnings", "2": "family, savings and speech", "3": "siblings, courage and effort",
                "4": "mother, home and peace of mind", "5": "children, learning and creativity", "6": "service, health-awareness and competition",
                "7": "spouse, partnership and business", "8": "mystery, change and shared resources", "9": "fortune, teacher and dharma",
                "10": "work, position and father", "11": "income, friends and fulfilment of wishes", "12": "expenses, solitude and foreign lands"}
for k, v in lk["house_theme_hi"].items():
    EXACT[v] = LK_THEMES_EN[k]
for f in (ROOT / "data" / "rules").glob("*.json"):
    for r in json.loads(f.read_text(encoding="utf-8")).get("rules", []):
        put(r["text_hi"], r["text_en"])

import json as _json  # noqa: E402
for _pl in _json.loads((ROOT / "data" / "places.json").read_text(encoding="utf-8"))["places"]:
    put(_pl["hi"], _pl["name"])                         # city names shown in the dropdown / search
from jyotish import patri as _patri  # noqa: E402
for _en, _hi in _patri.HI.items():
    put(_hi, _en)
for _en, _hi in _patri.TATTVA_HI.items():
    put(_hi, _en)
for _en, _hi in _patri.RITU_HI.items():
    put(_hi, _en)
for _i, _hi in enumerate(_patri.MASA_HI):
    put(_hi, _patri.MASA[_i])
for _i, _hi in enumerate(_patri.SYLLABLES):
    put(_hi, _patri.SYLLABLES_EN[_i])
    for _a, _b in zip(_hi.split(), _patri.SYLLABLES_EN[_i].split()):
        put(_a, _b)
put(_patri.NOTE_HI, _patri.NOTE_EN)
from jyotish import compute_chart as _cc  # noqa: E402
_ch = _cc("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)["chalit"]
put(_ch["note_hi"], _ch["note_en"])
_full = _cc("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)
put(_full["sensitivity"]["note_hi"], _full["sensitivity"]["note_en"])
put(_full["kp"]["note_hi"], _full["kp"]["note_en"])
put(_full["jaimini"]["note_hi"], _full["jaimini"]["note_en"])
from jyotish import jaimini as _jm  # noqa: E402
for _k, _hi in _jm.KARAKA_HI.items():
    put(_hi, _k)
for _k, _hi in _jm.KARAKA_MEANS_HI.items():
    put(_hi, _jm.KARAKA_MEANS[_k])
for _h, _hi in _jm.PADA_HI.items():
    put(_hi, _jm.PADA_EN[_h])
put(_full["transit_calendar"]["note_hi"], _full["transit_calendar"]["note_en"])
for _en, _hi in _patri.GHATA_HI.items():
    put(_hi, _en)
put("अधिक", "Adhika")
from jyotish import ask as _ask  # noqa: E402
put(_ask.SAFE["hi"], _ask.SAFE["en"])
put(_ask.DISCLAIMER["hi"], _ask.DISCLAIMER["en"])
put("इस प्रश्न का उत्तर मेरी सामग्री में नहीं मिला। कृपया ग्रह, भाव, राशि, नक्षत्र या दशा के बारे में पूछिए।",
    "I could not find this in my material. Please ask about a planet, house, sign, nakshatra or dasha.")

from jyotish import tarot  # noqa: E402
for c in tarot.deck():
    put(c["name_hi"], c["name"])
    put(c["upright_hi"], c["upright"])
    put(c["reversed_hi"], c["reversed"])
for sp in tarot.spreads().values():
    put(sp["hi"], sp["name"])
    for ps in sp["positions"]:
        put(ps["hi"], ps.get("en", ""))
put(tarot.DISCLAIMER_HI, "Tarot is a tool for self-reflection, not a guarantee of prediction. Take big decisions (health, money, law) on an expert's advice.")

for en, hi in C.PLANETS_HI.items():
    put(hi, en)
for en, hi in zip(C.SIGNS, C.SIGNS_HI):
    put(hi, en)
for en, hi in zip(C.NAKSHATRAS, C.NAKSHATRAS_HI):
    put(hi, en)
for en, hi in zip(C.VARA, C.VARA_HI):
    put(hi, en)
for d in (C.TITHI_HI, C.PAKSHA_HI, C.YOGA_HI, C.KARANA_HI):
    for en, hi in d.items():
        put(hi, en)
for en, hi in C.PLANETS_SHORT_HI.items():
    EXACT[hi] = en[:2]

UI = {
 # --- report-specific strings are in REPORT below ---
 # page chrome
 "कुंडली": "Kundali", "पहला संस्करण": "first version", "मेरी कुंडलियाँ": "My charts",
 "ईमेल से लॉगिन (लिंक ईमेल पर आएगा)": "Log in by email (a link will be sent)", "लॉगिन लिंक भेजें": "Send login link",
 "इस कुंडली को सेव करें": "Save this chart", "लॉग-आउट": "Log out", "आपका ईमेल": "Your email",
 "नाम (वैकल्पिक)": "Name (optional)", "जन्म तारीख": "Date of birth", "जन्म समय": "Time of birth",
 "शहर खोजिए": "Search city", "या सूची से": "or pick from list", "जैसे: जबलपुर, Bombay": "e.g. Jabalpur, Bombay",
 "अन्य (नीचे अक्षांश/देशांतर भरें)": "Other (enter latitude/longitude below)",
 "अक्षांश (उत्तर +)": "Latitude (north +)", "देशांतर (पूर्व +)": "Longitude (east +)", "समय-क्षेत्र (IANA)": "Time zone (IANA)",
 "कुंडली बनाइए": "Make chart", "शहर का नाम": "City name",
 "जबलपुर": "Jabalpur", "दिल्ली": "Delhi", "मुंबई": "Mumbai", "कोलकाता": "Kolkata", "चेन्नई": "Chennai", "पटना": "Patna",
 "रांची": "Ranchi", "वाराणसी": "Varanasi", "लखनऊ": "Lucknow", "भोपाल": "Bhopal",
 "रिपोर्ट खोलिए (PDF के लिए प्रिंट कीजिए)": "Open report (print for PDF)",
 "लग्न कुंडली (D1)": "Lagna chart (D1)", "वर्ग कुंडली": "Divisional charts", "सीखिए": "Learn",
 "किसी खाने या ग्रह पर क्लिक कीजिए।": "Click a house or a planet.",
 "ग्रह स्थिति": "Planet positions", "ग्रह": "Planet", "राशि": "Sign", "अंश": "Degree", "भाव": "House",
 "नक्षत्र (पाद)": "Nakshatra (pada)", "वक्री": "retrograde", "उच्च": "exalted", "नीच": "debilitated", "स्वराशि": "own sign",
 "पंचांग": "Panchang", "वार": "Weekday", "तिथि": "Tithi", "नक्षत्र": "Nakshatra", "योग": "Yoga", "करण": "Karana",
 "योग और दोष": "Yogas and doshas", "नहीं": "No", "बना है": "Present",
 "(ड्राफ़्ट: विद्वान-समीक्षा बाकी)": "(draft: scholar review pending)", "ड्राफ़्ट (समीक्षा बाकी)": "Draft (review pending)",
 "अष्टकवर्ग": "Ashtakavarga", "कुल": "Total", "कमज़ोर": "weak", "मज़बूत": "strong",
 "ग्रह-वार भिन्नाष्टकवर्ग (BAV)": "Planet-wise Bhinnashtakavarga (BAV)",
 "गोचर (आज का आकाश)": "Transit (today's sky)", "अभी साढ़ेसाती नहीं है।": "Sade Sati is not running now.",
 "चंद्र से भाव": "House from Moon", "लग्न से भाव": "House from Lagna", "बिंदु": "Bindus", "संकेत": "Indication",
 "सहायक": "supportive", "कठिन": "demanding", "मिश्रित": "mixed", "अनुकूल": "favourable", "परिश्रम-साध्य": "needs effort",
 "ग्रह-बल (षड्बल)": "Planet strength (Shadbala)", "स्थान": "Sthana", "दिक्": "Dig", "काल": "Kala",
 "दृग्": "Drik", "केंद्रादि": "Kendradi", "नैसर्गिक": "Naisargika", "क्रम": "Rank",
 "दिन का मुहूर्त": "Muhurta of the day", "सूर्योदय / सूर्यास्त": "Sunrise / Sunset", "वैदिक वार": "Vedic weekday",
 "राहुकाल": "Rahu Kaal", "यमगंड": "Yamaganda", "गुलिक": "Gulika", "अभिजित": "Abhijit",
 "चौघड़िया (दिन)": "Choghadiya (day)", "चौघड़िया (रात)": "Choghadiya (night)", "शुभ": "good", "अशुभ": "inauspicious", "सम": "neutral",
 "अंक ज्योतिष": "Numerology", "मूलांक": "Moolank (birth number)", "भाग्यांक": "Bhagyank (destiny number)",
 "लो-शू ग्रिड": "Lo Shu grid", "(ड्राफ़्ट)": "(draft)", "शास्त्रीय संकेत (ड्राफ़्ट नियम)": "Classical indications (draft rules)",
 "वर्षफल (सौर-वापसी कुंडली)": "Varshaphal (solar-return chart)", "वर्षफल देखिए": "Show Varshaphal",
 "जीवन समय-रेखा (दशा के अनुसार)": "Life timeline (by dasha)", "बीता": "past", "चल रही": "running", "आगे": "ahead",
 "अंतर्दशा:": "Antardasha:", "विंशोत्तरी दशा": "Vimshottari dasha", "अभी चल रही:": "Running now:",
 "महादशा": "Mahadasha", "आयु": "age", "वर्ष": "years", "भाव": "house",
 "— लग्न:": "— Lagna:", "चंद्र राशि:": "Moon sign:", "· जन्म नक्षत्र:": "· birth nakshatra:",
 # matching
 "कुंडली मिलान (अष्टकूट, 36 गुण)": "Kundali matching (Ashtakoota, 36 points)", "वर (Groom)": "Groom", "वधू (Bride)": "Bride",
 "नाम": "Name", "अक्षांश": "Latitude", "देशांतर": "Longitude", "समय-क्षेत्र": "Time zone", "मिलान देखिए": "Show matching",
 "— अच्छा (25-32)": "— good (25-32)", "कूट": "Koota", "अंक": "Points", "कारण": "Reason", "भरोसा": "Confidence",
 "पक्का नियम": "firm rule", "वर्ण": "Varna", "वश्य": "Vashya", "तारा": "Tara", "योनि": "Yoni", "ग्रह मैत्री": "Graha Maitri",
 "घात चक्र (ड्राफ़्ट)": "Ghata chakra (draft)", "घात चक्र": "Ghata chakra", "प्रहर": "Prahar", "चंद्र": "Moon", "स्त्री चंद्र": "Moon (female)",
 "घात मास": "Ghata masa", "घात तिथि": "Ghata tithi", "घात वार": "Ghata vara", "घात नक्षत्र": "Ghata nakshatra", "घात योग": "Ghata yoga",
 "घात करण": "Ghata karana", "घात प्रहर": "Ghata prahar", "घात चंद्र": "Ghata Moon sign", "स्त्री घात चंद्र": "Ghata Moon sign (female)",
 "घात चक्र में ये मास, तिथि, वार आदि जातक के लिए परंपरा में सावधानी के समय माने गए हैं। सारणी विद्वान-समीक्षा के अधीन है।":
 "In the ghata chakra these months, tithis, weekdays etc. are traditionally held to be times of caution for the native. The table awaits scholar review.",
 "गण": "Gana", "भकूट": "Bhakoot", "नाड़ी": "Nadi", "मंगल दोष तुलना:": "Mangal Dosha comparison:",
 "दोनों की स्थिति समान है (दोनों मांगलिक या दोनों नहीं)।": "Both are in the same situation (both manglik or neither).",
 "मांगलिक नहीं": "not manglik", "मांगलिक": "manglik", "वर:": "Groom:", "वधू:": "Bride:",
 # tarot
 "टैरो": "Tarot", "प्रश्न (वैकल्पिक)": "Question (optional)", "स्प्रेड": "Spread", "एक कार्ड": "One card",
 "भूत · वर्तमान · भविष्य": "Past · Present · Future", "दस-कार्ड क्रॉस": "Ten-card cross", "कार्ड खींचिए": "Draw cards",
 "बीता प्रभाव": "Past influence", "वर्तमान स्थिति": "Present situation", "संभावित दिशा": "Likely direction",
 # vastu
 "वास्तु जाँच": "Vastu check", "पूजा घर": "Puja room", "रसोई": "Kitchen", "मुख्य शयनकक्ष": "Master bedroom",
 "बच्चों का कमरा": "Children's room", "अतिथि कक्ष": "Guest room", "बैठक / ड्रॉइंग रूम": "Living / drawing room",
 "भोजन कक्ष": "Dining room", "अध्ययन कक्ष": "Study room", "शौचालय": "Toilet", "स्नानघर": "Bathroom", "भंडार कक्ष": "Store room",
 "सीढ़ियाँ": "Staircase", "बोरवेल / भूमिगत टंकी": "Borewell / underground tank", "छत की पानी टंकी": "Overhead water tank",
 "गैराज": "Garage", "मुख्य द्वार": "Main entrance", "उत्तर": "North", "ईशान (उत्तर-पूर्व)": "Ishaan (north-east)",
 "पूर्व": "East", "आग्नेय (दक्षिण-पूर्व)": "Agneya (south-east)", "दक्षिण": "South", "नैऋत्य (दक्षिण-पश्चिम)": "Nairutya (south-west)",
 "पश्चिम": "West", "वायव्य (उत्तर-पश्चिम)": "Vayavya (north-west)", "केंद्र (ब्रह्मस्थान)": "Centre (Brahmasthan)",
 "+ कमरा जोड़िए": "+ Add room", "जाँचिए": "Check", "कमरा": "Room", "दिशा": "Direction", "स्थिति": "Status",
 "कारण / सुझाव": "Reason / suggestion", "उत्तम": "excellent",
 "दुर्ग-भिलाई": "Durg-Bhilai",
 # patri
 "जन्म विवरण": "Birth details", "अवकहड़ा चक्र": "Avakahada chakra", "वार": "Weekday", "नक्षत्र-चरण": "Nakshatra-pada",
 "सूर्योदय / सूर्यास्त": "Sunrise / sunset", "इष्टकाल (घटी:पल)": "Ishta kaal (ghati:pala)", "मास (अमांत)": "Lunar month (amanta)", "मास (अमांत / पूर्णिमांत)": "Lunar month (amanta / purnimanta)",
 "मास (अमांत) ≈": "Lunar month (amanta) ≈", "ऋतु": "Season (ritu)", "अयन": "Ayana", "विक्रम संवत्": "Vikram samvat", "शक संवत्": "Shaka samvat",
 "विक्रम संवत् ≈": "Vikram samvat ≈", "शक संवत् ≈": "Shaka samvat ≈",
 "सूर्य राशि (पाश्चात्य)": "Sun sign (tropical)", "अयनांश (लाहिरी)": "Ayanamsa (Lahiri)", "लग्न-लग्नेश": "Lagna & lord",
 "राशि-राशि स्वामी": "Moon sign & lord", "नक्षत्र स्वामी": "Nakshatra lord", "वर्ण": "Varna", "वश्य": "Vashya", "योनि": "Yoni",
 "गण": "Gana", "नाड़ी": "Nadi", "तत्व": "Element (tattva)", "नाम अक्षर": "Name syllable",
 "भाव-चलित (श्रीपति)": "Bhava chalit (Sripati)", "कृष्णमूर्ति पद्धति (KP)": "Krishnamurti Paddhati (KP)", "जैमिनी": "Jaimini", "व": "R", "जैमिनी: चर कारक": "Jaimini: chara karakas", "आरूढ़ पद": "Arudha padas",
 "जैमिनी: चर कारक और आरूढ़ पद": "Jaimini: chara karakas and arudha padas", "कारक": "Karaka", "विषय": "Signifies", "पद": "Pada", "पद की राशि": "Pada sign", "लग्न से भाव": "House from Lagna",
 "8-कारक (राहु सहित)": "8-karaka scheme (with Rahu)", "अपवाद": "exception", "(अपवाद)": "(exception)", "कारकांश:": "Karakamsa:", "भाव-स्पष्ट": "Cusp", "राशि-स्वामी": "Sign lord",
 "नक्षत्र-स्वामी": "Star lord", "उप-स्वामी": "Sub lord", "उप-उप": "Sub-sub", "भाव (KP)": "House (KP)", "भाव-कारक (चार स्तर)": "House significators (four levels)",
 "क: भावस्थ ग्रहों के नक्षत्र में": "A: in stars of occupants", "ख: भावस्थ": "B: occupants", "ग: भावेश के नक्षत्र में": "C: in stars of owners", "घ: भावेश": "D: owners", "जन्म-समय की संवेदनशीलता": "Birth-time sensitivity", "पहले": "earlier", "बाद": "later",
 "स्थिर (15 मिनट तक)": "stable (up to 15 min)", "सावधान (5-15 मिनट)": "caution (5-15 min)", "संवेदनशील (5 मिनट से कम)": "sensitive (under 5 min)",
 "स्थिर": "stable", "सावधान": "caution", "संवेदनशील": "sensitive", "लग्न राशि": "Lagna sign", "नवांश लग्न": "Navamsa Lagna", "चंद्र राशि": "Moon sign",
 "चंद्र नक्षत्र (दशा स्वामी)": "Moon nakshatra (dasha lord)", "आगामी 12 महीनों का गोचर": "Transits of the next 12 months", "मास-वार ग्रह-राशियाँ": "Month-by-month planet signs",
 "अगले 12 महीनों में धीमे ग्रहों का कोई राशि-प्रवेश नहीं।": "No sign ingress of the slow planets in the next 12 months.", "धीमे ग्रहों का कोई राशि-प्रवेश नहीं।": "No sign ingress of the slow planets.",
 "माह": "Month", "राशि के साथ छोटा अंक = चंद्र से भाव। व = वक्री।": "Small number next to the sign = house from the Moon. R = retrograde.", "दोष:": "Dosha:", "(परिहार मिला)": "(cancelled)", "परिहार:": "Parihara:",
 "भकूट या नाड़ी दोष नहीं।": "No Bhakoot or Nadi dosha.", "भकूट दोष": "Bhakoot dosha", "नाड़ी दोष": "Nadi dosha",
 "एक ही राशि, अलग नक्षत्र": "same Moon sign, different nakshatras", "एक ही नक्षत्र, अलग चरण": "same nakshatra, different padas",
 "एक ही नक्षत्र, अलग राशि": "same nakshatra in different signs", "दोनों का जन्म-नक्षत्र एक ही है": "same birth nakshatra", "भाव-मध्य (12)": "House middles (12)", "सभी ग्रह राशि-भाव वाले भाव में ही हैं।": "Every planet stays in its rasi house.",
 "चेष्टा": "Cheshta", "इष्ट": "Ishta", "कष्ट": "Kashta", "रूप": "Rupas", "स्थान": "Sthana", "काल": "Kala", "दृग्": "Drik",
 # tabs
 "मिलान": "Matching", "वास्तु": "Vastu", "हस्तरेखा": "Palmistry", "मेरी कुंडलियाँ": "My charts", "सारांश": "Summary", "ग्रह व बल": "Planets & strength",
 "पंचांग व मुहूर्त": "Panchang & muhurta", "योग व संकेत": "Yogas & indications", "दशा व समय-रेखा": "Dasha & timeline",
 "अष्टकवर्ग व गोचर": "Ashtakavarga & transits", "वर्षफल": "Varshaphal", "अंक": "Numbers",
 # ask
 "पूछिए (ज्योतिष सहायक)": "Ask (astrology assistant)", "पूछिए": "Ask", "खोज रहा हूँ…": "Searching…", "स्रोत": "Sources",
 "ग्रह, भाव, राशि, नक्षत्र, दशा, योग, वास्तु या टैरो के बारे में पूछिए। उत्तर केवल इस ऐप की अपनी सामग्री से आते हैं। कुंडली बनाने के बाद \"मेरा\" वाले प्रश्न उसी कुंडली से जुड़ते हैं।":
 "Ask about planets, houses, signs, nakshatras, dashas, yogas, Vastu or tarot. Answers come only from this app's own content. After you make a chart, questions with \"my\" use that chart.",
 "जैसे: शनि 10वें भाव में क्या फल देता है?": "e.g. What does Saturn in the 10th house indicate?",
 # palmistry
 "हस्तरेखा (मार्गदर्शित)": "Palmistry (guided)", "पढ़िए": "Read", "लंबी": "long", "मध्यम": "medium", "छोटी": "short",
 "सीधी": "straight", "साफ़": "clear", "हल्की": "faint", "नहीं दिखती": "not visible", "दिखती है": "visible",
 "उभरा हुआ": "raised", "सपाट": "flat", "घुमावदार": "curved", "जीवन रेखा": "Life line", "मस्तिष्क रेखा": "Head line",
 "हृदय रेखा": "Heart line", "भाग्य रेखा": "Fate line", "सूर्य रेखा": "Sun line", "पर्वत": "Mount", "हाथ": "Hand",
}

REPORT = {
 "जातक": "native", "सारांश": "Summary", "लग्न": "Lagna", "चंद्र राशि / नक्षत्र": "Moon sign / nakshatra",
 "चल रही दशा": "Running dasha", "नवांश (D9)": "Navamsa (D9)", "योग / करण": "Yoga / Karana",
 "जीवन समय-रेखा": "Life timeline", "आरंभ": "Start", "समाप्ति": "End", "सक्रिय क्षेत्र": "Active areas",
 "स्तर": "Level", "बल-संकेत": "Strength indication", "कुंडली रिपोर्ट": "Kundali report", "कुंडलियाँ": "Charts",
 "कुंडली रिपोर्ट — जातक": "Kundali report — native", "कुल (चेष्टा के बिना)": "Total (without cheshta)",
 "उस भाव में ग्रह": "Planets in that house", "देखा गया भाव": "House aspected", "स्थित भाव": "House occupied",
 "पक्का घर": "Permanent house", "घर (लग्न)": "House (Lagna)", "घर (मेष)": "House (Aries)", "परंपरागत उपाय": "Traditional remedy",
 "दृष्टि": "Aspect", "साढ़ेसाती": "Sade Sati", "कालसर्प दोष": "Kalsarpa dosha", "गजकेसरी योग": "Gajakesari yoga",
 "बुधादित्य योग": "Budhaditya yoga", "चंद्र-मंगल योग": "Chandra-Mangala yoga", "मंगल दोष (लग्न से)": "Mangal dosha (from Lagna)",
 "रुचक योग (पंच महापुरुष)": "Ruchaka yoga (Pancha Mahapurusha)", "भद्र योग (पंच महापुरुष)": "Bhadra yoga (Pancha Mahapurusha)",
 "हंस योग (पंच महापुरुष)": "Hamsa yoga (Pancha Mahapurusha)", "मालव्य योग (पंच महापुरुष)": "Malavya yoga (Pancha Mahapurusha)",
 "शश योग (पंच महापुरुष)": "Shasha yoga (Pancha Mahapurusha)", "लाल किताब (ड्राफ़्ट)": "Lal Kitab (draft)",
 "ग्रह-संबंध: नीच-भंग, युति, अस्त, दृष्टि": "Planetary relations: neecha-bhanga, conjunctions, combustion, aspects",
 "सूर्योदय · सूर्यास्त (स्थानीय समय)।": "Sunrise · sunset (local time).",
 "अभी साढ़ेसाती नहीं है.": "Sade Sati is not running now.",
 "खानों में अंक राशि-संख्या हैं (1 = मेष)। ‘v’ = वक्री।": "Numbers in the boxes are sign numbers (1 = Aries). ‘v’ = retrograde.",
 "यह विकास-संस्करण की गणना है; ग्रह-स्थिति में कुछ कला तक अंतर संभव है और सटीकता का सत्यापन बाकी है। सभी व्याख्याएँ ‘ड्राफ़्ट’ हैं और विद्वान-समीक्षा के अधीन हैं।":
   "This is a development-version calculation; planet positions may differ by a few arc-minutes and accuracy verification is still pending. All interpretations are ‘draft’ and subject to scholar review.",
 "अष्टकवर्ग में हर ग्रह को हर राशि में 0 से 8 बिंदु मिलते हैं (सात ग्रह और लग्न बिंदु देते हैं)। किसी भाव के सर्व-अष्टकवर्ग (SAV) का कुल जितना ऊँचा, उस भाव के फल उतने सहज माने जाते हैं। औसत लगभग 28 है; 30+ मज़बूत और 25 से कम कमज़ोर, यह अंगूठे का नियम है, अंतिम फ़ैसला नहीं।":
   "In Ashtakavarga each planet gives 0 to 8 bindus in every sign (the seven planets and the Lagna contribute). The higher the Sarvashtakavarga (SAV) total of a house, the more easily its results are considered to flow. The average is about 28; 30+ is strong and below 25 is weak — a rule of thumb, not a final verdict.",
 "गोचर में हर ग्रह जन्म-चंद्र राशि से कुछ ख़ास भावों में शुभ माना जाता है। हमने इसे उस राशि में ग्रह के अष्टकवर्ग बिंदुओं (4 या अधिक = सहायक) से मिलाया है। ‘मिश्रित’ का मतलब है कि दोनों संकेत अलग-अलग हैं। वेध अभी लागू नहीं है; यह दिशा-संकेत है, भविष्यवाणी नहीं।":
   "In transit, each planet is considered favourable in certain houses from the natal Moon sign. We cross-checked this with the planet's Ashtakavarga bindus in that sign (4 or more = supportive). ‘Mixed’ means the two indications differ. Vedha is not applied yet; this is a directional indication, not a prediction.",
 "सभी छह बल (स्थान, दिक्, काल सहित अब्द-मास-वार-होरा, चेष्टा, नैसर्गिक, दृग्) और ग्रह-युद्ध शामिल हैं। यह संस्करण-1 की गणना है; कुल अंक शास्त्रीय न्यूनतम-आवश्यकता से तुलना के लिए हैं, पर व्याख्या विद्वान-समीक्षा के अधीन है।":
   "All six strengths (sthana, dig, kala incl. abda-masa-vara-hora, cheshta, naisargika, drik) and planetary war are included. This is a version-1 computation; totals can be compared with the classical minimum-requirement table, but interpretation awaits scholar review.",
 "अब्दबल, मासबल और युद्धबल अभी शामिल नहीं हैं, इसलिए यह पूर्ण षड्बल नहीं है। कुल अंकों की तुलना शास्त्रीय न्यूनतम-आवश्यकता तालिका से न करें; केवल एक ही कुंडली के ग्रहों की आपस में तुलना करें।":
   "Abda bala, masa bala and yuddha bala are not included yet, so this is not the full Shadbala. Do not compare the totals with the classical minimum-requirement tables; compare only the planets of one chart with each other.",
 "यह समय-रेखा बताती है कि किस दशा में जीवन के कौन-से क्षेत्र सक्रिय रहते हैं, घटनाओं की भविष्यवाणी नहीं। बल-संकेत दशेश की स्थिति (गरिमा, भाव, अष्टकवर्ग बिंदु) से बनता है; गोचर, दृष्टियाँ और योग अभी शामिल नहीं हैं।":
   "This timeline shows which areas of life are active in which dasha, not predictions of events. The strength indication is built from the dasha lord's condition (dignity, house, Ashtakavarga bindus); transits, aspects and yogas are not included yet.",
 "दृष्टि: हर ग्रह अपने से 7वें भाव को देखता है; मंगल 4 और 8, गुरु 5 और 9, शनि 3 और 10, राहु-केतु 5 और 9 को भी देखते हैं। यहाँ पूरी-राशि दृष्टि गिनी गई है (अंशों के हिसाब से दृष्टि-बल षड्बल के दृग्बल में है)।":
   "Aspect: every planet aspects the 7th house from itself; Mars also aspects the 4th and 8th, Jupiter the 5th and 9th, Saturn the 3rd and 10th, Rahu-Ketu the 5th and 9th. Whole-sign aspects are counted here (degree-wise aspect strength is in the Drik bala of Shadbala).",
 "सूर्य से शनि तक सातों ग्रह राहु-केतु अक्ष के एक ही ओर हों तो यह दोष कहा जाता है। इसके प्रभाव पर परंपराओं में बहुत मतभेद है।":
   "When the seven planets from Sun to Saturn all lie on one side of the Rahu-Ketu axis, this is called the dosha. Traditions differ widely on its effect.",
 "चंद्र और मंगल एक ही राशि में हों तो यह योग माना जाता है।": "This yoga is recognised when the Moon and Mars are in the same sign.",
 "सूर्य और बुध एक ही राशि में हों तो यह योग माना जाता है (बुध सूर्य से दूर नहीं जाता, इसलिए यह आम है)।":
   "This yoga is recognised when the Sun and Mercury are in the same sign (Mercury never moves far from the Sun, so it is common).",
 "'लग्न' दृश्य में घर जन्म-लग्न से गिने गए हैं; 'मेष' दृश्य में मेष हमेशा पहला घर है (लाल किताब की पारंपरिक कुंडली)। दोनों दिखाए गए हैं क्योंकि स्कूलों में मतभेद है.":
   "In the ‘Lagna’ view houses are counted from the natal Lagna; in the ‘Aries’ view Aries is always house 1 (the traditional Lal Kitab chart). Both are shown because schools differ.",
 "लाल किताब की कई परंपराएँ हैं और यह सामग्री अभी विद्वान से जाँची नहीं गई है। उपाय केवल परंपरागत रीति-रिवाज हैं, विश्वास पर आधारित हैं और इनका कोई वैज्ञानिक प्रमाण नहीं है; चिकित्सा, क़ानूनी या आर्थिक सलाह का विकल्प नहीं हैं। किसी उपाय में बहुत खर्च या जोखिम न उठाएँ।":
   "Lal Kitab has several traditions and this material has not yet been checked by a scholar. The remedies are only traditional customs, based on belief with no scientific proof, and are not a substitute for medical, legal or financial advice. Do not take on great expense or risk for any remedy.",
 "परंपरागत उपाय: सुबह उगते सूर्य को जल चढ़ाना, पिता और बुज़ुर्गों का सम्मान करना।": "Traditional remedy: offering water to the rising Sun in the morning; respecting father and elders.",
 "परंपरागत उपाय: माता की सेवा करना, ज़रूरतमंद को दूध या चावल दान करना।": "Traditional remedy: serving one's mother; donating milk or rice to someone in need.",
 "परंपरागत उपाय: भाइयों से मधुर संबंध रखना, मीठी रोटी या गुड़ बाँटना।": "Traditional remedy: keeping warm relations with brothers; sharing sweet roti or jaggery.",
 "परंपरागत उपाय: बच्चों और कन्याओं की मदद करना, हरी सब्ज़ी या चारा दान करना।": "Traditional remedy: helping children and girls; donating green vegetables or fodder.",
 "परंपरागत उपाय: गुरु-शिक्षक का आदर करना, पीली दाल या हल्दी का दान करना।": "Traditional remedy: respecting teachers; donating yellow lentils or turmeric.",
 "परंपरागत उपाय: घर और वस्त्र साफ़ रखना, गाय को चारा खिलाना, जीवन-साथी का सम्मान करना।": "Traditional remedy: keeping home and clothes clean; feeding fodder to a cow; respecting one's spouse.",
 "परंपरागत उपाय: कामगारों और सेवकों से अच्छा व्यवहार करना, ज़रूरतमंद को तेल या काला चना दान करना।": "Traditional remedy: treating workers and helpers well; donating oil or black gram to someone in need.",
 "परंपरागत उपाय: आसपास सफ़ाई रखना, जौ या मूली जैसी चीज़ें ज़रूरतमंद को देना।": "Traditional remedy: keeping surroundings clean; giving things like barley or radish to someone in need.",
 "परंपरागत उपाय: कुत्ते को रोटी खिलाना, बुज़ुर्गों और साधु-संतों की सेवा करना।": "Traditional remedy: feeding roti to a dog; serving elders and holy people.",
}
REPORT.update({
 "नीच-भंग: नीच ग्रह की कमज़ोरी तब घटती मानी जाती है जब उसकी नीच राशि का स्वामी, उसकी उच्च राशि का स्वामी या उस राशि में उच्च होने वाला ग्रह केंद्र में हो, या नीच ग्रह पर/साथ में नीच-राशि स्वामी हो, या वह नवांश में उच्च हो। परंपराओं में शर्तें अलग-अलग गिनी जाती हैं, इसलिए हर शर्त अलग दिखाई गई है।":
   "Neecha-bhanga: the weakness of a debilitated planet is considered reduced when the lord of its debilitation sign, the lord of its exaltation sign, or the planet exalted in that sign is in a kendra, or when the lord of the debilitation sign aspects or joins it, or when it is exalted in the navamsa. Traditions count the conditions differently, so each condition is shown separately.",
 "अष्टम शनि चल रहा है.": "Ashtama Shani (Saturn in the 8th from the Moon) is running.",
})
EXTRA_PATTERNS = [
 ("({1}): {2}", "({1}): {2}"),
 ("{1} नीच राशि में है और नीच-भंग की कोई सामान्य शर्त नहीं मिली: इसके कारकत्व में अतिरिक्त मेहनत और धैर्य की ज़रूरत बताई जाती है।",
  "{1} is in a debilitated sign and no common neecha-bhanga condition was found: its significations are said to need extra effort and patience."),
 ("{1} नीच राशि में है, पर {2} शास्त्रीय शर्त(ें) पूरी होने से नीच-भंग माना जाता है: कमज़ोरी का असर घटकर, संघर्ष के बाद फल देने की प्रवृत्ति बताई जाती है।",
  "{1} is in a debilitated sign, but {2} classical condition(s) are met, so neecha-bhanga is considered: the weakness is said to reduce, with a tendency to give results after struggle."),
 ("• नीच राशि के स्वामी {1} लग्न या चंद्र से केंद्र में हैं।", "• {1}, lord of the debilitation sign, is in a kendra from the Lagna or Moon."),
 ("• {1} की उच्च राशि के स्वामी {2} लग्न या चंद्र से केंद्र में हैं।", "• {2}, lord of {1}'s exaltation sign, is in a kendra from the Lagna or Moon."),
 ("• इस राशि में उच्च होने वाला ग्रह {1} लग्न या चंद्र से केंद्र में है।", "• {1}, which is exalted in this sign, is in a kendra from the Lagna or Moon."),
 ("• {1} अपनी नीच राशि के स्वामी {2} के साथ युति में है।", "• {1} is conjunct {2}, lord of its debilitation sign."),
 ("• {1} पर नीच राशि के स्वामी {2} की दृष्टि है।", "• {1} is aspected by {2}, lord of its debilitation sign."),
 ("• {1} नवांश कुंडली में उच्च राशि में है।", "• {1} is exalted in the navamsa chart."),
 ("{1} + {2} युति ({3}, {4}वाँ भाव), अंतर {5}° — बहुत पास", "{1} + {2} conjunction ({3}, house {4}), orb {5}° — very close"),
 ("{1} सूर्य से {2}° पर है (अस्त-सीमा {3}°): अस्त ग्रह के कारकत्व कुछ दबे हुए या सूर्य के प्रभाव में बताए जाते हैं।",
  "{1} is {2}° from the Sun (combustion limit {3}°): the significations of a combust planet are said to be somewhat suppressed or under the Sun's influence."),
 ("साढ़ेसाती चल रही है ({1} चरण).", "Sade Sati is running ({1} phase)."),
]
REPORT_WORDS = {"पहला": "first", "मध्य": "middle", "अंतिम": "last", "लाहिड़ी": "Lahiri", "सामान्य": "normal", "उच्च": "exalted", "स्वराशि": "own sign", "नीच": "debilitated", "वक्री": "retrograde"}
# {1}, {2}... match any text; each captured group is translated on its own (names, numbers, themes).
PATTERNS = [
 ("{1} अपने पक्के घर में है: लाल किताब में इसे सहज और स्थिर माना जाता है; इसके कारकत्व अपने-आप संतुलित रहने की प्रवृत्ति बताई जाती है।",
  "{1} is in its own permanent house: in Lal Kitab this is considered natural and stable; its significations tend to balance themselves."),
 ("{1} अपने उच्च घर में है: इसके कारकत्व को सहारा मिलने की प्रवृत्ति बताई जाती है।", "{1} is in its exalted house: its significations tend to receive support."),
 ("{1} अपने नीच घर में है: इसके कारकत्व में अधिक सजगता और संयम की ज़रूरत बताई जाती है।", "{1} is in its debilitated house: its significations are said to need extra care and restraint."),
 ("{1} {2}वें घर में है ({3}): इस घर के विषय इस ग्रह के स्वभाव से रंगे रहने की प्रवृत्ति बताई जाती है।",
  "{1} is in house {2} ({3}): the matters of this house tend to be coloured by this planet's nature."),
 ("{1} {2}वाँ घर में है ({3}): इस घर के विषय इस ग्रह के स्वभाव से रंगे रहने की प्रवृत्ति बताई जाती है।",
  "{1} is in house {2} ({3}): the matters of this house tend to be coloured by this planet's nature."),
 ("{1} अपनी या उच्च राशि में और लग्न से केंद्र भाव में हो तो यह योग बनता है। यहाँ स्थिति: {2}, भाव {3}।",
  "This yoga forms when {1} is in its own or exalted sign and in a kendra house from the Lagna. Here the status is: {2}, house {3}."),
 ("गुरु चंद्र से केंद्र (1/4/7/10) में हो तो यह योग माना जाता है। यहाँ गुरु चंद्र से {1}वें भाव में है।",
  "This yoga is recognised when Jupiter is in a kendra (1/4/7/10) from the Moon. Here Jupiter is in the {1} house from the Moon."),
 ("मंगल लग्न से {1}वें भाव में है। मंगल 1, 4, 7, 8, 12 में हो तो दोष गिना जाता है। परंपराओं में मतभेद हैं (कुछ दूसरा भाव भी गिनते हैं, कई चंद्र और शुक्र से भी देखते हैं), और परिहार (काट) भी होते हैं, इसलिए इसे अकेले फ़ैसला न मानें।",
  "Mars is in house {1} from the Lagna. The dosha is counted when Mars is in 1, 4, 7, 8 or 12. Traditions differ (some also count the 2nd house, many also check from the Moon and Venus), and cancellations (parihara) exist, so do not treat this alone as a verdict."),
 ("जन्म के समय {1} की दशा शेष: {2} वर्ष (वर्ष = {3} दिन)।", "Dasha balance of {1} at birth: {2} years (year = {3} days)."),
 ("महादशा {1} ({2} → {3}) · अंतर्दशा {4} ({5} → {6})", "Mahadasha {1} ({2} → {3}) · Antardasha {4} ({5} → {6})"),
 ("{1} ◀ अभी", "{1} ◀ now"), ("{1} (व)", "{1} (R)"),
 ("{1} · {2} पाद {3} · स्वामी {4}", "{1} · {2} pada {3} · lord {4}"), ("{1} · {2} पाद {3}", "{1} · {2} pada {3}"),
 ("{1} + {2} युति ({3}, {4}वाँ भाव), अंतर {5}°", "{1} + {2} conjunction ({3}, house {4}), orb {5}°"),
 ("गोचर ({1})", "Transit ({1})"),
 ("· जन्म: {1} · अक्षांश {2}, देशांतर {3} · अयनांश: {4}", "· Born: {1} · Latitude {2}, Longitude {3} · Ayanamsa: {4}"),
 ("इंजन संस्करण {1} · बैकएंड: {2} · बनाया गया: {3}। यह रिपोर्ट शिक्षा और मार्गदर्शन के लिए है; स्वास्थ्य, धन या क़ानून के फ़ैसले विशेषज्ञ की सलाह से लें।",
  "Engine version {1} · backend: {2} · generated: {3}. This report is for education and guidance; take health, money or legal decisions on an expert's advice."),
]

from jyotish import vargas as _vg  # noqa: E402
for _k, (_en, _hi) in _vg.NAMES.items():
    if _k != "D1":
        EXACT[_hi] = _en
VARGA_MEANING_EN = {
}
REPORT.update({
 "जन्म विवरण डालिए। गणना खगोलीय है; फलादेश परंपरागत शास्त्र पर आधारित मार्गदर्शन है, अंतिम निर्णय नहीं।":
   "Enter the birth details. The calculation is astronomical; the interpretation is guidance based on traditional texts, not a final decision.",
 "वर और वधू का जन्म विवरण भरिए। यह एक पारंपरिक पैमाना है, पूरी कुंडली का विश्लेषण नहीं।":
   "Fill in the birth details of the groom and bride. This is a traditional yardstick, not an analysis of the full chart.",
 "यह अंक एक पारंपरिक पैमाना है। इसमें दोनों कुंडलियों की दशा, सप्तम भाव और ग्रह-बल नहीं देखे जाते, भकूट-नाड़ी परिहार की प्रचलित शर्तें जाँची जाती हैं (ड्राफ़्ट)। ‘ड्राफ़्ट’ वाले कूट की विद्वान-समीक्षा बाकी है।":
   "This score is a traditional yardstick. It does not look at the dashas, 7th house or planetary strength of the two charts; common Bhakoot/Nadi parihara conditions are checked (draft). Kootas marked ‘draft’ are pending scholar review.",
 "मन में अपना प्रश्न रखिए, स्प्रेड चुनिए और कार्ड खींचिए। यह आत्म-चिंतन के लिए है।":
   "Hold your question in mind, choose a spread and draw cards. This is for self-reflection.",
 "अपने घर के कमरे और उनकी दिशा चुनिए। यह परंपरागत मार्गदर्शन है।": "Choose the rooms of your home and their directions. This is traditional guidance.",
 "वार सूर्योदय से शुरू होने वाले वैदिक दिन के अनुसार है।": "The weekday follows the Vedic day, which starts at sunrise.",
 "व्याख्या ड्राफ़्ट है; अंग्रेज़ी (लैटिन) नाम के अक्षरों से गणना।": "The interpretation is a draft; computed from the letters of the English (Latin) name.",
 "जिस क्षण सूर्य जन्म के अंश पर लौटता है, उस क्षण की कुंडली। वर्ष चुनिए:": "The chart of the moment when the Sun returns to its birth degree. Choose a year:",
 "उलटा": "Reversed", "चंद्र राशि:": "Moon sign:", "· जन्म नक्षत्र:": "· birth nakshatra:",
 "वर:": "Groom:", "वधू:": "Bride:",
})
EXTRA_PATTERNS += [
 ("{1} महादशा — {2} → {3}", "{1} Mahadasha — {2} → {3}"),
 ("· आयु {1}–{2} वर्ष ({3}–{4})", "· age {1}–{2} years ({3}–{4})"),
 ("{1}वाँ भाव ({2})", "house {1} ({2})"),
 ("{1}वें (केंद्र/त्रिकोण) भाव में", "in house {1} (kendra/trikona)"), ("{1}वें (त्रिक) भाव में", "in house {1} (trika)"),
 ("अष्टकवर्ग में {1} बिंदु", "{1} bindus in Ashtakavarga"),
 ("{1} जन्म-कुंडली में {2}वें भाव में है और {3} भाव का स्वामी है, इसलिए इस {4} में {5} से जुड़े विषय सक्रिय रहते हैं। बल-संकेत: {6} ({7})।",
  "{1} is in house {2} of the birth chart and rules house(s) {3}, so in this {4} matters of {5} are active. Strength indication: {6} ({7})."),
 ("{1} जन्म-कुंडली में {2}वें भाव में है (छाया ग्रह: कोई भाव स्वामित्व नहीं), इसलिए इस {3} में {4} से जुड़े विषय सक्रिय रहते हैं। बल-संकेत: {5} ({6})।",
  "{1} is in house {2} of the birth chart (shadow planet: owns no house), so in this {3} matters of {4} are active. Strength indication: {5} ({6})."),
 ("क्यों: {1} → भाव {2}, राशि {3}. स्रोत: {4} · स्थिति: {5}", "Why: {1} → house {2}, sign {3}. Source: {4} · status: {5}"),
 ("गणना इंजन: {1}", "Calculation engine: {1}"),
 ("पाद {1} · अयनांश (लाहिरी): {2} · भाव पद्धति: राशि-भाव (whole sign)", "pada {1} · Ayanamsa (Lahiri): {2} · house system: whole sign"),
 ("{1} ({2} पाद {3}) ·", "{1} ({2} pada {3}) ·"),
 ("D{1} {2}", "D{1} {2}"),
 ("व्यक्तिगत वर्ष {1}", "Personal year {1}"),
 ("अनुपस्थित अंक: {1} · दोहराए अंक: {2}", "Missing digits: {1} · repeated digits: {2}"),
 ("कुल: {1} / 36", "Total: {1} / 36"),
 ("वर: {1} राशि, {2} पाद {3} · वधू: {4} राशि, {5} पाद {6}", "Groom: {1} sign, {2} pada {3} · Bride: {4} sign, {5} pada {6}"),
 ("वर: लग्न से भाव {1} · चंद्र से भाव {2} → {3}", "Groom: house {1} from Lagna · house {2} from Moon → {3}"),
 ("वधू: लग्न से भाव {1} · चंद्र से भाव {2} → {3}", "Bride: house {1} from Lagna · house {2} from Moon → {3}"),
 ("{1} के क्षेत्र में: {2}।", "In matters of {1}: {2}."),
 ("{1}: {2}", "{1}: {2}"),
 ("{1} — {2}", "{1} — {2}"),
]
for _hi, _en in {"समग्र जीवन और शरीर": "overall life and body", "धन और संपत्ति": "wealth and assets", "भाई-बहन और साहस": "siblings and courage",
                 "भाग्य और अचल संपत्ति": "fortune and fixed property", "संतान": "children", "विवाह और धर्म, ग्रह का भीतरी बल": "marriage and dharma, the inner strength of a planet",
                 "कर्म और व्यवसाय": "work and career", "माता-पिता": "parents"}.items():
    EXACT.setdefault(_hi, _en)
REPORT.update({
 "टैरो आत्म-चिंतन का साधन है, भविष्यवाणी की गारंटी नहीं। बड़े फ़ैसले (स्वास्थ्य, धन, क़ानून) विशेषज्ञ की सलाह से लीजिए। अर्थ ड्राफ़्ट हैं और समीक्षा बाकी है।":
   "Tarot is a tool for self-reflection, not a guarantee of prediction. Take big decisions (health, money, law) on an expert's advice. The meanings are drafts and review is pending.",
 "यह परंपरागत मार्गदर्शन है। संरचनात्मक बदलाव (तोड़-फोड़) अपनी सुरक्षा और क़ानूनी अनुमति देखकर ही कीजिए, ख़ासकर डर में आकर नहीं।":
   "This is traditional guidance. Make structural changes (demolition) only after checking safety and legal permission, and never out of fear.",
 "यह परंपरागत वास्तु-मार्गदर्शन है, वैज्ञानिक या क़ानूनी सलाह नहीं। अलग-अलग परंपराओं में मतभेद हैं। अर्थ ड्राफ़्ट हैं।":
   "This is traditional Vastu guidance, not scientific or legal advice. Traditions differ. The meanings are drafts.",
})
EXTRA_PATTERNS += [("{1} महादशा", "{1} Mahadasha"), ("{1} ({2} पाद {3}) · चंद्र राशि:", "{1} ({2} pada {3}) · Moon sign:")]
REPORT.update({
 "स्थानबल: उच्च बिंदु से निकटता, सात वर्गों में मित्र/स्वराशि स्थिति, विषम-सम राशि, केंद्रादि और द्रेष्काण। दिग्बल: बलवान दिशा (सूर्य-मंगल दशम, गुरु-बुध लग्न, चंद्र-शुक्र चतुर्थ, शनि सप्तम) के पास। कालबल: दिन-रात की स्थिति, पक्ष, त्रिभाग, वार, होरा और अयन। नैसर्गिक बल: हर ग्रह का स्थिर बल। दृग्बल: शुभ ग्रहों की दृष्टि जोड़कर और पाप ग्रहों की दृष्टि घटाकर, चौथाई। चेष्टाबल: सूर्य के लिए अयनबल और चंद्र के लिए पक्षबल।":
   "Sthana bala: closeness to the exaltation point, friendly/own-sign position in seven divisional charts, odd-even sign, kendradi and drekkana. Dig bala: closeness to the strong direction (Sun-Mars 10th, Jupiter-Mercury Lagna, Moon-Venus 4th, Saturn 7th). Kala bala: day/night position, paksha, tribhaga, weekday, hora and ayana. Naisargika bala: the fixed strength of each planet. Drik bala: benefic aspects added and malefic aspects subtracted, one quarter. Cheshta bala: ayana bala for the Sun and paksha bala for the Moon.",
 "अपनी हथेली देखकर जो दिखे वह चुनिए; जो समझ न आए उसे \"—\" रहने दीजिए। यह परंपरागत कला है, भविष्यवाणी नहीं।":
   "Look at your palm and choose what you see; leave \"—\" for anything you cannot tell. This is a traditional art, not a prediction.",
})
EXTRA_PATTERNS += [("{1} (KP अयनांश {2}°)", "{1} (KP ayanamsa {2}°)"), ("{1} (अपवाद)", "{1} (exception)"), ("{1} कारकांश: {2}।", "{1} Karakamsa: {2}."), ("{1} मिनट", "{1} min"), ("(चंद्र से {1}, लग्न से {2})", "(from Moon {1}, from Lagna {2})"),
                   ("⚠ {1} जन्म-समय से केवल {2} मिनट {3} बदल जाती है। अगर जन्म-समय पक्का नहीं है तो इस पर आधारित फल सावधानी से पढ़ें।",
                    "⚠ The {1} changes only {2} minutes {3} than the given birth time. If the time is not exact, read results based on it with care."), ("{1}: {2} {3} → {4} (चंद्र से {5}, लग्न से {6})", "{1}: {2} {3} → {4} (from Moon {5}, from Lagna {6})"),
                   ("{1} जन्म-समय से केवल {2} मिनट {3} बदल जाती है। अगर जन्म-समय पक्का नहीं है तो इस पर आधारित फल सावधानी से पढ़ें।",
                    "The {1} changes only {2} minutes {3} than the given birth time. If the time is not exact, read results based on it with care.")]
EXTRA_PATTERNS += [("परिहार सहित योग: {1} / 36", "Total with parihara: {1} / 36"), ("{1} दोष (परिहार मिला)", "{1} dosha (cancelled)"), ("{1} दोष", "{1} dosha"),
                   ("दोनों राशियों का स्वामी {1} है", "both Moon-sign lords are {1}"), ("राशि-स्वामी {1} और {2} परस्पर मित्र हैं", "Moon-sign lords {1} and {2} are mutual friends")]
EXTRA_PATTERNS += [("{1}: राशि-भाव {2} → चलित भाव {3}", "{1}: rasi house {2} → chalit house {3}"), ("दशम भाव-मध्य (MC): {1} {2}", "Tenth house middle (MC): {1} {2}"), ("दशम भाव-मध्य (MC):", "Tenth house middle (MC):")]
EXTRA_PATTERNS += [("स्रोत ({1})", "Sources ({1})"), ("{1}-{2} (स्वामी {3})", "{1}-{2} (lord {3})")]
EXTRA_PATTERNS += [("{1} (गणना: {2})", "{1} (as of {2})"), ("{1} की प्रधानता ({2} कार्ड): {3} पर ज़ोर।", "Dominance of {1} ({2} cards): emphasis on {3}.")]
REPORT.update({"स्वराशि/उच्च में": "in own/exalted sign", "उच्च राशि में": "in exalted sign", "नीच राशि में": "in debilitated sign",
               "सामान्य स्थिति": "ordinary condition", "ड्राफ़्ट": "draft"})

PATTERNS += EXTRA_PATTERNS
for hi, en in REPORT.items():
    EXACT[hi] = en
for hi, en in REPORT_WORDS.items():
    PHRASES[hi] = en

# Words that may be replaced inside longer text (always at Devanagari word boundaries).
UI_WORDS = {"पाद": "pada", "वक्री": "retrograde", "भाव": "house"}
for hi, en in UI.items():
    EXACT[hi] = en
for hi, en in UI_WORDS.items():
    PHRASES[hi] = en

out = ROOT / "data" / "i18n_en.json"
out.write_text(json.dumps({"_note": "Generated by engine/tools/build_i18n.py. Partial Hindi->English dictionary; unknown text stays Hindi.",
                           "exact": EXACT, "phrases": PHRASES, "patterns": PATTERNS}, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
print(f"{len(EXACT)} exact, {len(PHRASES)} phrases -> {out}")
