"""Muhurta finder v1: rank the next N days for a kind of activity, from the panchang at sunrise.

Rules are the common almanac-level ones (draft, pending scholar review): avoid rikta tithis (4, 9, 14) and
amavasya, avoid the "bad" yogas, avoid Vishti (Bhadra) karana at sunrise, prefer nakshatras traditionally
suited to the activity and avoid the ones traditionally shunned for it, avoid the weekday the tradition
dislikes for it. Each day gets a score and the reasons; the day's good choghadiya windows, abhijit and Rahu
kaal are attached so the user can pick an hour. This is guidance, not a pandit's muhurta (no tarabala /
chandrabala from the person's Moon unless a chart is given; then they are added).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .constants import NAKSHATRAS, NAKSHATRAS_HI
from .core import ayanamsa, nakshatra_of
from .ephemeris import AnalyticBackend, norm360
from .muhurta import day_table
from .panchang import panchang
from .sun import sun_times
from .timeutil import delta_t, julian_day, year_fraction

_BACKEND = AnalyticBackend()
BAD_YOGAS = {"Vishkambha", "Atiganda", "Shoola", "Ganda", "Vyaghata", "Vajra", "Vyatipata", "Parigha", "Vaidhriti"}
RIKTA = {4, 9, 14}
N = {n: i for i, n in enumerate(NAKSHATRAS)}

ACTIVITIES = {
    "travel": {"hi": "यात्रा", "en": "Travel",
               "good_nak": ["Ashwini", "Mrigashira", "Punarvasu", "Pushya", "Hasta", "Anuradha", "Shravana", "Dhanishta", "Revati"],
               "bad_nak": ["Bharani", "Krittika", "Ardra", "Ashlesha", "Magha", "Jyeshtha", "Mula"],
               "bad_vara": [], "bad_vara_dir": {"east": 0, "north": 3, "south": 4, "west": 5}},
    "business": {"hi": "व्यापार / नया काम", "en": "Business / new venture",
                 "good_nak": ["Ashwini", "Rohini", "Mrigashira", "Punarvasu", "Pushya", "Uttara Phalguni", "Hasta", "Chitra", "Anuradha",
                              "Uttara Ashadha", "Shravana", "Uttara Bhadrapada", "Revati"],
                 "bad_nak": ["Bharani", "Krittika", "Ardra", "Ashlesha", "Magha", "Vishakha", "Jyeshtha", "Mula", "Purva Bhadrapada"], "bad_vara": [2]},
    "griha_pravesh": {"hi": "गृह प्रवेश", "en": "House-warming",
                      "good_nak": ["Rohini", "Mrigashira", "Pushya", "Uttara Phalguni", "Chitra", "Anuradha", "Uttara Ashadha", "Shravana",
                                   "Uttara Bhadrapada", "Revati"],
                      "bad_nak": ["Bharani", "Krittika", "Ardra", "Ashlesha", "Magha", "Jyeshtha", "Mula", "Purva Bhadrapada"], "bad_vara": [0, 2, 6]},
    "vehicle": {"hi": "वाहन ख़रीद", "en": "Buying a vehicle",
                "good_nak": ["Ashwini", "Rohini", "Mrigashira", "Punarvasu", "Pushya", "Hasta", "Chitra", "Swati", "Anuradha", "Shravana",
                             "Dhanishta", "Shatabhisha", "Revati"],
                "bad_nak": ["Bharani", "Krittika", "Ardra", "Ashlesha", "Magha", "Jyeshtha", "Mula"], "bad_vara": [2, 6]},
    "education": {"hi": "विद्यारंभ / पढ़ाई", "en": "Starting studies",
                  "good_nak": ["Ashwini", "Rohini", "Mrigashira", "Punarvasu", "Pushya", "Hasta", "Chitra", "Swati", "Anuradha", "Shravana",
                               "Revati", "Uttara Phalguni"],
                  "bad_nak": ["Bharani", "Krittika", "Ardra", "Ashlesha", "Magha", "Jyeshtha", "Mula"], "bad_vara": [0, 2, 6]},
    "marriage": {"hi": "विवाह", "en": "Marriage",
                 "good_nak": ["Rohini", "Mrigashira", "Magha", "Uttara Phalguni", "Hasta", "Swati", "Anuradha", "Mula", "Uttara Ashadha", "Uttara Bhadrapada", "Revati"],
                 "bad_nak": ["Bharani", "Krittika", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Purva Phalguni", "Chitra", "Vishakha", "Jyeshtha", "Purva Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Ashwini"],
                 "good_tithi": [2, 3, 5, 7, 10, 11, 12, 13], "bad_vara": [2], "samskara": True, "no_kharmas": True, "no_chaturmas": True, "no_holashtak": True, "no_asta": True},
    "mundan": {"hi": "मुंडन", "en": "Mundan (first haircut)",
               "good_nak": ["Ashwini", "Mrigashira", "Punarvasu", "Pushya", "Hasta", "Chitra", "Swati", "Jyeshtha", "Shravana", "Dhanishta", "Shatabhisha", "Revati"],
               "bad_nak": ["Bharani", "Krittika", "Ardra", "Ashlesha", "Magha", "Vishakha", "Mula", "Purva Bhadrapada"], "good_tithi": [2, 3, 5, 7, 10, 11, 13], "bad_vara": [0, 2, 6],
               "samskara": True, "no_chaturmas": True, "no_asta": True, "months": [11, 0, 1, 2]},
    "namakaran": {"hi": "नामकरण", "en": "Naming ceremony",
                  "good_nak": ["Ashwini", "Rohini", "Mrigashira", "Punarvasu", "Pushya", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Anuradha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Uttara Bhadrapada", "Revati"],
                  "bad_nak": ["Bharani", "Krittika", "Ardra", "Ashlesha", "Magha", "Vishakha", "Jyeshtha", "Mula", "Purva Bhadrapada"], "good_tithi": [1, 2, 3, 5, 6, 7, 10, 11, 12, 13, 15], "bad_vara": [2, 6], "samskara": True},
    "annaprashan": {"hi": "अन्नप्राशन", "en": "First feeding (annaprashan)",
                    "good_nak": ["Ashwini", "Rohini", "Mrigashira", "Punarvasu", "Pushya", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Anuradha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Uttara Bhadrapada", "Revati"],
                    "bad_nak": ["Bharani", "Krittika", "Ardra", "Ashlesha", "Magha", "Vishakha", "Jyeshtha", "Mula", "Purva Bhadrapada"], "good_tithi": [2, 3, 5, 7, 10, 11, 12, 13, 15], "bad_vara": [2, 6], "samskara": True},
    "upanayana": {"hi": "उपनयन (जनेऊ)", "en": "Upanayana (sacred thread)",
                  "good_nak": ["Ashwini", "Rohini", "Mrigashira", "Punarvasu", "Pushya", "Hasta", "Chitra", "Swati", "Anuradha", "Shravana", "Dhanishta", "Shatabhisha", "Revati"],
                  "bad_nak": ["Bharani", "Krittika", "Ardra", "Ashlesha", "Magha", "Vishakha", "Jyeshtha", "Mula", "Purva Bhadrapada"], "good_tithi": [2, 3, 5, 10, 11, 12], "bad_vara": [2, 6],
                  "samskara": True, "no_asta": True, "no_chaturmas": True, "shukla_only": True, "months": [9, 10, 11, 0, 1, 2]},
    "bhoomi_pujan": {"hi": "भूमि पूजन / नींव", "en": "Ground-breaking (bhoomi pujan)",
                     "good_nak": ["Rohini", "Mrigashira", "Pushya", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Anuradha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Uttara Bhadrapada", "Revati"],
                     "bad_nak": ["Bharani", "Krittika", "Ardra", "Ashlesha", "Magha", "Jyeshtha", "Mula", "Purva Bhadrapada"], "good_tithi": [2, 3, 5, 6, 7, 10, 11, 12, 13, 15], "bad_vara": [0, 2], "no_chaturmas": True, "no_asta": True},
    "property": {"hi": "संपत्ति ख़रीद / रजिस्ट्री", "en": "Property purchase / registry",
                 "good_nak": ["Ashwini", "Rohini", "Mrigashira", "Punarvasu", "Pushya", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Anuradha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Uttara Bhadrapada", "Revati"],
                 "bad_nak": ["Bharani", "Krittika", "Ardra", "Ashlesha", "Magha", "Vishakha", "Jyeshtha", "Mula", "Purva Bhadrapada"], "bad_vara": [2]},
    "general": {"hi": "सामान्य शुभ कार्य", "en": "General auspicious work",
                "good_nak": ["Ashwini", "Rohini", "Mrigashira", "Punarvasu", "Pushya", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Anuradha",
                             "Uttara Ashadha", "Shravana", "Dhanishta", "Uttara Bhadrapada", "Revati"],
                "bad_nak": ["Bharani", "Krittika", "Ardra", "Ashlesha", "Magha", "Vishakha", "Jyeshtha", "Mula", "Purva Bhadrapada"], "bad_vara": []},
}
VARA_HI = ["रविवार", "सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार"]


def _sid(dt_utc: datetime) -> tuple[float, float]:
    jd_ut = julian_day(dt_utc)
    jd_tt = jd_ut + delta_t(year_fraction(dt_utc)) / 86400.0
    pos = _BACKEND.positions(jd_tt)
    ayan = ayanamsa(jd_tt)
    return norm360(pos["Sun"] - ayan), norm360(pos["Moon"] - ayan)


def _asta(sun: float, planet_lon: float, orb: float) -> bool:
    return abs((planet_lon - sun + 180.0) % 360.0 - 180.0) <= orb


def month_flags(dt_utc: datetime, sun: float, moon: float, amanta_masa: int | None, adhika: bool, tithi_number: int) -> list[dict]:
    """Period-level cautions used by the samskara activities: Kharmas (Sun in Dhanu/Meena), Chaturmas (Ashadha Shukla 11 →
    Kartika Shukla 11, amanta), adhika masa, Holashtak (Phalguna Shukla 8 → Purnima), Pitru paksha (Bhadrapada Krishna, amanta),
    Guru/Shukra asta (combust within 11°/10° of the Sun)."""
    flags = []
    ss = int(sun // 30)
    if ss in (8, 11):
        flags.append({"key": "kharmas", "hi": "खरमास (सूर्य धनु/मीन में)", "en": "Kharmas (Sun in Dhanu/Meena)"})
    if adhika:
        flags.append({"key": "adhika", "hi": "अधिक मास", "en": "Adhika masa"})
    if amanta_masa is not None:
        # chaturmas: from Ashadha (2) Shukla 11 to Kartika (6) Shukla 11
        if (amanta_masa == 2 and tithi_number >= 11) or amanta_masa in (3, 4, 5) or (amanta_masa == 6 and tithi_number < 11):
            flags.append({"key": "chaturmas", "hi": "चातुर्मास", "en": "Chaturmas"})
        if amanta_masa == 10 and 8 <= tithi_number <= 15:
            flags.append({"key": "holashtak", "hi": "होलाष्टक", "en": "Holashtak"})
        if amanta_masa == 4 and tithi_number > 15:
            flags.append({"key": "pitru_paksha", "hi": "पितृ पक्ष", "en": "Pitru paksha"})
    jd_ut = julian_day(dt_utc)
    jd_tt = jd_ut + delta_t(year_fraction(dt_utc)) / 86400.0
    pos = _BACKEND.positions(jd_tt); ayan = ayanamsa(jd_tt)
    if _asta(sun, norm360(pos["Jupiter"] - ayan), 11.0):
        flags.append({"key": "guru_asta", "hi": "गुरु अस्त", "en": "Jupiter combust"})
    if _asta(sun, norm360(pos["Venus"] - ayan), 10.0):
        flags.append({"key": "shukra_asta", "hi": "शुक्र अस्त", "en": "Venus combust"})
    return flags


def find(activity: str, lat: float, lon: float, tz: str, start_date: str | None = None, days: int = 30,
         birth_moon_lon: float | None = None) -> dict:
    if activity not in ACTIVITIES:
        raise ValueError(f"unknown activity '{activity}' (choose {', '.join(ACTIVITIES)})")
    act = ACTIVITIES[activity]
    zone = ZoneInfo(tz)
    first = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else datetime.now(zone).date()
    days = max(1, min(60, int(days)))
    out = []
    for i in range(days):
        d = first + timedelta(days=i)
        st = sun_times(d, lat, lon, tz)
        if not st:
            continue
        sunrise = st["sunrise"]
        sun, moon = _sid(sunrise.astimezone(ZoneInfo("UTC")))
        pc = panchang(sun, moon, sunrise)
        vara = sunrise.weekday() + 1 if sunrise.weekday() < 6 else 0           # Python Mon=0 -> Sunday=0
        nak = pc["nakshatra"]["name"]
        score, why, why_hi = 50, [], []
        t = pc["tithi"]
        if t["number"] in RIKTA or t["number"] - 15 in RIKTA:
            score -= 25; why.append(f"rikta tithi ({t['name']})"); why_hi.append(f"रिक्ता तिथि ({t['name_hi']})")
        if t["number"] == 30:
            score -= 30; why.append("amavasya"); why_hi.append("अमावस्या")
        if pc["yoga"]["name"] in BAD_YOGAS:
            score -= 20; why.append(f"inauspicious yoga ({pc['yoga']['name']})"); why_hi.append(f"अशुभ योग ({pc['yoga']['name_hi']})")
        if pc["karana"]["name"] == "Vishti":
            score -= 15; why.append("Vishti (Bhadra) karana at sunrise"); why_hi.append("सूर्योदय पर विष्टि (भद्रा) करण")
        if nak in act["good_nak"]:
            score += 25; why.append(f"favourable nakshatra ({nak})"); why_hi.append(f"अनुकूल नक्षत्र ({pc['nakshatra']['name_hi']})")
        elif nak in act["bad_nak"]:
            score -= 25; why.append(f"nakshatra avoided for this ({nak})"); why_hi.append(f"इस कार्य के लिए वर्जित नक्षत्र ({pc['nakshatra']['name_hi']})")
        if vara in act["bad_vara"]:
            score -= 15; why.append("weekday avoided for this"); why_hi.append("इस कार्य के लिए वर्जित वार")
        if act.get("good_tithi") and t["number"] not in act["good_tithi"] and (t["number"] - 15) not in act["good_tithi"] and t["number"] not in RIKTA and t["number"] - 15 not in RIKTA and t["number"] != 30:
            score -= 10; why.append("tithi not in the preferred list"); why_hi.append("तिथि इस कार्य की सूची में नहीं")
        if act.get("shukla_only") and t["number"] > 15:
            score -= 15; why.append("Krishna paksha (Shukla preferred)"); why_hi.append("कृष्ण पक्ष (शुक्ल पक्ष वांछित)")
        # period-level cautions (samskaras and new beginnings)
        from .patri import lunar_month
        _u = sunrise.astimezone(ZoneInfo("UTC")); _jd = julian_day(_u) + delta_t(year_fraction(_u)) / 86400.0
        lm = lunar_month(_BACKEND, _jd, ayanamsa(_jd))
        masa_i, adhika = lm["index"], bool(lm["adhika"])
        for fl in month_flags(sunrise.astimezone(ZoneInfo("UTC")), sun, moon, masa_i, adhika, t["number"]):
            k = fl["key"]
            blocks = ((k == "kharmas" and act.get("no_kharmas")) or (k == "chaturmas" and act.get("no_chaturmas")) or (k == "holashtak" and act.get("no_holashtak"))
                      or (k in ("guru_asta", "shukra_asta") and act.get("no_asta")) or (k == "adhika" and act.get("samskara")) or (k == "pitru_paksha" and act.get("samskara")))
            if blocks:
                score -= 40; why.append(fl["en"]); why_hi.append(fl["hi"])
        if act.get("months") and masa_i is not None and masa_i not in act["months"]:
            score -= 10; why.append("month not among the preferred months"); why_hi.append("मास इस संस्कार के वांछित मासों में नहीं")
        if birth_moon_lon is not None:
            # tarabala: count from the birth star to the day's star; 3, 5, 7 (vipat, pratyak, naidhana) are avoided
            bn = nakshatra_of(birth_moon_lon)["index"]
            count = (N[nak] - bn) % 27 + 1
            tara = count % 9
            if tara in (3, 5, 7):
                score -= 20; why.append(f"tarabala unfavourable ({count})"); why_hi.append(f"ताराबल प्रतिकूल ({count}वाँ तारा)")
            else:
                score += 10; why.append("tarabala favourable"); why_hi.append("ताराबल अनुकूल")
            # chandrabala: Moon's sign from the birth Moon sign; 6, 8, 12 avoided
            cb = (int(moon // 30) - int(birth_moon_lon // 30)) % 12 + 1
            if cb in (6, 8, 12):
                score -= 15; why.append(f"chandrabala unfavourable ({cb})"); why_hi.append(f"चंद्रबल प्रतिकूल ({cb}वाँ)")
            else:
                score += 5; why.append("chandrabala favourable"); why_hi.append("चंद्रबल अनुकूल")
        dt = day_table(sunrise + timedelta(hours=6), lat, lon, tz)
        good = [c for c in dt.get("choghadiya_day", []) if c["nature"] == "good"]
        out.append({"date": d.isoformat(), "vara": vara, "vara_hi": VARA_HI[vara], "score": max(0, min(100, score)),
                    "tithi": t["name"], "tithi_hi": f'{t["paksha_hi"]} {t["name_hi"]}', "nakshatra": nak, "nakshatra_hi": pc["nakshatra"]["name_hi"],
                    "yoga": pc["yoga"]["name"], "yoga_hi": pc["yoga"]["name_hi"], "karana": pc["karana"]["name"],
                    "sunrise": sunrise.strftime("%H:%M"), "reasons": why, "reasons_hi": why_hi,
                    "good_windows": [{"name": c["name"], "start": c["start"], "end": c["end"]} for c in good],
                    "abhijit": dt.get("abhijit"), "rahu_kaal": dt.get("rahu_kaal")})
    ranked = sorted(out, key=lambda x: (-x["score"], x["date"]))
    return {"activity": activity, "activity_hi": act["hi"], "activity_en": act["en"], "from": first.isoformat(), "days": days,
            "best": ranked[:5], "all": out, "review_status": "draft",
            "note_hi": "पंचांग-स्तर का मुहूर्त (सूर्योदय की तिथि-नक्षत्र-योग-करण, वार, चौघड़िया; संस्कारों के लिए खरमास, चातुर्मास, होलाष्टक, अधिक मास, पितृ पक्ष और गुरु-शुक्र अस्त की जाँच)। जन्म-कुंडली दी हो तो ताराबल और चंद्रबल भी। "
                       "यह मार्गदर्शन है; विवाह, उपनयन जैसे बड़े संस्कारों के लिए लग्न-शुद्धि सहित पंडित से मुहूर्त निकलवाएँ।",
            "note_en": "Almanac-level muhurta (tithi, nakshatra, yoga, karana at sunrise; weekday; choghadiya; for samskaras also Kharmas, Chaturmas, Holashtak, adhika masa, Pitru paksha and Jupiter/Venus combustion). With a birth chart, tarabala and chandrabala are added. "
                       "Guidance only; for major samskaras such as marriage, have a pandit fix the muhurta including the lagna."}
