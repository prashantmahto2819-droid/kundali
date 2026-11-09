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

from .constants import NAKSHATRAS, PLANETS_HI, SIGNS, SIGNS_HI
NAKSHATRAS_INDEX = {n: i for i, n in enumerate(NAKSHATRAS)}
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


# ---------------------------------------------------------------- ashtakavarga transit score (personal day) and year-ahead table
AV_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]


def personal_day(chart: dict, day: date, tz: str = "Asia/Kolkata") -> dict:
    """Today's transits scored against the natal Ashtakavarga: for each planet, the bindus of its own BAV in the sign it transits
    (≥5 favourable, ≤3 weak) and the SAV of that sign; plus the Moon's house from the natal Moon (chandra-bala) and tara-bala."""
    av = chart.get("ashtakavarga") or {}
    pos = positions_at(_noon(day, tz), _B)
    moon_sign = next(p for p in chart["planets"] if p["name"] == "Moon")["sign"]
    moon_nak = NAKSHATRAS_INDEX[next(p for p in chart["planets"] if p["name"] == "Moon")["nakshatra"]]
    rows, score, mx = [], 0.0, 0.0
    for pl in AV_PLANETS:
        s = pos[pl]["sign"]
        bav = (av.get("bav") or {}).get(pl, {}).get("by_sign")
        b = bav[s] if bav else None
        sav = (av.get("sav") or {}).get("by_sign", [None] * 12)[s] if av.get("sav") else None
        if b is None:
            continue
        w = {"Moon": 1.0, "Sun": 0.8, "Mars": 1.0, "Mercury": 0.7, "Jupiter": 1.3, "Venus": 0.9, "Saturn": 1.3}[pl]
        score += w * (b / 8.0); mx += w
        rows.append({"planet": pl, "planet_hi": PLANETS_HI[pl], "sign": s, "sign_hi": SIGNS_HI[s], "bindus": b, "sav": sav, "house_from_moon": (s - moon_sign) % 12 + 1,
                     "grade": "good" if b >= 5 else "weak" if b <= 3 else "mixed"})
    pct = round(100 * score / mx) if mx else 0
    tm = pos["Moon"]["sign"]
    chandra = (tm - moon_sign) % 12 + 1
    chandra_good = chandra in (1, 3, 6, 7, 10, 11)
    tnak = int(pos["Moon"]["longitude"] // (360 / 27)) if "longitude" in pos["Moon"] else None
    tara = None
    if tnak is not None:
        t = ((tnak - moon_nak) % 27) % 9 + 1
        tara = {"n": t, "hi": ["जन्म", "संपत", "विपत", "क्षेम", "प्रत्यरि", "साधक", "वध", "मित्र", "अति-मित्र"][t - 1], "good": t in (2, 4, 6, 8, 9)}
    good = [r["planet_hi"] for r in rows if r["grade"] == "good"]
    weak = [r["planet_hi"] for r in rows if r["grade"] == "weak"]
    text_hi = (f"अष्टकवर्ग के अनुसार आज {pct}/100: " + (f"{', '.join(good)} अनुकूल बिंदुओं में" if good else "कोई ग्रह विशेष अनुकूल नहीं") + (f"; {', '.join(weak)} कम बिंदुओं में" if weak else "") +
               f"। चंद्र आपके चंद्र से {chandra}वें ({'अनुकूल' if chandra_good else 'सामान्य'})" + (f", तारा {tara['hi']} ({'शुभ' if tara['good'] else 'सावधानी'})" if tara else "") + "।")
    text_en = (f"By Ashtakavarga today scores {pct}/100: " + (f"{', '.join(r['planet'] for r in rows if r['grade'] == 'good')} in favourable bindus" if good else "no planet especially favourable") +
               (f"; {', '.join(r['planet'] for r in rows if r['grade'] == 'weak')} in low bindus" if weak else "") + f". Moon {chandra} from your Moon ({'favourable' if chandra_good else 'ordinary'})" +
               (f", tara {tara['n']} ({'good' if tara['good'] else 'care'})" if tara else "") + ".")
    return {"date": day.isoformat(), "score": pct, "planets": rows, "chandra_bala": {"house": chandra, "good": chandra_good}, "tara_bala": tara, "text_hi": text_hi, "text_en": text_en,
            "note_hi": "व्यक्तिगत दिन-स्कोर: गोचर ग्रह की अपनी भिन्नाष्टकवर्ग रेखाएँ उस राशि में (5+ शुभ), सर्वाष्टकवर्ग, चंद्रबल और ताराबल — प्रवृत्ति-संकेत।",
            "note_en": "Personal day score: each transiting planet's own BAV bindus in its sign (5+ good), SAV, chandra-bala and tara-bala — a tendency pointer."}


def year_ahead(chart: dict, start: date, tz: str = "Asia/Kolkata", months: int = 12) -> dict:
    """Month-by-month transit table for this chart: where Jupiter, Saturn, Rahu, Mars and the Sun sit (house from the natal Moon,
    BAV bindus), the running MD/AD, and the dasha/sign-change dates within the window (from _day_changes, scanned by day)."""
    av = (chart.get("ashtakavarga") or {}).get("bav") or {}
    moon_sign = next(p for p in chart["planets"] if p["name"] == "Moon")["sign"]
    rows = []
    d = start.replace(day=1)
    for i in range(months):
        y, m = d.year + (d.month - 1 + i) // 12, (d.month - 1 + i) % 12 + 1
        mid = date(y, m, 15)
        pos = positions_at(_noon(mid, tz), _B)
        run = current_periods(chart["dasha"], _noon(mid, tz))
        pl = {}
        for p in ("Jupiter", "Saturn", "Rahu", "Mars", "Sun"):
            s = pos[p]["sign"]
            b = av.get(p, {}).get("by_sign", [None] * 12)[s] if p in av else None
            pl[p] = {"sign": s, "sign_hi": SIGNS_HI[s], "house_from_moon": (s - moon_sign) % 12 + 1, "bindus": b, "retrograde": pos[p].get("retrograde", False)}
        rows.append({"year": y, "month": m, "planets": pl, "dasha": [{"level": r["level"], "lord": r["lord"], "lord_hi": PLANETS_HI[r["lord"]]} for r in run if r["level"] <= 2]})
    # events in the window
    events = []
    cur = start
    end_y, end_m = start.year + (start.month - 1 + months) // 12, (start.month - 1 + months) % 12 + 1
    end = date(end_y, end_m, 1)
    while cur < end:
        for ev in _day_changes(chart, cur - timedelta(days=1), cur, tz):
            if ev["kind"] in ("dasha", "sadesati", "ashtama") or (ev["kind"] == "ingress" and ev["planet"] in ("Jupiter", "Saturn", "Rahu", "Mars")) or ev["kind"] == "station":
                events.append({"date": cur.isoformat(), **ev})
        cur += timedelta(days=1)
    return {"from": start.isoformat(), "months": rows, "events": events,
            "note_hi": "आगामी वर्ष की गोचर-सारणी: गुरु, शनि, राहु, मंगल, सूर्य की राशि (आपके चंद्र से भाव, उस राशि में उनकी अष्टकवर्ग रेखाएँ), चल रही महादशा-अंतर्दशा, और बदलाव की तारीख़ें।",
            "note_en": "Year-ahead transit table: Jupiter, Saturn, Rahu, Mars, Sun by sign (house from your Moon, their BAV bindus there), running MD/AD, and the change dates."}
