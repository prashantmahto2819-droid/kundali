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
                                "maximum_local": when.astimezone(zone).strftime("%H:%M"), "maximum_utc": when.astimezone(timezone.utc).isoformat(timespec="minutes"), "node_distance_deg": round(dist, 2),
                                "certainty": "sure" if dist <= limit_sure else "possible",
                                "note_hi": "भारत में दृश्यता और सूतक अलग से जाँचें; यहाँ केवल ग्रहण की संभावना और अधिकतम का अनुमानित समय है।",
                                "note_en": "Check visibility from India and sutak separately; this gives only the eclipse possibility and an approximate maximum."})
        e0, t = e1, t2
    return out


# ---------------------------------------------------------------- local eclipse circumstances and sutak
def _equatorial(lon_deg: float, lat_deg: float, jd_tt: float) -> tuple[float, float]:
    import math
    from .core import obliquity_deg
    lam, beta, eps = math.radians(lon_deg), math.radians(lat_deg), math.radians(obliquity_deg(jd_tt))
    ra = math.atan2(math.sin(lam) * math.cos(eps) - math.tan(beta) * math.sin(eps), math.cos(lam))
    dec = math.asin(math.sin(beta) * math.cos(eps) + math.cos(beta) * math.sin(eps) * math.sin(lam))
    return ra, dec


def _topocentric(ra: float, dec: float, parallax_deg: float, jd_ut: float, lat: float, lon_east: float) -> tuple[float, float, float]:
    """Apply diurnal parallax (Meeus ch. 40) → topocentric RA, Dec, and altitude (deg)."""
    import math
    from .core import gmst_deg
    phi = math.radians(lat)
    u = math.atan(0.99664719 * math.tan(phi))
    rho_sin = 0.99664719 * math.sin(u); rho_cos = math.cos(u)
    pi = math.radians(parallax_deg)
    h = math.radians((gmst_deg(jd_ut) + lon_east) % 360.0) - ra
    d_ra = math.atan2(-rho_cos * math.sin(pi) * math.sin(h), math.cos(dec) - rho_cos * math.sin(pi) * math.cos(h))
    ra_t = ra + d_ra
    dec_t = math.atan2((math.sin(dec) - rho_sin * math.sin(pi)) * math.cos(d_ra), math.cos(dec) - rho_cos * math.sin(pi) * math.cos(h))
    h_t = h - d_ra
    alt = math.degrees(math.asin(math.sin(phi) * math.sin(dec_t) + math.cos(phi) * math.cos(dec_t) * math.cos(h_t)))
    return ra_t, dec_t, alt


def _sep(ra1, dec1, ra2, dec2) -> float:
    import math
    c = math.sin(dec1) * math.sin(dec2) + math.cos(dec1) * math.cos(dec2) * math.cos(ra1 - ra2)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def eclipse_local(ec: dict, lat: float, lon: float, tz: str) -> dict:
    """Contact times, magnitude and visibility of one eclipse (from eclipses()) at a place, plus the sutak window.

    Solar: topocentric Sun–Moon separation against the sum of the semidiameters (first/last contact), maximum = minimum separation,
    magnitude = (s_sun + s_moon − sep) / (2 s_sun). Lunar: geocentric Moon against Earth's umbra and penumbra (partial / total / penumbral).
    Visible when the eclipsed body is above the horizon for some part of the eclipse. Sutak (tradition): solar — four prahar (~12 h)
    before first contact; lunar — three prahar (~9 h) before the Moon enters the umbra (penumbral eclipses carry no sutak); both end at
    the last contact. Sutak applies only where the eclipse is visible.
    """
    import math
    from .moon import moon_latitude, moon_parallax_deg
    zone = ZoneInfo(tz)
    if ec.get("maximum_utc"):
        centre = datetime.fromisoformat(ec["maximum_utc"]).astimezone(timezone.utc)
    else:                                              # legacy rows: local maximum in Asia/Kolkata
        date_local = datetime.fromisoformat(ec["date"])
        hh, mm = (int(x) for x in ec["maximum_local"].split(":"))
        centre = datetime(date_local.year, date_local.month, date_local.day, hh, mm, tzinfo=ZoneInfo("Asia/Kolkata")).astimezone(timezone.utc)
    solar = ec["kind"] == "solar"
    S_SUN = 0.2666
    rows = []
    t = centre - timedelta(hours=4)
    while t <= centre + timedelta(hours=4):
        u = t.astimezone(timezone.utc)
        jd_ut = julian_day(u); jd_tt = jd_ut + delta_t(year_fraction(u)) / 86400.0
        pos = _B.positions(jd_tt)
        pi_m = moon_parallax_deg(jd_tt)
        s_moon = 0.2725 * pi_m
        ra_m, dec_m = _equatorial(pos["Moon"], moon_latitude(jd_tt), jd_tt)
        ra_s, dec_s = _equatorial(pos["Sun"], 0.0, jd_tt)
        if solar:
            ra_mt, dec_mt, alt_m = _topocentric(ra_m, dec_m, pi_m, jd_ut, lat, lon)
            _, _, alt_s = _topocentric(ra_s, dec_s, 0.0024, jd_ut, lat, lon)
            sep = _sep(ra_mt, dec_mt, ra_s, dec_s)
            limit = S_SUN + s_moon
            rows.append((t, sep, limit, alt_s, (S_SUN + s_moon - sep) / (2 * S_SUN)))
        else:
            # anti-Sun point and shadow radii (Danjon-style 1.02 enlargement)
            ra_a, dec_a = _equatorial((pos["Sun"] + 180.0) % 360.0, 0.0, jd_tt)
            sep = _sep(ra_m, dec_m, ra_a, dec_a)
            umbra = 1.02 * (0.99834 * pi_m - S_SUN + 0.0024)
            penumbra = 1.02 * (0.99834 * pi_m + S_SUN + 0.0024)
            _, _, alt_m = _topocentric(ra_m, dec_m, pi_m, jd_ut, lat, lon)
            rows.append((t, sep, (umbra, penumbra, s_moon), alt_m, (umbra + s_moon - sep) / (2 * s_moon)))
        t += timedelta(minutes=1)
    fmt = lambda d: d.astimezone(zone).strftime("%H:%M")
    out = {"kind": ec["kind"], "kind_hi": ec["kind_hi"], "date": centre.astimezone(zone).date().isoformat(), "place": {"lat": lat, "lon": lon, "tz": tz}}
    if solar:
        inside = [r for r in rows if r[1] < r[2]]
        if not inside:
            return {**out, "occurs_here": False, "visible": False, "text_hi": "इस स्थान पर यह सूर्य ग्रहण नहीं लगता (चंद्र की छाया यहाँ से नहीं गुज़रती)।", "text_en": "This solar eclipse does not occur at this place."}
        mx = min(inside, key=lambda r: r[1])
        vis = [r for r in inside if r[3] > -0.3]
        out.update({"occurs_here": True, "first_contact": fmt(inside[0][0]), "maximum": fmt(mx[0]), "last_contact": fmt(inside[-1][0]), "magnitude": round(max(0.0, mx[4]), 3),
                    "visible": bool(vis), "visible_from": fmt(vis[0][0]) if vis else None, "visible_until": fmt(vis[-1][0]) if vis else None,
                    "sun_altitude_at_max": round(mx[3], 1), "type": "total" if mx[4] >= 1.0 and mx[1] < abs(0.2725 * moon_parallax_deg(julian_day(mx[0].astimezone(timezone.utc))) - S_SUN) else "partial"})
        if vis:
            start = inside[0][0]; end = inside[-1][0]
            out["sutak"] = {"start": (start - timedelta(hours=12)).astimezone(zone).strftime("%d-%m %H:%M"), "end": fmt(end),
                            "text_hi": f"सूतक ग्रहण-स्पर्श से 12 घंटे (4 प्रहर) पहले {(start - timedelta(hours=12)).astimezone(zone).strftime('%d-%m %H:%M')} से मोक्ष {fmt(end)} तक; बच्चे, वृद्ध, रोगी के लिए परंपरा में छूट।",
                            "text_en": f"Sutak from 12 h (4 prahar) before first contact, {(start - timedelta(hours=12)).astimezone(zone).strftime('%d-%m %H:%M')}, to the last contact {fmt(end)}; tradition exempts children, the old and the ill."}
            out["text_hi"] = f"यहाँ {'खग्रास' if out['type'] == 'total' else 'खंडग्रास'} सूर्य ग्रहण दिखेगा: स्पर्श {out['first_contact']}, मध्य {out['maximum']}, मोक्ष {out['last_contact']}; दृश्य {out['visible_from']}–{out['visible_until']} (सूर्य क्षितिज के ऊपर), ग्रास {out['magnitude']}।"
            out["text_en"] = f"A {out['type']} solar eclipse is visible here: first contact {out['first_contact']}, maximum {out['maximum']}, last contact {out['last_contact']}; visible {out['visible_from']}–{out['visible_until']}, magnitude {out['magnitude']}."
        else:
            out["text_hi"] = f"यह सूर्य ग्रहण यहाँ सूर्यास्त के बाद/सूर्योदय से पहले होता है ({out['first_contact']}–{out['last_contact']}), अतः यहाँ दिखाई नहीं देगा और सूतक नहीं लगता।"
            out["text_en"] = f"This solar eclipse happens here while the Sun is below the horizon ({out['first_contact']}–{out['last_contact']}); not visible, so no sutak."
        return out
    # lunar
    pen = [r for r in rows if r[1] < r[2][1] + r[2][2]]
    umb = [r for r in rows if r[1] < r[2][0] + r[2][2]]
    tot = [r for r in rows if r[1] < r[2][0] - r[2][2]]
    if not pen:
        return {**out, "occurs_here": False, "visible": False, "text_hi": "इस तिथि को चंद्र ग्रहण की गणना नहीं बनी।", "text_en": "No lunar eclipse geometry on this date."}
    mx = min(pen, key=lambda r: r[1])
    kind = "total" if tot else "partial" if umb else "penumbral"
    span = umb if umb else pen
    vis = [r for r in span if r[3] > -0.3]
    out.update({"occurs_here": True, "type": kind, "type_hi": {"total": "खग्रास", "partial": "खंडग्रास", "penumbral": "उपच्छाया (मांद्य)"}[kind],
                "penumbral_start": fmt(pen[0][0]), "penumbral_end": fmt(pen[-1][0]), "umbral_start": fmt(umb[0][0]) if umb else None, "umbral_end": fmt(umb[-1][0]) if umb else None,
                "total_start": fmt(tot[0][0]) if tot else None, "total_end": fmt(tot[-1][0]) if tot else None, "maximum": fmt(mx[0]), "magnitude": round(max(0.0, mx[4]), 3),
                "visible": bool(vis), "visible_from": fmt(vis[0][0]) if vis else None, "visible_until": fmt(vis[-1][0]) if vis else None, "moon_altitude_at_max": round(mx[3], 1)})
    if kind == "penumbral":
        out["text_hi"] = f"उपच्छाया चंद्र ग्रहण ({out['penumbral_start']}–{out['penumbral_end']}): चंद्रमा केवल मांद्य छाया में, आँख से लगभग अदृश्य; परंपरा में इसका सूतक नहीं माना जाता।"
        out["text_en"] = f"Penumbral lunar eclipse ({out['penumbral_start']}–{out['penumbral_end']}): the Moon only dims slightly; tradition observes no sutak."
    elif vis:
        start = umb[0][0]; end = umb[-1][0]
        out["sutak"] = {"start": (start - timedelta(hours=9)).astimezone(zone).strftime("%d-%m %H:%M"), "end": fmt(end),
                        "text_hi": f"सूतक स्पर्श से 9 घंटे (3 प्रहर) पहले {(start - timedelta(hours=9)).astimezone(zone).strftime('%d-%m %H:%M')} से मोक्ष {fmt(end)} तक।",
                        "text_en": f"Sutak from 9 h (3 prahar) before the umbral contact, {(start - timedelta(hours=9)).astimezone(zone).strftime('%d-%m %H:%M')}, to the last umbral contact {fmt(end)}."}
        out["text_hi"] = f"यहाँ {out['type_hi']} चंद्र ग्रहण दिखेगा: स्पर्श {out['umbral_start']}, मध्य {out['maximum']}, मोक्ष {out['umbral_end']}" + (f" (पूर्ण {out['total_start']}–{out['total_end']})" if tot else "") + f"; दृश्य {out['visible_from']}–{out['visible_until']}, ग्रास {out['magnitude']}।"
        out["text_en"] = f"A {kind} lunar eclipse is visible here: umbral contact {out['umbral_start']}, maximum {out['maximum']}, last contact {out['umbral_end']}" + (f" (totality {out['total_start']}–{out['total_end']})" if tot else "") + f"; visible {out['visible_from']}–{out['visible_until']}, magnitude {out['magnitude']}."
    else:
        out["text_hi"] = f"{out['type_hi']} चंद्र ग्रहण ({out['umbral_start']}–{out['umbral_end']}) यहाँ चंद्रोदय से पहले/चंद्रास्त के बाद होता है, अतः दिखाई नहीं देगा और सूतक नहीं लगता।"
        out["text_en"] = f"This {kind} lunar eclipse ({out['umbral_start']}–{out['umbral_end']}) happens while the Moon is below the horizon here; not visible, so no sutak."
    return out
