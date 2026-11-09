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
    if f.name == "vastu_zones.json":          # handled below: its devata names must not override planet names (सूर्य → Sun)
        continue
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
put(_full["life_transits"]["note_hi"], _full["life_transits"]["note_en"])
put(_full["gochara"]["why_hi"], "In transit each planet is held favourable in certain houses from the natal Moon sign. We combine this with the planet's ashtakavarga bindus in that sign (4 or more = supportive). 'Mixed' means the two signals disagree. Vedha is applied: a favourable house's result is held to be blocked when another planet sits at its vedha point (Sun-Saturn and Moon-Mercury do not obstruct each other); this is an indication, not a prediction.")
from jyotish import lalkitab as _lk  # noqa: E402
_vp = _lk.varshphal(_full, 2026)
for _m in ("table", "mixed", "rotation"):
    _x = dict(_vp); 
put(_vp["method_note_hi"], _vp["method_note_en"])
put("लाल किताब की 120-वर्षीय वर्षफल सारणी से (Astrostudents संकलन; 46वें वर्ष का स्तंभ प्रकाशित उदाहरण से मिलाया गया)।", "From the 120-year Lal Kitab varshphal table (Astrostudents collection; the 46th-year column cross-checked with a published example).")
put("कुछ ग्रह सत्यापित स्तंभ से, बाक़ी सरल घूर्णन से; मूल सारणी अभी पूरी नहीं भरी।", "Some planets from a verified column, the rest by simple rotation; the original table is not fully filled yet.")
put("मूल लाल किताब वर्षफल सारणी से।", "From the original Lal Kitab varshphal table.")
put(_full["jaimini"]["note_hi"], _full["jaimini"]["note_en"])
put(_full["jaimini"]["chara_dasha"]["note_hi"], _full["jaimini"]["chara_dasha"]["note_en"])
put(_full["kp"]["ruling_planets"]["note_hi"], _full["kp"]["ruling_planets"]["note_en"])
from jyotish import matching as _mt  # noqa: E402
_mm = _mt.ashtakoota(5.0, 215.0)
put(_mm["parihara_note_hi"], _mm["parihara_note_en"])
from jyotish import prashna as _pr  # noqa: E402
for _t in _pr.TOPICS.values():
    put(_t["hi"], _t["en"])
put("कोई नहीं", "none")
_prr = _pr.prashna("general", __import__("datetime").datetime(2026, 1, 1, tzinfo=__import__("datetime").timezone.utc), 23.18, 79.99, __import__("jyotish.ephemeris", fromlist=["AnalyticBackend"]).AnalyticBackend())
put(_prr["disclaimer_hi"], _prr["disclaimer_en"])
from jyotish import muhurta_find as _mf  # noqa: E402
_mr = _mf.find("general", 23.18, 79.99, "Asia/Kolkata", "2026-01-01", 1)
put(_mr["note_hi"], _mr["note_en"])
for _a in _mf.ACTIVITIES.values():
    put(_a["hi"], _a["en"])
for _hi, _en in (("तिथि इस कार्य की सूची में नहीं", "tithi not in the preferred list"), ("कृष्ण पक्ष (शुक्ल पक्ष वांछित)", "Krishna paksha (Shukla preferred)"), ("मास इस संस्कार के वांछित मासों में नहीं", "month not among the preferred months"),
                 ("खरमास (सूर्य धनु/मीन में)", "Kharmas (Sun in Dhanu/Meena)"), ("अधिक मास", "Adhika masa"), ("चातुर्मास", "Chaturmas"), ("होलाष्टक", "Holashtak"), ("पितृ पक्ष", "Pitru paksha"), ("गुरु अस्त", "Jupiter combust"), ("शुक्र अस्त", "Venus combust")):
    put(_hi, _en)
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
# birth-time rectification aid
from jyotish import rectify as _rc
_rc_sample = _rc.rectify("2000-01-01", "12:00", "Asia/Kolkata", 22.0, 82.0, 10, 5, [])
put(_rc_sample["note_hi"], _rc_sample["note_en"])
for k, hi in _rc.EVENT_HI.items():
    put(hi, {"marriage": "Marriage", "child": "Child", "job": "Job / work", "property": "Property", "travel": "Abroad / travel", "education": "Education"}[k])
UI_RECTIFY = {"जन्म-समय संशोधन सहायक": "Birth-time rectification aid",
              "दिए समय के आस-पास की वे अवधियाँ जिनमें लग्न, नवांश-लग्न और चंद्र-नक्षत्र नहीं बदलते। जीवन की घटनाएँ (वर्ष) दें तो हर अवधि को दशा-जाँच से अंक मिलते हैं। यह प्रमाण नहीं, संकेत है।":
              "Stretches around the given time within which the Lagna, navamsa Lagna and Moon nakshatra do not change. Give life events (years) and each stretch is scored by a dasha check. A hint, not a proof.",
              "± मिनट": "± minutes", "चरण (मिनट)": "Step (minutes)", "+ घटना": "+ Event", "अवधियाँ देखिए": "Show stretches", "हटाइए": "Remove", "वर्ष": "Year",
              "गणना हो रही है…": "Calculating…", "घटनाओं से सबसे मेल खाती अवधियाँ:": "Stretches that best match the events:", "शीर्ष अवधि की दशा-जाँच": "Dasha check of the top stretch",
              "समय": "Time", "नवांश-लग्न": "Navamsa Lagna", "चंद्र-नक्षत्र": "Moon nakshatra", "घटना-मेल": "Event match", "घटना": "Event", "दशा / अंतर्दशा": "Dasha / antardasha", "मेल": "Match", "हाँ": "Yes", "नहीं": "No"}
for hi, en in UI_RECTIFY.items():
    EXACT.setdefault(hi, en)
# tajika layer
from jyotish import tajika as _tj
for name, hi, *_ in _tj.SAHAMS:
    put(hi, name)
for _, (en, hi, _n) in _tj.ASPECTS.items():
    put(hi, en.capitalize() + hi[hi.find("("):] if "(" in hi else en.capitalize())
UI_TAJIKA = {"ताजिक परत (ड्राफ़्ट)": "Tajika layer (draft)", "वर्षेश: {1}": "Year lord: {1}", "(दिन की वर्ष-प्रवेश कुंडली)": "(day-time annual chart)", "(रात्रि की वर्ष-प्रवेश कुंडली)": "(night-time annual chart)",
             "पंचवर्गीय बल": "Panchavargiya bala", "क्षेत्र": "Kshetra", "उच्च": "Uchcha", "हद्दा": "Hadda", "द्रेष्काण": "Drekkana", "कुल": "Total", "पंचाधिकारी": "Office-bearers (panchadhikari)",
             "पद": "Office", "बल": "Strength", "लग्न को देखता है": "Aspects the Lagna", "सहम (12)": "Sahams (12)", "सहम": "Saham", "सूत्र": "Formula", "मुद्दा दशा": "Mudda dasha",
             "ताजिक दृष्टियाँ (इत्थशाल / ईसराफ)": "Tajika aspects (ithasala / ishrafa)", "दृष्टि": "Aspect", "अंतर": "Orb", "अवस्था": "Phase", "कोई दृष्टि दीप्तांश के भीतर नहीं": "No aspect within the deeptamsha orbs",
             "इत्थशाल (बनता हुआ)": "Ithasala (applying)", "ईसराफ (बीतता हुआ)": "Ishrafa (separating)", "अति बली": "very strong", "बली": "strong", "निर्बल": "weak",
             "मुन्थेश": "Muntha lord", "जन्म-लग्नेश": "Birth-Lagna lord", "वर्ष-लग्नेश": "Varsha-Lagna lord", "त्रिराशीश": "Trirashi lord", "दिन/रात्रि-पति": "Day/night lord",
             "लग्नेश": "Lagna lord", "पुण्य-सहम": "Punya saham", "(रात्रि में उलट)": "(reversed at night)"}
for hi, en in UI_TAJIKA.items():
    EXACT.setdefault(hi, en)
for _hi, _en in (("पंचाधिकारियों में से, लग्न को देखने वालों में सबसे बली ग्रह वर्षेश है।", "Among the office-bearers, the strongest that aspects the Lagna is the year lord."),
                 ("कोई पंचाधिकारी लग्न को नहीं देखता; सबसे बली ग्रह वर्षेश लिया गया।", "No office-bearer aspects the Lagna; the strongest overall is taken as year lord."),
                 ("यह सौर-वापसी (वर्षफल) कुंडली है: जिस क्षण सूर्य जन्म के सूर्य-अंश पर लौटता है। ताजिक परत (वर्षेश, सहम, मुद्दा दशा, इत्थशाल) ड्राफ़्ट है; पाठ केवल दिशा-संकेत हैं।",
                  "This is the solar-return (varshaphal) chart: the moment the Sun returns to its natal degree. The Tajika layer (year lord, sahams, mudda dasha, ithasala) is a draft; texts are only pointers."),
                 ("मुन्था = जन्म-लग्न राशि + पूरे हुए वर्ष (हर वर्ष एक राशि आगे)।", "Muntha = birth-Lagna sign + completed years (one sign forward each year)."),
                 ("मुन्था:", "Muntha:"), ("राशि, वर्ष-कुंडली के भाव", "sign, in house"), ("में।", "of the annual chart."), ("वर्षफल देखिए", "Show varshaphal"), ("वर्ष (वर्षफल)", "Year (varshaphal)")):
    put(_hi, _en)
# festivals
from jyotish import festivals as _fe
for _k, _hi, _en, _m, _t, _mo, _nhi, _nen in _fe.FESTIVALS:
    put(_hi, _en)
    if _nhi: put(_nhi, _nen)
put("मकर संक्रांति", "Makar Sankranti"); put("सूर्य का निरयन मकर प्रवेश (लाहिड़ी)।", "The Sun's sidereal ingress into Makara (Lahiri).")
put("क्षय तिथि: उस दिन लिया गया जिसमें तिथि समाप्त हुई।", "Kshaya tithi: the day on which the tithi ended was taken.")
_fc = _fe.calendar(2026, 22.35, 82.68, "Asia/Kolkata")
put(_fc["note_hi"], _fc["note_en"])
for _e in _fc["events"]:
    if _e["kind"] != "festival":
        put(_e["name_hi"], _e["name_en"])
EXACT.setdefault("चंद्रोदय / चंद्रास्त", "Moonrise / moonset")
for _hi, _en in (("त्योहार और व्रत कैलेंडर", "Festival and vrat calendar"),
                 ("इस ऐप के अपने पंचांग से: 32 प्रमुख त्योहार, 24 एकादशी (नाम सहित), पूर्णिमा-अमावस्या, अधिक मास। स्थान कुंडली वाला या ऊपर चुना शहर।", "From this app's own panchang: 32 major festivals, 24 Ekadashis (named), Purnima/Amavasya, adhika masa. Location: the chart's or the city chosen above."),
                 ("दिखाइए", "Show"), ("त्योहार", "Festivals"), ("एकादशी", "Ekadashi"), ("पूर्णिमा / अमावस्या", "Purnima / Amavasya"), ("सब", "All"), ("देखिए", "Show"),
                 ("— इस मास में त्योहार नहीं गिने गए।", "— festivals are not counted in this month."), ("अधिक मास:", "Adhika masa:")):
    EXACT.setdefault(_hi, _en)
for _i, (_hi, _en) in enumerate((("जनवरी", "January"), ("फ़रवरी", "February"), ("मार्च", "March"), ("अप्रैल", "April"), ("मई", "May"), ("जून", "June"), ("जुलाई", "July"), ("अगस्त", "August"), ("सितंबर", "September"), ("अक्टूबर", "October"), ("नवंबर", "November"), ("दिसंबर", "December"))):
    EXACT.setdefault(_hi, _en); EXACT.setdefault(_hi[:3], _en[:3])
FEST_PATTERNS = [("अधिक मास: {1} — इस मास में त्योहार नहीं गिने गए।", "Adhika masa: {1} — festivals are not counted in this month.")]
# lagna shuddhi
from jyotish import muhurta_lagna as _ml
_mlr = _ml.lagna_muhurta("2026-11-26", 22.35, 82.68, "Asia/Kolkata", "marriage", 3, 5)
put(_mlr["note_hi"], _mlr["note_en"])
for _l in _mlr["lagnas"]:
    for _d in _l["doshas"] + _l["strengths"]:
        put(_d["hi"], _d["en"])
for _hi, _en in (("वर की चंद्र राशि", "Groom's Moon sign"), ("वधू की चंद्र राशि", "Bride's Moon sign"), ("लग्न-शुद्धि", "Lagna shuddhi"), ("लग्न-सारणी बन रही है…", "Building the lagna table…"), ("निर्णय", "Verdict"), ("दोष", "Doshas"),
                 ("शुभ", "good"), ("मध्यम", "middling"), ("वर्जित", "avoid"), ("(रात्रि)", "(night)"), ("मंगल अष्टम में", "Mars in the 8th"), ("शुक्र षष्ठ में", "Venus in the 6th"), ("स्थिर/द्विस्वभाव लग्न", "Fixed or dual lagna"), ("चर लग्न (विवाह में कम वांछित)", "Movable lagna (less preferred for marriage)")):
    EXACT.setdefault(_hi, _en)
_fc2 = _fe.calendar(2026, 22.35, 82.68, "Asia/Kolkata")
for _e in _fc2["events"]:
    if _e["kind"] in ("regional", "national", "christian", "islamic"):
        put(_e["name_hi"], _e["name_en"])
        if _e["note_hi"]: put(_e["note_hi"], _e["note_en"])
for _hi, _en in zip(["जन्म", "संपत्", "विपत्", "क्षेम", "प्रत्यरि", "साधक", "वध", "मित्र", "अति-मित्र"], ["Janma", "Sampat", "Vipat", "Kshema", "Pratyari", "Sadhaka", "Vadha", "Mitra", "Ati-mitra"]):
    EXACT.setdefault(_hi, _en)
LAGNA_PATTERNS = [("वर: ताराबल", "Groom: tarabala"), ("वधू: ताराबल", "Bride: tarabala"), ("({1}वाँ, {2}) ✓", "({1}th, {2}) ✓"), ("({1}वाँ, {2}) ✗", "({1}th, {2}) ✗"),("वर: चंद्रबल {1}वाँ ({2}) ✓", "Groom: chandrabala {1}th ({2}) ✓"), ("वर: चंद्रबल {1}वाँ ({2}) ✗", "Groom: chandrabala {1}th ({2}) ✗"), ("वधू: चंद्रबल {1}वाँ ({2}) ✓", "Bride: chandrabala {1}th ({2}) ✓"), ("वधू: चंद्रबल {1}वाँ ({2}) ✗", "Bride: chandrabala {1}th ({2}) ✗"),("{1} — लग्न-सारणी और लग्न-शुद्धि", "{1} — lagna table and lagna shuddhi"), ("सप्तम भाव में ग्रह ({1}) — जामित्र दोष", "Planet(s) in the 7th ({1}) — Jamitra dosha"), ("अष्टम भाव में ग्रह ({1})", "Planet(s) in the 8th ({1})"),
                  ("द्वादश में पाप ग्रह ({1})", "Malefic in the 12th ({1})"), ("लग्नेश {1} {2}वें भाव में", "Lagna lord {1} in house {2}"), ("चंद्र {1}वें भाव में", "Moon in house {1}"), ("लग्न में पाप ग्रह ({1})", "Malefic in the lagna ({1})"),
                  ("शुभ ग्रह केंद्र/त्रिकोण में ({1})", "Benefic in kendra/trikona ({1})"), ("लग्न वर की चंद्र राशि से {1}वाँ", "Lagna is the {1}th from the groom's Moon sign"), ("लग्न वधू की चंद्र राशि से {1}वाँ", "Lagna is the {1}th from the bride's Moon sign"),
                  ("अभिजित {1} · राहु काल {2} · शुभ चौघड़िया: {3}", "Abhijit {1} · Rahu kaal {2} · good choghadiya: {3}")]
# calendar studio (static card labels)
UI_CAL = {"कैलेंडर": "Calendar", "कैलेंडर डिज़ाइन स्टूडियो — पंचांग सहित छपने योग्य कैलेंडर": "Calendar design studio — printable calendar with panchang",
          "महीना या पूरा वर्ष चुनिए, ऊपर-नीचे विज्ञापन पट्टी (चित्र या पाठ), लोगो, रंग-योजना, आकार और दिखाने वाली जानकारी तय कीजिए; दाईं ओर लाइव झलक, फिर \"प्रिंट / PDF\"। चित्र आपके ब्राउज़र में ही रहते हैं (डिज़ाइन इसी डिवाइस पर सहेजा जाता है)।":
          "Pick a month or the whole year, set the top and bottom advertisement bands (image or text), logo, colour theme, size and what to show; live preview on the right, then \"Print / PDF\". Images stay in your browser (the design is saved on this device).",
          "1. माह, स्थान, भाषा": "1. Month, place, language", "माह": "Month", "पूरा वर्ष (12 पृष्ठ)": "Whole year (12 pages)", "शहर (ख़ाली = कुंडली वाला)": "City (empty = the chart's)", "भाषा": "Language",
          "2. रूप — रंग, आकार, अक्षर": "2. Look — colours, size, type", "रंग-योजना": "Colour theme", "केसरिया": "Saffron", "नील": "Indigo", "हरा": "Forest", "मैरून": "Maroon", "श्वेत-श्याम": "Monochrome",
          "आकार": "Size", "A4 खड़ा": "A4 portrait", "A4 आड़ा": "A4 landscape", "A3 खड़ा": "A3 portrait", "A3 आड़ा": "A3 landscape", "अक्षर आकार": "Font size", "लोगो (PNG/JPG)": "Logo (PNG/JPG)", "लोगो हटाइए": "Remove logo",
          "3. ऊपर की विज्ञापन पट्टी": "3. Top advertisement band", "4. नीचे की विज्ञापन पट्टी": "4. Bottom advertisement band", "पट्टी दिखाइए": "Show band", "चित्र (बैनर)": "Image (banner)", "चित्र हटाइए": "Remove image",
          "चित्र भराव": "Image fit", "पूरा दिखे": "Fit inside", "पट्टी भर दे": "Fill band", "चित्र न हो तो नीचे का पाठ दिखेगा:": "Without an image the text below is shown:", "शीर्षक": "Title", "पंक्ति": "Line", "संपर्क": "Contact",
          "व्यवसाय / विज्ञापनदाता का नाम": "Business / advertiser name", "क्या बेचते/करते हैं": "What you sell / do", "पता · फ़ोन": "Address · phone", "ऊँचाई (मिमी)": "Height (mm)", "पृष्ठभूमि": "Background", "अक्षर रंग": "Text colour",
          "चित्र लगा है।": "Image set.", "कोई चित्र नहीं।": "No image.", "5. व्यवसाय / फ़ुटर": "5. Business / footer", "नाम": "Name", "पता / फ़ोन": "Address / phone", "टैगलाइन": "Tagline", "स्थान का नाम (कैलेंडर पर)": "Place name (on the calendar)",
          "6. क्या-क्या दिखे": "6. What to show", "समाप्ति समय": "End times", "पूर्णिमा/अमावस्या": "Purnima/Amavasya", "चंद्रोदय": "Moonrise", "राहु काल": "Rahu kaal", "योग-करण": "Yoga-karana", "पर्व-सूची (दाएँ)": "Festival list (right)",
          "7. अपनी तिथियाँ और छुट्टियाँ": "7. Your own dates and holidays", "किसी दिन पर अपना नोट (जैसे \"दुकान बंद\", \"वार्षिकोत्सव\") या छुट्टी (लाल अंक)।": "A note on any day (e.g. \"shop closed\", \"anniversary\") or a holiday (red date).",
          "तारीख़": "Date", "नोट": "Note", "पाठ (ख़ाली = सिर्फ़ छुट्टी)": "Text (empty = holiday only)", "जोड़िए": "Add", "झलक ताज़ा कीजिए": "Refresh preview", "प्रिंट / PDF": "Print / PDF", "डिज़ाइन सहेजिए": "Save design", "रीसेट": "Reset",
          "प्रिंट संवाद में \"Save as PDF\" चुनिए, कागज़ वही आकार, मार्जिन \"None/Default\", \"Background graphics\" चालू।": "In the print dialog choose \"Save as PDF\", the same paper size, margins \"None/Default\", \"Background graphics\" on.",
          "डिज़ाइन इस डिवाइस पर सहेजा गया।": "Design saved on this device.", "शहर": "City", "हिंदी": "Hindi", "विज्ञापन के लिए स्थान": "Space for an advertisement", "(छुट्टी)": "(holiday)"}
from jyotish import rashifal as _rfm
_rf = _rfm.rashifal("2026-11-09", "Asia/Kolkata", "daily")
for _per in ("daily", "weekly", "monthly"):
    _x = _rfm.rashifal("2026-11-09", "Asia/Kolkata", _per); put(_x["note_hi"], _x["note_en"]); put(_x["period_hi"], _x["period_en"])
for _s in _rf["signs"]:
    put(_s["summary_hi"], _s["summary_en"])
for _v in _rfm.LUCKY.values():
    put(_v[0], _v[1])
for _hi, _en in (("उत्तम", "excellent"), ("अच्छा", "good"), ("संयम", "restraint"), ("राशिफल — दैनिक / साप्ताहिक / मासिक (चंद्र राशि से गोचर)", "Rashifal — daily / weekly / monthly (transits over the Moon sign)"),
                 ("बारह राशियों के लिए गोचर-आधारित प्रवृत्ति; यह भविष्यवाणी नहीं। अपनी चंद्र राशि कुंडली से देखिए।", "Transit-based tendencies for the twelve signs; not a prediction. Find your Moon sign in the chart."),
                 ("अवधि", "Period"), ("दैनिक", "Daily"), ("साप्ताहिक", "Weekly"), ("मासिक", "Monthly"), ("वार-स्वामी", "weekday lord"), ("शुभ रंग", "lucky colour"), ("शुभ अंक", "lucky number"), ("अनुकूल", "favourable"), ("हर माह के बाद राशिफल पृष्ठ", "Rashifal page after every month"), ("मासिक राशिफल", "Monthly rashifal"), ("राशिफल", "Rashifal")):
    EXACT.setdefault(_hi, _en)
for _hi, _en in (("सूर्योदय", "Sunrise"), ("सूर्यास्त", "Sunset"), ("पूरा राशिफल", "full rashifal")):
    EXACT.setdefault(_hi, _en)
EXACT.setdefault("तक", "until"); EXACT.setdefault("विक्रम संवत", "Vikram samvat")
RASHI_PATTERNS = [("आज का राशिफल ({1}):", "Today's rashifal ({1}):"),("{1} ग्रह अनुकूल भावों में ({2}); सावधानी: {3}।", "{1} planet(s) in favourable houses ({2}); care with {3}."), ("{1} ग्रह अनुकूल भावों में ({2})।", "{1} planet(s) in favourable houses ({2})."),
                  ("{1} ग्रह अनुकूल भावों में; सावधानी: {2}।", "{1} planet(s) in favourable houses; care with {2}."), ("वेध: {1}", "vedha: {1}"), ("· शुभ अंक {1}", "· lucky number {1}"), ("{1} राशिफल", "{1} rashifal")]
UI_CAL.update({"राष्ट्रीय दिवस": "National days", "क्षेत्रीय पर्व (पोंगल, ओणम, दुर्गा पूजा…)": "Regional festivals (Pongal, Onam, Durga Puja…)", "ईद, क्रिसमस आदि": "Eid, Christmas etc.", "क्षेत्रीय पर्व": "Regional festivals", "अन्य धर्म (ईद, क्रिसमस…)": "Other faiths (Eid, Christmas…)", "प्रदोष / चतुर्थी / शिवरात्रि": "Pradosh / Chaturthi / Shivaratri",
               "वर का नक्षत्र": "Groom's nakshatra", "वधू का नक्षत्र": "Bride's nakshatra",
               "प्रदोष, चतुर्थी, मासिक शिवरात्रि": "Pradosh, Chaturthi, monthly Shivaratri", "शक संवत + तमिल/बंगाली/मलयालम मास": "Shaka samvat + Tamil/Bengali/Malayalam months", "तीन माह / पृष्ठ": "Three months / page", "तिमाही; पूरे वर्ष के 4 पृष्ठ": "Quarterly; 4 pages for a year",
               "होरा (ग्रह-घंटे, 24)": "Hora (planetary hours, 24)", "प्रदोष व्रत": "Pradosh vrat", "विनायक चतुर्थी": "Vinayaka Chaturthi", "संकष्टी चतुर्थी": "Sankashti Chaturthi", "मासिक शिवरात्रि": "Masik Shivaratri",
               "वार्षिक शुभ-मुहूर्त पृष्ठ": "Yearly auspicious-dates page", "वार्षिक शुभ मुहूर्त": "Auspicious dates of the year",
               "पंचांग-स्तर: तिथि, नक्षत्र, वार, योग, भद्रा; संस्कारों में खरमास, चातुर्मास, होलाष्टक, अधिक मास, पितृ पक्ष, गुरु-शुक्र अस्त वर्जित": "Almanac level: tithi, nakshatra, weekday, yoga, Bhadra; samskaras exclude Kharmas, Chaturmas, Holashtak, adhika masa, Pitru paksha, Jupiter/Venus combust",
               "विवाह, उपनयन आदि संस्कारों के लिए लग्न-शुद्धि सहित पंडित से मुहूर्त निकलवाएँ; यह सूची दिशा-संकेत है।": "For marriage, upanayana and other samskaras have a pandit fix the muhurta with the lagna; this list is a pointer.",
"टेम्पलेट चुनिए, रंग-फ़ॉन्ट-पृष्ठभूमि सजाइए, ऊपर-नीचे-बगल की विज्ञापन पट्टियाँ और लोगो लगाइए, माह की तस्वीर जोड़िए; दाईं ओर लाइव झलक, फिर \"प्रिंट / PDF\"। चित्र आपके ब्राउज़र में ही रहते हैं; डिज़ाइन इसी डिवाइस पर सहेजे जाते हैं।":
               "Choose a template, set colours, fonts and background, add top/bottom/side advertisement bands and a logo, add a month picture; live preview on the right, then \"Print / PDF\". Images stay in your browser; designs are saved on this device.",
               "1. टेम्पलेट": "1. Template", "क्लासिक ग्रिड": "Classic grid", "ग्रिड + दाईं ओर पर्व-सूची": "Grid + festival list on the right", "मॉडर्न": "Modern", "तस्वीर-पट्टी, बड़ा माह, पिल्स": "Hero image, big month, pills",
               "पोस्टर सूची": "Poster list", "दिन-वार खड़ी सूची": "Vertical day list", "पूर्ण पंचांग": "Full panchang", "तिथि-नक्षत्र-योग-करण समय, राहु काल, मुहूर्त, गोचर": "Tithi/nakshatra/yoga/karana times, Rahu kaal, muhurta, ingresses",
               "दो माह / पृष्ठ": "Two months / page", "सघन; पूरे वर्ष के 6 पृष्ठ": "Compact; 6 pages for a year", "पूरे वर्ष में कवर पृष्ठ": "Cover page for the full year", "माह-नाम दोनों भाषाओं में": "Month names in both languages", "सप्ताह सोमवार से": "Week starts Monday",
               "2. रंग": "2. Colours", "पैलेट चुनिए या हर रंग अपने हिसाब से बदलिए।": "Pick a palette or change every colour yourself.", "मुख्य रंग": "Main colour", "पर्व रंग": "Festival colour", "रविवार / छुट्टी": "Sunday / holiday", "काग़ज़": "Paper", "अक्षर": "Text", "पट्टी पर अक्षर": "Text on bands",
               "सादा": "Plain", "हल्का ग्रेडिएंट": "Soft gradient", "बिंदु-पैटर्न": "Dot pattern", "हल्की धारियाँ": "Light stripes", "डार्क": "Dark", "रंग रीसेट": "Reset colours", "टील": "Teal", "रॉयल": "Royal", "सनसेट": "Sunset",
               "3. फ़ॉन्ट, आकार, तस्वीर": "3. Fonts, size, picture", "फ़ॉन्ट": "Font", "मॉडर्न (Poppins + Noto)": "Modern (Poppins + Noto)", "क्लासिक (Playfair + Tiro)": "Classic (Playfair + Tiro)", "क्लीन (Inter + Mukta)": "Clean (Inter + Mukta)", "सिस्टम": "System", "वर्ग 297 मिमी": "Square 297 mm",
               "लोगो फ़ुटर में भी": "Logo in the footer too", "माह की तस्वीर (मॉडर्न/पोस्टर/कवर में शीर्ष पर दिखती है):": "Month picture (shown at the top in Modern/Poster/Cover):", "किस माह के लिए": "For which month", "सभी माह": "All months", "तस्वीर": "Picture", "फ़ोकस": "Focus", "बीच": "Centre", "ऊपर": "Top", "नीचे": "Bottom",
               "कोई तस्वीर नहीं।": "No picture.", "ऑनलाइन फ़ॉन्ट (Google Fonts) लोड करें": "Load online fonts (Google Fonts)", "4. विज्ञापन पट्टियाँ — ऊपर": "4. Advertisement band — top", "5. विज्ञापन पट्टियाँ — नीचे": "5. Advertisement band — bottom", "6. विज्ञापन पट्टी — बगल (खड़ी)": "6. Advertisement band — side (vertical)",
               "स्थान": "Position", "दाएँ": "Right", "बाएँ": "Left", "किनारे": "Corners", "गोल": "Rounded", "सीधे": "Square", "चौड़ाई (मिमी)": "Width (mm)", "चित्र न हो तो पाठ दिखेगा:": "Without an image the text is shown:",
               "7. व्यवसाय / फ़ुटर / कवर": "7. Business / footer / cover", "वेबसाइट": "Website", "कवर शीर्षक": "Cover title", "ख़ाली = व्यवसाय का नाम": "empty = business name", "कवर उप-शीर्षक": "Cover subtitle", "ख़ाली = टैगलाइन": "empty = tagline",
               "8. क्या-क्या दिखे": "8. What to show", "विशेष योग (सर्वार्थ सिद्धि, पंचक, भद्रा…)": "Special yogas (Sarvartha Siddhi, Panchak, Bhadra…)", "सूर्योदय-अस्त": "Sunrise/sunset", "9. अपनी तिथियाँ और छुट्टियाँ": "9. Your own dates and holidays",
               "10. सहेजे डिज़ाइन": "10. Saved designs", "डिज़ाइन का नाम": "Design name", "सहेजिए": "Save", "कोई सहेजा डिज़ाइन नहीं।": "No saved designs.", "HTML डाउनलोड": "Download HTML", "पृष्ठ बन रहे हैं…": "Building pages…",
               "प्रिंट संवाद में \"Save as PDF\" चुनिए, कागज़ वही आकार, मार्जिन \"None\", \"Background graphics\" चालू। पूरे वर्ष की झलक में सिर्फ़ चुना माह दिखता है; प्रिंट में सभी 12 पृष्ठ (+ कवर) जाते हैं।": "In the print dialog choose \"Save as PDF\", the same paper size, margins \"None\", \"Background graphics\" on. The whole-year preview shows one month; print produces all 12 pages (+ cover)."})
for _hi, _en in UI_CAL.items():
    EXACT.setdefault(_hi, _en)
# year overlay
from jyotish import timeline as _tl
for _h, (_hi, _en) in _tl.KEY_HOUSES.items():
    put(_hi, _en)
_ov_note = _tl.year_overlay.__doc__ and None
for _hi, _en in (("वर्ष-वार दोहरा गोचर (शनि + गुरु) और दशा", "Year by year: double transit (Saturn + Jupiter) and dasha"), ("हरा", "Green"), ("= वही भाव चल रही महादशा के स्वामी से भी जुड़ा।", "= that house is also linked to the running mahadasha lord."),
                 ("वर्ष", "Year"), ("आयु", "Age"), ("महादशा / अंतर्दशा", "Mahadasha / antardasha"), ("शनि भाव", "Saturn house"), ("गुरु भाव", "Jupiter house"), ("शनि-चरण", "Saturn phase"), ("दोहरा गोचर (मुख्य भाव)", "Double transit (key houses)"),
                 ("साढ़ेसाती", "Sade Sati"), ("अष्टम शनि", "Ashtama Shani")):
    EXACT.setdefault(_hi, _en)
put("हर वर्ष (1 जुलाई को) चल रही महादशा-अंतर्दशा, शनि-गुरु की राशि, साढ़ेसाती, और वे भाव जिन्हें शनि (3,7,10 दृष्टि + स्थिति) और गुरु (5,7,9 + स्थिति) दोनों प्रभावित करते हैं — 'दोहरा गोचर'। जब वही भाव चल रही महादशा के स्वामी से भी जुड़ा हो, तो परंपरा उस वर्ष को उस भाव के विषय में सक्रिय मानती है। यह समय-संकेत है, घटना की भविष्यवाणी नहीं।",
    "For every year (at 1 July): the running mahadasha/antardasha, Saturn's and Jupiter's signs, Sade Sati, and the houses both Saturn (aspects 3,7,10 + occupation) and Jupiter (5,7,9 + occupation) influence — the 'double transit'. When that house is also linked to the running mahadasha lord, tradition treats the year as active for that house's matters. A timing hint, not an event prediction.")
OVERLAY_PATTERNS = []
# tajika yogas
for _id, (_hi, _thi, _ten) in _tj.YOGA_HI.items():
    put(_hi, _id.capitalize() if _id not in ("ikkavala", "induvara", "kamboola") else {"ikkavala": "Ikkavala", "induvara": "Induvara", "kamboola": "Kambula"}[_id]); put(_thi, _ten)
put("लग्नेश और इस भाव के स्वामी में कोई ताजिक योग नहीं।", "No Tajika yoga between the Lagna lord and this house lord.")
_tjy = _tj.tajika_yogas({"Sun": 10.0, "Moon": 100.0, "Mars": 200.0, "Mercury": 20.0, "Jupiter": 300.0, "Venus": 40.0, "Saturn": 250.0}, {k: 1.0 for k in _tj.SEVEN}, 5.0, {k: {"total": 50} for k in _tj.SEVEN}, {k: 1 for k in _tj.SEVEN}, set(), set())
put(_tjy["note_hi"], _tjy["note_en"])
for _hi, _en in (("भावेश", "House lord"), ("अर्थ", "Meaning")):
    EXACT.setdefault(_hi, _en)
TAJIKA_YOGA_PATTERNS = [("ताजिक योग (लग्नेश {1} बनाम भावेश)", "Tajika yogas (Lagna lord {1} vs house lords)"), ("({1} द्वारा)", "(via {1})")]
# vastu from a floor plan
import json as _json
_vz = _json.loads((ROOT / "data" / "knowledge" / "vastu_zones.json").read_text(encoding="utf-8"))
for z in _vz["zones"]:
    put(z["hi"], z["en"]); put(z["theme_hi"], z["theme"]); put(z["element_hi"], z["element"])
for d in _vz["mandala"]["outer_32_clockwise_from_ne"] + list(_vz["mandala"]["inner_8"].values()) + [_vz["mandala"]["centre"]]:
    if d["hi"] not in PHRASES and d["hi"] not in EXACT:      # planet names (सूर्य → Sun) keep priority over the devata spelling
        put(d["hi"], d["en"])
for r in _vz["extra_rooms"].values():
    put(r["hi"], r["en"])
from jyotish import vastu_plan as _vp
_vpr = _vp.evaluate_plan({"polygon": [[0, 0], [10, 0], [10, 10], [0, 10]], "north_angle": 0, "rooms": []})
put(_vpr["note_hi"], _vpr["note_en"])
_vpc = _vp.evaluate_plan({"polygon": [[0, 0], [10, 0], [10, 10], [5, 10], [5, 5], [0, 5]], "north_angle": 0, "rooms": []})
for c in _vpc["cut_corners"]:
    put(c["text_hi"], c["text_en"])
for n in (90, 180, 270):
    for c in _vp.evaluate_plan({"polygon": [[0, 0], [10, 0], [10, 10], [5, 10], [5, 5], [0, 5]], "north_angle": n, "rooms": []})["cut_corners"]:
        put(c["text_hi"], c["text_en"])
_sk = _vp.evaluate_plan({"polygon": [[0, 0], [10, 0], [10, 10], [5, 10], [5, 5], [0, 5]], "north_angle": 45, "rooms": []})["skew_note"]
put(_sk["hi"], _sk["en"])
UI_VPLAN = {"नक्शे से वास्तु — 16-ज़ोन डिग्री-चक्र और वास्तु पुरुष मंडल": "Vastu from a floor plan — 16-zone degree wheel and Vastu Purusha Mandala",
            "घर/प्लॉट का नक्शा (PDF, AutoCAD DXF, PNG/JPG) चढ़ाइए, उत्तर दिशा बताइए, प्लॉट की सीमा और कमरे चित्र पर चिह्नित कीजिए। हर कमरे का अंश, 16-ज़ोन, 8-दिशा और 81-पद देवता निकलेगा। DWG हो तो पहले DXF या PDF में सेव कीजिए।":
            "Upload the house/plot plan (PDF, AutoCAD DXF, PNG/JPG), set the north direction, mark the plot boundary and rooms on the picture. Each room gets its degree, 16-zone, 8-direction and 81-pada devata. For a DWG, save it as DXF or PDF first.",
            "1. नक्शा फ़ाइल": "1. Plan file", "2. उत्तर-कोण (चित्र के ऊपर से घड़ी की दिशा में, °)": "2. North angle (clockwise from the top of the picture, °)",
            "चित्र पर उत्तर तीर खींचिए": "Draw the north arrow", "फ़ोन कम्पास से": "From phone compass", "3. प्लॉट सीमा बनाइए": "3. Draw plot boundary", "सीमा पूरी": "Boundary done",
            "4. कमरा": "4. Room", "कमरा रखिए": "Place room", "पीछे": "Undo", "साफ़": "Clear", "5. स्थान (नक्शे पर दिखाने के लिए)": "5. Location (to show on the map)",
            "शहर / गाँव": "City / village", "अक्षांश": "Latitude", "देशांतर": "Longitude", "मेरा स्थान": "My location", "विश्लेषण": "Analyse",
            "16-ज़ोन चक्र": "16-zone wheel", "81-पद मंडल": "81-pada mandala", "अंश-चिह्न": "Degree ticks",
            "प्लॉट की सीमा: कोनों पर क्लिक कीजिए, फिर \"सीमा पूरी\"।": "Plot boundary: click the corners, then \"Boundary done\".", "चुने हुए कमरे के बीच में क्लिक कीजिए।": "Click the middle of the chosen room.",
            "पहले प्लॉट के बीच में, फिर उत्तर की ओर एक बिंदु पर क्लिक कीजिए।": "Click the plot centre first, then a point towards north.",
            "फ़ाइल पढ़ी जा रही है…": "Reading the file…", "कम से कम 3 कोने चाहिए।": "At least 3 corners are needed.", "पहले प्लॉट की सीमा बनाइए (कम से कम 3 कोने)।": "Draw the plot boundary first (at least 3 corners).",
            "नक्शा लाइब्रेरी नहीं मिली (ऑफ़लाइन?)। स्थान सहेजा गया है।": "Map library not available (offline?). The location was kept.", "इस ब्राउज़र में स्थान सेवा नहीं है।": "This browser has no location service.",
            "स्थान नहीं मिला (अनुमति दीजिए)।": "Location not found (allow access).", "नक्शे का ऊपरी सिरा इस ओर": "The top of the plan points this way",
            "कमरे चिह्नित नहीं किए गए; केवल चक्र और मंडल दिखाए गए हैं।": "No rooms marked; only the wheel and the mandala are shown.", "(सीमा से बाहर)": "(outside the boundary)",
            "ज़ोन (16)": "Zone (16)", "दिशा (8)": "Direction (8)", "पद देवता": "Pada devata", "16-ज़ोन चक्र (अंश-सारणी)": "16-zone wheel (degree table)", "केंद्र अंश": "Centre degree", "ज़ोन-विषय": "Zone theme", "ज़ोन": "Zone",
            "उत्तम ज़ोन:": "Best zones:", "अंश": "Degrees", "दिशा-अंश": "Bearing", "कटे कोने": "Cut corners", "उत्तर-कोण (चित्र पर):": "North angle (on the picture):", "प्लॉट केंद्र": "plot centre",
            "वास्तु (नक्शे से)": "Vastu (from the plan)", "वास्तु — नक्शे से 16-ज़ोन विश्लेषण": "Vastu — 16-zone analysis from the plan", "PDF का पहला पृष्ठ चित्र में बदला गया।": "Page 1 of the PDF was rendered to an image.",
            "DWG है: AutoCAD/LibreCAD से DXF या PDF में सेव करके चढ़ाइए।": "DWG: save it as DXF or PDF from AutoCAD/LibreCAD and upload that."}
for hi, en in UI_VPLAN.items():
    EXACT.setdefault(hi, en)
VPLAN_PATTERNS = [("अंक {1} / {2} · उत्तर-कोण {3}°", "Score {1} / {2} · north angle {3}°"), ("अंक {1} / {2} · उत्तर-कोण {3}° · कटे कोने: {4}", "Score {1} / {2} · north angle {3}° · cut corners: {4}"),
                  ("कटे कोने: {1}", "cut corners: {1}"), ("· उत्तर-कोण {1}°", "· north angle {1}°"), ("उत्तम ज़ोन: {1}", "Best zones: {1}"),
                  ("फ़ोन का शीर्ष {1}° की ओर था → उत्तर-कोण {2}°।", "The phone's top pointed to {1}° → north angle {2}°."),
                  ("DXF की {1} रेखा-आकृतियाँ (LINE/POLYLINE/CIRCLE/ARC) चित्र में बदली गईं; टेक्स्ट, हैच और ब्लॉक नहीं दिखते। DWG हो तो AutoCAD/LibreCAD से DXF में सेव कीजिए।",
                   "{1} DXF entities (LINE/POLYLINE/CIRCLE/ARC) rendered; text, hatches and blocks are not shown. For a DWG, save it as DXF from AutoCAD/LibreCAD.")]
# pattern yogas (Mahapurusha, Nabhasa, conjunction)
from jyotish import yogas_nabhasa as _yn
for _pl, (_id, _nm, _hi, _thi, _ten) in _yn.MAHAPURUSHA.items():
    put(f"{_hi} महापुरुष योग", f"{_nm} Mahapurusha Yoga"); put(_thi, _ten)
for _id, (_nm, _hi, _g, _thi, _ten) in _yn.NABHASA_TEXT.items():
    put(f"{_hi} (नाभस) योग", f"{_nm} (Nabhasa) Yoga"); put(_thi, _ten)
for _id, (_nm, _hi, _thi, _ten) in _yn.CONJ_TEXT.items():
    put(f"{_hi} योग", f"{_nm} Yoga"); put(_thi, _ten)
put("नहीं बना (ग्रह एक राशि में नहीं)।", "Not formed (the planets are not in one sign).")
put("कोई विशेष योग नहीं बना।", "No special yoga is formed.")
YOGA_PATTERNS = [("सातों ग्रहों के भाव: {1}", "houses occupied by the seven planets: {1}"), ("राशि-स्वभाव: {1} (0 चर, 1 स्थिर, 2 द्विस्वभाव)", "sign qualities occupied: {1} (0 movable, 1 fixed, 2 dual)"), ("सात ग्रह {1} राशि(यों) में", "seven planets occupy {1} sign(s)"),
                 ("सात ग्रह {1} राशि(यों) में; आकृति योग को प्राथमिकता", "seven planets occupy {1} sign(s); an Akriti yoga takes precedence"),
                 ("{1} स्वराशि या उच्च में, लग्न से केंद्र में (यहाँ भाव {2}, {3})।", "{1} in its own or exaltation sign in a kendra from the Lagna (here house {2}, {3} sign)."),
                 ("चंद्र गुरु से {1}वें भाव में।", "Moon is in house {1} from Jupiter."), ("नहीं बने योग ({1})", "Yogas not formed ({1})"),
                 ("{1} योग जाँचे गए (शास्त्रीय, पंच-महापुरुष, 32 नाभस आकृति-योग, युति-योग); {2} बने हैं।", "{1} yogas checked (classical, Pancha Mahapurusha, 32 Nabhasa pattern yogas, conjunction yogas); {2} are formed.")]
for _hi, _en in (("स्वराशि", "own"), ("उच्च", "exalted"), ("सामान्य राशि", "ordinary")):
    EXACT.setdefault(_hi, _en)
# learn tab (rendered directly in the chosen language; only the static card text needs the dictionary)
for _hi, _en in (("सीखिए — दस पाठ, शब्दकोश और अभ्यास-प्रश्न", "Learn — ten lessons, glossary and practice questions"),
                 ("ग्रह से पंचांग तक दस छोटे पाठ; हर पाठ के अंत में 8 प्रश्नों का अभ्यास। शब्दकोश में खोजिए। पाठ ड्राफ़्ट हैं (समीक्षा बाकी)।", "Ten short lessons from planets to panchang; eight practice questions at the end of each. Search the glossary. Lessons are drafts (review pending)."),
                 ("पाठ", "Lessons"), ("शब्दकोश", "Glossary"), ("मिश्रित प्रश्नोत्तरी", "Mixed quiz"), ("सीखिए", "Learn")):
    EXACT.setdefault(_hi, _en)
# palm tracing
from jyotish import palm_trace as _ptr
_pk = _json.loads((ROOT / "data" / "knowledge" / "palm.json").read_text(encoding="utf-8"))
for k in _ptr.LANDMARKS:
    put(_ptr.LANDMARK_HI[k], _ptr.LANDMARK_EN[k])
for m in _pk["marks"].values():
    put(m["hi"], m["en"])
    for ln in _pk["lines"].values():
        put(m["hi_t"].replace("{line}", ln["hi"]), m["en_t"].replace("{line}", ln["en"]))
for x in _pk["extras"].values():
    put(x["hi"], x["en"])
    for b in x["bands"]:
        put(b["hi"], b["en"])
put(_pk["trace_note_hi"], _pk["trace_note"])
UI_PTRACE = {"हस्तरेखा — फ़ोटो पर रेखाएँ ट्रेस कीजिए": "Palmistry — trace the lines on a photo",
             "हथेली की साफ़ फ़ोटो चुनिए (उँगलियाँ ऊपर)। फ़ोटो आपके फ़ोन में ही रहती है, सर्वर को सिर्फ़ बिंदु जाते हैं। पहले 6 निशान (कलाई, चार उँगलियों के आधार, अंगूठे का जोड़), फिर हर रेखा पर 3–8 बिंदु क्लिक कीजिए।":
             "Choose a clear photo of the palm (fingers up). The photo stays on your phone; only points go to the server. First the 6 landmarks (wrist, four finger bases, thumb joint), then click 3–8 points along each line.",
             "1. हथेली की फ़ोटो": "1. Palm photo", "2. निशान लगाइए": "2. Set landmarks", "3. रेखा": "3. Line", "रेखा ट्रेस कीजिए": "Trace line", "4. चिह्न": "4. Mark", "चिह्न रखिए": "Place mark", "5. पढ़िए": "5. Read",
             "गिनती": "count", "ट्रेसिंग से": "from tracing", "रेखाओं पर चिह्न": "Marks on the lines", "अन्य रेखाएँ": "Other lines", "माप (हथेली के अनुपात में)": "Measurements (ratios of the palm)", "माप": "Measure", "मान": "Value",
             "निष्कर्ष": "Finding", "(ट्रेसिंग से)": "(from tracing)", "हस्तरेखा (फ़ोटो ट्रेसिंग)": "Palmistry (photo tracing)", "हस्तरेखा — फ़ोटो पर ट्रेस की गई रेखाओं से": "Palmistry — from lines traced on a photo",
             "पहले छहों निशान लगाइए।": "Set all six landmarks first.", "पहले कोई रेखा ट्रेस कीजिए, फिर उस पर चिह्न रखिए।": "Trace a line first, then place the mark on it.",
             "निशान पूरे। अब रेखा चुनकर \"रेखा ट्रेस कीजिए\" दबाइए।": "Landmarks done. Now choose a line and press \"Trace line\".", "कोई नहीं": "none", "चिह्न": "Mark", "रेखा": "Line"}
for hi, en in UI_PTRACE.items():
    EXACT.setdefault(hi, en)
PTRACE_PATTERNS = [("ट्रेस की गई रेखाएँ: {1}", "Lines traced: {1}"), ("निशान {1}/6: {2} पर क्लिक कीजिए।", "Landmark {1}/6: click on the {2}."),
                   ("हथेली लंबाई/चौड़ाई = {1} (लंबी हथेली); हाथ का तत्व उँगलियों की लंबाई से भी तय होता है, इसलिए वह आप चुनिए।", "Palm length/width = {1} (long palm); the hand's element also depends on finger length, so choose it yourself."),
                   ("हथेली लंबाई/चौड़ाई = {1} (चौकोर हथेली); हाथ का तत्व उँगलियों की लंबाई से भी तय होता है, इसलिए वह आप चुनिए।", "Palm length/width = {1} (square palm); the hand's element also depends on finger length, so choose it yourself."),
                   ("{1}: शुरू से अंत तक 3–8 बिंदु क्लिक कीजिए (शुरू: {2})।", "{1}: click 3–8 points from start to end (start: {2})."), ("चिह्न \"{1}\": रेखा पर उस जगह क्लिक कीजिए।", "Mark \"{1}\": click that spot on the line."),
                   ("{1} — {2}", "{1} — {2}")]
for _hi, _en in (("कनिष्ठा के नीचे", "under the little finger"), ("तर्जनी-अंगूठे के बीच", "between the index finger and thumb"), ("कलाई की ओर", "towards the wrist")):
    put(_hi, _en)
TAJIKA_PATTERNS = VPLAN_PATTERNS + PTRACE_PATTERNS + YOGA_PATTERNS + TAJIKA_YOGA_PATTERNS + OVERLAY_PATTERNS + FEST_PATTERNS + LAGNA_PATTERNS + RASHI_PATTERNS + [("(आयु {1}): सूर्य-वापसी", "(age {1}): solar return"), ("({1}) · वर्ष-लग्न", "({1}) · annual Lagna"),
                   ("{1} − {2} + लग्न +30°", "{1} − {2} + Lagna +30°"), ("{1} − {2} + लग्न (रात्रि में उलट) +30°", "{1} − {2} + Lagna (reversed at night) +30°"),
                   ("{1} — {2} → {3} ({4} दिन)", "{1} — {2} → {3} ({4} days)"), ("{1} − {2} + लग्न", "{1} − {2} + Lagna"), ("{1} − {2} + लग्न (रात्रि में उलट)", "{1} − {2} + Lagna (reversed at night)"),
                   ("वर्षेश: {1}", "Year lord: {1}")]
_tj_sample = _tj.tajika.__doc__  # noqa
_tjs = _tj.tajika({"planets": [{"name": k, "longitude": v, "house": 1} for k, v in {"Sun": 10.0, "Moon": 100.0, "Mars": 200.0, "Mercury": 20.0, "Jupiter": 300.0, "Venus": 40.0, "Saturn": 250.0}.items()], "lagna": {"longitude": 5.0}},
                  0, 0, {k: 1.0 for k in _tj.SEVEN}, __import__("datetime").datetime(2026, 1, 1, tzinfo=__import__("datetime").timezone.utc))
put(_tjs["note_hi"], _tjs["note_en"])

# AI tools (summary, calendar text, quiz, consult draft), language packs
for hi, en in [("AI सार", "AI summary"), ("AI सार बन रहा है…", "Preparing the AI summary…"), ("आज की AI सीमा पूरी हो गई।", "Today's AI quota is used up."),
               ("AI सेट नहीं है — सर्वर पर provider key जोड़ने के बाद यह बटन काम करेगा।", "AI is not configured — this button works once a provider key is added on the server."),
               ("AI से माह-संदेश व टैगलाइन", "AI month lines & tagline"), ("बन रहा है…", "working…"), ("AI प्रश्नोत्तरी का विषय (जैसे: साढ़ेसाती)", "AI quiz topic (e.g. Sade Sati)"), ("AI से 5 प्रश्न", "5 questions from AI"),
               ("प्रश्न बन रहे हैं…", "Making questions…"), ("सही", "correct"), ("AI मसौदा", "AI draft"), ("आप ज्योतिषी के रूप में देख रहे हैं", "You are viewing as the astrologer"), ("जन्म", "birth")]:
    put(hi, en)

# AI chat / palm scan, consultation, nadi, outer planets, eclipse, regional
for hi, en in [("AI से बातचीत", "Chat with AI"), ("जाँच रहा हूँ…", "checking…"), ("AI चालू", "AI on"), ("AI सेट नहीं — उत्तर ऐप की सामग्री से", "AI not configured — answers from the app's material"), ("vision AI सेट नहीं", "vision AI not configured"),
               ("लगातार सवाल-जवाब; उत्तर आपकी कुंडली (बनाई हो तो), ऐप के नियम-ग्रंथ और आज के पंचांग से बँधे रहते हैं। यह प्रवृत्ति-मार्गदर्शन है, भविष्यवाणी नहीं।", "A running conversation; answers stay grounded in your chart (if made), the app's rule texts and today's panchang. Tendency guidance, not prediction."),
               ("भेजिए", "Send"), ("नई बातचीत", "New chat"), ("सोच रहा हूँ…", "thinking…"), ("स्रोत", "Sources"), ("आज की AI सीमा पूरी — सामग्री से उत्तर", "Today's AI quota is used — answer from the material"), ("सामग्री से", "from the material"),
               ("हस्तरेखा — फ़ोटो से AI पहचान", "Palmistry — AI recognition from a photo"), ("हथेली की फ़ोटो", "Palm photo"), ("हाथ", "Hand"), ("दायाँ", "right"), ("बायाँ", "left"), ("AI से पढ़िए", "Read with AI"), ("पहचाने गए लक्षण", "Recognised features"),
               ("नीचे की सूची में विकल्प भर दिए गए हैं — बदलकर \"पढ़िए\" दबाइए।", "The choices below have been filled in — adjust and press \"Read\"."), ("पहले फ़ोटो चुनिए।", "Choose a photo first."),
               ("हथेली की साफ़ फ़ोटो (ऊपर से, उँगलियाँ थोड़ी खुली, अच्छी रोशनी)। AI केवल दिखने वाले लक्षण (रेखा लंबी/छोटी, पर्वत उभरे/सपाट…) पहचानता है; अर्थ ऐप की अपनी हस्तरेखा-सामग्री से आता है। पहचाने गए विकल्प नीचे की सूची में भर जाते हैं — आप बदल सकते हैं।", "A clear palm photo (from above, fingers slightly apart, good light). The AI only recognises visible features (line long/short, mounts raised/flat…); the meaning comes from the app's own palmistry material. Recognised choices fill the list below — you can change them."),
               ("परामर्श", "Consult"), ("ज्योतिषी से परामर्श", "Consult an astrologer"), ("सशुल्क (वॉलेट)", "paid (wallet)"), ("निःशुल्क · दक्षिणा वैकल्पिक", "free · dakshina optional"), ("निःशुल्क", "free"),
               ("अपना प्रश्न चुने हुए ज्योतिषी को भेजिए — उन्हें WhatsApp पर सूचना जाती है और उत्तर यहीं धागे में (और आपके WhatsApp पर) आता है। कुंडली बनाई हो तो जन्म-विवरण साथ जाता है।", "Send your question to the chosen astrologer — they are notified on WhatsApp and the reply arrives in this thread (and on your WhatsApp). Birth details go along if a chart was made."),
               ("अनुरोध", "Request"), ("माध्यम", "Mode"), ("प्रश्न", "Question"), ("रद्द", "Cancel"), ("मेरे अनुरोध", "My requests"), ("वॉलेट", "Wallet"), ("प्रश्न भेजिए", "Send a question"), ("अभी कोई ज्योतिषी सूचीबद्ध नहीं है।", "No astrologer is listed yet."),
               ("अनुरोध भेजा गया", "Request sent"), ("(ज्योतिषी को WhatsApp सूचना नहीं जा सकी — Relay सेट नहीं)", "(the astrologer could not be notified on WhatsApp — Relay not configured)"), ("शेष", "balance"), ("ज्योतिषी", "Astrologer"), ("स्थिति", "Status"), ("खोलिए", "Open"), ("कोई अनुरोध नहीं।", "No requests."),
               ("बंद करें (रेटिंग ★5)", "Close (rate ★5)"), ("संदेश…", "Message…"),
               ("नाड़ी (भृगु नंदी नाड़ी)", "Nadi (Bhrigu Nandi Nadi)"), ("गुरु-गोचर घड़ी", "Jupiter transit clock"), ("नाड़ी (कूट)", "Nadi (kuta)"), ("नाड़ी-अंश", "Nadi amsha"), ("जीव (जातक)", "Jeeva (the native)"), ("कर्म / व्यवसाय", "Karma / profession"), ("जीवनसाथी", "Spouse"), ("छाया ग्रह", "Shadow planets"),
               ("बाह्य ग्रह", "outer planet"), ("राहु-केतु", "Rahu-Ketu"), ("मध्यम नोड", "Mean node"), ("सत्य नोड", "True node"), ("सत्य (true) नोड", "true node"), ("मध्यम (mean) नोड", "mean node"),
               ("बाह्य ग्रह (यूरेनस, नेपच्यून, प्लूटो) केवल संदर्भ के लिए; दशा, योग, बल में प्रयुक्त नहीं।", "Outer planets (Uranus, Neptune, Pluto) for reference only; not used in dashas, yogas or strength."),
               ("इस स्थान पर ग्रहण", "Eclipses at this place"), ("दशकूट (दक्षिण भारतीय)", "Dashakoota (South Indian)"), ("कार्ड साझा करें", "Share card"), ("पंचांग का चित्र-कार्ड", "Panchang image card"), ("कूट", "Koota"), ("प्राप्तांक", "Points"), ("विवरण", "Detail"), ("आपकी वर्ष-सारणी (गोचर × अष्टकवर्ग)", "Your year table (transits × Ashtakavarga)"), ("बनाइए", "Build"), ("बन रही है…", "building…"), ("बदलाव की तारीख़ें", "Change dates"), ("(भाव आपके चंद्र से; संख्या = उस राशि में ग्रह की अष्टकवर्ग रेखाएँ, 5+ शुभ)", "(house from your Moon; number = the planet's Ashtakavarga bindus in that sign, 5+ good)"), ("भाषा", "Language"), ("यूरेनस (अरुण)", "Uranus"), ("नेपच्यून (वरुण)", "Neptune"), ("प्लूटो (यम)", "Pluto"), ("आदि (वात)", "Adi (vata)"), ("मध्य (पित्त)", "Madhya (pitta)"), ("अंत्य (कफ)", "Antya (kapha)")]:
    put(hi, en)

# doshas, remedies, yogini, chart views, ayanamsa, today extras
for hi, en in [("दोष-विचार (कालसर्प, पितृ, मंगल)", "Doshas (Kaal Sarp, Pitru, Mangal)"), ("उपाय-संकेत (रत्न, रुद्राक्ष, इष्ट, मंत्र)", "Remedy pointers (gem, rudraksha, Ishta, mantra)"),
               ("कालसर्प योग", "Kaal Sarp yoga"), ("पितृ दोष", "Pitru dosha"), ("मंगल दोष", "Mangal dosha"), ("आंशिक", "partial"), ("परिहार सहित", "with cancellation"), ("मध्यम", "medium"), ("प्रबल", "strong"), ("है", "yes"), ("नहीं", "no"),
               ("साढ़ेसाती", "Sade Sati"), ("पहला चरण चल रहा", "first phase running"), ("मध्य चरण चल रहा", "peak phase running"), ("अंतिम चरण चल रहा", "last phase running"), ("अभी नहीं", "not now"),
               ("रुद्राक्ष", "Rudraksha"), ("इष्ट देवता", "Ishta Devata"), ("लग्नेश मंत्र", "Lagna-lord mantra"), ("टालें", "Avoid"), ("के रत्न", "stones"),
               ("योगिनी दशा", "Yogini dasha"), ("अभी चल रही", "Running now"), ("अंतर", "antar"), ("वर्ष", "years"),
               ("दृष्टि:", "View:"), ("लग्न", "Lagna"), ("चंद्र कुंडली", "Chandra kundali"), ("सूर्य कुंडली", "Surya kundali"), ("अयनांश", "Ayanamsa"), ("लाहिरी (चित्रपक्ष)", "Lahiri (Chitrapaksha)"), ("रमण", "Raman"), ("कृष्णमूर्ति (KP)", "Krishnamurti (KP)"), ("युक्तेश्वर", "Yukteshwar"),
               ("नाम-सुझाव", "Name suggestions"), ("लड़का", "boy"), ("लड़की", "girl"),
               ("अभी चल रहा", "running now"), ("मिनट शेष", "min left"), ("दुर्मुहूर्त", "Dur muhurtam"), ("वर्ज्य", "Varjyam"), ("अमृत काल", "Amrit kalam"), ("आनंदादि योग", "Anandadi yoga"), ("ग्रहण", "Eclipse"),
               ("जीवन-रत्न", "life stone"), ("भाग्य-रत्न", "fortune stone"), ("लग्नेश (जीवन-रत्न)", "Lagna lord (life stone)"), ("नवमेश (भाग्य-रत्न)", "9th lord (fortune stone)"), ("पंचमेश (बुद्धि/संतान)", "5th lord (intellect/children)"),
               ("रविवार", "Sunday"), ("सोमवार", "Monday"), ("मंगलवार", "Tuesday"), ("बुधवार", "Wednesday"), ("गुरुवार", "Thursday"), ("शुक्रवार", "Friday"), ("शनिवार", "Saturday"),
               ("अनामिका", "ring finger"), ("कनिष्ठा", "little finger"), ("तर्जनी", "index finger"), ("मध्यमा", "middle finger")]:
    put(hi, en)

# chart style toggle, Today city picker, alerts
for hi, en in [("शैली:", "Style:"), ("उत्तर भारतीय", "North Indian"), ("दक्षिण भारतीय", "South Indian"), ("शहर बदलिए (जैसे: इंदौर)", "Change city (e.g. Indore)"), ("दिखाइए", "Show"), ("से", "from")]:
    put(hi, en)

# grouped navigation + "आज" home tab
for hi, en in [("आज", "Today"), ("मेरी कुंडली", "My kundali"), ("पंचांग-मुहूर्त", "Panchang & muhurta"), ("अन्य विद्याएँ", "Other disciplines"), ("सीखिए-पूछिए", "Learn & ask"),
               ("आज का पंचांग", "Today's panchang"), ("लोड हो रहा है…", "Loading…"), ("आज और कल के व्रत-पर्व", "Today's and tomorrow's vrats & festivals"), ("आज के शुभ-अशुभ समय", "Today's good and bad hours"),
               ("आज का राशिफल (सभी 12 राशियाँ)", "Today's rashifal (all 12 signs)"), ("चंद्र राशि से गोचर-आधारित प्रवृत्ति-संकेत; अपनी राशि अपनी कुंडली से जानिए।", "Transit-based tendency pointers from the Moon sign; find your sign from your chart."),
               ("जल्दी जाइए", "Quick links"), ("कुंडली बनाइए", "Make a kundali"), ("मुहूर्त खोजिए", "Find a muhurta"), ("कुंडली मिलान", "Kundali matching"), ("कैलेंडर बनाइए", "Make a calendar"), ("सवाल पूछिए", "Ask a question"),
               ("कोई व्रत-पर्व नहीं", "no vrat or festival"), ("कल की तिथि", "Tomorrow's tithi"), ("शुभ चौघड़िया", "Good choghadiya"), ("योग / करण", "Yoga / Karana"), ("मास", "Month"), ("शक", "Shaka"), ("कल", "Tomorrow"), ("और", "and"),
               ("पंचांग लोड नहीं हो सका:", "The panchang could not load:"), ("दिशाशूल", "Disha shool"), ("उद्वेग", "Udveg"), ("अमृत", "Amrit"), ("लाभ", "Labh"), ("रोग", "Rog"), ("चल", "Chal")]:
    put(hi, en)

# WhatsApp (Vivid Relay) daily-update card
for hi, en in [("WhatsApp पर रोज़ का अपडेट", "Daily update on WhatsApp"),
               ("(पंचांग, आपका राशिफल, कल के व्रत-पर्व की सूचना, साप्ताहिक सूची — निःशुल्क)", "(panchang, your rashifal, tomorrow's vrat/festival alert, weekly list — free)"),
               ("WhatsApp नंबर", "WhatsApp number"), ("रोज़ का समय", "Daily time"), ("मेरा राशिफल", "My rashifal"), ("कल के व्रत-पर्व की सूचना", "Tomorrow's vrat/festival alert"),
               ("साप्ताहिक सूची (रविवार)", "Weekly list (Sunday)"), ("क्षेत्रीय पर्व", "Regional festivals"), ("राष्ट्रीय दिवस", "National days"), ("मासिक शिवरात्रि", "Masik Shivaratri"), ("प्रदोष", "Pradosh"),
               ("संदेश का नमूना देखिए", "Preview the message"), ("कोड भेजिए", "Send code"), ("6 अंकों का कोड", "6-digit code"), ("सत्यापित करें", "Verify"), ("बंद करें", "Stop updates"),
               ("WhatsApp पर कोड भेजा गया", "Code sent on WhatsApp"), ("नीचे कोड डालकर सत्यापित करें।", "Enter the code below to verify."), ("कोड भेजा नहीं जा सका:", "The code could not be sent:"),
               ("सत्यापित! पहला संदेश भेज दिया गया; अब रोज़ चुने हुए समय पर आएगा।", "Verified! The first message has been sent; it will now arrive daily at the chosen time."),
               ("सत्यापित, पर पहला संदेश नहीं गया:", "Verified, but the first message did not go:"), ("अपडेट बंद कर दिए गए।", "Updates stopped."),
               ("(सर्वर पर Relay अभी सेट नहीं है — संदेश भेजे नहीं जाएँगे)", "(Relay is not configured on the server yet — messages will not be sent)")]:
    put(hi, en)

put("ताजिक परत (वर्षेश, सहम, मुद्दा दशा, इत्थशाल) ड्राफ़्ट है; पाठ केवल दिशा-संकेत हैं।", "The Tajika layer (year lord, sahams, mudda dasha, ithasala) is a draft; texts are only pointers.")

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
 "भाव-चलित (श्रीपति)": "Bhava chalit (Sripati)", "कृष्णमूर्ति पद्धति (KP)": "Krishnamurti Paddhati (KP)", "जैमिनी": "Jaimini",
 "सुनफा योग": "Sunapha Yoga", "अनफा योग": "Anapha Yoga", "दुरुधरा योग": "Durudhara Yoga", "केमद्रुम योग": "Kemadruma Yoga", "वेशि योग": "Vesi Yoga", "वासि योग": "Vasi Yoga",
 "उभयचरी योग": "Ubhayachari Yoga", "अधि योग": "Adhi Yoga", "अमला योग": "Amala Yoga", "हर्ष योग (विपरीत राजयोग)": "Harsha Yoga (Viparita Raja)", "सरल योग (विपरीत राजयोग)": "Sarala Yoga (Viparita Raja)",
 "विमल योग (विपरीत राजयोग)": "Vimala Yoga (Viparita Raja)", "परिवर्तन योग": "Parivartana Yoga (exchange)", "धन योग (2/11 व 5/9 के स्वामी)": "Dhana Yoga (lords of 2/11 with 5/9)",
 "राजयोग (केंद्र-त्रिकोण स्वामी)": "Raja Yoga (kendra–trikona lords)", "लक्ष्मी योग": "Lakshmi Yoga", "सरस्वती योग": "Saraswati Yoga",
 "चंद्र से दूसरे और बारहवें में (सूर्य के अलावा) कोई ग्रह नहीं, और चंद्र से केंद्र में भी कोई ग्रह नहीं (जो प्रचलित परिहार है)।": "No planet (other than the Sun) in the 2nd or 12th from the Moon, and none in a kendra from the Moon (a common cancellation).",
 "गुरु, शुक्र और बुध तीनों केंद्र, त्रिकोण या दूसरे भाव में, और गुरु स्वराशि/उच्च में (मित्र राशि यहाँ नहीं जाँची गई)।": "Jupiter, Venus and Mercury each in a kendra, trikona or the 2nd, with Jupiter in own/exalted sign (friendly sign not checked here).",
 "दो ग्रह एक-दूसरे की राशि में: कोई नहीं।": "Two planets occupy each other's signs: none.", "कोई नहीं।": "none.", "चल रही अंतर्दशा के प्रत्यंतर": "Pratyantar dashas of the running antardasha", "प्रत्यंतर": "Pratyantar", "PDF (प्रिंट)": "PDF (print)", "टैरो पठन": "Tarot reading", "स्थान": "Position", "कार्ड": "Card", "अर्थ (ड्राफ़्ट)": "Meaning (draft)", "आपका चुनाव": "Your choice", "लक्षण": "Feature",
 "मान": "Value", "टालने योग्य": "avoid", "स्वीकार्य": "acceptable",
 "यह परंपरागत वास्तु-मार्गदर्शन है, वैज्ञानिक या क़ानूनी सलाह नहीं। अलग-अलग परंपराओं में मतभेद हैं।": "This is traditional Vastu guidance, not scientific or legal advice. Traditions differ.",
 "हस्तरेखा परंपरागत कला है; इसका वैज्ञानिक आधार सिद्ध नहीं है। इसे आत्म-चिंतन और मनोरंजन की तरह लें। स्वास्थ्य, आयु, धन या क़ानूनी फ़ैसले इससे न करें।": "Palmistry is a traditional art; its scientific basis is not established. Take it as reflection and entertainment. Do not base health, lifespan, money or legal decisions on it.", "बहुत से बड़े अर्काना: बड़े जीवन-विषय या मोड़ का संकेत माना जाता है।": "Many major arcana: traditionally a sign of big life themes or a turning point.", "नामांक (कैल्डियन)": "Name number (Chaldean)", "नामांक (पाइथागोरियन)": "Name number (Pythagorean)", "स्वभाव (ड्राफ़्ट)": "Traits (draft)", "आदर्श दिशा": "Ideal direction", "अंक-ज्योतिष परंपरागत मार्गदर्शन है; व्याख्याएँ ड्राफ़्ट हैं। नामांक अंग्रेज़ी (लैटिन) अक्षरों से गिना गया है।": "Numerology is traditional guidance; readings are drafts. The name number is counted from Latin letters.",
 "वास्तु परंपरागत मार्गदर्शन है; व्याख्याएँ ड्राफ़्ट हैं।": "Vastu is traditional guidance; readings are drafts.", "हस्तरेखा परंपरागत कला है, भविष्यवाणी नहीं; व्याख्याएँ ड्राफ़्ट हैं।": "Palmistry is a traditional art, not prediction; readings are drafts.", "· उलटा": "· reversed", "पिछले प्रश्न": "Previous questions", "इतिहास मिटाएँ": "Clear history", "मुहूर्त PDF (प्रिंट)": "Muhurta PDF (print)", "प्रश्न PDF (प्रिंट)": "Prashna PDF (print)", "राहु काल": "Rahu kaal", "भाव-स्पष्ट": "Cusps", "ग्रह": "Planets", "सेव की गई कुंडली से भरें…": "Fill from a saved chart…", "मिलान:": "Match:", "(वर)": "(groom)", "(वधू)": "(bride)", "मिलान रिपोर्ट खोलिए (PDF के लिए प्रिंट कीजिए)": "Open matching report (print for PDF)", "कुंडली मिलान (अष्टकूट)": "Kundali matching (Ashtakoota)", "मंगल दोष तुलना": "Manglik comparison",
 "अष्टकूट": "Ashtakoota", "वर": "Groom", "वधू": "Bride", "लिंक कॉपी करें": "Copy link", "लिंक कॉपी हो गया।": "Link copied.", "आज क्या ख़ास है": "What matters today", "दशा:": "Dasha:", "शनि:": "Saturn:", "गुरु:": "Jupiter:", "आगे:": "Ahead:", "सक्रिय क्षेत्र:": "active areas:",
 "दशा और गोचर को साथ पढ़ने का संक्षेप; पूरा विवरण संबंधित टैब में।": "A short reading of dasha and transits together; full detail in the related tabs.",
 "चल रही है (पहला चरण); धैर्य और अनुशासन का समय माना जाता है।": "is running (first phase); traditionally a time for patience and discipline.",
 "चल रही है (मध्य चरण); धैर्य और अनुशासन का समय माना जाता है।": "is running (middle phase); traditionally a time for patience and discipline.",
 "चल रही है (अंतिम चरण); धैर्य और अनुशासन का समय माना जाता है।": "is running (last phase); traditionally a time for patience and discipline.", "विवरण बदलें": "Edit details", "इस कुंडली के बारे में पूछिए": "Ask about this chart", "सेव करें": "Save", "चल रही दशा": "Running dasha", "आज का गोचर": "Today's transits",
 "जन्म-समय": "Birth time", "पहला चरण": "first phase", "मध्य चरण": "middle phase", "अंतिम चरण": "last phase", "नहीं": "no", "लग्न 3 घंटे तक नहीं बदलता": "Lagna stable for 3 hours", "सावधानी": "caution",
 "कुंडली ऐप · गणना खगोलीय (NASA JPL DE440s, लाहिरी अयनांश); फलादेश परंपरागत मार्गदर्शन है, भविष्यवाणी या पेशेवर सलाह नहीं। व्याख्याएँ ड्राफ़्ट हैं और विद्वान-समीक्षा के अधीन हैं।":
 "Kundali app · astronomical computation (NASA JPL DE440s, Lahiri ayanamsa); interpretations are traditional guidance, not predictions or professional advice. Readings are drafts pending scholar review.", "लाल किताब": "Lal Kitab", "लाल किताब: ग्रह और घर": "Lal Kitab: planets and houses", "लाल किताब वर्षफल (वर्ष-कुंडली)": "Lal Kitab varshphal (annual chart)",
 "वर्ष (जन्मदिन से)": "Year (from the birthday)", "देखिए": "Show", "पक्का घर": "Pakka ghar", "घर (लग्न से)": "House (from Lagna)", "घर (मेष से)": "House (from Mesha)", "उपाय (ड्राफ़्ट)": "Remedy (draft)",
 "जन्म घर": "Natal house", "इस वर्ष का घर": "House this year", "जीवन भर के शनि-गुरु गोचर": "Saturn and Jupiter transits over life", "जीवन भर के शनि गोचर": "Saturn transits over life", "गुरु के भाव-वार काल": "Jupiter periods by house",
 "साढ़ेसाती": "Sade Sati", "बीत चुकी": "past", "चल रही": "running", "आगामी": "upcoming", "इस अवधि में नहीं": "none in this span", "अष्टम शनि:": "Ashtama Shani:", "कंटक शनि (चौथा):": "Kantaka Shani (4th):",
 "अष्टम शनि": "Ashtama Shani", "चरण": "Phases", "शुभ": "favourable", "पहला चरण (चंद्र से 12वाँ)": "first phase (12th from Moon)", "मध्य चरण (चंद्र राशि पर)": "middle phase (on the Moon sign)", "अंतिम चरण (चंद्र से दूसरा)": "last phase (2nd from Moon)", "गोचर-फल (ड्राफ़्ट)": "Transit results (draft)", "प्रश्न": "Prashna", "प्रश्न कुंडली (KP होरारी)": "Prashna chart (KP horary)", "विषय": "Topic", "KP अंक (1-249, वैकल्पिक)": "KP number (1-249, optional)",
 "समय (ख़ाली = अभी)": "Time (blank = now)", "प्रश्न पूछिए": "Ask the question", "गणना…": "Computing…", "रूलिंग प्लैनेट्स:": "Ruling planets:", "भाव-स्पष्ट और ग्रह": "Cusps and planets",
 "अनुकूल": "favourable", "प्रतिकूल": "unfavourable", "मिश्रित (देरी या शर्तों के साथ)": "mixed (with delay or conditions)", "अस्पष्ट": "unclear",
 "प्रश्न का विषय चुनिए। कुंडली इसी क्षण (या दिए समय) और स्थान की बनती है; चाहें तो 1 से 249 के बीच कोई अंक मन से कहिए (KP पद्धति)। स्वास्थ्य, क़ानून और आयु के प्रश्न यहाँ नहीं लिए जाते।":
 "Choose the topic. The chart is cast for this moment (or the given time) and place; you may also give a number from 1 to 249 that comes to mind (KP method). Health, legal and lifespan questions are not taken here.", "मुहूर्त": "Muhurta", "मुहूर्त खोज": "Muhurta finder", "कार्य": "Activity", "कब से": "From", "कितने दिन": "How many days", "स्थान": "Place",
 "शहर (ख़ाली = कुंडली वाला)": "City (blank = the chart's)", "खोजिए": "Search", "सबसे अच्छे दिन": "Best days", "सभी दिन": "All days", "तारीख़": "Date", "स्कोर": "Score", "पंचांग": "Panchang",
 "शुभ समय": "Good times", "सामान्य शुभ कार्य": "General auspicious work", "यात्रा": "Travel", "व्यापार / नया काम": "Business / new venture", "गृह प्रवेश": "House-warming",
 "वाहन ख़रीद": "Buying a vehicle", "विद्यारंभ / पढ़ाई": "Starting studies", "(ताराबल-चंद्रबल सहित)": "(with tarabala and chandrabala)", "अमावस्या": "amavasya",
 "सूर्योदय पर विष्टि (भद्रा) करण": "Vishti (Bhadra) karana at sunrise", "इस कार्य के लिए वर्जित वार": "weekday avoided for this", "ताराबल अनुकूल": "tarabala favourable", "चंद्रबल अनुकूल": "chandrabala favourable",
 "किस काम के लिए, कहाँ, और कब से: अगले दिनों में पंचांग के आधार पर अच्छे दिन और उनके शुभ चौघड़िया। कुंडली बनी हो तो ताराबल-चंद्रबल भी जुड़ते हैं।":
 "For which work, where and from when: good days in the coming period from the panchang, with their good choghadiya windows. With a chart made, tarabala and chandrabala are added.", "चर दशा": "Chara dasha", "सभी दशाएँ": "All dashas", "वार-स्वामी": "Day lord", "लग्न राशि/नक्षत्र/उप": "Lagna sign/star/sub",
 "चंद्र राशि/नक्षत्र/उप": "Moon sign/star/sub", "रूलिंग प्लैनेट्स (अभी)": "Ruling planets (now)", "जन्म से 120 वर्ष के बाहर।": "Outside 120 years from birth.", "अभी:": "Now:", "ज्योतिषी प्रोफ़ाइल (रिपोर्ट पर आपका नाम)": "Astrologer profile (your name on reports)", "यह जानकारी आपकी हर PDF रिपोर्ट के ऊपर छपेगी।": "This is printed at the top of every PDF report you make.",
 "नाम / संस्था": "Name / organisation", "फ़ोन": "Phone", "वेबसाइट": "Website", "पता": "Address", "एक पंक्ति (जैसे: \"परामर्श के लिए संपर्क करें\")": "One line (e.g. \"Contact for consultation\")",
 "प्रोफ़ाइल सेव करें": "Save profile", "सेव हो गया।": "Saved.", "नोट": "Note", "नोट सेव करें": "Save note", "ऐप इंस्टॉल करें": "Install app",
 "ऑफ़लाइन: कुंडली बनाने के लिए इंटरनेट चाहिए; सीखने की सामग्री खुली रहेगी।": "Offline: making a chart needs the internet; the learning material stays available.", "व": "R", "जैमिनी: चर कारक": "Jaimini: chara karakas", "आरूढ़ पद": "Arudha padas",
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
EXTRA_PATTERNS += [("{1} (KP अयनांश {2}°)", "{1} (KP ayanamsa {2}°)"),
                   ("चंद्र से दूसरे भाव में सूर्य के अलावा कोई ग्रह: {1}।", "A planet other than the Sun in the 2nd from the Moon: {1}."), ("चंद्र से बारहवें भाव में सूर्य के अलावा कोई ग्रह: {1}।", "A planet other than the Sun in the 12th from the Moon: {1}."),
                   ("चंद्र के दोनों ओर ग्रह: दूसरे में {1}, बारहवें में {2}।", "Planets on both sides of the Moon: 2nd {1}, 12th {2}."), ("सूर्य से दूसरे भाव में चंद्र के अलावा ग्रह: {1}।", "A planet other than the Moon in the 2nd from the Sun: {1}."),
                   ("सूर्य से बारहवें भाव में चंद्र के अलावा ग्रह: {1}।", "A planet other than the Moon in the 12th from the Sun: {1}."), ("सूर्य के दोनों ओर ग्रह: {1} / {2}।", "Planets on both sides of the Sun: {1} / {2}."),
                   ("चंद्र से 6/7/8 में शुभ ग्रह: {1} (यहाँ दो या अधिक गिने गए)।", "Benefics in the 6th/7th/8th from the Moon: {1} (two or more counted here)."), ("लग्न से दसवें में शुभ ग्रह ({1}) या चंद्र से दसवें में ({2})।", "A natural benefic in the 10th from the Lagna ({1}) or from the Moon ({2})."),
                   ("{1}वें भाव का स्वामी ({2}) {3}वें भाव में है; 6, 8 या 12 में हो तो यह योग गिना जाता है।", "Lord of the {1}th ({2}) is in house {3}; counted when it falls in 6, 8 or 12."),
                   ("दो ग्रह एक-दूसरे की राशि में: {1}।", "Two planets occupy each other's signs: {1}."), ("धन भावों (2, 11) के स्वामी आपस में या त्रिकोण (5, 9) के स्वामी के साथ: {1}।", "Lords of the wealth houses (2, 11) joined with each other or with trikona lords (5, 9): {1}."),
                   ("केंद्र (1/4/7/10) का स्वामी त्रिकोण (5/9) के स्वामी से युति या परिवर्तन में: {1}।", "A kendra lord (1/4/7/10) joined with a trikona lord (5/9) by conjunction or exchange: {1}."),
                   ("नवमेश ({1}) स्वराशि/उच्च में केंद्र या त्रिकोण में, और शुक्र स्वराशि/उच्च में। यहाँ: {2} भाव {3} में, शुक्र {4}।", "Lord of the 9th ({1}) in own/exalted sign in a kendra or trikona, and Venus in own/exalted sign. Here: {2} in house {3}; Venus {4}."),
                   ("{1}–{2}", "{1}–{2}"), ("{1} शुभ · {2} सावधानी", "{1} favourable · {2} caution"),
                   ("महादशा {1} ({2} → {3}) · अंतर्दशा {4} ({5} → {6}) · प्रत्यंतर {7} ({8} → {9})", "Mahadasha {1} ({2} → {3}) · Antardasha {4} ({5} → {6}) · Pratyantar {7} ({8} → {9})"), ("वेध: {1}", "vedha: {1}"), ("{1} (वेध: {2})", "{1} (vedha: {2})"), ("{1} · जन्म {2}", "{1} · born {2}"), ("· जन्म {1}", "· born {1}"), ("वैयक्तिक वर्ष {1}", "Personal year {1}"), ("अनुपस्थित अंक: {1} · दोहराए अंक: {2}", "Missing numbers: {1} · repeated numbers: {2}"),
                   ("स्प्रेड: {1} · प्रश्न: {2} · seed {3}", "Spread: {1} · question: {2} · seed {3}"), ("स्प्रेड: {1} · seed {2}", "Spread: {1} · seed {2}"), ("{1} (योग {2}, {3})", "{1} (compound {2}, {3})"), ("{1} (योग {2})", "{1} (compound {2})"), ("(योग {1}, {2})", "(compound {1}, {2})"), ("(योग {1})", "(compound {1})"), ("मुहूर्त खोज: {1}", "Muhurta finder: {1}"), ("प्रश्न कुंडली (KP): {1}", "Prashna chart (KP): {1}"), ("मुहूर्त — {1}", "Muhurta — {1}"), ("प्रश्न कुंडली — {1}", "Prashna chart — {1}"),
                   ("{1} से {2} दिन · बनाया गया: {3}", "{2} days from {1} · generated: {3}"), ("{1} से {2} दिन (ताराबल-चंद्रबल सहित) · बनाया गया: {3}", "{2} days from {1} (with tarabala and chandrabala) · generated: {3}"),
                   ("प्रश्न लग्न: {1} {2}° · समय: {3} · KP अयनांश {4}°", "Prashna Lagna: {1} {2}° · time: {3} · KP ayanamsa {4}°"), ("प्रश्न लग्न: {1} {2}° (KP अंक {3}) · समय: {4} · KP अयनांश {5}°", "Prashna Lagna: {1} {2}° (KP number {3}) · time: {4} · KP ayanamsa {5}°"), ("बनाया गया: {1}", "Generated: {1}"), ("कुंडली मिलान — {1} / {2}", "Kundali matching — {1} / {2}"),
                   ("— पारंपरिक न्यूनतम 18 से कम", "— below the traditional minimum of 18"), ("— स्वीकार्य (18-24)", "— acceptable (18-24)"), ("— अच्छा (25-32)", "— good (25-32)"), ("— उत्तम (33+)", "— excellent (33+)"), ("लग्न {1} {2} · चंद्र {3}, {4} पाद {5}", "Lagna {1} {2} · Moon {3}, {4} pada {5}"), ("जन्म {1} {2} · लग्न {3} {4} · चंद्र {5}, {6} पाद {7}", "Born {1} {2} · Lagna {3} {4} · Moon {5}, {6} pada {7}"),
                   ("बनाया गया: {1} · बैकएंड: {2}। यह रिपोर्ट शिक्षा और मार्गदर्शन के लिए है; विवाह जैसे निर्णय में पूरी कुंडली और विशेषज्ञ की सलाह देखें।", "Generated: {1} · backend: {2}. This report is for education and guidance; for a decision such as marriage, consider the full charts and an expert's advice."),
                   ("वर: {1}", "Groom: {1}"), ("वधू: {1}", "Bride: {1}"), ("{1} महादशा, {2} अंतर्दशा ({3} तक) — {4}; सक्रिय क्षेत्र: {5}।", "{1} mahadasha, {2} antardasha (until {3}) — {4}; active areas: {5}."),
                   ("{1} महादशा — {2}; सक्रिय क्षेत्र: {3}।", "{1} mahadasha — {2}; active areas: {3}."), ("{1} को {2} {3} में (चंद्र से {4}वाँ)।", "{2} enters {3} on {1} ({4}th from the Moon)."), ("{1} तक", "until {1}"), ("लग्न {1} मिनट में बदलता", "Lagna changes in {1} min"), ("{1} से {2}: जीवन का {3}वाँ वर्ष। {4}", "{1} to {2}: year {3} of life. {4}"), ("{1} से {2}: जीवन का {3}वाँ वर्ष। {4} (स्रोत की छपी सारणी में इस वर्ष की पंक्ति में एक अंक दोहराया है: {5})", "{1} to {2}: year {3} of life. {4} (the printed source row for this year repeats one number: {5})"), ("अष्टम शनि: {1}", "Ashtama Shani: {1}"),
                   ("{1}: {2}–{3} · {4}: {5}–{6} · {7}: {8}–{9}", "{1}: {2}–{3} · {4}: {5}–{6} · {7}: {8}–{9}"), ("{1}: {2}–{3} · {4}: {5}–{6}", "{1}: {2}–{3} · {4}: {5}–{6}"), ("{1}: {2}–{3}", "{1}: {2}–{3}"), ("प्रश्न लग्न: {1} {2}° · समय: {3}", "Prashna Lagna: {1} {2}° · time: {3}"), ("प्रश्न लग्न: {1} {2}° (KP अंक {3}) · समय: {4}", "Prashna Lagna: {1} {2}° (KP number {3}) · time: {4}"),
                   ("{1} का भाव {2}; उसके भाव-स्पष्ट का उप-स्वामी {3} है।", "House {2} rules {1}; the sub-lord of its cusp is {3}."),
                   ("{1} भाव {2} का कारक है: अनुकूल भाव {3}, प्रतिकूल भाव {4}।", "{1} signifies houses {2}: favouring {3}, denying {4}."),
                   ("चंद्र (प्रश्नकर्ता का मन) {1} में, उप-स्वामी {2}: प्रश्न विषय से जुड़ा है।", "The Moon (the querent's mind) in {1}, sub-lord {2}: connected to the matter."),
                   ("चंद्र (प्रश्नकर्ता का मन) {1} में, उप-स्वामी {2}: प्रश्न विषय से सीधा जुड़ाव नहीं दिखता।", "The Moon (the querent's mind) in {1}, sub-lord {2}: no direct connection to the matter."), ("{1}: {2} से {3} दिन", "{1}: {3} days from {2}"), (": {1} से {2} दिन", ": {2} days from {1}"), (": {1} से {2} दिन (ताराबल-चंद्रबल सहित)", ": {2} days from {1} (with tarabala and chandrabala)"), ("{1}: {2} से {3} दिन (ताराबल-चंद्रबल सहित)", "{1}: {3} days from {2} (with tarabala and chandrabala)"),
                   ("रिक्ता तिथि ({1})", "rikta tithi ({1})"), ("अशुभ योग ({1})", "inauspicious yoga ({1})"), ("अनुकूल नक्षत्र ({1})", "favourable nakshatra ({1})"), ("इस कार्य के लिए वर्जित नक्षत्र ({1})", "nakshatra avoided for this ({1})"),
                   ("ताराबल प्रतिकूल ({1}वाँ तारा)", "tarabala unfavourable ({1}th tara)"), ("चंद्रबल प्रतिकूल ({1}वाँ)", "chandrabala unfavourable ({1}th)"), ("अभिजित {1}–{2}", "Abhijit {1}–{2}"), ("राहु काल {1}–{2}", "Rahu kaal {1}–{2}"), ("अभी: {1} महादशा ({2} → {3}), अंतर्दशा {4} ({5} → {6})", "Now: {1} mahadasha ({2} → {3}), antardasha {4} ({5} → {6})"),
                   ("अभी: {1} ({2} → {3})", "Now: {1} ({2} → {3})"), ("महादशा ({1} → {2}), अंतर्दशा", "mahadasha ({1} → {2}), antardasha"), ("महादशा ({1} → {2})", "mahadasha ({1} → {2})"), ("अभी: {1} महादशा ({2} → {3})", "Now: {1} mahadasha ({2} → {3})"), ("{1} (अपवाद)", "{1} (exception)"), ("{1} कारकांश: {2}।", "{1} Karakamsa: {2}."), ("{1} मिनट", "{1} min"), ("(चंद्र से {1}, लग्न से {2})", "(from Moon {1}, from Lagna {2})"),
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

PATTERNS += EXTRA_PATTERNS + TAJIKA_PATTERNS
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
