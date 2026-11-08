import pytest

from jyotish import handlers
from jyotish import matching as m
from jyotish.core import nakshatra_of, sign_of


def scores(r):
    return {k["name"]: k["score"] for k in r["kootas"]}


def test_tables_are_well_formed():
    n = len(m._YONI_ORDER)
    assert len(m._YONI_MATRIX) == n and all(len(r) == n for r in m._YONI_MATRIX)
    assert all(m._YONI_MATRIX[i][i] == 4 for i in range(n))
    assert all(m._YONI_MATRIX[i][j] == m._YONI_MATRIX[j][i] for i in range(n) for j in range(n))
    assert len(m._NAK_YONI) == 27 and len(m._GANA) == 27
    for g in ("Deva", "Manushya", "Rakshasa"):
        assert m._GANA.count(g) == 9
    # the seven classical enemy pairs score 0
    pairs = [("Cow", "Tiger"), ("Elephant", "Lion"), ("Horse", "Buffalo"), ("Dog", "Deer"),
             ("Serpent", "Mongoose"), ("Monkey", "Sheep"), ("Cat", "Rat")]
    for a, b in pairs:
        assert m._YONI_MATRIX[m._YONI_ORDER.index(a)][m._YONI_ORDER.index(b)] == 0


def test_same_moon_scores():
    r = m.ashtakoota(100.0, 100.0)
    s = scores(r)
    assert s["Nadi"] == 0                       # same nakshatra means same nadi
    assert s["Bhakoot"] == 7 and s["Gana"] == 6 and s["Yoni"] == 4
    assert s["Graha Maitri"] == 5 and s["Tara"] == 3
    assert r["total"] == 28 and r["max"] == 36


def test_bhakoot_inauspicious_pairs():
    base = 15.0  # Mesha
    for dist, expected in [(2, 0), (12, 0), (5, 0), (9, 0), (6, 0), (8, 0),
                           (1, 7), (3, 7), (4, 7), (7, 7), (10, 7), (11, 7)]:
        girl = base + 30 * (dist - 1)
        assert scores(m.ashtakoota(base, girl))["Bhakoot"] == expected, dist


def test_nadi_cycle():
    assert [m._NADI[i % 6] for i in range(6)] == ["Adi", "Madhya", "Antya", "Antya", "Madhya", "Adi"]
    ashwini, bharani = 5.0, 18.0                # nakshatras 1 and 2
    assert scores(m.ashtakoota(ashwini, bharani))["Nadi"] == 8       # Adi vs Madhya
    assert scores(m.ashtakoota(ashwini, 5.0 + 6 * 13.34))["Nadi"] == 0  # 7th nakshatra, Adi again


def test_tara_counting():
    # groom in the 3rd nakshatra from bride: count 3 is inauspicious one way
    bride = 5.0                                  # Ashwini
    groom = 5.0 + 2 * (360 / 27)                 # Krittika (3rd)
    assert nakshatra_of(groom)["index"] == 2
    assert scores(m.ashtakoota(groom, bride))["Tara"] in (1.5, 0)


def test_graha_maitri_rules():
    # Sun sign (Simha) vs Moon sign (Karka): lords Sun/Moon are mutual friends -> 5
    simha, karka = 4 * 30 + 5.0, 3 * 30 + 5.0
    assert scores(m.ashtakoota(simha, karka))["Graha Maitri"] == 5
    # Venus (Vrishabha) vs Sun (Simha): mutual enemies -> 0
    vrish = 30 + 5.0
    assert scores(m.ashtakoota(vrish, simha))["Graha Maitri"] == 0


def test_varna_and_vashya_helpers():
    assert m._VARNA_OF_SIGN[3] == "Brahmin" and m._VARNA_OF_SIGN[0] == "Kshatriya"
    assert m.vashya_group(8 * 30 + 5) == "Manav" and m.vashya_group(8 * 30 + 20) == "Chatushpada"
    assert m.vashya_group(9 * 30 + 5) == "Chatushpada" and m.vashya_group(9 * 30 + 20) == "Jalachara"
    assert m.vashya_group(4 * 30 + 1) == "Vanachara" and m.vashya_group(7 * 30 + 1) == "Keeta"


def test_confidence_flags_present():
    r = m.ashtakoota(100.0, 250.0)
    by = {k["name"]: k["confidence"] for k in r["kootas"]}
    assert by["Nadi"] == "firm" and by["Yoni"] == "draft" and by["Gana"] == "draft"
    assert "caution" in r


def test_manglik_logic():
    a = m.manglik_from(7, 0, 0)       # Mars in 7th, same sign as Moon -> 1st from Moon
    b = m.manglik_from(3, 5, 0)       # Mars in 3rd, 6th from Moon
    assert a["from_lagna"] and a["from_moon"] and not b["from_lagna"] and not b["from_moon"]
    assert m.compare_manglik(a, b)["level"] == "check"
    assert m.compare_manglik(a, a)["level"] == "balanced"


def test_handler_roundtrip_and_validation():
    person = {"date": "1990-05-17", "time": "06:45", "tz": "Asia/Kolkata", "lat": 23.18, "lon": 79.99}
    r = handlers.match_from_payload({"boy": person, "girl": {**person, "date": "1992-11-03", "time": "14:20"}})
    assert 0 <= r["total"] <= 36 and len(r["kootas"]) == 8 and "manglik" in r
    with pytest.raises(handlers.BadRequest):
        handlers.match_from_payload({"boy": person})
    with pytest.raises(handlers.BadRequest, match="girl"):
        handlers.match_from_payload({"boy": person, "girl": {**person, "tz": "Nowhere/Land"}})


def test_parihara_of_bhakoot_and_nadi():
    from jyotish import matching as m
    r = m.ashtakoota(5.0, 215.0)                      # Mesha / Vrishchika Moons: 6-8 Bhakoot, both ruled by Mars
    assert [d["name"] for d in r["doshas"]] == ["Bhakoot"] and r["doshas"][0]["cancelled"]
    assert r["parihara"][0]["dosha"] == "Bhakoot" and "Mars" in r["parihara"][0]["why"]
    assert r["total_with_parihara"] == r["total"] + 7
    r = m.ashtakoota(1.0, 5.0)                        # Ashwini pada 1 and pada 2: same nadi, cancelled by different padas
    assert any(d["name"] == "Nadi" and d["cancelled"] for d in r["doshas"])
    assert "different padas" in r["parihara"][0]["why"] and r["total_with_parihara"] == r["total"] + 8
    r = m.ashtakoota(5.0, 100.0)
    assert r["doshas"] == [] and r["parihara"] == [] and r["total_with_parihara"] == r["total"]
    # Nadi dosha without any parihara stays uncancelled
    r = m.ashtakoota(1.0, 81.0)                       # Ashwini and Punarvasu (index 6): both Adi nadi, different signs/lords
    nadi = next(k for k in r["kootas"] if k["name"] == "Nadi")
    assert nadi["score"] == 0 and not nadi.get("dosha_cancelled")
