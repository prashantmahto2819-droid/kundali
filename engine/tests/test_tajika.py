"""Tajika layer of the varshaphal."""
from datetime import datetime, timezone

from jyotish import compute_chart, tajika, varshaphal
from jyotish.ephemeris import AnalyticBackend

B = AnalyticBackend()


def _v(year=2026):
    n = compute_chart("1991-04-09", "16:30", "Asia/Kolkata", 22.35, 82.68, backend=B)
    return varshaphal.varshaphal(n, year, backend=B)


def test_hadda_and_drekkana_tables():
    assert tajika.hadda_lord(0.5) == "Jupiter" and tajika.hadda_lord(29.9) == "Saturn"        # Aries
    assert tajika.hadda_lord(30 + 7.9) == "Venus" and tajika.hadda_lord(30 + 8.0) == "Mercury"  # Taurus boundary
    assert all(row[-1][0] == 30 for row in tajika.HADDA) and all(len(row) == 5 for row in tajika.HADDA)
    assert tajika.drekkana_lord(5) == "Mars" and tajika.drekkana_lord(15) == "Sun" and tajika.drekkana_lord(25) == "Jupiter"


def test_panchavargiya_bounds_and_exaltation():
    b = tajika.panchavargiya("Sun", 10.0)          # deep exaltation
    assert b["uchcha"] == 20.0 and 0 < b["total"] <= 80
    d = tajika.panchavargiya("Sun", 190.0)         # deep debilitation
    assert d["uchcha"] == 0.0 and d["total"] < b["total"]


def test_mudda_dasha_fills_the_year():
    start = datetime(2026, 4, 9, tzinfo=timezone.utc)
    md = tajika.mudda_dasha(100.0, start)
    assert abs(sum(m["days"] for m in md) - 365.25) < 0.5
    assert md[0]["start"] == "2026-04-09" and md[-1]["end"] == "2027-04-09"
    assert md[0]["lord"] == md[-1]["lord"]            # balance at the start, remainder at the end
    for m in md:
        assert len(m["children"]) == 9 and m["children"][0]["lord"] == m["lord"]


def test_sahams_formula_and_reversal():
    lons = {"Sun": 10.0, "Moon": 100.0, "Mars": 200.0, "Mercury": 20.0, "Jupiter": 300.0, "Venus": 40.0, "Saturn": 250.0}
    day = tajika.sahams(lons, 130.0, True)
    night = tajika.sahams(lons, 130.0, False)
    punya_day = next(s for s in day if s["name"] == "Punya")
    punya_night = next(s for s in night if s["name"] == "Punya")
    assert punya_day["longitude"] != punya_night["longitude"]
    sam_day = next(s for s in day if s["name"] == "Samarthya"); sam_night = next(s for s in night if s["name"] == "Samarthya")
    assert sam_day["longitude"] == sam_night["longitude"]     # formula with the Lagna lord is not reversed
    assert len(day) == 12 and all(0 <= s["longitude"] < 360 for s in day)


def test_varshaphal_carries_tajika():
    v = _v()
    t = v["tajika"]
    assert t["varshesha"] in tajika.SEVEN and t["varshesha_hi"]
    assert {r["role"] for r in t["panchadhikaris"]} == {"muntha_lord", "birth_lagna_lord", "varsha_lagna_lord", "trirashi_lord", "dina_ratri_lord"}
    assert t["varshesha"] in {r["planet"] for r in t["panchadhikaris"]}
    assert len(t["sahams"]) == 12 and t["mudda_dasha"][0]["start"] == v["return_local"][:10]
    for a in t["aspects"]:
        assert a["orb"] <= a["max_orb"] and a["phase"] in ("ithasala", "ishrafa")
    assert t["review_status"] == "draft"
