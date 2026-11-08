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

from .constants import SIGNS, SIGNS_HI
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


def month(year: int, mon: int, lat: float, lon: float, tz: str) -> dict:
    year = max(1950, min(2099, int(year))); mon = max(1, min(12, int(mon)))
    zone = ZoneInfo(tz)
    luns = lunations(year)
    fest = _festivals_by_day(year, lat, lon, tz)
    # Chaitra Shukla 1 of this Gregorian year (first non-adhika Chaitra lunation that starts in the year)
    chaitra_start = next((m["start"] for m in luns if m["masa"] == 11 and not m["adhika"]
                          and datetime(year, 1, 1, tzinfo=timezone.utc) <= datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(days=m["start"] - 2451544.5)), None)
    days = []
    ndays = _cal.monthrange(year, mon)[1]
    for dnum in range(1, ndays + 1):
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
            "vikram_samvat": vik, "sun_sign": SIGNS[sun_sign], "sun_sign_hi": SIGNS_HI[sun_sign], "sankranti": sank,
            "rahu_kaal": dt_tab.get("rahu_kaal"), "abhijit": dt_tab.get("abhijit"),
            "events": fest.get(d.isoformat(), []),
        })
    return {"year": year, "month": mon, "tz": tz, "lat": lat, "lon": lon, "first_weekday": (date(year, mon, 1).weekday() + 1) % 7, "days": days,
            "note_hi": "सूर्योदय-कालीन तिथि-नक्षत्र-योग-करण (लाहिड़ी); तिथि/नक्षत्र का समाप्ति-समय स्थानीय घड़ी में, '+' = अगले दिन। अमांत और पूर्णिमांत दोनों मास दिए हैं। समय ±कुछ मिनट।",
            "note_en": "Tithi, nakshatra, yoga and karana at sunrise (Lahiri); end times in local clock time, '+' = next day. Both amanta and purnimanta months are given. Times within a few minutes."}
