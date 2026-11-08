"""Panchang elements at a given instant (tithi, vara, nakshatra, yoga, karana)."""
from __future__ import annotations

from datetime import datetime

from .constants import (KARANA_REPEATING, TITHI_NAMES, VARA, VARA_HI, YOGA_NAMES)
from .core import nakshatra_of


def tithi_info(sun_sid: float, moon_sid: float) -> dict:
    diff = (moon_sid - sun_sid) % 360.0
    n = int(diff // 12.0)  # 0..29
    paksha = "Shukla" if n < 15 else "Krishna"
    pos = n % 15
    if n == 14:
        name = "Purnima"
    elif n == 29:
        name = "Amavasya"
    else:
        name = TITHI_NAMES[pos]
    return {"number": n + 1, "paksha": paksha, "name": name,
            "fraction_elapsed": (diff % 12.0) / 12.0}


def karana_info(sun_sid: float, moon_sid: float) -> dict:
    diff = (moon_sid - sun_sid) % 360.0
    k = int(diff // 6.0)  # 0..59
    if k == 0:
        name = "Kimstughna"
    elif k <= 56:
        name = KARANA_REPEATING[(k - 1) % 7]
    else:
        name = ["Shakuni", "Chatushpada", "Naga"][k - 57]
    return {"number": k + 1, "name": name}


def yoga_info(sun_sid: float, moon_sid: float) -> dict:
    total = (sun_sid + moon_sid) % 360.0
    idx = int(total * 27 // 360) % 27
    return {"number": idx + 1, "name": YOGA_NAMES[idx]}


def panchang(sun_sid: float, moon_sid: float, local_dt: datetime) -> dict:
    wd = (local_dt.weekday() + 1) % 7  # Python Mon=0 -> Sunday=0
    nak = nakshatra_of(moon_sid)
    return {
        "vara": {"index": wd, "name": VARA[wd], "name_hi": VARA_HI[wd]},
        "tithi": tithi_info(sun_sid, moon_sid),
        "nakshatra": {"name": nak["name"], "name_hi": nak["name_hi"], "pada": nak["pada"]},
        "yoga": yoga_info(sun_sid, moon_sid),
        "karana": karana_info(sun_sid, moon_sid),
        "note": "Vara uses the civil weekday of the local date (sunrise-based vara comes with the sunrise module).",
    }
