"""Extra daily panchang elements found in full almanacs (Drik-style):
Varjyam and Amrit Kalam (nakshatra-portion based), Dur Muhurtam (weekday muhurta numbers), Ravi Pushya / Guru Pushya,
Ravi yoga, Tripushkara / Dwipushkara, Anandadi yoga (27 vara-nakshatra yogas), plus the year's eclipses from the syzygies.

Conventions: the nakshatra is divided into 60 ghatis of its own duration; Varjyam begins at the table ghati and lasts 4 ghatis;
Amrit Kalam begins 30 ghatis after Varjyam's start (wrapping into the next nakshatra when needed) and also lasts 4 ghatis.
Dur Muhurtam: the day (sunrise→sunset) is split into 15 muhurtas; the inauspicious ones by weekday are
Sun 14; Mon 9, 12; Tue 4 (and 7th of night, not listed); Wed 8; Thu 6, 12; Fri 4, 9; Sat 1, 2.
Eclipses: a solar eclipse is possible when the Sun is within 18.5° of a lunar node at new moon (certain within 15.4°),
a lunar eclipse when within 12.1° at full moon (certain within 9.5°). Visibility from India is not computed here.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .constants import NAKSHATRAS
from .ephemeris import AnalyticBackend, mean_node, norm360
from .core import ayanamsa
from .timeutil import delta_t, julian_day, year_fraction

_B = AnalyticBackend()
VARJYAM_GHATI = {"Ashwini": 50, "Bharani": 24, "Krittika": 30, "Rohini": 40, "Mrigashira": 14, "Ardra": 21, "Punarvasu": 30, "Pushya": 20, "Ashlesha": 32,
                 "Magha": 30, "Purva Phalguni": 20, "Uttara Phalguni": 18, "Hasta": 21, "Chitra": 20, "Swati": 14, "Vishakha": 14, "Anuradha": 10, "Jyeshtha": 14,
                 "Mula": 56, "Purva Ashadha": 24, "Uttara Ashadha": 20, "Shravana": 10, "Dhanishtha": 10, "Shatabhisha": 18, "Purva Bhadrapada": 16, "Uttara Bhadrapada": 24, "Revati": 30}
DUR_MUHURTAM = {0: [14], 1: [9, 12], 2: [4], 3: [8], 4: [6, 12], 5: [4, 9], 6: [1, 2]}
RAVI_YOGA_DIST = {4, 6, 9, 10, 13, 20}            # Moon's nakshatra counted from the Sun's nakshatra
DWIPADA = {"Punarvasu", "Uttara Phalguni", "Krittika", "Uttara Ashadha", "Purva Bhadrapada", "Vishakha"}
TRIPADA = {"Mrigashira", "Chitra", "Dhanishtha"}
PUSHKARA_TITHI = {2, 7, 12, 17, 22, 27}            # dwitiya, saptami, dwadashi of either paksha
PUSHKARA_VARA = {0, 2, 6}
ANANDADI = [("Ananda", "आनंद", True), ("Kaladanda", "कालदंड", False), ("Dhumra", "धूम्र", False), ("Prajapati", "प्रजापति", True), ("Saumya", "सौम्य", True), ("Dhwanksha", "ध्वांक्ष", False),
            ("Dhwaja", "ध्वज", True), ("Srivatsa", "श्रीवत्स", True), ("Vajra", "वज्र", False), ("Mudgara", "मुद्गर", False), ("Chhatra", "छत्र", True), ("Mitra", "मित्र", True),
            ("Manasa", "मानस", True), ("Padma", "पद्म", True), ("Lumbaka", "लुंबक", False), ("Utpata", "उत्पात", False), ("Mrityu", "मृत्यु", False), ("Kana", "काण", False),
            ("Siddhi", "सिद्धि", True), ("Shubha", "शुभ", True), ("Amrita", "अमृत", True), ("Musala", "मुसल", False), ("Gada", "गद", False), ("Matanga", "मातंग", True),
            ("Rakshasa", "राक्षस", False), ("Chara", "चर", True), ("Sthira", "स्थिर", True)]
ANANDADI_START = {0: 0, 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 23}   # weekday → nakshatra index that gives Ananda


def _fmt(dt: datetime, zone: ZoneInfo) -> str:
    return dt.astimezone(zone).strftime("%H:%M")


def _span(start: datetime, end: datetime, zone: ZoneInfo, day) -> dict | None:
    """Window as local HH:MM; None when it lies entirely before the local day (it belonged to yesterday's panchang)."""
    if end.astimezone(zone).date() < day:
        return None
    out = {"start": _fmt(start, zone), "end": _fmt(end, zone)}
    if start.astimezone(zone).date() > day:
        out["next_day"] = True
    return out


def nakshatra_windows(nak_name: str, nak_start: datetime, nak_end: datetime, next_nak: str | None, next_end: datetime | None, zone: ZoneInfo, day) -> dict:
    """Varjyam and Amrit Kalam for the nakshatra running at sunrise (and, when the next nakshatra also starts today, its Varjyam)."""
    dur = nak_end - nak_start
    g = dur / 60
    out = {}
    v0 = nak_start + g * VARJYAM_GHATI[nak_name]
    out["varjyam"] = [w for w in [_span(v0, v0 + g * 4, zone, day)] if w]
    a_ghati = VARJYAM_GHATI[nak_name] + 30
    if a_ghati < 60:
        a0 = nak_start + g * a_ghati
        out["amrit_kalam"] = _span(a0, a0 + g * 4, zone, day)
    elif next_nak and next_end:
        g2 = (next_end - nak_end) / 60
        a0 = nak_end + g2 * (a_ghati - 60)
        out["amrit_kalam"] = _span(a0, a0 + g2 * 4, zone, day)
    if next_nak and next_end and nak_end.astimezone(zone).date() == day:
        g2 = (next_end - nak_end) / 60
        v1 = nak_end + g2 * VARJYAM_GHATI[next_nak]
        w = _span(v1, v1 + g2 * 4, zone, day)
        if w:
            out["varjyam"].append(w)
    return out


def dur_muhurtam(sunrise: datetime, sunset: datetime, weekday: int, zone: ZoneInfo) -> list[dict]:
    m = (sunset - sunrise) / 15
    return [{"start": _fmt(sunrise + m * (k - 1), zone), "end": _fmt(sunrise + m * k, zone)} for k in DUR_MUHURTAM[weekday]]


def special_yogas(weekday: int, nak_name: str, sun_nak_idx: int, moon_nak_idx: int, tithi_number: int) -> list[dict]:
    out = []
    if nak_name == "Pushya" and weekday == 0:
        out.append({"key": "ravi_pushya", "hi": "रवि पुष्य योग", "en": "Ravi Pushya"})
    if nak_name == "Pushya" and weekday == 4:
        out.append({"key": "guru_pushya", "hi": "गुरु पुष्य योग", "en": "Guru Pushya"})
    if ((moon_nak_idx - sun_nak_idx) % 27) + 1 in RAVI_YOGA_DIST:
        out.append({"key": "ravi_yoga", "hi": "रवि योग", "en": "Ravi Yoga"})
    if tithi_number in PUSHKARA_TITHI and weekday in PUSHKARA_VARA:
        if nak_name in DWIPADA:
            out.append({"key": "tripushkara", "hi": "त्रिपुष्कर योग", "en": "Tripushkara"})
        elif nak_name in TRIPADA:
            out.append({"key": "dwipushkara", "hi": "द्विपुष्कर योग", "en": "Dwipushkara"})
    return out


def anandadi(weekday: int, moon_nak_idx: int) -> dict:
    name, hi, good = ANANDADI[(moon_nak_idx - ANANDADI_START[weekday]) % 27]
    return {"name": name, "hi": hi, "auspicious": good}


# ---------------------------------------------------------------- eclipses
def _jd(dt: datetime) -> float:
    u = dt.astimezone(timezone.utc)
    return julian_day(u) + delta_t(year_fraction(u)) / 86400.0


def _elong(jd: float) -> float:
    p = _B.positions(jd)
    return norm360(p["Moon"] - p["Sun"])


def _syzygy(jd_guess: float, target: float) -> float:
    """Refine the instant where Moon−Sun elongation equals target (0 new, 180 full) near jd_guess."""
    lo, hi = jd_guess - 1.5, jd_guess + 1.5
    f = lambda j: ((_elong(j) - target + 180) % 360) - 180
    for _ in range(40):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def eclipses(year: int, tz: str = "Asia/Kolkata") -> list[dict]:
    zone = ZoneInfo(tz)
    out = []
    jd = _jd(datetime(year, 1, 1, tzinfo=timezone.utc)) - 2.0
    end = _jd(datetime(year + 1, 1, 1, tzinfo=timezone.utc))
    # step by half-lunations: find each new and full moon
    e0 = _elong(jd)
    t = jd
    while t < end:
        t2 = t + 1.0
        e1 = _elong(t2)
        hits = []
        if e1 < e0:                                   # elongation wrapped 360→0: new moon
            hits.append(0.0)
        if e0 < 180.0 <= e1:                          # full moon
            hits.append(180.0)
        for target in hits:
            if True:
                js = _syzygy(t2, target)
                if js < _jd(datetime(year, 1, 1, tzinfo=timezone.utc)) or js >= end:
                    continue
                sun = _B.positions(js)["Sun"]
                node = mean_node(js)
                dist = min(abs(((sun - node + 180) % 360) - 180), abs(((sun - node) % 360) - 180))
                limit_possible, limit_sure = (18.5, 15.4) if target == 0.0 else (12.1, 9.5)
                if dist <= limit_possible:
                    when = datetime(2000, 1, 1, 12, tzinfo=timezone.utc) + timedelta(days=js - 2451545.0 - delta_t(year) / 86400.0)
                    kind = "solar" if target == 0.0 else "lunar"
                    out.append({"kind": kind, "kind_hi": "सूर्य ग्रहण" if kind == "solar" else "चंद्र ग्रहण", "date": when.astimezone(zone).date().isoformat(),
                                "maximum_local": when.astimezone(zone).strftime("%H:%M"), "node_distance_deg": round(dist, 2),
                                "certainty": "sure" if dist <= limit_sure else "possible",
                                "note_hi": "भारत में दृश्यता और सूतक अलग से जाँचें; यहाँ केवल ग्रहण की संभावना और अधिकतम का अनुमानित समय है।",
                                "note_en": "Check visibility from India and sutak separately; this gives only the eclipse possibility and an approximate maximum."})
        e0, t = e1, t2
    return out
