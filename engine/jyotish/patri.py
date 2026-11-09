"""Traditional janma-patri header: birth details and the Avakahada chakra.

What a printed Indian patri shows above the charts — vara, tithi, paksha, nakshatra-pada and lord,
yoga, karana, sunrise/sunset, ishta kaal (ghati-pala), Vikram and Shaka samvat, lunar month,
ritu, ayana, tropical Sun sign — plus the Avakahada chakra used for naming and matching
(varna, vashya, yoni, gana, nadi, tattva, name syllable, rashi/nakshatra/lagna lords).

Samvat, masa and ritu are computed from the Sun's sidereal sign at the start of the lunar month
(amanta reckoning, no adhika-masa handling) and are marked approximate.
"""
from __future__ import annotations

from functools import lru_cache

from . import matching as M
from .core import ayanamsa, norm360
from .ephemeris import AnalyticBackend

_LUNATION_BACKEND = AnalyticBackend()   # new-moon search needs ~100 Sun/Moon evaluations; the analytic Moon is within
                                        # 0.01 deg of DE440s (about a minute of time), so the slow JPL backend is not used here
from .constants import NAKSHATRAS, NAKSHATRAS_HI, PLANETS_HI, SIGNS, SIGNS_HI, SIGN_LORDS

NAK_LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"] * 3

# name syllables per nakshatra pada (standard table used in Indian almanacs)
SYLLABLES = [
    "चू चे चो ला", "ली लू ले लो", "अ इ उ ए", "ओ वा वी वू", "वे वो का की", "कू घ ङ छ", "के को हा ही",
    "हू हे हो डा", "डी डू डे डो", "मा मी मू मे", "मो टा टी टू", "टे टो पा पी", "पू ष ण ठ",
    "पे पो रा री", "रू रे रो ता", "ती तू ते तो", "ना नी नू ने", "नो या यी यू", "ये यो भा भी",
    "भू धा फा ढा", "भे भो जा जी", "खी खू खे खो", "गा गी गू गे", "गो सा सी सू", "से सो दा दी",
    "दू थ झ ञ", "दे दो चा ची",
]
SYLLABLES_EN = [
    "Chu Che Cho La", "Li Lu Le Lo", "A I U E", "O Va Vi Vu", "Ve Vo Ka Ki", "Ku Gha Nga Chha", "Ke Ko Ha Hi",
    "Hu He Ho Da", "Di Du De Do", "Ma Mi Mu Me", "Mo Ta Ti Tu", "Te To Pa Pi", "Pu Sha Na Tha",
    "Pe Po Ra Ri", "Ru Re Ro Ta", "Ti Tu Te To", "Na Ni Nu Ne", "No Ya Yi Yu", "Ye Yo Bha Bhi",
    "Bhu Dha Pha Dha", "Bhe Bho Ja Ji", "Khi Khu Khe Kho", "Ga Gi Gu Ge", "Go Sa Si Su", "Se So Da Di",
    "Du Tha Jha Nya", "De Do Cha Chi",
]
TATTVA = ["Agni", "Prithvi", "Vayu", "Jala"] * 3          # by Moon sign (fire, earth, air, water)
TATTVA_HI = {"Agni": "अग्नि", "Prithvi": "पृथ्वी", "Vayu": "वायु", "Jala": "जल"}
MASA = ["Vaishakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada", "Ashwina",
        "Kartika", "Margashirsha", "Pausha", "Magha", "Phalguna", "Chaitra"]           # by Sun sign Mesha.. at amavasya
MASA_HI = ["वैशाख", "ज्येष्ठ", "आषाढ़", "श्रावण", "भाद्रपद", "आश्विन", "कार्तिक", "मार्गशीर्ष", "पौष", "माघ", "फाल्गुन", "चैत्र"]
RITU = {"Chaitra": "Vasanta", "Vaishakha": "Vasanta", "Jyeshtha": "Grishma", "Ashadha": "Grishma",
        "Shravana": "Varsha", "Bhadrapada": "Varsha", "Ashwina": "Sharad", "Kartika": "Sharad",
        "Margashirsha": "Hemanta", "Pausha": "Hemanta", "Magha": "Shishira", "Phalguna": "Shishira"}
RITU_HI = {"Vasanta": "वसंत", "Grishma": "ग्रीष्म", "Varsha": "वर्षा", "Sharad": "शरद", "Hemanta": "हेमंत", "Shishira": "शिशिर"}
NOTE_HI = "मास असली अमावस्याओं से, अधिक मास सहित (अमांत और पूर्णिमांत दोनों नाम); संवत् चैत्र शुक्ल से। घात चक्र ड्राफ़्ट है। सूर्योदय: पहला समय ऊपरी किनारा (सामान्य), कोष्ठक में सूर्य-केंद्र (पंचांग सॉफ़्टवेयर की परंपरा); इष्टकाल केंद्र वाले से।"
NOTE_EN = "Masa from the actual new moons incl. adhika masa (amanta and purnimanta names); samvat from Chaitra Shukla. Ghata chakra is a draft. Sunrise: first time is upper limb (usual), in brackets the disc centre (Indian panchang-software convention); ishta kaal uses the centre one."
WESTERN = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
           "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
HI = {"Brahmin": "ब्राह्मण", "Kshatriya": "क्षत्रिय", "Vaishya": "वैश्य", "Shudra": "शूद्र",
      "Chatushpada": "चतुष्पद", "Manav": "मानव", "Jalachara": "जलचर", "Vanachara": "वनचर", "Keeta": "कीट",
      "Horse": "अश्व", "Elephant": "गज", "Sheep": "मेष", "Serpent": "सर्प", "Dog": "श्वान", "Cat": "मार्जार",
      "Rat": "मूषक", "Cow": "गौ", "Buffalo": "महिष", "Tiger": "व्याघ्र", "Deer": "मृग", "Monkey": "वानर",
      "Mongoose": "नकुल", "Lion": "सिंह", "Deva": "देव", "Manushya": "मनुष्य", "Rakshasa": "राक्षस",
      "Adi": "आद्य", "Madhya": "मध्य", "Antya": "अंत्य", "Uttarayana": "उत्तरायण", "Dakshinayana": "दक्षिणायन"}


def _elong(backend, jd_tt: float) -> float:
    pos = backend.positions(jd_tt)
    return norm360(pos["Moon"] - pos["Sun"])


@lru_cache(maxsize=8192)
def _amavasya_before(backend, jd_tt: float) -> float:
    """JD (TT) of the last new moon at or before jd_tt: step back day by day until the elongation wraps, then bisect."""
    hi = jd_tt
    e_hi = _elong(backend, hi)
    lo = hi - 1.0
    while True:                                   # elongation decreases going back in time; a jump up means we crossed 0
        e_lo = _elong(backend, lo)
        if e_lo > e_hi:
            break
        hi, e_hi = lo, e_lo
        lo -= 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if _elong(backend, mid) > 180:            # still before the new moon
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


@lru_cache(maxsize=8192)
def lunar_month(backend, jd_tt: float, ayan: float) -> dict:
    """Amanta month containing jd_tt: name from the Sun's sidereal sign at its start; adhika when no sankranti falls inside."""
    t0 = _amavasya_before(backend, jd_tt)
    t1 = _amavasya_before(backend, t0 + 31.0)
    s0 = int(norm360(backend.positions(t0)["Sun"] - ayan) // 30)
    s1 = int(norm360(backend.positions(t1)["Sun"] - ayan) // 30)
    adhika = s0 == s1
    return {"index": s0, "name": MASA[s0], "name_hi": MASA_HI[s0], "adhika": adhika, "start_jd_tt": t0, "end_jd_tt": t1}


# Ghata chakra (Muhurta Chintamani): inauspicious month/tithi/vara/nakshatra/yoga/karana/prahar/Moon-sign
# for each janma rashi. Draft table; the Dhanu row was checked against a printed patri.
GHATA = {
    "Mesha":      {"masa": "Kartika",     "tithi": "1 6 11", "vara": "Ravivara",    "nakshatra": "Magha",            "yoga": "Vishkambha", "karana": "Bava",     "prahar": 1, "chandra": "Mesha",      "stri_chandra": "Vrishchika"},
    "Vrishabha":  {"masa": "Margashirsha","tithi": "5 10 15", "vara": "Shanivara",   "nakshatra": "Hasta",            "yoga": "Shiva",      "karana": "Bava",     "prahar": 4, "chandra": "Kanya",      "stri_chandra": "Dhanu"},
    "Mithuna":    {"masa": "Ashadha",     "tithi": "2 7 12", "vara": "Somavara",    "nakshatra": "Swati",            "yoga": "Vyaghata",   "karana": "Kaulava",  "prahar": 2, "chandra": "Kumbha",     "stri_chandra": "Mithuna"},
    "Karka":      {"masa": "Pausha",      "tithi": "2 7 12", "vara": "Budhavara",   "nakshatra": "Anuradha",         "yoga": "Vriddhi",    "karana": "Taitila",  "prahar": 3, "chandra": "Simha",      "stri_chandra": "Vrishchika"},
    "Simha":      {"masa": "Jyeshtha",    "tithi": "3 8 13", "vara": "Shanivara",   "nakshatra": "Mula",             "yoga": "Vajra",      "karana": "Garija",   "prahar": 1, "chandra": "Makara",     "stri_chandra": "Tula"},
    "Kanya":      {"masa": "Bhadrapada",  "tithi": "5 10 15", "vara": "Shanivara",   "nakshatra": "Shravana",         "yoga": "Ganda",      "karana": "Bava",     "prahar": 2, "chandra": "Mithuna",    "stri_chandra": "Mesha"},
    "Tula":       {"masa": "Magha",       "tithi": "4 9 14", "vara": "Guruvara",    "nakshatra": "Shatabhisha",      "yoga": "Vyatipata",  "karana": "Vishti",   "prahar": 3, "chandra": "Karka",      "stri_chandra": "Mesha"},
    "Vrishchika": {"masa": "Chaitra",     "tithi": "1 6 11", "vara": "Shukravara",  "nakshatra": "Revati",           "yoga": "Parigha",    "karana": "Bava",     "prahar": 4, "chandra": "Vrishabha",  "stri_chandra": "Kumbha"},
    "Dhanu":      {"masa": "Shravana",    "tithi": "3 8 13", "vara": "Shukravara",  "nakshatra": "Bharani",          "yoga": "Vyaghata",   "karana": "Taitila",  "prahar": 1, "chandra": "Karka",      "stri_chandra": "Makara"},
    "Makara":     {"masa": "Vaishakha",   "tithi": "4 9 14", "vara": "Mangalavara", "nakshatra": "Rohini",           "yoga": "Sukarma",    "karana": "Kaulava",  "prahar": 2, "chandra": "Mesha",      "stri_chandra": "Simha"},
    "Kumbha":     {"masa": "Chaitra",     "tithi": "3 8 13", "vara": "Guruvara",    "nakshatra": "Ardra",            "yoga": "Atiganda",   "karana": "Bava",     "prahar": 3, "chandra": "Dhanu",      "stri_chandra": "Mesha"},
    "Meena":      {"masa": "Ashwina",     "tithi": "5 10 15", "vara": "Shukravara",  "nakshatra": "Ashlesha",         "yoga": "Shoola",     "karana": "Garija",   "prahar": 4, "chandra": "Kumbha",     "stri_chandra": "Dhanu"},
}
GHATA_HI = {"Vishkambha": "विष्कम्भ", "Shiva": "शिव", "Vyaghata": "व्याघात", "Vriddhi": "वृद्धि", "Vajra": "वज्र", "Ganda": "गण्ड",
            "Vyatipata": "व्यतीपात", "Parigha": "परिघ", "Sukarma": "सुकर्मा", "Atiganda": "अतिगण्ड", "Shoola": "शूल",
            "Bava": "बव", "Kaulava": "कौलव", "Taitila": "तैतिल", "Garija": "गरज", "Vishti": "विष्टि",
            "Ravivara": "रविवार", "Somavara": "सोमवार", "Mangalavara": "मंगलवार", "Budhavara": "बुधवार",
            "Guruvara": "गुरुवार", "Shukravara": "शुक्रवार", "Shanivara": "शनिवार"}


def ghata_chakra(moon_sign_name: str) -> dict:
    g = GHATA[moon_sign_name]
    mi, ci, si = MASA.index(g["masa"]), SIGNS.index(g["chandra"]), SIGNS.index(g["stri_chandra"])
    ni = NAKSHATRAS.index(g["nakshatra"])
    return {"rashi": moon_sign_name, "rashi_hi": SIGNS_HI[SIGNS.index(moon_sign_name)],
            "masa": g["masa"], "masa_hi": MASA_HI[mi], "tithi": g["tithi"],
            "vara": g["vara"], "vara_hi": GHATA_HI[g["vara"]],
            "nakshatra": g["nakshatra"], "nakshatra_hi": NAKSHATRAS_HI[ni],
            "yoga": g["yoga"], "yoga_hi": GHATA_HI[g["yoga"]], "karana": g["karana"], "karana_hi": GHATA_HI[g["karana"]],
            "prahar": g["prahar"], "chandra": g["chandra"], "chandra_hi": SIGNS_HI[ci], "chandra_house_from_moon": (ci - SIGNS.index(moon_sign_name)) % 12 + 1,
            "stri_chandra": g["stri_chandra"], "stri_chandra_hi": SIGNS_HI[si], "stri_chandra_house_from_moon": (si - SIGNS.index(moon_sign_name)) % 12 + 1,
            "review_status": "draft"}


def _hhmm_to_min(t: str) -> float:
    h, m = t.split(":")[:2]
    return int(h) * 60 + int(m)


_NAMES = None


def _name_suggestions(pada_syllable: str, all_syllables: list[str]) -> dict:
    """Seed names for the pada syllable first, then the other syllables of the nakshatra."""
    global _NAMES
    import json
    from pathlib import Path
    if _NAMES is None:
        try:
            _NAMES = json.loads((Path(__file__).resolve().parents[2] / "data" / "knowledge" / "baby_names.json").read_text("utf-8"))["names"]
        except Exception:
            _NAMES = {}
    boys, girls = [], []
    for syl in [pada_syllable] + [x for x in all_syllables if x != pada_syllable]:
        e = _NAMES.get(syl, {})
        boys += [n for n in e.get("boys", []) if n not in boys]
        girls += [n for n in e.get("girls", []) if n not in girls]
    return {"boys": boys[:8], "girls": girls[:8]}


def details(chart: dict) -> dict:
    inp, pc, day = chart["input"], chart["panchang"], chart.get("day") or {}
    planets = {p["name"]: p for p in chart["planets"]}
    moon, sun, lg = planets["Moon"], planets["Sun"], chart["lagna"]
    nak_i = NAKSHATRAS.index(moon["nakshatra"])
    pada = int(moon["pada"])
    msign = int(moon["sign"])
    tlon = (sun["longitude"] + chart["ayanamsa_value"]) % 360          # tropical Sun → western sun sign

    t = pc["tithi"]
    # lunar month from the actual lunations (new moons found in the ephemeris), amanta reckoning
    try:
        jd_tt = chart["jd_ut"] + 69.0 / 86400.0
        lm = lunar_month(_LUNATION_BACKEND, jd_tt, chart["ayanamsa_value"])
        masa_i, adhika = lm["index"], lm["adhika"]
    except Exception:                                               # backend unavailable: tithi-based estimate
        days_since_amavasya = ((t["number"] - 1) + t.get("fraction_elapsed", 0.5)) * (29.53 / 30)
        masa_i = int(((sun["longitude"] - days_since_amavasya * 360 / 365.25) % 360) // 30)
        adhika = False
    masa = MASA[masa_i]
    year = int(inp["date"][:4])
    # Chaitra Shukla 1 starts the Vikram/Shaka year; months Chaitra..Phalguna in calendar order
    month_order = (masa_i + 1) % 12                                     # Chaitra = 0 ... Phalguna = 11
    # the lunar new year (Chaitra Shukla 1) falls in March/April: Magha/Phalguna early in the calendar year → previous samvat
    before_new_year = (month_order >= 10) and inp["date"][5:7] <= "04"  # Magha/Phalguna of early calendar year
    vikram = year + 56 if before_new_year else year + 57
    shaka = year - 79 if before_new_year else year - 78

    ishta = None
    rise_for_ishta = day.get("sunrise_centre") or day.get("sunrise")   # Indian programs use the disc-centre sunrise
    if rise_for_ishta:
        birth_min = _hhmm_to_min(inp["time"])
        delta = birth_min - _hhmm_to_min(rise_for_ishta)
        if delta < 0:
            delta += 24 * 60
        ghati = delta / 24.0
        ishta = {"ghati": int(ghati), "pala": int(round((ghati - int(ghati)) * 60)), "text": f"{int(ghati)}:{int(round((ghati - int(ghati)) * 60)):02d}"}

    ayana = "Uttarayana" if 270 <= sun["longitude"] or sun["longitude"] < 90 else "Dakshinayana"
    birth = {
        "vara": {"name": pc["vara"]["name"], "name_hi": pc["vara"]["name_hi"]},
        "tithi": {"name": t["name"], "name_hi": t["name_hi"], "paksha": t["paksha"], "paksha_hi": t["paksha_hi"]},
        "nakshatra": {"name": moon["nakshatra"], "name_hi": moon["nakshatra_hi"], "pada": pada,
                      "lord": NAK_LORDS[nak_i], "lord_hi": PLANETS_HI[NAK_LORDS[nak_i]]},
        "yoga": {"name": pc["yoga"]["name"], "name_hi": pc["yoga"]["name_hi"]},
        "karana": {"name": pc["karana"]["name"], "name_hi": pc["karana"]["name_hi"]},
        "sunrise": day.get("sunrise"), "sunset": day.get("sunset"),
        "sunrise_centre": day.get("sunrise_centre"), "sunset_centre": day.get("sunset_centre"),
        "ishta_kaal": ishta,
        "masa": {"name": ("Adhika " if adhika else "") + masa, "name_hi": ("अधिक " if adhika else "") + MASA_HI[masa_i], "adhika": adhika,
                 # purnimanta (north-Indian) reckoning: the krishna paksha belongs to the following month's name
                 "purnimanta": ("Adhika " if adhika else "") + (MASA[(masa_i + 1) % 12] if t["paksha"] == "Krishna" else masa),
                 "purnimanta_hi": ("अधिक " if adhika else "") + (MASA_HI[(masa_i + 1) % 12] if t["paksha"] == "Krishna" else MASA_HI[masa_i])},
        "ritu": {"name": RITU[masa], "name_hi": RITU_HI[RITU[masa]]},
        "ayana": {"name": ayana, "name_hi": HI[ayana]},
        "vikram_samvat": vikram, "shaka_samvat": shaka, "samvat_approx": True,
        "sun_sign_tropical": {"name": WESTERN[int(tlon // 30)], "name_hi": SIGNS_HI[int(tlon // 30)]},
        "ayanamsa": chart["ayanamsa_dms"],
    }
    varna = M._VARNA_OF_SIGN[msign]
    vashya = M.vashya_group(moon["longitude"])
    yoni = M._NAK_YONI[nak_i]
    gana = M._GANA[nak_i]
    nadi = M._NADI[nak_i % 6]
    tattva = TATTVA[msign]
    avakahada = {
        "varna": {"name": varna, "name_hi": HI[varna]},
        "vashya": {"name": vashya, "name_hi": HI.get(vashya, vashya)},
        "yoni": {"name": yoni, "name_hi": HI.get(yoni, yoni)},
        "gana": {"name": gana, "name_hi": HI[gana]},
        "nadi": {"name": nadi, "name_hi": HI[nadi]},
        "tattva": {"name": tattva, "name_hi": TATTVA_HI[tattva]},
        "name_syllable": {"all": SYLLABLES[nak_i], "all_en": SYLLABLES_EN[nak_i],
                          "pada": SYLLABLES[nak_i].split()[pada - 1], "pada_en": SYLLABLES_EN[nak_i].split()[pada - 1],
                          "suggestions": _name_suggestions(SYLLABLES[nak_i].split()[pada - 1], SYLLABLES[nak_i].split())},
        "rashi": {"name": SIGNS[msign], "name_hi": SIGNS_HI[msign], "lord": SIGN_LORDS[msign], "lord_hi": PLANETS_HI[SIGN_LORDS[msign]]},
        "lagna": {"name": lg["sign_name"], "name_hi": lg["sign_name_hi"], "lord": lg["lord"], "lord_hi": PLANETS_HI[lg["lord"]]},
        "nakshatra_lord": {"name": NAK_LORDS[nak_i], "name_hi": PLANETS_HI[NAK_LORDS[nak_i]]},
    }
    return {"birth": birth, "avakahada": avakahada, "ghata": ghata_chakra(SIGNS[msign]), "note_hi": NOTE_HI, "note_en": NOTE_EN}
