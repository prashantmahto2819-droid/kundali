"""Moonrise and moonset (topocentric upper limb with refraction, Meeus-style) from the analytic Moon.

Latitude of the Moon from the main Meeus ch.47 terms (good to ~0.05 deg); horizontal parallax from the
distance terms is replaced by the mean value scaled by the main elliptic term (error < 1 min of time).
The standard altitude for moonrise/set is h0 = 0.7275*pi - 34' (Meeus 15.1). Times are found by scanning
the local day in 10-minute steps for altitude sign changes and bisecting; accuracy about +-1 minute
against almanacs. Returns None for a rise or set that does not happen on that local date.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .core import gmst_deg, obliquity_deg
from .ephemeris import moon_longitude, norm360
from .timeutil import delta_t, julian_day, year_fraction

DEG = math.pi / 180.0
# (D, M, M', F, coefficient in 1e-6 deg) — Meeus table 47.B, leading terms
_LAT = [(0, 0, 0, 1, 5128122), (0, 0, 1, 1, 280602), (0, 0, 1, -1, 277693), (2, 0, 0, -1, 173237), (2, 0, -1, 1, 55413), (2, 0, -1, -1, 46271),
        (2, 0, 0, 1, 32573), (0, 0, 2, 1, 17198), (2, 0, 1, -1, 9266), (0, 0, 2, -1, 8822), (2, -1, 0, -1, 8216), (2, 0, -2, -1, 4324),
        (2, 0, 1, 1, 4200), (2, 1, 0, -1, -3359), (2, -1, -1, 1, 2463), (2, -1, 0, 1, 2211), (2, -1, -1, -1, 2065), (0, 1, -1, -1, -1870),
        (4, 0, -1, -1, 1828), (0, 1, 0, 1, -1794), (0, 0, 0, 3, -1749), (0, 1, -1, 1, -1565), (1, 0, 0, 1, -1491), (0, 1, 1, 1, -1475),
        (0, 1, 1, -1, -1410), (0, 1, 0, -1, -1344), (1, 0, 0, -1, -1335), (0, 0, 3, 1, 1107), (4, 0, 0, -1, 1021), (4, 0, -1, 1, 833)]


def moon_latitude(jd_tt: float) -> float:
    t = (jd_tt - 2451545.0) / 36525.0
    lp = 218.3164477 + 481267.88123421 * t - 0.0015786 * t**2 + t**3 / 538841
    d = 297.8501921 + 445267.1114034 * t - 0.0018819 * t**2 + t**3 / 545868
    m = 357.5291092 + 35999.0502909 * t - 0.0001536 * t**2
    mp = 134.9633964 + 477198.8675055 * t + 0.0087414 * t**2 + t**3 / 69699
    f = 93.2720950 + 483202.0175233 * t - 0.0036539 * t**2 - t**3 / 3526000
    a1 = 119.75 + 131.849 * t
    a3 = 313.45 + 481266.484 * t
    e = 1 - 0.002516 * t - 0.0000074 * t * t
    total = 0.0
    for cd, cm, cmp_, cf, coef in _LAT:
        total += coef * (e ** abs(cm)) * math.sin((cd * d + cm * m + cmp_ * mp + cf * f) * DEG)
    total += -2235 * math.sin(lp * DEG) + 382 * math.sin(a3 * DEG) + 175 * math.sin((a1 - f) * DEG) + 175 * math.sin((a1 + f) * DEG) \
        + 127 * math.sin((lp - mp) * DEG) - 115 * math.sin((lp + mp) * DEG)
    return total / 1e6


def moon_parallax_deg(jd_tt: float) -> float:
    """Equatorial horizontal parallax, mean 0.9507 deg modulated by the main elliptic term."""
    t = (jd_tt - 2451545.0) / 36525.0
    mp = (134.9633964 + 477198.8675055 * t) * DEG
    d = (297.8501921 + 445267.1114034 * t) * DEG
    dist_km = 385000.56 - 20905.355 * math.cos(mp) - 3699.111 * math.cos(2 * d - mp) - 2955.968 * math.cos(2 * d)
    return math.degrees(math.asin(6378.14 / dist_km))


def moon_altitude(dt_utc: datetime, lat: float, lon_east: float) -> float:
    """Geocentric altitude of the Moon's centre (deg); parallax is handled through h0."""
    jd_ut = julian_day(dt_utc)
    jd_tt = jd_ut + delta_t(year_fraction(dt_utc)) / 86400.0
    lam, beta = moon_longitude(jd_tt) * DEG, moon_latitude(jd_tt) * DEG
    eps = obliquity_deg(jd_tt) * DEG
    ra = math.atan2(math.sin(lam) * math.cos(eps) - math.tan(beta) * math.sin(eps), math.cos(lam))
    dec = math.asin(math.sin(beta) * math.cos(eps) + math.cos(beta) * math.sin(eps) * math.sin(lam))
    lst = (gmst_deg(jd_ut) + lon_east) * DEG
    ha = lst - ra
    phi = lat * DEG
    return math.degrees(math.asin(math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(ha)))


def moon_times(day: date, lat: float, lon_east: float, tz: str) -> dict:
    """Moonrise and moonset (aware datetimes) for the local calendar date; None when absent that day."""
    zone = ZoneInfo(tz)
    start = datetime(day.year, day.month, day.day, tzinfo=zone)
    end = start + timedelta(days=1)
    jd0 = julian_day(start.astimezone(timezone.utc)) + delta_t(year_fraction(start.astimezone(timezone.utc))) / 86400.0
    h0 = 0.7275 * moon_parallax_deg(jd0) - 34.0 / 60.0
    f = lambda dt: moon_altitude(dt.astimezone(timezone.utc), lat, lon_east) - h0
    step = timedelta(minutes=10)
    t, prev = start, f(start)
    rise = sett = None
    while t < end:
        t2 = min(t + step, end)
        cur = f(t2)
        if prev < 0 <= cur or prev >= 0 > cur:
            lo, hi = t, t2
            for _ in range(20):
                mid = lo + (hi - lo) / 2
                if (f(mid) < 0) == (prev < 0):
                    lo = mid
                else:
                    hi = mid
            when = lo + (hi - lo) / 2
            if prev < 0 and rise is None:
                rise = when
            elif prev >= 0 and sett is None:
                sett = when
        t, prev = t2, cur
    return {"moonrise": rise, "moonset": sett}
