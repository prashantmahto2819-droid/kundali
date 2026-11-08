"""Ayanamsa, ascendant, nakshatra, navamsa, dignity helpers."""
from __future__ import annotations

import math

from .constants import (DEBILITATION, EXALTATION, NAKSHATRAS, NAKSHATRAS_HI,
                        OWN_SIGNS, DASHA_ORDER)
from .ephemeris import _precession_deg, norm360, DEG

NAK_SPAN = 360.0 / 27.0     # 13 deg 20'
PADA_SPAN = NAK_SPAN / 4.0  # 3 deg 20'

# Lahiri (Chitrapaksha) ayanamsa at J2000.0, degrees. DEV VALUE: verify against a
# reference (e.g. published Lahiri tables / another trusted package) in Phase 0.
LAHIRI_J2000 = 23.853055


def ayanamsa(jd_tt: float, system: str = "lahiri") -> float:
    if system != "lahiri":
        raise ValueError(f"Unsupported ayanamsa '{system}' (only 'lahiri' for now)")
    t = (jd_tt - 2451545.0) / 36525.0
    return LAHIRI_J2000 + _precession_deg(t)


def gmst_deg(jd_ut: float) -> float:
    t = (jd_ut - 2451545.0) / 36525.0
    g = (280.46061837 + 360.98564736629 * (jd_ut - 2451545.0)
         + 0.000387933 * t * t - t ** 3 / 38710000.0)
    return norm360(g)


def obliquity_deg(jd_tt: float) -> float:
    t = (jd_tt - 2451545.0) / 36525.0
    return 23.439291 - 0.0130042 * t - 1.64e-7 * t * t + 5.04e-7 * t ** 3


def ascendant_tropical(jd_ut: float, jd_tt: float, lat: float, lon_east: float) -> float:
    """Tropical ascendant longitude (degrees)."""
    ramc = (gmst_deg(jd_ut) + lon_east) * DEG
    eps = obliquity_deg(jd_tt) * DEG
    phi = lat * DEG
    y = math.cos(ramc)
    x = -(math.sin(ramc) * math.cos(eps) + math.tan(phi) * math.sin(eps))
    return norm360(math.degrees(math.atan2(y, x)))


def midheaven_tropical(jd_ut: float, jd_tt: float, lon_east: float) -> float:
    """Tropical MC longitude (degrees): the ecliptic point on the meridian."""
    ramc = (gmst_deg(jd_ut) + lon_east) * DEG
    eps = obliquity_deg(jd_tt) * DEG
    return norm360(math.degrees(math.atan2(math.sin(ramc), math.cos(ramc) * math.cos(eps))))


def sripati_cusps(asc: float, mc: float) -> list[float]:
    """Bhava-chalit (Sripati / Porphyry) cusps, 12 values, cusp 1 = Lagna degree, cusp 10 = MC degree.

    Each quadrant between the angles is trisected; the cusp is the *middle* (bhava madhya) of the house,
    so a planet belongs to the house whose span (midpoint to midpoint, i.e. sandhi to sandhi) contains it."""
    arc = lambda a, b: (b - a) % 360.0
    ic, dsc = norm360(mc + 180.0), norm360(asc + 180.0)
    q1 = arc(asc, ic) / 3.0            # houses 1-3: Lagna -> IC
    q2 = arc(ic, dsc) / 3.0            # houses 4-6: IC -> Descendant
    c = [asc, asc + q1, asc + 2 * q1, ic, ic + q2, ic + 2 * q2]
    c += [x + 180.0 for x in c]        # 7-12 opposite
    return [norm360(x) for x in c]


def chalit_house(lon: float, cusps: list[float]) -> int:
    """House number 1-12 whose span (from the sandhi before its madhya to the sandhi after) contains lon."""
    arc = lambda a, b: (b - a) % 360.0
    for i in range(12):
        start = norm360(cusps[i] - arc(cusps[i - 1], cusps[i]) / 2.0)   # sandhi before house i+1
        end = norm360(cusps[i] + arc(cusps[i], cusps[(i + 1) % 12]) / 2.0)
        if arc(start, lon) < arc(start, end):
            return i + 1
    return 1


def sign_of(lon: float) -> int:
    return int(lon // 30) % 12


def nakshatra_of(lon: float) -> dict:
    # integer-friendly arithmetic so exact boundaries (13d20', 30d ...) don't suffer
    # from float division error
    idx = int(lon * 27 // 360) % 27
    within = lon - idx * NAK_SPAN
    pada = int(lon * 108 // 360) % 4 + 1
    return {"index": idx, "name": NAKSHATRAS[idx], "name_hi": NAKSHATRAS_HI[idx],
            "pada": pada, "lord": DASHA_ORDER[idx % 9], "fraction": within / NAK_SPAN}


def navamsa_sign(lon: float) -> int:
    """D9 sign index: continuous 3deg20' segments starting from Mesha."""
    return int(lon * 9 // 30) % 12


def dignity(planet: str, sign: int) -> str | None:
    if planet in EXALTATION and EXALTATION[planet] == sign:
        return "exalted"
    if planet in DEBILITATION and DEBILITATION[planet] == sign:
        return "debilitated"
    if sign in OWN_SIGNS.get(planet, []):
        return "own"
    return None
