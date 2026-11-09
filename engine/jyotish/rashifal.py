"""Rashifal (Moon-sign horoscope) for a day, week or month, built from the transit (gochara) rule library.

For each of the twelve Moon signs the transiting planets' houses from that sign are read with the gochara texts
(`data/rules/gochara.json`, favourable-house lists with vedha), summed into a score and a short tendency reading.
Daily: positions at local noon; weekly: Moon dropped (it changes sign every 2-3 days) and the other planets at the
middle of the week; monthly: the slow planets only (Sun, Mars, Jupiter, Venus, Mercury, Saturn, nodes) at mid-month.
Wording is the rule library's tendency language; nothing here predicts events. Draft.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .constants import PLANETS_HI, SIGNS, SIGNS_HI
from .ephemeris import AnalyticBackend
from .rules import gochara_text
from .transit import positions_at, vedha_for

_B = AnalyticBackend()
PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
WEIGHT = {"Sun": 1.0, "Moon": 1.0, "Mars": 1.2, "Mercury": 0.8, "Jupiter": 1.6, "Venus": 1.0, "Saturn": 1.6, "Rahu": 1.0, "Ketu": 0.8}
DAY_LORD_HI = ["सूर्य", "चंद्र", "मंगल", "बुध", "गुरु", "शुक्र", "शनि"]
LUCKY = {0: ("लाल, नारंगी", "red, orange", 1), 1: ("सफ़ेद, क्रीम", "white, cream", 2), 2: ("लाल", "red", 9), 3: ("हरा", "green", 5), 4: ("पीला", "yellow", 3), 5: ("गुलाबी, सफ़ेद", "pink, white", 6), 6: ("नीला, काला", "blue, black", 8)}


def _houses_from(sign: int, pos: dict) -> dict:
    return {p: (pos[p]["sign"] - sign) % 12 + 1 for p in PLANETS if p in pos}


def reading_for_sign(sign: int, pos: dict, planets: list[str]) -> dict:
    houses = _houses_from(sign, pos)
    rows, score, mx = [], 0.0, 0.0
    for p in planets:
        if p not in houses:
            continue
        h = houses[p]
        rule = gochara_text(p, h)
        if not rule:
            continue
        vb = vedha_for(p, h, houses)
        fav = bool(rule.get("favourable"))
        w = WEIGHT[p]
        mx += w
        if fav and vb:
            score += 0.3 * w
        elif fav:
            score += w
        else:
            score += 0.15 * w
        rows.append({"planet": p, "planet_hi": PLANETS_HI[p], "house": h, "favourable": fav, "vedha_by": vb, "vedha_by_hi": [PLANETS_HI[v] for v in vb],
                     "text_hi": rule["text_hi"], "text_en": rule["text_en"], "retrograde": bool(pos[p].get("retrograde"))})
    pct = round(100 * score / mx) if mx else 0
    good = [r for r in rows if r["favourable"] and not r["vedha_by"]]
    care = [r for r in rows if not r["favourable"]]
    summary_hi = (f"{len(good)} ग्रह अनुकूल भावों में" + (f" ({', '.join(r['planet_hi'] for r in good)})" if good else "") +
                  (f"; सावधानी: {', '.join(r['planet_hi'] for r in care)}" if care else "") + "।")
    summary_en = (f"{len(good)} planet(s) in favourable houses" + (f" ({', '.join(r['planet'] for r in good)})" if good else "") +
                  (f"; care with {', '.join(r['planet'] for r in care)}" if care else "") + ".")
    grade = "उत्तम" if pct >= 70 else "अच्छा" if pct >= 55 else "मध्यम" if pct >= 40 else "संयम"
    grade_en = "excellent" if pct >= 70 else "good" if pct >= 55 else "mixed" if pct >= 40 else "restraint"
    return {"sign": sign, "sign_name": SIGNS[sign], "sign_name_hi": SIGNS_HI[sign], "score": pct, "grade_hi": grade, "grade_en": grade_en,
            "summary_hi": summary_hi, "summary_en": summary_en, "planets": rows}


def rashifal(day_iso: str, tz: str = "Asia/Kolkata", period: str = "daily", lat: float = 28.61, lon: float = 77.2) -> dict:
    d = date.fromisoformat(day_iso)
    zone = ZoneInfo(tz)
    if period == "weekly":
        start = d - timedelta(days=d.weekday()); mid = start + timedelta(days=3)
        planets = [p for p in PLANETS if p != "Moon"]; label_hi, label_en = "साप्ताहिक", "weekly"
        span = {"from": start.isoformat(), "to": (start + timedelta(days=6)).isoformat()}
    elif period == "monthly":
        start = d.replace(day=1); mid = start + timedelta(days=14)
        planets = [p for p in PLANETS if p != "Moon"]; label_hi, label_en = "मासिक", "monthly"
        nxt = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        span = {"from": start.isoformat(), "to": (nxt - timedelta(days=1)).isoformat()}
    else:
        mid = d; planets = PLANETS; label_hi, label_en = "दैनिक", "daily"; span = {"from": d.isoformat(), "to": d.isoformat()}
    when = datetime(mid.year, mid.month, mid.day, 12, 0, tzinfo=zone).astimezone(timezone.utc)
    pos = positions_at(when, _B)
    signs = [reading_for_sign(s, pos, planets) for s in range(12)]
    wd = (d.weekday() + 1) % 7
    lucky = LUCKY[wd]
    return {"date": day_iso, "period": period, "period_hi": label_hi, "period_en": label_en, "span": span,
            "transits": {p: {"sign": pos[p]["sign"], "sign_hi": SIGNS_HI[pos[p]["sign"]], "retrograde": bool(pos[p].get("retrograde"))} for p in PLANETS if p in pos},
            "day_lord_hi": DAY_LORD_HI[wd], "lucky_colour_hi": lucky[0], "lucky_colour": lucky[1], "lucky_number": lucky[2],
            "signs": signs, "review_status": "draft",
            "note_hi": f"{label_hi} राशिफल चंद्र-राशि से गोचर (फलदीपिका की अनुकूल-भाव सूची, वेध सहित) के आधार पर; यह प्रवृत्ति-संकेत है, घटना की भविष्यवाणी नहीं। शुभ रंग/अंक वार के स्वामी से।",
            "note_en": f"{label_en.capitalize()} rashifal from the transits over the Moon sign (Phaladeepika favourable houses with vedha); a tendency pointer, not a prediction. Lucky colour/number from the weekday lord."}
