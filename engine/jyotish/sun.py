"""Sunrise / sunset (NOAA general solar position equations, about +-1 minute)."""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ZENITH = 90.833  # standard refraction + solar semi-diameter (upper limb, what almanacs/NOAA print)
ZENITH_CENTRE = 90.0  # centre of the disc, no refraction: the convention of most Indian panchang software


def _solar_terms(gamma: float) -> tuple[float, float]:
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
                       - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))
    decl = (0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
            - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
            - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma))
    return eqtime, decl


def _event_minutes(day_of_year: int, lat: float, lon: float, sunrise: bool, hour_guess: float, zenith: float = ZENITH):
    """Minutes after 00:00 UTC (may be outside 0..1440) or None in polar day/night."""
    gamma = 2 * math.pi / 365 * (day_of_year - 1 + (hour_guess - 12) / 24)
    eqtime, decl = _solar_terms(gamma)
    la = math.radians(lat)
    cos_ha = (math.cos(math.radians(zenith)) / (math.cos(la) * math.cos(decl))
              - math.tan(la) * math.tan(decl))
    if cos_ha > 1 or cos_ha < -1:
        return None
    ha = math.degrees(math.acos(cos_ha))
    return 720 - 4 * (lon + ha if sunrise else lon - ha) - eqtime


def sun_times(day: date, lat: float, lon: float, tz: str, convention: str = "upper_limb") -> dict | None:
    """Sunrise and sunset (aware datetimes in ``tz``) for the *local* calendar date.

    convention: "upper_limb" (refraction + semi-diameter, the usual printed time) or "centre"
    (disc centre, no refraction, as most Indian panchang programs compute; about 3-4 minutes later/earlier).
    Returns None where the sun does not rise or set (polar regions).
    """
    zenith = ZENITH_CENTRE if convention == "centre" else ZENITH
    zone = ZoneInfo(tz)
    best: dict[str, datetime] = {}
    for delta in (-1, 0, 1):
        base = datetime(day.year, day.month, day.day, tzinfo=timezone.utc) + timedelta(days=delta)
        doy = base.timetuple().tm_yday
        for name, rising, guess in (("sunrise", True, 6.0), ("sunset", False, 18.0)):
            m = _event_minutes(doy, lat, lon, rising, guess, zenith)
            if m is None:
                continue
            # refine once at the event time
            m = _event_minutes(doy, lat, lon, rising, m / 60.0, zenith) or m
            when = (base + timedelta(minutes=m)).astimezone(zone)
            if when.date() == day:
                best[name] = when
    if "sunrise" in best and "sunset" in best and best["sunset"] > best["sunrise"]:
        return best
    return None
