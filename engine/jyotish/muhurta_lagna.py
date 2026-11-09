"""Lagna table for a day and lagna shuddhi for a muhurta (marriage and other samskaras) v1.

The twelve ascendant windows of a local calendar day are found by scanning the sidereal ascendant and bisecting the
sign changes. For each window a chart is cast at its middle (analytic Sun..Saturn + mean nodes, whole-sign houses)
and the common almanac rules for a muhurta lagna are checked:
  - 7th house empty (Jamitra shuddhi), 8th house empty (Ashtama shuddhi), no malefic in the 12th, lagna lord not in 6/8/12
  - Moon not in 1, 6, 8 or 12; Mars not in the 8th; Venus not in the 6th (marriage)
  - benefic (Jupiter/Venus/Mercury) in a kendra or trikona strengthens; a malefic in the lagna weakens
  - fixed and dual signs preferred for marriage; the lagna should not be 6/8/12 from the Moon sign of the bride or groom
    when those are given (also 8th from either is avoided)
Each window gets a score 0-100, the doshas found, and a verdict. Almanac level and draft; the final muhurta is a
pandit's call (Abhijit, Godhuli and the day's choghadiya are reported alongside).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .constants import PLANETS_HI, SIGN_LORDS, SIGNS, SIGNS_HI
from .core import ascendant_tropical, ayanamsa, nakshatra_of, sign_of
from .constants import NAKSHATRAS_HI
from .ephemeris import AnalyticBackend, mean_node, norm360
from .muhurta import day_table
from .timeutil import delta_t, julian_day, year_fraction

_B = AnalyticBackend()
BENEFIC = ("Jupiter", "Venus", "Mercury")
MALEFIC = ("Sun", "Mars", "Saturn", "Rahu", "Ketu")
KENDRA_TRIKONA = {1, 4, 5, 7, 9, 10}
FIXED = {1, 4, 7, 10}
DUAL = {2, 5, 8, 11}


def _jd(dt: datetime) -> tuple[float, float]:
    u = dt.astimezone(timezone.utc)
    jd_ut = julian_day(u)
    return jd_ut, jd_ut + delta_t(year_fraction(u)) / 86400.0


def asc_sidereal(dt: datetime, lat: float, lon: float) -> float:
    jd_ut, jd_tt = _jd(dt)
    return norm360(ascendant_tropical(jd_ut, jd_tt, lat, lon) - ayanamsa(jd_tt))


def lagna_table(day: date, lat: float, lon: float, tz: str) -> list[dict]:
    """Ascendant sign windows covering the local calendar day."""
    zone = ZoneInfo(tz)
    start = datetime(day.year, day.month, day.day, tzinfo=zone)
    end = start + timedelta(days=1)
    step = timedelta(minutes=6)
    t = start
    cur = sign_of(asc_sidereal(t, lat, lon))
    win_start = start
    out = []
    while t < end:
        t2 = min(t + step, end)
        s2 = sign_of(asc_sidereal(t2, lat, lon))
        if s2 != cur:
            lo, hi = t, t2
            for _ in range(16):
                mid = lo + (hi - lo) / 2
                if sign_of(asc_sidereal(mid, lat, lon)) == cur:
                    lo = mid
                else:
                    hi = mid
            out.append({"sign": cur, "start": win_start, "end": hi})
            win_start, cur = hi, s2
        t = t2
    out.append({"sign": cur, "start": win_start, "end": end})
    return out


def _chart_at(dt: datetime, lat: float, lon: float) -> dict:
    jd_ut, jd_tt = _jd(dt)
    ayan = ayanamsa(jd_tt)
    pos = _B.positions(jd_tt)
    pos["Rahu"] = mean_node(jd_tt)
    pos["Ketu"] = norm360(pos["Rahu"] + 180.0)
    lons = {k: norm360(v - ayan) for k, v in pos.items()}
    asc = norm360(ascendant_tropical(jd_ut, jd_tt, lat, lon) - ayan)
    lagna = sign_of(asc)
    houses = {k: (sign_of(v) - lagna) % 12 + 1 for k, v in lons.items()}
    return {"asc": asc, "lagna": lagna, "lons": lons, "houses": houses}


def judge(ch: dict, activity: str = "marriage", groom_moon_sign: int | None = None, bride_moon_sign: int | None = None) -> dict:
    H = ch["houses"]; lagna = ch["lagna"]
    score, dosha, good = 70, [], []
    occupants = lambda h: [p for p, hh in H.items() if hh == h]
    if occupants(7):
        score -= 25; dosha.append({"key": "jamitra", "hi": f"सप्तम भाव में ग्रह ({', '.join(PLANETS_HI[p] for p in occupants(7))}) — जामित्र दोष", "en": f"Planet(s) in the 7th ({', '.join(occupants(7))}) — Jamitra dosha"})
    if occupants(8):
        score -= 25; dosha.append({"key": "ashtama", "hi": f"अष्टम भाव में ग्रह ({', '.join(PLANETS_HI[p] for p in occupants(8))})", "en": f"Planet(s) in the 8th ({', '.join(occupants(8))})"})
    m12 = [p for p in occupants(12) if p in MALEFIC]
    if m12:
        score -= 10; dosha.append({"key": "malefic_12", "hi": f"द्वादश में पाप ग्रह ({', '.join(PLANETS_HI[p] for p in m12)})", "en": f"Malefic in the 12th ({', '.join(m12)})"})
    lord = SIGN_LORDS[lagna]
    if H.get(lord) in (6, 8, 12):
        score -= 15; dosha.append({"key": "lord_dusthana", "hi": f"लग्नेश {PLANETS_HI[lord]} {H[lord]}वें भाव में", "en": f"Lagna lord {lord} in house {H[lord]}"})
    if H["Moon"] in (1, 6, 8, 12):
        score -= 15; dosha.append({"key": "moon", "hi": f"चंद्र {H['Moon']}वें भाव में", "en": f"Moon in house {H['Moon']}"})
    if activity == "marriage":
        if H["Mars"] == 8:
            score -= 15; dosha.append({"key": "mars_8", "hi": "मंगल अष्टम में", "en": "Mars in the 8th"})
        if H["Venus"] == 6:
            score -= 15; dosha.append({"key": "venus_6", "hi": "शुक्र षष्ठ में", "en": "Venus in the 6th"})
        if lagna in FIXED or lagna in DUAL:
            score += 5; good.append({"hi": "स्थिर/द्विस्वभाव लग्न", "en": "Fixed or dual lagna"})
        else:
            score -= 5; dosha.append({"key": "movable", "hi": "चर लग्न (विवाह में कम वांछित)", "en": "Movable lagna (less preferred for marriage)"})
    ml = [p for p in occupants(1) if p in MALEFIC]
    if ml:
        score -= 10; dosha.append({"key": "malefic_lagna", "hi": f"लग्न में पाप ग्रह ({', '.join(PLANETS_HI[p] for p in ml)})", "en": f"Malefic in the lagna ({', '.join(ml)})"})
    bk = [p for p in BENEFIC if H[p] in KENDRA_TRIKONA]
    if bk:
        score += 5 * min(2, len(bk)); good.append({"hi": f"शुभ ग्रह केंद्र/त्रिकोण में ({', '.join(PLANETS_HI[p] for p in bk)})", "en": f"Benefic in kendra/trikona ({', '.join(bk)})"})
    for who, sgn, hi_name in (("groom", groom_moon_sign, "वर"), ("bride", bride_moon_sign, "वधू")):
        if sgn is not None:
            rel = (lagna - sgn) % 12 + 1
            if rel in (6, 8, 12):
                score -= 15; dosha.append({"key": f"{who}_rashi", "hi": f"लग्न {hi_name} की चंद्र राशि से {rel}वाँ", "en": f"Lagna is the {rel}th from the {who}'s Moon sign"})
    score = max(0, min(100, score))
    verdict = "shubh" if score >= 70 and not any(d["key"] in ("jamitra", "ashtama") for d in dosha) else "madhyam" if score >= 50 else "varjit"
    return {"score": score, "doshas": dosha, "strengths": good, "verdict": verdict,
            "verdict_hi": {"shubh": "शुभ", "madhyam": "मध्यम", "varjit": "वर्जित"}[verdict], "verdict_en": {"shubh": "good", "madhyam": "middling", "varjit": "avoid"}[verdict]}


def lagna_muhurta(day_iso: str, lat: float, lon: float, tz: str, activity: str = "marriage",
                  groom_moon_sign: int | None = None, bride_moon_sign: int | None = None,
                  groom_nakshatra: int | None = None, bride_nakshatra: int | None = None) -> dict:
    day = date.fromisoformat(day_iso)
    zone = ZoneInfo(tz)
    wins = lagna_table(day, lat, lon, tz)
    rows = []
    for w in wins:
        mid = w["start"] + (w["end"] - w["start"]) / 2
        ch = _chart_at(mid, lat, lon)
        j = judge(ch, activity, groom_moon_sign, bride_moon_sign)
        rows.append({"sign": w["sign"], "sign_name": SIGNS[w["sign"]], "sign_name_hi": SIGNS_HI[w["sign"]], "start": w["start"].astimezone(zone).strftime("%H:%M"), "end": w["end"].astimezone(zone).strftime("%H:%M"),
                     "night": not (6 <= w["start"].astimezone(zone).hour < 18) and not (6 <= (w["end"].astimezone(zone) - timedelta(minutes=1)).hour < 18),
                     "planets_in_houses": {h: [PLANETS_HI[p] for p in ch["houses"] if ch["houses"][p] == h] for h in range(1, 13) if any(v == h for v in ch["houses"].values())},
                     **j})
    dt = day_table(datetime(day.year, day.month, day.day, 12, 0, tzinfo=zone), lat, lon, tz)
    # chandrabala for bride and groom: the day's Moon sign (at noon) counted from their Moon sign; 6, 8, 12 unfavourable
    noon_ch = _chart_at(datetime(day.year, day.month, day.day, 12, 0, tzinfo=zone), lat, lon)
    day_moon = sign_of(noon_ch["lons"]["Moon"])
    chandrabala = {}
    for who, sgn in (("groom", groom_moon_sign), ("bride", bride_moon_sign)):
        if sgn is not None:
            cnt = (day_moon - sgn) % 12 + 1
            chandrabala[who] = {"count": cnt, "ok": cnt not in (6, 8, 12), "day_moon_sign_hi": SIGNS_HI[day_moon], "day_moon_sign": SIGNS[day_moon]}
    # tarabala: the day's nakshatra (at noon) counted from the birth star; taras 3 (vipat), 5 (pratyak), 7 (naidhana) unfavourable
    day_nak = nakshatra_of(noon_ch["lons"]["Moon"])["index"]
    TARA_HI = ["जन्म", "संपत्", "विपत्", "क्षेम", "प्रत्यरि", "साधक", "वध", "मित्र", "अति-मित्र"]
    TARA_EN = ["Janma", "Sampat", "Vipat", "Kshema", "Pratyari", "Sadhaka", "Vadha", "Mitra", "Ati-mitra"]
    tarabala = {}
    for who, nk in (("groom", groom_nakshatra), ("bride", bride_nakshatra)):
        if nk is not None:
            cnt = (day_nak - nk) % 27 + 1
            tara = (cnt - 1) % 9
            tarabala[who] = {"count": cnt, "tara": tara + 1, "tara_hi": TARA_HI[tara], "tara_en": TARA_EN[tara], "ok": (tara + 1) not in (3, 5, 7),
                             "day_nakshatra_hi": NAKSHATRAS_HI[day_nak]}
    best = sorted([r for r in rows if r["verdict"] != "varjit"], key=lambda r: -r["score"])[:3]
    return {"date": day_iso, "activity": activity, "lagnas": rows, "best": best, "abhijit": dt.get("abhijit"), "rahu_kaal": dt.get("rahu_kaal"), "chandrabala": chandrabala, "tarabala": tarabala,
            "good_choghadiya": [{"name": c["name"], "start": c["start"], "end": c["end"]} for c in dt.get("choghadiya_day", []) + dt.get("choghadiya_night", []) if c.get("nature") == "good"],
            "review_status": "draft",
            "note_hi": "लग्न-शुद्धि (पंचांग-स्तर): सप्तम-अष्टम रिक्त, द्वादश में पाप ग्रह नहीं, लग्नेश 6/8/12 में नहीं, चंद्र 1/6/8/12 में नहीं; विवाह में मंगल अष्टम व शुक्र षष्ठ वर्जित, स्थिर/द्विस्वभाव लग्न वांछित, वर-वधू की राशि से 6/8/12 लग्न वर्जित। "
                       "राहु काल, भद्रा और चौघड़िया साथ देखिए। अंतिम मुहूर्त पंडित तय करें।",
            "note_en": "Lagna shuddhi (almanac level): 7th and 8th empty, no malefic in the 12th, lagna lord not in 6/8/12, Moon not in 1/6/8/12; for marriage Mars in the 8th and Venus in the 6th are avoided, fixed/dual lagnas preferred, lagna 6/8/12 from the bride's or groom's Moon sign avoided. "
                       "Check Rahu kaal, Bhadra and choghadiya alongside; a pandit fixes the final muhurta."}
