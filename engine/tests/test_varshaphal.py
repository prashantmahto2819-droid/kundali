from datetime import datetime, timezone

import pytest

from jyotish import compute_chart, handlers, varshaphal

BASE = {"date": "1990-05-17", "time": "06:45", "tz": "Asia/Kolkata", "lat": 23.18, "lon": 79.99}


def test_sun_returns_to_natal_longitude():
    natal = compute_chart(**BASE)
    nsun = next(p for p in natal["planets"] if p["name"] == "Sun")["longitude"]
    for year in (1995, 2026, 2043):
        v = varshaphal.varshaphal(natal, year)
        rsun = next(p for p in v["planets"] if p["name"] == "Sun")["longitude"]
        assert abs(varshaphal._diff(rsun, nsun)) * 3600 < 1.0, year       # within 1 arc-second
        assert v["return_local"].startswith(f"{year}-05-1") or v["return_local"].startswith(f"{year}-05-2")


def test_return_time_drifts_as_a_sidereal_year():
    natal = compute_chart(**BASE)
    t = lambda y: datetime.strptime(varshaphal.varshaphal(natal, y)["return_utc"], "%Y-%m-%dT%H:%M:%SZ")
    gap = (t(2027) - t(2026)).total_seconds() / 86400
    assert 365.0 < gap < 366.0                                             # one sidereal year, give or take the leap day
    # 36 sidereal years exceed 36 calendar years (incl. 9 leap days) by about 0.229 day, i.e. 5.5 hours
    drift = (t(2026) - datetime(1990, 5, 17, 1, 15)).total_seconds() / 86400 - (36 * 365 + 9)
    assert drift == pytest.approx(0.229, abs=0.02)


def test_muntha_advances_one_sign_a_year():
    natal = compute_chart(**BASE)
    lagna = natal["lagna"]["sign"]
    for year in (1991, 2000, 2026):
        v = varshaphal.varshaphal(natal, year)
        assert v["muntha"]["sign"] == (lagna + year - 1990) % 12
        assert v["muntha"]["house"] == (v["muntha"]["sign"] - v["lagna"]["sign"]) % 12 + 1
        assert 1 <= v["muntha"]["house"] <= 12


def test_handler_validation_and_alternate_location():
    ok = handlers.varshaphal_from_payload({**BASE, "year": 2027})
    assert ok["age"] == 37 and ok["tz"] == "Asia/Kolkata"
    abroad = handlers.varshaphal_from_payload({**BASE, "year": 2027, "return_lat": 51.51, "return_lon": -0.13,
                                               "return_tz": "Europe/London"})
    assert abroad["tz"] == "Europe/London" and abroad["return_utc"] == ok["return_utc"]
    for bad in ({}, {"year": "x"}, {"year": 1950 - 100}, {"year": 1989}, {"year": 2027, "return_tz": "Nowhere/Land"}):
        with pytest.raises(handlers.BadRequest):
            handlers.varshaphal_from_payload({**BASE, **bad})
