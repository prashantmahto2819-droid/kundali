"""Birth-time sensitivity: how many minutes of clock error would change the Lagna sign, the Moon sign,
the Moon nakshatra (hence the dasha lord) or the navamsa Lagna.

A patri is only as good as the birth time. Lagna moves ~1 sign per 2 hours, the Moon ~1 nakshatra per
day, so a 5-minute error can flip the Lagna near a boundary while leaving the Moon untouched. The
numbers here let the app warn ("लग्न 4 मिनट में बदल जाएगा") and tell the user which results are robust.
Uses the fast analytic backend for the Moon (within ~0.01 deg of DE440s), Lagna is pure geometry."""
from __future__ import annotations

from datetime import timedelta

from .constants import SIGNS, SIGNS_HI
from .core import ascendant_tropical, ayanamsa, nakshatra_of, navamsa_sign, sign_of
from .ephemeris import AnalyticBackend, norm360
from .timeutil import delta_t, julian_day, local_to_utc, year_fraction

_BACKEND = AnalyticBackend()
ASC_DEG_PER_MIN = 0.25                  # ~360 deg per 24 h; refined below by actual recomputation
MAX_MIN = 180                           # search window each side (minutes)


def _state(date: str, time_hhmm: str, tz: str, lat: float, lon: float, offset_min: int) -> dict:
    utc = local_to_utc(date, time_hhmm, tz) + timedelta(minutes=offset_min)
    jd_ut = julian_day(utc)
    jd_tt = jd_ut + delta_t(year_fraction(utc)) / 86400.0
    ayan = ayanamsa(jd_tt)
    asc = norm360(ascendant_tropical(jd_ut, jd_tt, lat, lon) - ayan)
    moon = norm360(_BACKEND.positions(jd_tt)["Moon"] - ayan)
    return {"lagna_sign": sign_of(asc), "navamsa_lagna": navamsa_sign(asc), "moon_sign": sign_of(moon),
            "moon_nak": nakshatra_of(moon)["index"], "asc": asc, "moon": moon}


def _first_change(date, time_hhmm, tz, lat, lon, key, base, step, direction) -> int | None:
    """Minutes (positive) in the given direction until `key` differs from base, or None within MAX_MIN."""
    lo, hi = 0, None
    m = step
    while m <= MAX_MIN:
        if _state(date, time_hhmm, tz, lat, lon, direction * m)[key] != base:
            hi = m
            break
        lo = m
        m *= 2
    if hi is None:
        return None
    while hi - lo > 1:                   # bisect to the minute
        mid = (lo + hi) // 2
        if _state(date, time_hhmm, tz, lat, lon, direction * mid)[key] != base:
            hi = mid
        else:
            lo = mid
    return hi


def sensitivity(date: str, time_hhmm: str, tz: str, lat: float, lon: float) -> dict:
    base = _state(date, time_hhmm, tz, lat, lon, 0)
    out = {}
    for key, label, label_hi in (("lagna_sign", "Lagna sign", "लग्न राशि"), ("navamsa_lagna", "Navamsa Lagna", "नवांश लग्न"),
                                 ("moon_sign", "Moon sign", "चंद्र राशि"), ("moon_nak", "Moon nakshatra (dasha lord)", "चंद्र नक्षत्र (दशा स्वामी)")):
        earlier = _first_change(date, time_hhmm, tz, lat, lon, key, base[key], 1, -1)
        later = _first_change(date, time_hhmm, tz, lat, lon, key, base[key], 1, +1)
        margin = min(x for x in (earlier, later) if x is not None) if (earlier or later) else None
        out[key] = {"label": label, "label_hi": label_hi, "minutes_earlier": earlier, "minutes_later": later,
                    "margin_minutes": margin, "stable_within_5_min": margin is None or margin > 5,
                    "stable_within_15_min": margin is None or margin > 15}
    tight = [v for v in out.values() if v["margin_minutes"] is not None and v["margin_minutes"] <= 10]
    warnings = []
    for v in tight:
        side = "later" if v["minutes_later"] == v["margin_minutes"] else "earlier"
        side_hi = "बाद" if side == "later" else "पहले"
        warnings.append({"code": "birth_time_sensitive", "what": v["label"], "minutes": v["margin_minutes"],
                         "text_hi": f"{v['label_hi']} जन्म-समय से केवल {v['margin_minutes']} मिनट {side_hi} बदल जाती है। "
                                    "अगर जन्म-समय पक्का नहीं है तो इस पर आधारित फल सावधानी से पढ़ें।",
                         "text_en": f"The {v['label']} changes only {v['margin_minutes']} minutes {side} than the given birth time. "
                                    "If the time is not exact, read results based on it with care."})
    return {"items": out, "warnings": warnings,
            "lagna_sign_name": SIGNS[base["lagna_sign"]], "lagna_sign_name_hi": SIGNS_HI[base["lagna_sign"]],
            "note_hi": "जन्म-समय की संवेदनशीलता: बताया गया है कि घड़ी में कितने मिनट की चूक से लग्न, नवांश लग्न, चंद्र राशि या नक्षत्र बदल जाता है। "
                       "खाली का मतलब है 3 घंटे के भीतर नहीं बदलता।",
            "note_en": "Birth-time sensitivity: how many minutes of clock error would change the Lagna, navamsa Lagna, Moon sign or nakshatra. "
                       "Blank means no change within 3 hours."}
