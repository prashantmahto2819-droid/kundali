"""Birth chart assembly (sidereal, whole-sign houses by default)."""
from __future__ import annotations

from datetime import datetime, timezone

from . import ENGINE_VERSION
from .constants import (ASPECTS, PLANETS, PLANETS_HI, PLANETS_SHORT_HI, SIGN_LORDS,
                        SIGNS, SIGNS_HI)
from .ashtakavarga import ashtakavarga
from .core import (ascendant_tropical, ayanamsa, dignity, navamsa_sign, nakshatra_of,
                   obliquity_deg, sign_of)
from .dasha import current_periods, vimshottari
from .ephemeris import get_backend, mean_node, norm360
from .panchang import panchang
from .muhurta import day_table
from .rules import match_rules
from .timeutil import delta_t, julian_day, local_to_utc, year_fraction
from .vargas import all_vargas
from zoneinfo import ZoneInfo
from .yogas import detect_yogas


def dms(deg: float) -> str:
    d = int(deg)
    m_full = (deg - d) * 60
    m = int(m_full)
    s = round((m_full - m) * 60)
    if s == 60:
        s, m = 0, m + 1
    if m == 60:
        m, d = 0, d + 1
    return f"{d}°{m:02d}′{s:02d}″"


def _house_of(sign: int, lagna_sign: int) -> int:
    return (sign - lagna_sign) % 12 + 1


def _retro(backend, jd_tt: float, name: str) -> bool:
    if name in ("Rahu", "Ketu"):
        return True  # mean nodes always move backward
    if name in ("Sun", "Moon"):
        return False
    a = backend.positions(jd_tt - 0.5)[name]
    b = backend.positions(jd_tt + 0.5)[name]
    return ((b - a + 180) % 360 - 180) < 0


def compute_chart(date: str, time: str, tz: str, lat: float, lon: float,
                  name: str | None = None, ayanamsa_system: str = "lahiri",
                  year_days: float = 365.25, as_of: datetime | None = None,
                  backend=None, dasha_level: int = 2) -> dict:
    backend = backend or get_backend()
    birth_utc = local_to_utc(date, time, tz)
    jd_ut = julian_day(birth_utc)
    jd_tt = jd_ut + delta_t(year_fraction(birth_utc)) / 86400.0

    trop = backend.positions(jd_tt)
    trop["Rahu"] = mean_node(jd_tt)
    trop["Ketu"] = norm360(trop["Rahu"] + 180.0)
    ayan = ayanamsa(jd_tt, ayanamsa_system)
    sid = {p: norm360(trop[p] - ayan) for p in PLANETS}

    asc_trop = ascendant_tropical(jd_ut, jd_tt, lat, lon)
    asc = norm360(asc_trop - ayan)
    lagna_sign = sign_of(asc)
    lagna_nak = nakshatra_of(asc)

    planets = []
    for p in PLANETS:
        lon_p = sid[p]
        s = sign_of(lon_p)
        house = _house_of(s, lagna_sign)
        nak = nakshatra_of(lon_p)
        planets.append({
            "name": p, "name_hi": PLANETS_HI[p], "short_hi": PLANETS_SHORT_HI[p],
            "longitude": lon_p, "sign": s, "sign_name": SIGNS[s], "sign_name_hi": SIGNS_HI[s],
            "degree_in_sign": lon_p - s * 30, "dms": dms(lon_p - s * 30),
            "house": house,
            "nakshatra": nak["name"], "nakshatra_hi": nak["name_hi"], "pada": nak["pada"],
            "nakshatra_lord": nak["lord"],
            "retrograde": _retro(backend, jd_tt, p),
            "dignity": dignity(p, s),
            "navamsa_sign": navamsa_sign(lon_p),
            "aspects_houses": [((house - 1) + (a - 1)) % 12 + 1 for a in ASPECTS[p]],
        })

    by_name = {p["name"]: p for p in planets}
    houses = []
    for h in range(1, 13):
        s = (lagna_sign + h - 1) % 12
        houses.append({"house": h, "sign": s, "sign_name": SIGNS[s], "sign_name_hi": SIGNS_HI[s],
                       "lord": SIGN_LORDS[s],
                       "lord_house": by_name[SIGN_LORDS[s]]["house"],
                       "planets": [p["name"] for p in planets if p["house"] == h]})

    nav_lagna = navamsa_sign(asc)
    navamsa = {"lagna_sign": nav_lagna,
               "houses": [{"house": h, "sign": (nav_lagna + h - 1) % 12,
                           "planets": [p["name"] for p in planets
                                       if _house_of(p["navamsa_sign"], nav_lagna) == h]}
                          for h in range(1, 13)]}

    dasha = vimshottari(sid["Moon"], birth_utc, year_days=year_days, max_level=dasha_level)
    now = as_of or datetime.now(timezone.utc)
    running = current_periods(dasha, now)

    local_date = datetime.strptime(date, "%Y-%m-%d")
    chart = {
        "engine_version": ENGINE_VERSION,
        "backend": backend.name, "backend_note": backend.accuracy_note,
        "input": {"name": name, "date": date, "time": time, "tz": tz, "lat": lat, "lon": lon,
                  "ayanamsa": ayanamsa_system, "house_system": "whole-sign"},
        "birth_utc": birth_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "jd_ut": jd_ut, "ayanamsa_value": ayan, "ayanamsa_dms": dms(ayan),
        "obliquity": obliquity_deg(jd_tt),
        "lagna": {"longitude": asc, "sign": lagna_sign, "sign_name": SIGNS[lagna_sign],
                  "sign_name_hi": SIGNS_HI[lagna_sign], "degree_in_sign": asc - lagna_sign * 30,
                  "dms": dms(asc - lagna_sign * 30), "nakshatra": lagna_nak["name"],
                  "nakshatra_hi": lagna_nak["name_hi"], "pada": lagna_nak["pada"],
                  "lord": SIGN_LORDS[lagna_sign]},
        "planets": planets, "houses": houses, "navamsa": navamsa,
        "panchang": panchang(sid["Sun"], sid["Moon"], local_date),
        "dasha": dasha, "dasha_running": running, "as_of": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    chart["vargas"] = all_vargas(asc, planets)
    local_dt = birth_utc.astimezone(ZoneInfo(tz))
    chart["day"] = day_table(local_dt, lat, lon, tz)
    if chart["day"].get("available"):  # the Vedic day starts at sunrise
        chart["panchang"]["vara"] = chart["day"]["vedic_vara"]
        chart["panchang"]["note"] = "Vara follows the sunrise-based Vedic day."
    chart["ashtakavarga"] = ashtakavarga({**{p["name"]: p["sign"] for p in planets}, "Lagna": lagna_sign}, lagna_sign)
    chart["yogas"] = detect_yogas(chart)
    chart["readings"] = match_rules(chart)
    return chart
