"""Monthly panchang calendar: one row per civil day with the sunrise panchang and end times.

For every day of the month at the place: sunrise/sunset (upper limb), moonrise/moonset, vara, tithi at sunrise
with its end time (next multiple of 12 deg of elongation), nakshatra at sunrise with its end time, yoga and
karana at sunrise, amanta and purnimanta month, paksha, Vikram samvat (changes on Chaitra Shukla 1), the Sun's
sidereal sign (sankranti day flagged), Rahu kaal, Abhijit, and the festivals / vrats of the day from the
festival calendar. Analytic backend (Sun/Moon within ~0.01 deg): end times within a few minutes.
"""
from __future__ import annotations

import calendar as _cal
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from .constants import NAKSHATRAS, PLANETS_HI, SIGNS, SIGNS_HI
from .core import ayanamsa, nakshatra_of, sign_of
from .ephemeris import AnalyticBackend, norm360
from .festivals import calendar as festival_calendar, lunations
from .moon import moon_times
from .muhurta import day_table
from .panchang import panchang
from .patri import MASA, MASA_HI
from .sun import sun_times
from .timeutil import delta_t, julian_day, year_fraction

_B = AnalyticBackend()
# Sarvartha-siddhi yoga: nakshatra at sunrise on the weekday (almanac table); Amrita-siddhi: one star per weekday
SARVARTHA = {0: {"Hasta", "Mula", "Uttara Ashadha", "Uttara Phalguni", "Uttara Bhadrapada", "Pushya", "Ashwini"},
             1: {"Shravana", "Rohini", "Mrigashira", "Pushya", "Anuradha"}, 2: {"Ashwini", "Uttara Bhadrapada", "Krittika", "Ashlesha"},
             3: {"Rohini", "Anuradha", "Hasta", "Krittika", "Mrigashira"}, 4: {"Revati", "Anuradha", "Ashwini", "Punarvasu", "Pushya"},
             5: {"Revati", "Anuradha", "Ashwini", "Punarvasu", "Shravana"}, 6: {"Shravana", "Rohini", "Swati"}}
AMRITA = {0: "Hasta", 1: "Mrigashira", 2: "Ashwini", 3: "Anuradha", 4: "Pushya", 5: "Revati", 6: "Rohini"}
GAND_MOOL = {"Ashwini", "Ashlesha", "Magha", "Jyeshtha", "Mula", "Revati"}
# solar month names by the Sun's sidereal sign (0 = Mesha): Tamil, Bengali, Malayalam; Gujarati/Marathi use the amanta lunar names
TAMIL = ["சித்திரை", "வைகாசி", "ஆனி", "ஆடி", "ஆவணி", "புரட்டாசி", "ஐப்பசி", "கார்த்திகை", "மார்கழி", "தை", "மாசி", "பங்குனி"]
TAMIL_LATIN = ["Chithirai", "Vaikasi", "Aani", "Aadi", "Aavani", "Purattasi", "Aippasi", "Karthigai", "Margazhi", "Thai", "Maasi", "Panguni"]
BENGALI = ["বৈশাখ", "জ্যৈষ্ঠ", "আষাঢ়", "শ্রাবণ", "ভাদ্র", "আশ্বিন", "কার্তিক", "অগ্রহায়ণ", "পৌষ", "মাঘ", "ফাল্গুন", "চৈত্র"]
BENGALI_LATIN = ["Boishakh", "Joishtho", "Asharh", "Srabon", "Bhadro", "Ashwin", "Kartik", "Ogrohayon", "Poush", "Magh", "Falgun", "Choitro"]
MALAYALAM = ["മേടം", "ഇടവം", "മിഥുനം", "കർക്കടകം", "ചിങ്ങം", "കന്നി", "തുലാം", "വൃശ്ചികം", "ധനു", "മകരം", "കുംഭം", "മീനം"]
MALAYALAM_LATIN = ["Medam", "Edavam", "Mithunam", "Karkidakam", "Chingam", "Kanni", "Thulam", "Vrischikam", "Dhanu", "Makaram", "Kumbham", "Meenam"]
DISHA_SHOOL = {0: ("पश्चिम", "West"), 1: ("पूर्व", "East"), 2: ("उत्तर", "North"), 3: ("उत्तर", "North"), 4: ("दक्षिण", "South"), 5: ("पश्चिम", "West"), 6: ("पूर्व", "East")}


def _jd(dt: datetime) -> float:
    u = dt.astimezone(timezone.utc)
    return julian_day(u) + delta_t(year_fraction(u)) / 86400.0


def _sid(jd_tt: float) -> tuple[float, float]:
    pos = _B.positions(jd_tt)
    a = ayanamsa(jd_tt)
    return norm360(pos["Sun"] - a), norm360(pos["Moon"] - a)


def _crossing(start: datetime, value_at, target: float, horizon_hours: float = 60.0) -> datetime | None:
    """First time after `start` when the monotonic-increasing angle value_at(dt) reaches `target` (mod 360)."""
    v0 = value_at(start)
    need = (target - v0) % 360.0
    if need < 1e-9:
        need = 360.0
    lo, hi = start, start
    step = timedelta(hours=2)
    while (hi - start).total_seconds() / 3600 < horizon_hours:
        hi = hi + step
        if (value_at(hi) - v0) % 360.0 >= need - 1e-9 and (value_at(hi) - v0) % 360.0 < 300:
            break
        lo = hi
    else:
        return None
    for _ in range(30):
        mid = lo + (hi - lo) / 2
        if (value_at(mid) - v0) % 360.0 >= need:
            hi = mid
        else:
            lo = mid
    return lo + (hi - lo) / 2


@lru_cache(maxsize=32)
def _festivals_by_day(year: int, lat: float, lon: float, tz: str) -> dict:
    out: dict[str, list] = {}
    for e in festival_calendar(year, lat, lon, tz)["events"]:
        out.setdefault(e["date"], []).append({"key": e["key"], "name_hi": e["name_hi"], "name_en": e["name_en"], "kind": e["kind"]})
    return out


def month(year: int, mon: int, lat: float, lon: float, tz: str, only_day: int | None = None) -> dict:
    """Whole month; with only_day the rows cover that day alone and the month-level extras (muhurta, ingress) are skipped."""
    year = max(1950, min(2099, int(year))); mon = max(1, min(12, int(mon)))
    zone = ZoneInfo(tz)
    luns = lunations(year)
    fest = _festivals_by_day(year, lat, lon, tz)
    # Chaitra Shukla 1 of this Gregorian year (first non-adhika Chaitra lunation that starts in the year)
    chaitra_start = next((m["start"] for m in luns if m["masa"] == 11 and not m["adhika"]
                          and datetime(year, 1, 1, tzinfo=timezone.utc) <= datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(days=m["start"] - 2451544.5)), None)
    def _lun_start(masa_idx):
        return next((m["start"] for m in luns if m["masa"] == masa_idx and not m["adhika"]
                     and datetime(year, 1, 1, tzinfo=timezone.utc) <= datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(days=m["start"] - 2451544.5)), None)
    kartika_start = _lun_start(6)
    days = []
    ndays = _cal.monthrange(year, mon)[1]
    for dnum in ([only_day] if only_day else range(1, ndays + 1)):
        d = date(year, mon, dnum)
        st = sun_times(d, lat, lon, tz)
        if not st:
            continue
        rise, sset = st["sunrise"], st["sunset"]
        jr = _jd(rise)
        sun, moon = _sid(jr)
        pc = panchang(sun, moon, rise)
        elong = lambda dt: norm360(_sid(_jd(dt))[1] - _sid(_jd(dt))[0])
        moon_lon = lambda dt: _sid(_jd(dt))[1]
        t_end = _crossing(rise, elong, (pc["tithi"]["number"]) * 12.0 % 360.0)
        n_idx = nakshatra_of(moon)["index"]
        n_end = _crossing(rise, moon_lon, ((n_idx + 1) * (360.0 / 27.0)) % 360.0)
        lun = next((m for m in luns if m["start"] <= jr < m["end"]), None)
        masa_i = lun["masa"] if lun else None
        adhika = lun["adhika"] if lun else False
        paksha = pc["tithi"]["paksha"]
        purn_i = (masa_i + 1) % 12 if (masa_i is not None and paksha == "Krishna") else masa_i
        vik = year + 57 if (chaitra_start is not None and jr >= chaitra_start) else year + 56
        mt = moon_times(d, lat, lon, tz)
        dt_tab = day_table(rise + timedelta(hours=6), lat, lon, tz)
        sun_sign = sign_of(sun)
        yoga_lon = lambda dt: (lambda sm: norm360(sm[0] + sm[1]))(_sid(_jd(dt)))
        yoga_idx = int(norm360(sun + moon) // (360.0 / 27.0))
        y_end = _crossing(rise, yoga_lon, ((yoga_idx + 1) * (360.0 / 27.0)) % 360.0)
        # karana: half-tithi; the first karana of the day ends at the next multiple of 6 deg of elongation
        k_end = _crossing(rise, elong, (int(norm360(moon - sun) // 6.0) + 1) * 6.0 % 360.0)
        nak_name = pc["nakshatra"]["name"]; wd = pc["vara"]["index"]
        special = []
        if nak_name in SARVARTHA.get(wd, set()):
            special.append({"key": "sarvartha_siddhi", "hi": "सर्वार्थ सिद्धि", "en": "Sarvartha Siddhi"})
        if AMRITA.get(wd) == nak_name:
            special.append({"key": "amrita_siddhi", "hi": "अमृत सिद्धि", "en": "Amrita Siddhi"})
        if nak_name in GAND_MOOL:
            special.append({"key": "gand_mool", "hi": "गंड मूल", "en": "Gand Mool"})
        if moon >= 300.0:
            special.append({"key": "panchak", "hi": "पंचक", "en": "Panchak"})
        if pc["karana"]["name"] == "Vishti":
            special.append({"key": "bhadra", "hi": "भद्रा", "en": "Bhadra"})
        # sankranti: the local date of the Sun's sign ingress (bisected between consecutive sunrises)
        sank = False
        for back in (0, 1):
            a = rise - timedelta(days=back); b = a + timedelta(days=1)
            if sign_of(_sid(_jd(a))[0]) != sign_of(_sid(_jd(b))[0]):
                lo, hi = a, b
                for _ in range(25):
                    mid = lo + (hi - lo) / 2
                    if sign_of(_sid(_jd(mid))[0]) == sign_of(_sid(_jd(a))[0]):
                        lo = mid
                    else:
                        hi = mid
                if hi.astimezone(zone).date() == d:
                    sank = True
        days.append({
            "jd_rise": jr,
            "date": d.isoformat(), "day": dnum, "weekday": (d.weekday() + 1) % 7, "vara_hi": pc["vara"]["name_hi"], "vara": pc["vara"]["name"],
            "sunrise": rise.strftime("%H:%M"), "sunset": sset.strftime("%H:%M"),
            "moonrise": mt["moonrise"].strftime("%H:%M") if mt["moonrise"] else None, "moonset": mt["moonset"].strftime("%H:%M") if mt["moonset"] else None,
            "tithi": pc["tithi"]["name"], "tithi_hi": pc["tithi"]["name_hi"], "tithi_number": pc["tithi"]["number"], "paksha": paksha, "paksha_hi": pc["tithi"]["paksha_hi"],
            "tithi_ends": t_end.astimezone(zone).strftime("%H:%M") if t_end else None, "tithi_ends_next_day": bool(t_end and t_end.astimezone(zone).date() > d),
            "nakshatra": pc["nakshatra"]["name"], "nakshatra_hi": pc["nakshatra"]["name_hi"], "nakshatra_ends": n_end.astimezone(zone).strftime("%H:%M") if n_end else None,
            "nakshatra_ends_next_day": bool(n_end and n_end.astimezone(zone).date() > d),
            "yoga": pc["yoga"]["name"], "yoga_hi": pc["yoga"]["name_hi"], "karana": pc["karana"]["name"], "karana_hi": pc["karana"]["name_hi"],
            "masa_amanta": (("Adhika " if adhika else "") + MASA[masa_i]) if masa_i is not None else None, "masa_amanta_hi": (("अधिक " if adhika else "") + MASA_HI[masa_i]) if masa_i is not None else None,
            "masa_purnimanta": (("Adhika " if adhika else "") + MASA[purn_i]) if purn_i is not None else None, "masa_purnimanta_hi": (("अधिक " if adhika else "") + MASA_HI[purn_i]) if purn_i is not None else None,
            "vikram_samvat": vik, "shaka_samvat": vik - 135, "gujarati_samvat": (year + 57) if (kartika_start is not None and jr >= kartika_start) else year + 56,
            "tamil_month": TAMIL_LATIN[sun_sign], "tamil_month_ta": TAMIL[sun_sign], "bengali_month": BENGALI_LATIN[sun_sign], "bengali_month_bn": BENGALI[sun_sign], "malayalam_month": MALAYALAM_LATIN[sun_sign], "malayalam_month_ml": MALAYALAM[sun_sign],
            "sun_sign": SIGNS[sun_sign], "sun_sign_hi": SIGNS_HI[sun_sign], "sankranti": sank,
            "yoga_ends": y_end.astimezone(zone).strftime("%H:%M") if y_end else None, "yoga_ends_next_day": bool(y_end and y_end.astimezone(zone).date() > d),
            "karana_ends": k_end.astimezone(zone).strftime("%H:%M") if k_end else None,
            "moon_sign": SIGNS[sign_of(moon)], "moon_sign_hi": SIGNS_HI[sign_of(moon)], "disha_shool_hi": DISHA_SHOOL[wd][0], "disha_shool": DISHA_SHOOL[wd][1],
            "special": special,
            "rahu_kaal": dt_tab.get("rahu_kaal"), "yamaganda": dt_tab.get("yamaganda"), "gulika": dt_tab.get("gulika"), "abhijit": dt_tab.get("abhijit"),
            "good_choghadiya": [{"name": c["name"], "name_hi": c["name_hi"], "start": c["start"], "end": c["end"]} for c in dt_tab.get("choghadiya_day", []) if c.get("nature") == "good"],
            "events": fest.get(d.isoformat(), []),
        })
    if only_day:
        for x in days:
            x.pop("jd_rise", None)
        return {"year": year, "month": mon, "tz": tz, "lat": lat, "lon": lon, "days": days}
    # planet ingresses in the month (sign changes between consecutive sunrises, Sun..Saturn + nodes by sign at sunrise)
    ingress = []
    prev = None
    for x in days:
        pos = _B.positions(x["jd_rise"]); ayan = ayanamsa(x["jd_rise"])
        cur = {k: sign_of(norm360(v - ayan)) for k, v in pos.items()}
        if prev:
            for k, sgn in cur.items():
                if k != "Moon" and prev[k] != sgn:
                    ingress.append({"planet": k, "planet_hi": PLANETS_HI.get(k, k), "date": x["date"], "sign": SIGNS[sgn], "sign_hi": SIGNS_HI[sgn], "from_sign_hi": SIGNS_HI[prev[k]]})
        prev = cur
    # auspicious dates for common activities (almanac-level muhurta finder, best 4 per activity within the month)
    muhurta = []
    try:
        from .muhurta_find import ACTIVITIES, find
        for act in ("marriage", "griha_pravesh", "bhoomi_pujan", "property", "vehicle", "business", "mundan", "namakaran", "upanayana", "education", "travel"):
            res = find(act, lat, lon, tz, start_date=f"{year}-{mon:02d}-01", days=ndays)
            good = sorted([r for r in res["all"] if r["score"] >= 65], key=lambda r: r["date"])[:8]
            if good:
                muhurta.append({"activity": act, "activity_hi": ACTIVITIES[act]["hi"], "activity_en": ACTIVITIES[act]["en"], "dates": [{"date": r["date"], "day": int(r["date"][8:]), "score": r["score"], "nakshatra_hi": r["nakshatra_hi"]} for r in good]})
    except Exception:
        muhurta = []
    for x in days:
        x.pop("jd_rise", None)
    return {"year": year, "month": mon, "tz": tz, "lat": lat, "lon": lon, "first_weekday": (date(year, mon, 1).weekday() + 1) % 7, "days": days,
            "ingress": ingress, "muhurta": muhurta,
            "note_hi": "सूर्योदय-कालीन तिथि-नक्षत्र-योग-करण (लाहिड़ी); तिथि/नक्षत्र का समाप्ति-समय स्थानीय घड़ी में, '+' = अगले दिन। अमांत और पूर्णिमांत दोनों मास दिए हैं। समय ±कुछ मिनट।",
            "note_en": "Tithi, nakshatra, yoga and karana at sunrise (Lahiri); end times in local clock time, '+' = next day. Both amanta and purnimanta months are given. Times within a few minutes."}
