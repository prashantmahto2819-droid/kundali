import pytest

from jyotish import compute_chart
from jyotish import strength as st


def test_uccha_extremes():
    assert st.uccha_bala("Sun", 10.0) == pytest.approx(60)           # exaltation point
    assert st.uccha_bala("Sun", 190.0) == pytest.approx(0)           # debilitation point
    assert st.uccha_bala("Jupiter", 95.0) == pytest.approx(60)
    assert st.uccha_bala("Saturn", 20.0) == pytest.approx(0)         # 20 Aries
    assert st.uccha_bala("Moon", 33.0 + 90) == pytest.approx(30)     # halfway
    assert st.uccha_bala("Venus", 357.0 + 10) == pytest.approx(st.uccha_bala("Venus", 357.0 - 10))  # wraps


def test_dig_extremes():
    lagna = 100.0
    assert st.dig_bala("Jupiter", lagna, lagna) == pytest.approx(60)           # Jupiter on the ascendant
    assert st.dig_bala("Jupiter", lagna + 180, lagna) == pytest.approx(0)
    assert st.dig_bala("Saturn", lagna + 180, lagna) == pytest.approx(60)      # Saturn on the descendant
    assert st.dig_bala("Sun", lagna + 270, lagna) == pytest.approx(60)         # Sun at the 10th point
    assert st.dig_bala("Moon", lagna + 90, lagna) == pytest.approx(60)
    assert st.dig_bala("Venus", lagna + 90 + 90, lagna) == pytest.approx(30)


def test_kendradi_and_naisargika():
    assert [st.kendradi_bala(h) for h in range(1, 13)] == [60, 30, 15, 60, 30, 15, 60, 30, 15, 60, 30, 15]
    assert sum(st.NAISARGIKA.values()) == pytest.approx(240.0, abs=0.01)
    assert st.NAISARGIKA["Sun"] > st.NAISARGIKA["Moon"] > st.NAISARGIKA["Venus"] > st.NAISARGIKA["Jupiter"] \
        > st.NAISARGIKA["Mercury"] > st.NAISARGIKA["Mars"] > st.NAISARGIKA["Saturn"]


def test_chart_integration():
    c = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)
    s = c["strength"]
    assert len(s["planets"]) == 7 and not s["complete"]
    for r in s["planets"]:
        assert 0 <= r["uccha"] <= 60 and 0 <= r["dig"] <= 60 and r["kendradi"] in (60, 30, 15)
        assert r["total"] == pytest.approx(r["uccha"] + r["dig"] + r["kendradi"] + r["naisargika"], abs=0.02)
    assert sorted(r["rank"] for r in s["planets"]) == list(range(1, 8))
    venus = next(r for r in s["planets"] if r["name"] == "Venus")
    assert venus["uccha"] > 50      # Venus is at 20 Pisces, close to its exaltation point
