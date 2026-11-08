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
    assert len(s["planets"]) == 7 and s["complete"] and not s["missing"]
    for r in s["planets"]:
        assert 0 <= r["uccha"] <= 60 and 0 <= r["dig"] <= 60 and r["kendradi"] in (60, 30, 15)
        assert r["total"] == pytest.approx(r["sthana"] + r["dig"] + r["kala"] + r["cheshta"] + r["naisargika"] + r["drik"], abs=0.1)
        assert r["comparable"] == pytest.approx(r["total"], abs=0.02) and 0 <= r["cheshta"] <= 120
        assert 0 <= r["sthana"] <= 60 + 315 + 30 + 60 + 15
    assert sorted(r["rank"] for r in s["planets"]) == list(range(1, 8))
    venus = next(r for r in s["planets"] if r["name"] == "Venus")
    assert venus["uccha"] > 50      # Venus is at 20 Pisces, close to its exaltation point


def test_trimsamsa():
    assert st.trimsamsa_sign(2.0) == 0 and st.trimsamsa_sign(7.0) == 10 and st.trimsamsa_sign(14.0) == 8
    assert st.trimsamsa_sign(20.0) == 2 and st.trimsamsa_sign(28.0) == 6          # odd sign (Mesha)
    assert st.trimsamsa_sign(30 + 2.0) == 1 and st.trimsamsa_sign(30 + 8.0) == 5   # even sign (Vrishabha)
    assert st.trimsamsa_sign(30 + 15.0) == 11 and st.trimsamsa_sign(30 + 22.0) == 9 and st.trimsamsa_sign(30 + 28.0) == 7


def test_aspect_virupa_is_continuous_and_special():
    assert st.aspect_virupa("Venus", 180) == 60 and st.aspect_virupa("Venus", 10) == 0
    assert st.aspect_virupa("Venus", 60) == pytest.approx(15) and st.aspect_virupa("Venus", 90) == pytest.approx(45)
    assert st.aspect_virupa("Venus", 120) == pytest.approx(30) and st.aspect_virupa("Venus", 300) == 0
    for d in (30, 60, 90, 120, 150, 180, 300):                       # no jumps for planets without special aspects
        assert st.aspect_virupa("Sun", d - 1e-6) == pytest.approx(st.aspect_virupa("Sun", d + 1e-6), abs=0.01)
    assert st.aspect_virupa("Mars", 100) == 60 and st.aspect_virupa("Mars", 220) == 60
    assert st.aspect_virupa("Jupiter", 130) == 60 and st.aspect_virupa("Jupiter", 250) == 60
    assert st.aspect_virupa("Saturn", 70) == 60 and st.aspect_virupa("Saturn", 280) == 60


def test_kala_pieces():
    assert st.paksha_bala("Jupiter", 0, 180) == pytest.approx(60) and st.paksha_bala("Saturn", 0, 180) == pytest.approx(0)
    assert st.paksha_bala("Jupiter", 0, 0) == pytest.approx(0) and st.paksha_bala("Mars", 0, 0) == pytest.approx(60)
    noon = {"from_noon": 0.0, "from_midnight": 12.0, "third_lord": "Mercury"}
    assert st.natonnata_bala("Sun", noon) == 60 and st.natonnata_bala("Moon", noon) == 0 and st.natonnata_bala("Mercury", noon) == 60
    assert st.tribhaga_bala("Jupiter", noon) == 60 and st.tribhaga_bala("Mercury", noon) == 60 and st.tribhaga_bala("Sun", noon) == 0
    # ayana: Sun at 0 Cancer (max north declination) is strongest (doubled); Saturn weakest there
    assert st.ayana_bala("Sun", 90, 23.44) == pytest.approx(120, abs=0.1)
    assert st.ayana_bala("Saturn", 90, 23.44) == pytest.approx(0, abs=0.1)
    assert st.ayana_bala("Saturn", 270, 23.44) == pytest.approx(60, abs=0.1)


def test_time_context_hora_and_vara():
    c = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)     # Thursday, sunrise ~05:28
    tc = st.time_context(c)
    assert tc["is_day"] and tc["vara_lord"] == "Jupiter"
    assert tc["hora_lord"] == "Mars"                                            # 06:45 is the 2nd hora; order Jupiter -> Mars
    first = st.time_context(compute_chart("1990-05-17", "05:40", "Asia/Kolkata", 23.18, 79.99))
    assert first["hora_lord"] == "Jupiter"                                      # first hora belongs to the day lord
    assert tc["third_lord"] == "Mercury"
    night = compute_chart("1990-05-17", "21:00", "Asia/Kolkata", 23.18, 79.99)
    tn = st.time_context(night)
    assert not tn["is_day"] and tn["third_lord"] == "Moon"
    assert tn["from_midnight"] < tc["from_midnight"]


def test_saptavargaja_and_ojayugma_ranges():
    lons = {"Sun": 32.2, "Moon": 250.0, "Mars": 300.0, "Mercury": 14.0, "Jupiter": 76.0, "Venus": 350.0, "Saturn": 281.0}
    for p in st.SEVEN:
        assert 14 <= st.saptavargaja_bala(p, lons) <= 7 * 45
        assert st.ojayugma_bala(p, lons[p]) in (0.0, 15.0, 30.0)
    assert st.ojayugma_bala("Moon", 38.0) == 30.0       # 8 deg Taurus: even sign in D1 and in D9 (Pisces)


def test_cheshta_bala_motion():
    jd = 2448029.5                                                  # 1990-05-17 (TT ~ UT)
    c = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)
    rows = {r["name"]: r for r in c["strength"]["planets"]}
    retro = {p["name"]: p["retrograde"] for p in c["planets"]}
    assert retro["Saturn"] and rows["Saturn"]["cheshta"] > 35          # retrograde: far from conjunction, strong
    assert retro["Mercury"] and rows["Mercury"]["cheshta"] > 40
    k = compute_chart("1991-11-10", "14:20", "Asia/Kolkata", 22.3667, 82.7667)
    mars = next(r for r in k["strength"]["planets"] if r["name"] == "Mars")
    assert mars["cheshta"] < 5                                           # Mars conjunct the Sun: minimal motional strength
    for n in ("Mars", "Mercury", "Jupiter", "Venus", "Saturn"):
        assert 0 <= st.cheshta_bala(n, 123.4, jd) <= 60
    assert "cheshta" not in " ".join(c["strength"]["missing"])


def test_abda_masa_yuddha():
    c = compute_chart("1991-11-10", "14:20", "Asia/Kolkata", 22.3667, 82.7667)
    s = c["strength"]
    assert s["complete"] and s["missing"] == [] and s["lords"]["ahargana"] == 1860105
    assert s["lords"]["abda_lord"] in st.VARA_LORDS and s["lords"]["masa_lord"] in st.VARA_LORDS
    kala = {r["name"]: r["detail"]["kala"] for r in s["planets"]}
    assert kala[s["lords"]["abda_lord"]]["abda"] == 15.0 and kala[s["lords"]["masa_lord"]]["masa"] == 30.0
    assert sum(v["abda"] for v in kala.values()) == 15.0 and sum(v["masa"] for v in kala.values()) == 30.0
    # synthetic war: Jupiter and Venus 0.5 deg apart -> larger disc (Jupiter) gains, Venus loses the same amount
    rows = [{"name": n, "total": t} for n, t in (("Jupiter", 400.0), ("Venus", 300.0), ("Mars", 200.0), ("Mercury", 250.0), ("Saturn", 220.0))]
    wars = st.yuddha_adjust(rows, {"Jupiter": 100.0, "Venus": 100.5, "Mars": 10.0, "Mercury": 200.0, "Saturn": 300.0})
    assert wars == [{"winner": "Jupiter", "loser": "Venus", "gap_deg": 0.5, "adjust": round(100 / (190.4 - 16.6), 2)}]
    assert rows[0]["yuddha"] > 0 and rows[1]["yuddha"] == -rows[0]["yuddha"]


def test_ishta_kashta():
    import math
    c = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)
    for r in c["strength"]["planets"]:
        u, ch = min(r["uccha"], 60.0), min(r["cheshta"], 60.0)
        assert r["ishta"] == pytest.approx(math.sqrt(u * ch), abs=0.05)
        assert r["kashta"] == pytest.approx(math.sqrt((60 - u) * (60 - ch)), abs=0.05)
        assert 0 <= r["ishta"] <= 60 and 0 <= r["kashta"] <= 60
