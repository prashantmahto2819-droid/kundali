"""Personal alerts for a day: what changed in this chart's sky today, and what changes within the next week.

Compared between local noon yesterday and local noon today (and ahead day by day for 7 days):
- Vimshottari period changes at mahadasha and antardasha level (pratyantar changes are too frequent for an alert),
- sign changes of Sun, Mercury, Venus, Mars, Jupiter, Saturn, Rahu/Ketu with the house from the natal Moon and the gochara text,
- Sade Sati / Ashtama Shani starting, changing phase or ending,
- retrograde / direct station of Mercury, Venus, Mars, Jupiter, Saturn.
Texts are the rule library's tendency language; the alert says when a period starts, not what will happen.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .constants import PLANETS_HI, SIGNS, SIGNS_HI
from .dasha import current_periods
from .ephemeris import AnalyticBackend
from .rules import gochara_text
from .transit import positions_at, sade_sati

_B = AnalyticBackend()
SLOW = ["Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu"]
STATION = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
ORD_HI = {1: "1ले", 2: "2रे", 3: "3रे", 4: "4थे", 5: "5वें", 6: "6ठे", 7: "7वें", 8: "8वें", 9: "9वें", 10: "10वें", 11: "11वें", 12: "12वें"}
ORD_EN = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", 6: "6th", 7: "7th", 8: "8th", 9: "9th", 10: "10th", 11: "11th", 12: "12th"}
PHASE_HI = {"rising": "प्रथम चरण (चंद्र से 12वें शनि)", "peak": "द्वितीय/शिखर चरण (चंद्र राशि पर शनि)", "setting": "अंतिम चरण (चंद्र से 2रे शनि)"}
PHASE_EN = {"rising": "first phase (Saturn 12th from the Moon)", "peak": "peak phase (Saturn on the Moon sign)", "setting": "last phase (Saturn 2nd from the Moon)"}


def _noon(d: date, tz: str) -> datetime:
    return datetime(d.year, d.month, d.day, 12, 0, tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)


def _dmy(iso: str) -> str:
    return f"{iso[8:10]}-{iso[5:7]}-{iso[:4]}"


def _day_changes(chart: dict, prev: date, cur: date, tz: str) -> list[dict]:
    moon_sign = next(p for p in chart["planets"] if p["name"] == "Moon")["sign"]
    p0, p1 = positions_at(_noon(prev, tz), _B), positions_at(_noon(cur, tz), _B)
    out = []
    # dasha
    run0, run1 = current_periods(chart["dasha"], _noon(prev, tz)), current_periods(chart["dasha"], _noon(cur, tz))
    for lvl, lbl_hi, lbl_en in ((1, "महादशा", "mahadasha"), (2, "अंतर्दशा", "antardasha")):
        a = next((r for r in run0 if r["level"] == lvl), None); b = next((r for r in run1 if r["level"] == lvl), None)
        if b and (not a or a["lord"] != b["lord"] or a["start"] != b["start"]):
            md = next((r["lord"] for r in run1 if r["level"] == 1), None)
            within = f" ({PLANETS_HI[md]} महादशा में)" if lvl == 2 and md else ""
            within_en = f" (within the {md} mahadasha)" if lvl == 2 and md else ""
            out.append({"kind": "dasha", "level": lvl, "lord": b["lord"], "end": b["end"][:10],
                        "hi": f"{PLANETS_HI[b['lord']]} {lbl_hi} शुरू{within}, {_dmy(b['end'])} तक।",
                        "en": f"{b['lord']} {lbl_en} begins{within_en}, until {_dmy(b['end'])}."})
    # sign changes
    for pl in SLOW:
        if p0[pl]["sign"] != p1[pl]["sign"]:
            s = p1[pl]["sign"]; h = (s - moon_sign) % 12 + 1
            rule = gochara_text(pl, h) or {}
            short_hi = (rule.get("text_hi") or "").split(": ", 1)[-1].split("।")[0].split(", ख़ासकर")[0]
            short_en = (rule.get("text_en") or "").split(": ", 1)[-1].split(". ")[0].split(", especially")[0]
            name_hi = "राहु-केतु" if pl == "Rahu" else PLANETS_HI[pl]
            name_en = "Rahu-Ketu" if pl == "Rahu" else pl
            out.append({"kind": "ingress", "planet": pl, "sign": s, "house_from_moon": h, "favourable": rule.get("favourable"),
                        "hi": f"{name_hi} का गोचर {SIGNS_HI[s]} राशि में — आपके चंद्र से {ORD_HI[h]} भाव में।" + (f" {short_hi}।" if short_hi else ""),
                        "en": f"{name_en} enters {SIGNS[s]} — the {ORD_EN[h]} house from your Moon." + (f" {short_en[:1].upper() + short_en[1:]}." if short_en else "")})
    # sade sati
    s0, s1 = sade_sati(moon_sign, p0["Saturn"]["sign"]), sade_sati(moon_sign, p1["Saturn"]["sign"])
    if s0 != s1:
        if s1["active"] and not s0["active"]:
            out.append({"kind": "sadesati", "state": "start", "phase": s1["phase"], "hi": f"शनि की साढ़ेसाती शुरू — {PHASE_HI[s1['phase']]}। लगभग साढ़े सात वर्ष की यह अवधि परंपरा में धैर्य और अनुशासन का काल मानी जाती है।",
                        "en": f"Sade Sati begins — {PHASE_EN[s1['phase']]}. Tradition reads this seven-and-a-half-year stretch as a time for patience and discipline."})
        elif s1["active"] and s0["active"]:
            out.append({"kind": "sadesati", "state": "phase", "phase": s1["phase"], "hi": f"साढ़ेसाती का {PHASE_HI[s1['phase']]} शुरू।", "en": f"Sade Sati moves to its {PHASE_EN[s1['phase']]}."})
        elif s0["active"] and not s1["active"]:
            out.append({"kind": "sadesati", "state": "end", "hi": "शनि की साढ़ेसाती समाप्त।", "en": "Sade Sati ends."})
        if s1["ashtama"] and not s0["ashtama"]:
            out.append({"kind": "ashtama", "state": "start", "hi": "अष्टम शनि (चंद्र से 8वें भाव में शनि) शुरू — परंपरा में सावधानी का काल।", "en": "Ashtama Shani begins (Saturn 8th from the Moon) — traditionally a period for care."})
        elif s0["ashtama"] and not s1["ashtama"]:
            out.append({"kind": "ashtama", "state": "end", "hi": "अष्टम शनि समाप्त।", "en": "Ashtama Shani ends."})
    # stations
    for pl in STATION:
        if p0[pl]["retrograde"] != p1[pl]["retrograde"]:
            if p1[pl]["retrograde"]:
                out.append({"kind": "station", "planet": pl, "retrograde": True, "hi": f"{PLANETS_HI[pl]} वक्री हुआ ({SIGNS_HI[p1[pl]['sign']]} में) — शुरू किए काम की समीक्षा का समय माना जाता है।",
                            "en": f"{pl} turns retrograde (in {SIGNS[p1[pl]['sign']]}) — traditionally a time to review rather than launch."})
            else:
                out.append({"kind": "station", "planet": pl, "retrograde": False, "hi": f"{PLANETS_HI[pl]} मार्गी हुआ ({SIGNS_HI[p1[pl]['sign']]} में)।", "en": f"{pl} turns direct (in {SIGNS[p1[pl]['sign']]})."})
    return out


def alerts(chart: dict, day: date, tz: str = "Asia/Kolkata", ahead_days: int = 7) -> dict:
    """{"today": [...], "upcoming": [{"date": iso, ...}, ...]} for the given local day."""
    today = _day_changes(chart, day - timedelta(days=1), day, tz)
    upcoming = []
    for i in range(1, ahead_days + 1):
        d = day + timedelta(days=i)
        for ev in _day_changes(chart, d - timedelta(days=1), d, tz):
            if ev["kind"] in ("dasha", "sadesati", "ashtama") or (ev["kind"] == "ingress" and ev["planet"] in ("Jupiter", "Saturn", "Rahu", "Mars", "Sun")) or ev["kind"] == "station":
                upcoming.append({"date": d.isoformat(), **ev})
    return {"date": day.isoformat(), "today": today, "upcoming": upcoming,
            "note_hi": "दशा और गोचर परिवर्तन की सूचना; यह समय-संकेत है, घटना की भविष्यवाणी नहीं।",
            "note_en": "Notices of dasha and transit changes; a timing pointer, not a prediction of events."}
