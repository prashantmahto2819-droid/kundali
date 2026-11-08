"""KP (Krishnamurti Paddhati) layer: KP ayanamsa, Placidus cusps, star/sub/sub-sub lords, significators.

* Ayanamsa: Krishnamurti (about 5-6 arc-minutes less than Lahiri); KP_J2000 is the J2000 value, precessed
  with the same rate as Lahiri. Accuracy about +-1 arc-minute versus published KP tables (draft).
* Houses: Placidus (iterative semi-arc method), cusps 1 and 10 are the Ascendant and MC.
* Sub-lords: each nakshatra (13d20') is divided in Vimshottari order starting from its own lord, in
  proportion to the dasha years (sub); each sub is divided the same way again (sub-sub).
* Significators (4 levels, the usual KP order): planets in the stars of occupants, occupants, planets in
  the stars of owners, owners. Houses are cusp-based (a planet belongs to the house whose cusp precedes it).
"""
from __future__ import annotations

import math

from .constants import DASHA_ORDER, DASHA_YEARS, PLANETS, PLANETS_HI, SIGNS, SIGNS_HI, SIGN_LORDS
from .core import _precession_deg, ascendant_tropical, gmst_deg, midheaven_tropical, obliquity_deg
from .ephemeris import norm360

KP_J2000 = 23.7658                     # Krishnamurti ayanamsa at J2000.0 (approx.; Lahiri is 23.8531)
NAK_SPAN = 360.0 / 27.0
DEG = math.pi / 180.0


def kp_ayanamsa(jd_tt: float) -> float:
    t = (jd_tt - 2451545.0) / 36525.0
    return KP_J2000 + _precession_deg(t)


# ---- Placidus ----------------------------------------------------------------------------------
def _ra_to_lon(ra_deg: float, eps_deg: float) -> float:
    """Ecliptic longitude of the ecliptic point with right ascension ra (latitude 0)."""
    ra, eps = ra_deg * DEG, eps_deg * DEG
    return norm360(math.degrees(math.atan2(math.sin(ra), math.cos(ra) * math.cos(eps))))


def placidus_cusps(jd_ut: float, jd_tt: float, lat: float, lon_east: float) -> list[float]:
    """12 tropical Placidus cusps (degrees). Fails above the polar circles (returns Porphyry there)."""
    ramc = norm360(gmst_deg(jd_ut) + lon_east)
    eps, phi = obliquity_deg(jd_tt), lat
    asc = ascendant_tropical(jd_ut, jd_tt, lat, lon_east)
    mc = midheaven_tropical(jd_ut, jd_tt, lon_east)
    if abs(lat) > 66.0:
        from .core import sripati_cusps
        return sripati_cusps(asc, mc)
    k = math.tan(eps * DEG) * math.tan(phi * DEG)

    def cusp(f: float, above: bool) -> float:
        # above (houses 11, 12): R = ramc + f*acos(-sin R * k); below (houses 2, 3): R = ramc + 180 - f*acos(sin R * k)
        r = ramc + (f * 90.0 if above else 180.0 - f * 90.0)
        for _ in range(30):
            s = math.sin(r * DEG) * k
            s = max(-1.0, min(1.0, s))
            r = ramc + (f * math.degrees(math.acos(-s)) if above else 180.0 - f * math.degrees(math.acos(s)))
        return _ra_to_lon(r, eps)
    c11, c12 = cusp(1 / 3, True), cusp(2 / 3, True)
    c2, c3 = cusp(2 / 3, False), cusp(1 / 3, False)
    c = [asc, c2, c3, norm360(mc + 180), norm360(c11 + 180), norm360(c12 + 180),
         norm360(asc + 180), norm360(c2 + 180), norm360(c3 + 180), mc, c11, c12]
    return [norm360(x) for x in c]


# ---- lords ---------------------------------------------------------------------------------------
def _lords(lon: float) -> dict:
    lon = lon % 360.0
    nak = int(lon // NAK_SPAN) % 27
    star = DASHA_ORDER[nak % 9]
    within = lon - nak * NAK_SPAN
    # sub: Vimshottari order starting from the star lord, spans proportional to years
    order = DASHA_ORDER[DASHA_ORDER.index(star):] + DASHA_ORDER[:DASHA_ORDER.index(star)]
    pos, sub, sub_start, sub_span = 0.0, order[-1], 0.0, 0.0
    for p in order:
        span = NAK_SPAN * DASHA_YEARS[p] / 120.0
        if within < pos + span or p == order[-1]:
            sub, sub_start, sub_span = p, pos, span
            break
        pos += span
    # sub-sub: same again inside the sub, starting from the sub lord
    order2 = DASHA_ORDER[DASHA_ORDER.index(sub):] + DASHA_ORDER[:DASHA_ORDER.index(sub)]
    w2, pos2, subsub = within - sub_start, 0.0, order2[-1]
    for p in order2:
        span = sub_span * DASHA_YEARS[p] / 120.0
        if w2 < pos2 + span or p == order2[-1]:
            subsub = p
            break
        pos2 += span
    sign = int(lon // 30)
    return {"sign": sign, "sign_name": SIGNS[sign], "sign_name_hi": SIGNS_HI[sign], "sign_lord": SIGN_LORDS[sign],
            "nakshatra_index": nak, "star_lord": star, "sub_lord": sub, "sub_sub_lord": subsub,
            "degree_in_sign": lon - sign * 30}


def _house_of(lon: float, cusps: list[float]) -> int:
    for i in range(12):
        a, b = cusps[i], cusps[(i + 1) % 12]
        if (lon - a) % 360.0 < (b - a) % 360.0:
            return i + 1
    return 1


def kp(chart: dict) -> dict:
    inp = chart["input"]
    jd_ut = chart["jd_ut"]
    jd_tt = jd_ut + 69.0 / 86400.0
    ayan = kp_ayanamsa(jd_tt)
    shift = ayan - chart["ayanamsa_value"]                      # KP longitudes = Lahiri longitudes - shift
    cusps_trop = placidus_cusps(jd_ut, jd_tt, float(inp["lat"]), float(inp["lon"]))
    cusps = [norm360(c - ayan) for c in cusps_trop]
    planets = {}
    for p in chart["planets"]:
        lon = norm360(p["longitude"] - shift)
        planets[p["name"]] = {**_lords(lon), "longitude": lon, "house": _house_of(lon, cusps), "name_hi": p["name_hi"],
                              "retrograde": p["retrograde"]}
    cusp_rows = [{"house": i + 1, "longitude": c, **_lords(c)} for i, c in enumerate(cusps)]
    # significators
    occupants = {h: [n for n, v in planets.items() if v["house"] == h] for h in range(1, 13)}
    owners = {h: [n for n in PLANETS if n not in ("Rahu", "Ketu") and SIGN_LORDS[cusp_rows[h - 1]["sign"]] == n] for h in range(1, 13)}
    in_star_of = lambda lords: [n for n, v in planets.items() if v["star_lord"] in lords]
    significators = {}
    for h in range(1, 13):
        significators[h] = {"a_in_star_of_occupants": in_star_of(occupants[h]), "b_occupants": occupants[h],
                            "c_in_star_of_owners": in_star_of(owners[h]), "d_owners": owners[h]}
    return {"system": "KP", "ayanamsa": ayan, "ayanamsa_note": "Krishnamurti ayanamsa (approx., +-1 arc-min); houses Placidus",
            "houses": "placidus", "cusps": cusp_rows, "planets": planets, "significators": significators,
            "review_status": "draft",
            "note_hi": "कृष्णमूर्ति पद्धति: KP अयनांश (लाहिरी से लगभग 5-6 कला कम), प्लेसिडस भाव, हर ग्रह और भाव-स्पष्ट के नक्षत्र-स्वामी, उप-स्वामी और उप-उप-स्वामी। "
                       "कारक-सारणी चार स्तरों में है। यह ड्राफ़्ट है; KP विशेषज्ञ की समीक्षा चाहिए।",
            "note_en": "Krishnamurti Paddhati: KP ayanamsa (about 5-6 arc-min less than Lahiri), Placidus houses, star/sub/sub-sub lord of every planet and cusp, "
                       "four-level significators. Draft; needs review by a KP practitioner."}
