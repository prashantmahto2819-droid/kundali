from datetime import datetime, timezone

import pytest

from jyotish import compute_chart
from jyotish.constants import DASHA_YEARS
from jyotish.core import ascendant_tropical, navamsa_sign, nakshatra_of
from jyotish.dasha import vimshottari
from jyotish.ephemeris import AnalyticBackend, mean_node, moon_longitude
from jyotish.rules import match_rules
from jyotish.timeutil import jd_to_datetime, julian_day, local_to_utc


def test_julian_day_meeus_example():
    # Meeus ch.7: 1957 Oct 4.81 -> JD 2436116.31
    dt = datetime(1957, 10, 4, 19, 26, 24, tzinfo=timezone.utc)
    assert julian_day(dt) == pytest.approx(2436116.31, abs=1e-3)


def test_jd_roundtrip():
    dt = datetime(2026, 11, 8, 7, 6, 30, tzinfo=timezone.utc)
    assert abs((jd_to_datetime(julian_day(dt)) - dt).total_seconds()) < 1


def test_moon_meeus_example():
    # Meeus ex. 47.a: 1992 Apr 12 0h TD, geometric longitude 133.162655
    assert moon_longitude(2448724.5) == pytest.approx(133.162655, abs=0.002)


def test_sun_and_venus_meeus_examples():
    b = AnalyticBackend()
    assert b.positions(2448908.5)["Sun"] == pytest.approx(199.909, abs=0.01)
    assert b.positions(2448976.5)["Venus"] == pytest.approx(313.08, abs=0.1)


def test_mean_node_j2000():
    assert mean_node(2451545.0) == pytest.approx(125.04452, abs=1e-5)


def test_navamsa_and_nakshatra_boundaries():
    assert navamsa_sign(0.0) == 0            # Mesha 0 -> Mesha
    assert navamsa_sign(30.0) == 9           # Vrishabha 0 -> Makara
    assert navamsa_sign(60.0) == 6           # Mithuna 0 -> Tula
    assert navamsa_sign(90.0) == 3           # Karka 0 -> Karka
    n = nakshatra_of(13.34)
    assert n["name"] == "Bharani" and n["pada"] == 1
    assert nakshatra_of(359.99)["name"] == "Revati"


def test_ascendant_cycles_once_a_day():
    vals = [ascendant_tropical(2451545.0 + h / 24, 2451545.0 + h / 24, 23.18, 79.99)
            for h in range(0, 25)]
    wraps = sum(1 for a, b in zip(vals, vals[1:]) if b < a)
    assert wraps == 1


def test_ascendant_equator_quadrant():
    # on the equator, when RAMC = 90 deg the ascendant is 180 deg (0 Libra)
    # choose jd so that GMST+lon = 90
    from jyotish.core import gmst_deg
    jd = 2451545.0
    lon = (90 - gmst_deg(jd)) % 360
    assert ascendant_tropical(jd, jd, 0.0, lon) == pytest.approx(180.0, abs=1e-6)


def test_vimshottari_structure():
    birth = datetime(1990, 1, 1, tzinfo=timezone.utc)
    d = vimshottari(100.0, birth, max_level=2)
    assert sum(DASHA_YEARS.values()) == 120
    first = d["mahadashas"][0]
    for md in d["mahadashas"]:
        start = datetime.fromisoformat(md["start"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(md["end"].replace("Z", "+00:00"))
        ad_total = sum((datetime.fromisoformat(c["end"].replace("Z", "+00:00"))
                        - datetime.fromisoformat(c["start"].replace("Z", "+00:00"))).total_seconds()
                       for c in md["children"])
        assert ad_total == pytest.approx((end - start).total_seconds(), rel=1e-9)
        assert md["children"][0]["lord"] == md["lord"]
    assert first["lord"] == nakshatra_of(100.0)["lord"]


def test_timezone_conversion():
    assert local_to_utc("1947-08-15", "00:00", "Asia/Kolkata").isoformat() == "1947-08-14T18:30:00+00:00"


@pytest.fixture(scope="module")
def india_1947():
    return compute_chart("1947-08-15", "00:00", "Asia/Kolkata", 28.6139, 77.2090,
                         backend=AnalyticBackend(),
                         as_of=datetime(2026, 11, 8, tzinfo=timezone.utc))


def test_known_chart_shape(india_1947):
    c = india_1947
    p = {x["name"]: x for x in c["planets"]}
    assert c["lagna"]["sign_name"] == "Vrishabha"
    assert p["Sun"]["sign_name"] == "Karka"
    assert p["Moon"]["nakshatra"] == "Pushya"
    assert p["Jupiter"]["sign_name"] == "Tula"
    assert p["Ketu"]["longitude"] == pytest.approx((p["Rahu"]["longitude"] + 180) % 360)
    assert c["dasha"]["birth_nakshatra_lord"] == "Saturn"
    assert len(c["houses"]) == 12 and sum(len(h["planets"]) for h in c["houses"]) == 9
    assert [d["level"] for d in c["dasha_running"]] == [1, 2]


def test_house_numbers_consistent(india_1947):
    lagna = india_1947["lagna"]["sign"]
    for pl in india_1947["planets"]:
        assert pl["house"] == (pl["sign"] - lagna) % 12 + 1


def test_rule_matching():
    fake = {"planets": [{"name": "Sun", "house": 10, "sign": 3, "sign_name": "Karka", "dignity": None,
                         "retrograde": False}]}
    hits = match_rules(fake)
    assert [h["rule_id"] for h in hits] == ["sun_in_10"]
    assert hits[0]["source"] and hits[0]["review_status"] == "draft"
