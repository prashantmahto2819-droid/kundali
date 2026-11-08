"""Varshaphal (annual / solar-return chart): the chart for the moment the Sun returns to its
natal sidereal longitude. Muntha is the natal Lagna sign advanced one sign per completed year.

The return moment is found numerically with the same ephemeris backend used for the chart, so the
Sun in the returned chart equals the natal Sun by construction (to the solver tolerance).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import compute_chart, tajika
from .constants import SIGNS_HI
from .transit import positions_at

TOLERANCE_DEG = 1e-6


def _diff(a: float, b: float) -> float:
    return (a - b + 180.0) % 360.0 - 180.0


def solar_return_utc(natal_sun: float, birth_utc: datetime, year: int, backend, system: str = "lahiri") -> datetime:
    """UTC instant in `year` when the sidereal Sun is at `natal_sun` (secant/bisection hybrid)."""
    try:
        guess = birth_utc.replace(year=year)
    except ValueError:                       # born on 29 Feb
        guess = birth_utc.replace(year=year, day=28)
    lo, hi = guess - timedelta(days=3), guess + timedelta(days=3)
    f = lambda t: _diff(positions_at(t, backend, system)["Sun"]["longitude"], natal_sun)
    flo, fhi = f(lo), f(hi)
    if not (flo < 0 < fhi):
        raise ValueError("could not bracket the solar return")
    for _ in range(60):
        mid = lo + (hi - lo) / 2
        fm = f(mid)
        if abs(fm) < TOLERANCE_DEG:
            return mid
        if fm < 0:
            lo = mid
        else:
            hi = mid
    return lo + (hi - lo) / 2


def varshaphal(natal: dict, year: int, lat: float | None = None, lon: float | None = None,
               tz: str | None = None, backend=None) -> dict:
    from .ephemeris import get_backend
    backend = backend or get_backend()
    inp = natal["input"]
    birth_utc = datetime.strptime(natal["birth_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    birth_year = birth_utc.astimezone(ZoneInfo(inp["tz"])).year
    if year <= birth_year:
        raise ValueError("year must be after the birth year")
    natal_sun = next(p["longitude"] for p in natal["planets"] if p["name"] == "Sun")
    system = inp.get("ayanamsa", "lahiri")
    t = solar_return_utc(natal_sun, birth_utc, year, backend, system)
    use_tz = tz or inp["tz"]
    use_lat = inp["lat"] if lat is None else lat
    use_lon = inp["lon"] if lon is None else lon
    local = t.astimezone(ZoneInfo(use_tz))
    chart = compute_chart(local.strftime("%Y-%m-%d"), local.strftime("%H:%M:%S"), use_tz, use_lat, use_lon,
                          ayanamsa_system=system, backend=backend, as_of=t)
    age = year - birth_year
    muntha_sign = (natal["lagna"]["sign"] + age) % 12
    muntha_house = (muntha_sign - chart["lagna"]["sign"]) % 12 + 1
    sun_return = next(p["longitude"] for p in chart["planets"] if p["name"] == "Sun")
    before = positions_at(t - timedelta(days=0.5), backend, system)
    after = positions_at(t + timedelta(days=0.5), backend, system)
    speeds = {p: (after[p]["longitude"] - before[p]["longitude"] + 180.0) % 360.0 - 180.0 for p in before}
    taj = tajika.tajika(chart, natal["lagna"]["sign"], muntha_sign, speeds, t)
    return {
        "tajika": taj,
        "year": year, "age": age, "return_utc": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "return_local": local.strftime("%Y-%m-%d %H:%M:%S"), "tz": use_tz, "lat": use_lat, "lon": use_lon,
        "sun_error_arcsec": round(abs(_diff(sun_return, natal_sun)) * 3600, 4),
        "muntha": {"sign": muntha_sign, "sign_hi": SIGNS_HI[muntha_sign], "house": muntha_house,
                   "rule_hi": "मुन्था = जन्म-लग्न राशि + पूरे हुए वर्ष (हर वर्ष एक राशि आगे)।"},
        "lagna": chart["lagna"], "planets": chart["planets"], "houses": chart["houses"],
        "panchang": chart["panchang"], "confidence": "draft",
        "note_hi": ("यह सौर-वापसी (वर्षफल) कुंडली है: जिस क्षण सूर्य जन्म के सूर्य-अंश पर लौटता है। "
                    "ताजिक परत (वर्षेश, सहम, मुद्दा दशा, इत्थशाल) ड्राफ़्ट है; पाठ केवल दिशा-संकेत हैं।"),
    }
