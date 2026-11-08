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


# Vedha (obstruction) points: a favourable transit house is blocked when another planet occupies the paired house.
# Classical pairs (Brihat Samhita / Phaladeepika tradition). Sun-Saturn and Moon-Mercury do not obstruct each other.
VEDHA: dict[str, dict[int, int]] = {
    "Sun": {3: 9, 6: 12, 10: 4, 11: 5},
    "Moon": {1: 5, 3: 9, 6: 12, 7: 2, 10: 4, 11: 8},
    "Mars": {3: 12, 6: 9, 11: 5},
    "Mercury": {2: 5, 4: 3, 6: 9, 8: 1, 10: 8, 11: 12},
    "Jupiter": {2: 12, 5: 4, 7: 3, 9: 10, 11: 8},
    "Venus": {1: 8, 2: 7, 3: 1, 4: 10, 5: 9, 8: 5, 9: 11, 11: 6, 12: 3},
    "Saturn": {3: 12, 6: 9, 11: 5},
    "Rahu": {3: 12, 6: 9, 11: 5}, "Ketu": {3: 12, 6: 9, 11: 5},
}
_NO_VEDHA_PAIRS = {frozenset({"Sun", "Saturn"}), frozenset({"Moon", "Mercury"})}


def vedha_for(name: str, house_from_moon: int, houses_from_moon: dict[str, int]) -> list[str]:
    """Planets that obstruct `name`'s favourable transit (empty when not favourable or not obstructed)."""
    target = VEDHA.get(name, {}).get(house_from_moon)
    if target is None:
        return []
    return sorted(o for o, h in houses_from_moon.items()
                  if o != name and h == target and frozenset({o, name}) not in _NO_VEDHA_PAIRS)


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
    hfm = {n: (now_pos[n]["sign"] - moon_sign) % 12 + 1 for n in PLANETS}
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
            blockers = vedha_for(name, row["house_from_moon"], hfm) if fav else []
            pts = bav[name]["by_sign"][s]
            sup = pts >= SUPPORTIVE_BINDUS
            eff_fav = fav and not blockers
            row.update({"favourable_from_moon": fav, "vedha_by": blockers, "vedha_by_hi": [PLANETS_HI[b] for b in blockers],
                        "bindus": pts, "bindus_supportive": sup,
                        "verdict": "supportive" if eff_fav and sup else ("challenging" if not eff_fav and not sup else "mixed")})
        rows.append(row)
    saturn = next(r for r in rows if r["name"] == "Saturn")
    return {"as_of": when.strftime("%Y-%m-%dT%H:%M:%SZ"), "planets": rows,
            "sade_sati": sade_sati(moon_sign, saturn["sign"]),
            "reference": "natal Moon sign", "vedha_applied": True,
            "confidence": "draft",
            "why_hi": ("गोचर में हर ग्रह जन्म-चंद्र राशि से कुछ ख़ास भावों में शुभ माना जाता है। "
                       "हमने इसे उस राशि में ग्रह के अष्टकवर्ग बिंदुओं (4 या अधिक = सहायक) से मिलाया है। "
                       "‘मिश्रित’ का मतलब है कि दोनों संकेत अलग-अलग हैं। वेध लागू है: शुभ भाव का फल तब रुका माना जाता है जब कोई दूसरा ग्रह उसके वेध-स्थान पर हो (सूर्य-शनि और चंद्र-बुध एक-दूसरे को वेध नहीं देते); "
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


# ---- Lifetime Saturn / Jupiter transit periods (Sade Sati, Ashtama/Dhaiya, Jupiter by house) ----------------
@lru_cache(maxsize=16)
def _sign_periods(planet: str, start_year: int, end_year: int, system: str = "lahiri") -> tuple:
    """(sign, start_date, end_date) runs of a slow planet from a 2-day scan on the analytic backend."""
    from datetime import timedelta
    from .ephemeris import AnalyticBackend
    fast = AnalyticBackend()
    day = datetime(start_year, 1, 1, tzinfo=timezone.utc)
    end = datetime(end_year, 12, 31, tzinfo=timezone.utc)

    def sg(dt):
        jd_ut = julian_day(dt); jd_tt = jd_ut + delta_t(year_fraction(dt)) / 86400.0
        return sign_of(norm360(fast.positions(jd_tt)[planet] - ayanamsa(jd_tt, system)))
    runs, cur, cur_start = [], sg(day), day
    step = timedelta(days=4)
    while day < end:
        day += step
        s = sg(day)
        if s != cur:
            # refine the boundary to the day
            lo = day - step
            for k in range(1, 4):
                if sg(lo + timedelta(days=k)) != cur:
                    day = lo + timedelta(days=k); break
            runs.append((cur, cur_start.strftime("%Y-%m-%d"), day.strftime("%Y-%m-%d")))
            cur, cur_start = s, day
    runs.append((cur, cur_start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
    # merge retrograde dips: A, short B (< 240 days), A again -> one A run
    merged = list(runs)
    i = 0
    while i + 2 < len(merged):
        a, b, c = merged[i], merged[i + 1], merged[i + 2]
        if a[0] == c[0] and (datetime.strptime(b[2], "%Y-%m-%d") - datetime.strptime(b[1], "%Y-%m-%d")).days < 240:
            merged[i:i + 3] = [(a[0], a[1], c[2])]
        else:
            i += 1
    return tuple(merged)


def life_transits(chart: dict, years_after: int = 90) -> dict:
    """Sade Sati / Ashtama / Dhaiya windows and Jupiter's house-from-Moon periods over the native's life (+-2 days)."""
    moon_sign = next(p["sign"] for p in chart["planets"] if p["name"] == "Moon")
    by = int(chart["input"]["date"][:4])
    birth = chart["input"]["date"]
    last = f"{min(2100, by + years_after)}-12-31"
    sat = [r for r in _sign_periods("Saturn", 1900, 2100) if r[2] >= birth and r[1] <= last]    # one cached scan for everyone
    jup = [r for r in _sign_periods("Jupiter", 1900, 2100) if r[2] >= birth and r[1] <= last]
    PH = {11: ("rising", "पहला चरण (चंद्र से 12वाँ)"), 0: ("peak", "मध्य चरण (चंद्र राशि पर)"), 1: ("setting", "अंतिम चरण (चंद्र से दूसरा)")}
    sade, ashtama, dhaiya = [], [], []
    for s, a, b in sat:
        d = (s - moon_sign) % 12
        row = {"sign": s, "sign_name": SIGNS[s], "sign_name_hi": SIGNS_HI[s], "start": max(a, birth), "end": b, "house_from_moon": d + 1}
        if d in PH:
            sade.append({**row, "phase": PH[d][0], "phase_hi": PH[d][1]})
        elif d == 7:
            ashtama.append(row)
        elif d == 3:
            dhaiya.append({**row, "kind": "kantaka (4th)", "kind_hi": "कंटक शनि (चंद्र से चौथा)"})
    # group consecutive Sade Sati phases into one 7.5-year window
    windows, cur = [], None
    for p in sade:
        if cur and (datetime.strptime(p["start"], "%Y-%m-%d") - datetime.strptime(cur["end"], "%Y-%m-%d")).days <= 400:
            cur["end"] = p["end"]; cur["phases"].append(p)
        else:
            cur = {"start": p["start"], "end": p["end"], "phases": [p]}; windows.append(cur)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for w in windows:
        w["status"] = "running" if w["start"] <= today < w["end"] else ("past" if w["end"] <= today else "future")
    jup_rows = [{"sign": s, "sign_name_hi": SIGNS_HI[s], "start": max(a, birth), "end": b, "house_from_moon": (s - moon_sign) % 12 + 1,
                 "favourable": (s - moon_sign) % 12 + 1 in FAVOURABLE_FROM_MOON["Jupiter"]} for s, a, b in jup]
    return {"sade_sati_windows": windows, "ashtama_shani": ashtama, "kantaka_shani": dhaiya, "jupiter_periods": jup_rows,
            "note_hi": "साढ़ेसाती = शनि चंद्र राशि से 12वें, उसी और दूसरे भाव में (लगभग साढ़े सात वर्ष); अष्टम शनि = 8वें में; कंटक = 4थे में। "
                       "गुरु के भाव-वार काल भी दिए हैं (शुभ: 2, 5, 7, 9, 11)। तारीख़ें ±2 दिन; वक्री आवाजाही से छोटे टुकड़े बन सकते हैं।",
            "note_en": "Sade Sati = Saturn in the 12th, 1st and 2nd from the Moon sign (about 7.5 years); Ashtama = 8th; Kantaka = 4th. "
                       "Jupiter's periods by house from the Moon are listed too (favourable: 2, 5, 7, 9, 11). Dates +-2 days; retrograde loops may split a period."}
