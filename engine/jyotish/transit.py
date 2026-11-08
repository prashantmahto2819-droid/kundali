"""Gochara (transits): where the planets are now, read from the natal Moon and the Lagna.

Classical rule: each planet is favourable in certain houses counted from the natal Moon.
We combine that with the planet's ashtakavarga points in the sign it is transiting
(4 or more points is read as supportive). Vedha (obstruction) is not applied yet.
"""
from __future__ import annotations

from datetime import datetime

from .constants import PLANETS, PLANETS_HI, SIGNS, SIGNS_HI
from .core import ayanamsa, sign_of
from .ephemeris import mean_node, norm360
from .timeutil import delta_t, julian_day, year_fraction

# Houses from the natal Moon in which a transiting planet is traditionally favourable.
FAVOURABLE_FROM_MOON: dict[str, tuple[int, ...]] = {
    "Sun": (3, 6, 10, 11), "Moon": (1, 3, 6, 7, 10, 11), "Mars": (3, 6, 11),
    "Mercury": (2, 4, 6, 8, 10, 11), "Jupiter": (2, 5, 7, 9, 11),
    "Venus": (1, 2, 3, 4, 5, 8, 9, 11, 12), "Saturn": (3, 6, 11),
}
SUPPORTIVE_BINDUS = 4


def sade_sati(moon_sign: int, saturn_sign: int) -> dict:
    """Saturn in the 12th, 1st or 2nd sign from the natal Moon sign is the 7.5-year Sade Sati;
    in the 8th it is Ashtama Shani (the small Panoti is counted separately by tradition)."""
    d = (saturn_sign - moon_sign) % 12
    phase = {11: "rising", 0: "peak", 1: "setting"}.get(d)
    return {"active": phase is not None, "phase": phase, "ashtama": d == 7,
            "saturn_from_moon": d + 1}


def positions_at(dt_utc: datetime, backend, system: str = "lahiri") -> dict[str, dict]:
    jd_ut = julian_day(dt_utc)
    jd_tt = jd_ut + delta_t(year_fraction(dt_utc)) / 86400.0
    trop = backend.positions(jd_tt)
    trop["Rahu"] = mean_node(jd_tt)
    trop["Ketu"] = norm360(trop["Rahu"] + 180.0)
    ayan = ayanamsa(jd_tt, system)
    before = backend.positions(jd_tt - 0.5)
    after = backend.positions(jd_tt + 0.5)
    out = {}
    for p in PLANETS:
        lon = norm360(trop[p] - ayan)
        if p in ("Rahu", "Ketu"):
            retro = True
        elif p in ("Sun", "Moon"):
            retro = False
        else:
            retro = ((after[p] - before[p] + 180) % 360 - 180) < 0
        out[p] = {"longitude": lon, "sign": sign_of(lon), "retrograde": retro}
    return out


def gochara(chart: dict, now_pos: dict[str, dict], when: datetime) -> dict:
    moon_sign = next(p["sign"] for p in chart["planets"] if p["name"] == "Moon")
    lagna_sign = chart["lagna"]["sign"]
    bav = chart["ashtakavarga"]["bav"]
    rows = []
    for name in PLANETS:
        pos = now_pos[name]
        s = pos["sign"]
        row = {"name": name, "name_hi": PLANETS_HI[name], "longitude": pos["longitude"],
               "sign": s, "sign_name": SIGNS[s], "sign_name_hi": SIGNS_HI[s],
               "degree_in_sign": pos["longitude"] - s * 30, "retrograde": pos["retrograde"],
               "house_from_moon": (s - moon_sign) % 12 + 1, "house_from_lagna": (s - lagna_sign) % 12 + 1}
        if name in FAVOURABLE_FROM_MOON:
            fav = row["house_from_moon"] in FAVOURABLE_FROM_MOON[name]
            pts = bav[name]["by_sign"][s]
            sup = pts >= SUPPORTIVE_BINDUS
            row.update({"favourable_from_moon": fav, "bindus": pts, "bindus_supportive": sup,
                        "verdict": "supportive" if fav and sup else ("challenging" if not fav and not sup else "mixed")})
        rows.append(row)
    saturn = next(r for r in rows if r["name"] == "Saturn")
    return {"as_of": when.strftime("%Y-%m-%dT%H:%M:%SZ"), "planets": rows,
            "sade_sati": sade_sati(moon_sign, saturn["sign"]),
            "reference": "natal Moon sign", "vedha_applied": False,
            "confidence": "draft",
            "why_hi": ("गोचर में हर ग्रह जन्म-चंद्र राशि से कुछ ख़ास भावों में शुभ माना जाता है। "
                       "हमने इसे उस राशि में ग्रह के अष्टकवर्ग बिंदुओं (4 या अधिक = सहायक) से मिलाया है। "
                       "‘मिश्रित’ का मतलब है कि दोनों संकेत अलग-अलग हैं। वेध अभी लागू नहीं है; "
                       "यह दिशा-संकेत है, भविष्यवाणी नहीं।")}
