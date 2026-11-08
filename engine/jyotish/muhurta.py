"""Sunrise-based day divisions: vara, Rahu Kaal, Yamaganda, Gulika, Abhijit, Choghadiya."""
from __future__ import annotations

from datetime import datetime, timedelta

from .constants import VARA, VARA_HI
from .sun import sun_times

# weekday index: 0 = Sunday ... 6 = Saturday; value = which eighth of the day (1..8)
RAHU = {0: 8, 1: 2, 2: 7, 3: 5, 4: 6, 5: 4, 6: 3}
YAMA = {0: 5, 1: 4, 2: 3, 3: 2, 4: 1, 5: 7, 6: 6}
GULIKA = {0: 7, 1: 6, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1}

CHOG_SEQ = ["Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog"]
CHOG_DAY_START = {0: "Udveg", 1: "Amrit", 2: "Rog", 3: "Labh", 4: "Shubh", 5: "Chal", 6: "Kaal"}
CHOG_NIGHT_START = {0: "Shubh", 1: "Chal", 2: "Kaal", 3: "Udveg", 4: "Amrit", 5: "Rog", 6: "Labh"}
CHOG_NATURE = {"Amrit": "good", "Shubh": "good", "Labh": "good", "Chal": "neutral",
               "Udveg": "inauspicious", "Kaal": "inauspicious", "Rog": "inauspicious"}


def _fmt(d: datetime) -> str:
    return d.strftime("%H:%M")


def _slot(start: datetime, length: timedelta, index: int) -> dict:
    s = start + length * (index - 1)
    return {"start": _fmt(s), "end": _fmt(s + length)}


def _chog(start: datetime, length: timedelta, first: str) -> list[dict]:
    i0 = CHOG_SEQ.index(first)
    out = []
    for k in range(8):
        name = CHOG_SEQ[(i0 + k) % 7]
        s = start + length * k
        out.append({"name": name, "nature": CHOG_NATURE[name], "start": _fmt(s), "end": _fmt(s + length)})
    return out


def day_table(local_dt: datetime, lat: float, lon: float, tz: str) -> dict:
    """``local_dt`` is the aware local birth/query time. Vara follows the Vedic day:
    before sunrise the previous weekday still runs."""
    day = local_dt.date()
    today = sun_times(day, lat, lon, tz)
    centre = sun_times(day, lat, lon, tz, convention="centre")
    if today is None:
        return {"available": False, "reason": "Sun does not rise or set on this date at this latitude."}
    tomorrow = sun_times(day + timedelta(days=1), lat, lon, tz)
    yesterday = sun_times(day - timedelta(days=1), lat, lon, tz)

    before_sunrise = local_dt < today["sunrise"]
    if before_sunrise and yesterday:
        ref_day, sr, ss = day - timedelta(days=1), yesterday["sunrise"], yesterday["sunset"]
        next_sr = today["sunrise"]
    else:
        ref_day, sr, ss = day, today["sunrise"], today["sunset"]
        next_sr = tomorrow["sunrise"] if tomorrow else sr + timedelta(days=1)

    wd = (ref_day.weekday() + 1) % 7  # Sunday = 0
    day_len = ss - sr
    eighth = day_len / 8
    night_eighth = (next_sr - ss) / 8
    mid = sr + day_len / 2
    abhijit_half = day_len / 30  # 8th of 15 muhurtas, centred on local noon

    return {
        "available": True,
        "vedic_vara": {"index": wd, "name": VARA[wd], "name_hi": VARA_HI[wd],
                       "before_sunrise": before_sunrise},
        "sunrise": _fmt(today["sunrise"]), "sunset": _fmt(today["sunset"]),
        "sunrise_centre": _fmt(centre["sunrise"]) if centre else None, "sunset_centre": _fmt(centre["sunset"]) if centre else None,
        "day_length_hours": round(day_len.total_seconds() / 3600, 2),
        "rahu_kaal": _slot(sr, eighth, RAHU[wd]),
        "yamaganda": _slot(sr, eighth, YAMA[wd]),
        "gulika": _slot(sr, eighth, GULIKA[wd]),
        "abhijit": {"start": _fmt(mid - abhijit_half), "end": _fmt(mid + abhijit_half)},
        "choghadiya_day": _chog(sr, eighth, CHOG_DAY_START[wd]),
        "choghadiya_night": _chog(ss, night_eighth, CHOG_NIGHT_START[wd]),
        "note": "Times are local clock times for the ticked date; accuracy about +-1 minute (no altitude correction).",
    }
