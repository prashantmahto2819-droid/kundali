"""Birth-time rectification aid v1.

Given a birth time and a window (+-N minutes), splits the window into stretches inside which the Lagna sign,
navamsa Lagna and Moon nakshatra all stay the same (the "signature" of a chart), and lists each stretch with
its signature. Optionally scores every stretch against known life events using the classical dasha check:
at the event's year the running mahadasha/antardasha lords should be connected (by ownership or occupation)
to the houses that rule the event (marriage 7/2/11, child 5/2/11, job 10/6/2/11, property 4/11, travel 9/12/3).
This narrows the time; it does not prove it. The Moon is taken from the fast analytic backend (within ~0.01 deg).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .constants import SIGN_LORDS, SIGNS, SIGNS_HI, NAKSHATRAS, NAKSHATRAS_HI, PLANETS_HI
from .core import ascendant_tropical, ayanamsa, nakshatra_of, navamsa_sign, sign_of
from .dasha import current_periods, vimshottari
from .ephemeris import AnalyticBackend, norm360
from .timeutil import delta_t, julian_day, local_to_utc, year_fraction

_B = AnalyticBackend()
EVENT_HOUSES = {"marriage": [7, 2, 11], "child": [5, 2, 11], "job": [10, 6, 2, 11], "property": [4, 11], "travel": [9, 12, 3], "education": [4, 5, 9]}
EVENT_HI = {"marriage": "विवाह", "child": "संतान", "job": "नौकरी/कार्य", "property": "संपत्ति", "travel": "विदेश/यात्रा", "education": "शिक्षा"}


def _state(date, time_hhmm, tz, lat, lon, offset_min):
    utc = local_to_utc(date, time_hhmm, tz) + timedelta(minutes=offset_min)
    jd_ut = julian_day(utc)
    jd_tt = jd_ut + delta_t(year_fraction(utc)) / 86400.0
    ayan = ayanamsa(jd_tt)
    asc = norm360(ascendant_tropical(jd_ut, jd_tt, lat, lon) - ayan)
    pos = _B.positions(jd_tt)
    moon = norm360(pos["Moon"] - ayan)
    sid = {k: norm360(v - ayan) for k, v in pos.items()}
    return {"utc": utc, "asc": asc, "moon": moon, "lagna": sign_of(asc), "nav": navamsa_sign(asc), "nak": nakshatra_of(moon)["index"], "sid": sid}


def _signature(st):
    return (st["lagna"], st["nav"], st["nak"])


def _event_score(st, date, events, lagna_sign):
    """How many events are 'explained' by the running dasha lords at that time (0..len(events))."""
    if not events:
        return None, []
    dasha = vimshottari(st["moon"], st["utc"], max_level=2)
    # houses a planet connects to: the house it occupies and the houses it owns (whole sign from this Lagna)
    houses = {}
    for name, lon in st["sid"].items():
        s = sign_of(lon)
        occ = (s - lagna_sign) % 12 + 1
        owns = [h for h in range(1, 13) if SIGN_LORDS[(lagna_sign + h - 1) % 12] == name]
        houses[name] = {occ, *owns}
    hits, detail = 0, []
    for ev in events:
        when = datetime(int(ev["year"]), int(ev.get("month", 7)), 1, tzinfo=timezone.utc)
        chain = current_periods(dasha, when)
        lords = [c["lord"] for c in chain[:2]]
        want = set(EVENT_HOUSES.get(ev["type"], []))
        ok = any(houses.get(l, set()) & want for l in lords)
        hits += ok
        detail.append({"type": ev["type"], "type_hi": EVENT_HI.get(ev["type"], ev["type"]), "year": int(ev["year"]), "lords": lords,
                       "lords_hi": [PLANETS_HI[l] for l in lords], "supports": ok})
    return hits, detail


def rectify(date: str, time_hhmm: str, tz: str, lat: float, lon: float, range_min: int = 120, step_min: int = 2,
            events: list[dict] | None = None) -> dict:
    range_min = max(5, min(720, int(range_min)))
    step_min = max(1, min(10, int(step_min)))
    offsets = list(range(-range_min, range_min + 1, step_min))
    states = [(o, _state(date, time_hhmm, tz, lat, lon, o)) for o in offsets]
    # group consecutive offsets with the same signature into windows
    windows = []
    for o, st in states:
        sig = _signature(st)
        if windows and windows[-1]["sig"] == sig:
            windows[-1]["end_off"] = o
            windows[-1]["states"].append(st)
        else:
            windows.append({"sig": sig, "start_off": o, "end_off": o, "states": [st]})
    base = local_to_utc(date, time_hhmm, tz)
    zone = ZoneInfo(tz)
    out = []
    for w in windows:
        mid = w["states"][len(w["states"]) // 2]
        lagna, nav, nak = w["sig"]
        score, detail = _event_score(mid, date, events or [], lagna)
        t0 = (base + timedelta(minutes=w["start_off"])).astimezone(zone)
        t1 = (base + timedelta(minutes=w["end_off"])).astimezone(zone)
        out.append({"from_offset_min": w["start_off"], "to_offset_min": w["end_off"], "contains_given_time": w["start_off"] <= 0 <= w["end_off"],
                    "from": t0.strftime("%H:%M"), "to": t1.strftime("%H:%M"),
                    "lagna": SIGNS[lagna], "lagna_hi": SIGNS_HI[lagna], "navamsa_lagna": SIGNS[nav], "navamsa_lagna_hi": SIGNS_HI[nav],
                    "moon_nakshatra": NAKSHATRAS[nak], "moon_nakshatra_hi": NAKSHATRAS_HI[nak],
                    "event_hits": score, "event_detail": detail})
    ranked = sorted(out, key=lambda w: (-(w["event_hits"] or 0), abs(w["from_offset_min"] + w["to_offset_min"]) / 2)) if events else out
    return {"given_time": time_hhmm, "range_min": range_min, "step_min": step_min, "windows": out, "ranked": ranked[:5] if events else [],
            "events": events or [], "review_status": "draft",
            "note_hi": "जन्म-समय संशोधन सहायक: दिए समय के आस-पास की वे अवधियाँ जिनमें लग्न, नवांश-लग्न और चंद्र-नक्षत्र नहीं बदलते। "
                       "घटनाएँ दी हों तो हर अवधि को इस परंपरागत जाँच से अंक मिलते हैं कि घटना के वर्ष की दशा-अंतर्दशा के स्वामी उस घटना के भावों से जुड़े हों। "
                       "यह समय को संकुचित करने में मदद करता है; यह प्रमाण नहीं है।",
            "note_en": "Birth-time rectification aid: stretches around the given time within which the Lagna, navamsa Lagna and Moon nakshatra do not change. "
                       "With events, each stretch is scored by the classical check that the dasha/antardasha lords running in the event's year connect to that event's houses. "
                       "It narrows the time; it does not prove it."}
