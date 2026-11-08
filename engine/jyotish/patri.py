"""Traditional janma-patri header: birth details and the Avakahada chakra.

What a printed Indian patri shows above the charts — vara, tithi, paksha, nakshatra-pada and lord,
yoga, karana, sunrise/sunset, ishta kaal (ghati-pala), Vikram and Shaka samvat, lunar month,
ritu, ayana, tropical Sun sign — plus the Avakahada chakra used for naming and matching
(varna, vashya, yoni, gana, nadi, tattva, name syllable, rashi/nakshatra/lagna lords).

Samvat, masa and ritu are computed from the Sun's sidereal sign at the start of the lunar month
(amanta reckoning, no adhika-masa handling) and are marked approximate.
"""
from __future__ import annotations

from . import matching as M
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
NOTE_HI = "मास, ऋतु और संवत् अमांत गणना से अनुमानित हैं (अधिक मास नहीं देखा गया)। सूर्योदय बिना ऊँचाई-सुधार के है।"
NOTE_EN = "Masa, ritu and samvat are approximate (amanta reckoning, no adhika masa). Sunrise has no altitude correction."
WESTERN = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
           "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
HI = {"Brahmin": "ब्राह्मण", "Kshatriya": "क्षत्रिय", "Vaishya": "वैश्य", "Shudra": "शूद्र",
      "Chatushpada": "चतुष्पद", "Manav": "मानव", "Jalachara": "जलचर", "Vanachara": "वनचर", "Keeta": "कीट",
      "Horse": "अश्व", "Elephant": "गज", "Sheep": "मेष", "Serpent": "सर्प", "Dog": "श्वान", "Cat": "मार्जार",
      "Rat": "मूषक", "Cow": "गौ", "Buffalo": "महिष", "Tiger": "व्याघ्र", "Deer": "मृग", "Monkey": "वानर",
      "Mongoose": "नकुल", "Lion": "सिंह", "Deva": "देव", "Manushya": "मनुष्य", "Rakshasa": "राक्षस",
      "Adi": "आद्य", "Madhya": "मध्य", "Antya": "अंत्य", "Uttarayana": "उत्तरायण", "Dakshinayana": "दक्षिणायन"}


def _hhmm_to_min(t: str) -> float:
    h, m = t.split(":")[:2]
    return int(h) * 60 + int(m)


def details(chart: dict) -> dict:
    inp, pc, day = chart["input"], chart["panchang"], chart.get("day") or {}
    planets = {p["name"]: p for p in chart["planets"]}
    moon, sun, lg = planets["Moon"], planets["Sun"], chart["lagna"]
    nak_i = NAKSHATRAS.index(moon["nakshatra"])
    pada = int(moon["pada"])
    msign = int(moon["sign"])
    tlon = (sun["longitude"] + chart["ayanamsa_value"]) % 360          # tropical Sun → western sun sign

    # lunar month: Sun's sidereal sign at the start of the current lunar month (amanta, approx.)
    t = pc["tithi"]
    tithi_index = t["number"] - 1                                      # number already runs 1..30
    days_since_amavasya = (tithi_index + t.get("fraction_elapsed", 0.5)) * (29.53 / 30)
    sun_at_amavasya = (sun["longitude"] - days_since_amavasya * 360 / 365.25) % 360
    masa_i = int(sun_at_amavasya // 30)
    masa = MASA[masa_i]
    year = int(inp["date"][:4])
    # Chaitra Shukla 1 starts the Vikram/Shaka year; months Chaitra..Phalguna in calendar order
    month_order = (masa_i + 1) % 12                                     # Chaitra = 0 ... Phalguna = 11
    # the lunar new year (Chaitra Shukla 1) falls in March/April: Magha/Phalguna early in the calendar year → previous samvat
    before_new_year = (month_order >= 10) and inp["date"][5:7] <= "04"  # Magha/Phalguna of early calendar year
    vikram = year + 56 if before_new_year else year + 57
    shaka = year - 79 if before_new_year else year - 78

    ishta = None
    if day.get("sunrise"):
        birth_min = _hhmm_to_min(inp["time"])
        delta = birth_min - _hhmm_to_min(day["sunrise"])
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
        "ishta_kaal": ishta,
        "masa": {"name": masa, "name_hi": MASA_HI[masa_i], "approx": True},
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
                          "pada": SYLLABLES[nak_i].split()[pada - 1], "pada_en": SYLLABLES_EN[nak_i].split()[pada - 1]},
        "rashi": {"name": SIGNS[msign], "name_hi": SIGNS_HI[msign], "lord": SIGN_LORDS[msign], "lord_hi": PLANETS_HI[SIGN_LORDS[msign]]},
        "lagna": {"name": lg["sign_name"], "name_hi": lg["sign_name_hi"], "lord": lg["lord"], "lord_hi": PLANETS_HI[lg["lord"]]},
        "nakshatra_lord": {"name": NAK_LORDS[nak_i], "name_hi": PLANETS_HI[NAK_LORDS[nak_i]]},
    }
    return {"birth": birth, "avakahada": avakahada, "note_hi": NOTE_HI, "note_en": NOTE_EN}
