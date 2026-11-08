"""Gochara (transits): where the planets are now, read from the natal Moon and the Lagna.

Classical rule: each planet is favourable in certain houses counted from the natal Moon.
We combine that with the planet's ashtakavarga points in the sign it is transiting
(4 or more points is read as supportive). Vedha (obstruction) is not applied yet.
"""
from __future__ import annotations

from datetime import datetime, timezone

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
        from .rules import gochara_text
        txt = gochara_text(name, row["house_from_moon"])
        if txt:
            row.update({"text_hi": txt["text_hi"], "text_en": txt["text_en"], "rule_id": txt["rule_id"]})
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


# ---- 12-month transit calendar ------------------------------------------------------------------
from functools import lru_cache


@lru_cache(maxsize=64)
def _slow_ingress(first_iso: str, months: int, system: str) -> tuple:
    """Sign-ingress dates of the slow planets from a daily scan on the analytic backend (cached per start month)."""
    from datetime import timedelta
    from .ephemeris import AnalyticBackend
    fast = AnalyticBackend()
    first = datetime.strptime(first_iso, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    def signs(dt):
        jd_ut = julian_day(dt)
        jd_tt = jd_ut + delta_t(year_fraction(dt)) / 86400.0
        pos = fast.positions(jd_tt)
        pos["Rahu"] = mean_node(jd_tt)
        pos["Ketu"] = norm360(pos["Rahu"] + 180.0)
        ayan = ayanamsa(jd_tt, system)
        return {p: sign_of(norm360(pos[p] - ayan)) for p in ("Jupiter", "Saturn", "Rahu", "Ketu", "Mars")}
    out, prev, day = [], signs(first), first
    end = first + timedelta(days=int(30.5 * months) + 1)
    while day < end:
        day += timedelta(days=1)
        cur = signs(day)
        for p, sg in cur.items():
            if sg != prev[p]:
                out.append({"planet": p, "date": day.strftime("%Y-%m-%d"), "from": prev[p], "to": sg})
        prev = cur
    return tuple(out)
def transit_calendar(chart: dict, start: datetime, backend, system: str = "lahiri", months: int = 12) -> dict:
    """Month-by-month signs of all planets (from the main backend) plus sign-ingress dates of the slow planets
    found by a daily scan on the fast analytic backend (accurate to about a day for Saturn)."""
    from datetime import timedelta
    from .ephemeris import AnalyticBackend
    moon_sign = next(p for p in chart["planets"] if p["name"] == "Moon")["sign"]
    lagna_sign = chart["lagna"]["sign"]
    rows = []
    first = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    for i in range(months):
        y, m = first.year + (first.month - 1 + i) // 12, (first.month - 1 + i) % 12 + 1
        when = first.replace(year=y, month=m)
        pos = positions_at(when, backend, system)
        rows.append({"month": when.strftime("%Y-%m"), "planets": {
            p: {"sign": v["sign"], "sign_name_hi": SIGNS_HI[v["sign"]], "sign_name": SIGNS[v["sign"]],
                "house_from_moon": (v["sign"] - moon_sign) % 12 + 1, "house_from_lagna": (v["sign"] - lagna_sign) % 12 + 1,
                "retrograde": v["retrograde"]} for p, v in pos.items()}})
    ingress = [{**g, "house_from_moon": (g["to"] - moon_sign) % 12 + 1, "house_from_lagna": (g["to"] - lagna_sign) % 12 + 1,
                "from_sign_hi": SIGNS_HI[g["from"]], "to_sign": SIGNS[g["to"]], "to_sign_hi": SIGNS_HI[g["to"]], "planet_hi": PLANETS_HI[g["planet"]]}
               for g in _slow_ingress(first.strftime("%Y-%m-%d"), months, system)]
    for g in ingress:
        g.pop("from"), g.pop("to")
    return {"from": first.strftime("%Y-%m-%d"), "months": rows, "ingress": ingress,
            "note_hi": "हर महीने की पहली तारीख़ (UTC) की ग्रह-राशियाँ, और धीमे ग्रहों (गुरु, शनि, राहु-केतु, मंगल) के राशि-प्रवेश की तारीख़ें (±1 दिन)। चंद्र से भाव गोचर-फल के लिए, लग्न से भाव कुंडली के लिए।",
            "note_en": "Planet signs on the 1st of each month (UTC) and sign-ingress dates of the slow planets (Jupiter, Saturn, Rahu-Ketu, Mars), accurate to about a day. House from the Moon is for transit results, from the Lagna for the chart."}
