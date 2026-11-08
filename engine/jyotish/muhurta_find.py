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
            "note_hi": "पंचांग-स्तर का मुहूर्त (सूर्योदय की तिथि-नक्षत्र-योग-करण, वार, चौघड़िया)। जन्म-कुंडली दी हो तो ताराबल और चंद्रबल भी। "
                       "यह मार्गदर्शन है; विवाह, उपनयन जैसे बड़े संस्कारों के लिए पंडित से मुहूर्त निकलवाएँ।",
            "note_en": "Almanac-level muhurta (tithi, nakshatra, yoga, karana at sunrise; weekday; choghadiya). With a birth chart, tarabala and chandrabala are added. "
                       "Guidance only; for major samskaras such as marriage, have a pandit fix the muhurta."}
