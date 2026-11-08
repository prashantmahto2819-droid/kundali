"""Vimshottari dasha."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .constants import DASHA_ORDER, DASHA_YEARS
from .core import nakshatra_of

TOTAL_YEARS = 120


def _iso(d: datetime) -> str:
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sub_periods(lord: str, start: datetime, length_days: float, level: int, max_level: int):
    """Split a period into 9 sub-periods starting from its own lord."""
    out = []
    i0 = DASHA_ORDER.index(lord)
    cur = start
    for k in range(9):
        sub = DASHA_ORDER[(i0 + k) % 9]
        sub_days = length_days * DASHA_YEARS[sub] / TOTAL_YEARS
        end = cur + timedelta(days=sub_days)
        item = {"lord": sub, "start": _iso(cur), "end": _iso(end), "level": level}
        if level < max_level:
            item["children"] = _sub_periods(sub, cur, sub_days, level + 1, max_level)
        out.append(item)
        cur = end
    return out


def vimshottari(moon_sidereal: float, birth_utc: datetime, year_days: float = 365.25,
                max_level: int = 2, years: int = 120) -> dict:
    """Mahadasha list (with antardasha for level>=2) for ``years`` from birth.

    ``max_level``: 1 = mahadasha only, 2 = + antardasha, 3 = + pratyantardasha.
    ``year_days``: dasha year length. 365.25 (default), 365.2425 and 360 are all
    used by different schools; it is a user-facing setting.
    """
    nak = nakshatra_of(moon_sidereal)
    lord = nak["lord"]
    elapsed_fraction = nak["fraction"]
    first_days = DASHA_YEARS[lord] * year_days
    start = birth_utc - timedelta(days=elapsed_fraction * first_days)
    balance_years = (1 - elapsed_fraction) * DASHA_YEARS[lord]

    periods = []
    i0 = DASHA_ORDER.index(lord)
    cur = start
    horizon = birth_utc + timedelta(days=years * year_days)
    k = 0
    while cur < horizon and k < 18:
        md = DASHA_ORDER[(i0 + k) % 9]
        days = DASHA_YEARS[md] * year_days
        end = cur + timedelta(days=days)
        item = {"lord": md, "start": _iso(cur), "end": _iso(end), "level": 1}
        if max_level >= 2:
            item["children"] = _sub_periods(md, cur, days, 2, max_level)
        periods.append(item)
        cur = end
        k += 1
    return {"system": "vimshottari", "year_days": year_days,
            "birth_nakshatra_lord": lord, "balance_at_birth_years": balance_years,
            "mahadashas": periods}


def current_periods(dasha: dict, as_of: datetime) -> list[dict]:
    """Chain of running periods [MD, AD, PD...] at ``as_of`` (UTC)."""
    stamp = _iso(as_of)
    chain, level_list = [], dasha["mahadashas"]
    while level_list:
        hit = next((p for p in level_list if p["start"] <= stamp < p["end"]), None)
        if hit is None:
            break
        chain.append({"level": hit["level"], "lord": hit["lord"],
                      "start": hit["start"], "end": hit["end"]})
        level_list = hit.get("children", [])
    return chain
