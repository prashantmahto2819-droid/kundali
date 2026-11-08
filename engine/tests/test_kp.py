from jyotish import compute_chart, kp
from jyotish.core import ascendant_tropical, midheaven_tropical

C = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)


def test_sub_lords_follow_vimshottari_proportions():
    # Krittika (26°40'-40°), lord Sun: subs Sun 0.667, Moon 1.111, Mars 0.778, Rahu 2.0, Jupiter 1.778 ...
    base = 360 / 27 * 2
    assert kp._lords(base + 0.1)["sub_lord"] == "Sun"
    assert kp._lords(base + 1.0)["sub_lord"] == "Moon"
    assert kp._lords(base + 2.0)["sub_lord"] == "Mars"
    assert kp._lords(base + 3.0)["sub_lord"] == "Rahu"
    assert kp._lords(base + 5.6)["sub_lord"] == "Jupiter"
    assert kp._lords(base + 13.3)["sub_lord"] == "Venus"            # last sub of a Sun star is Venus
    assert kp._lords(0.02)["star_lord"] == "Ketu" and kp._lords(0.02)["sub_lord"] == "Ketu" and kp._lords(0.02)["sub_sub_lord"] == "Ketu"


def test_placidus_cusps_geometry():
    jd_ut = C["jd_ut"]; jd_tt = jd_ut + 69 / 86400
    cusps = kp.placidus_cusps(jd_ut, jd_tt, 23.18, 79.99)
    assert abs(cusps[0] - ascendant_tropical(jd_ut, jd_tt, 23.18, 79.99)) < 1e-6
    assert abs(cusps[9] - midheaven_tropical(jd_ut, jd_tt, 79.99)) < 1e-6
    for i in range(6):
        assert abs(((cusps[i + 6] - cusps[i]) % 360) - 180) < 1e-6
    # cusps increase in zodiacal order
    for i in range(12):
        assert 0 < (cusps[(i + 1) % 12] - cusps[i]) % 360 < 180
    # at the equator Placidus reduces to equal RA thirds: cusp 11 = MC + 30 deg in RA
    eq = kp.placidus_cusps(jd_ut, jd_tt, 0.0, 79.99)
    assert 20 < (eq[10] - eq[9]) % 360 < 40


def test_kp_layer_in_chart():
    K = C["kp"]
    assert K["system"] == "KP" and abs(K["ayanamsa"] - C["ayanamsa_value"] + 0.087) < 0.01   # ~5.2' less than Lahiri
    assert len(K["cusps"]) == 12 and set(K["planets"]) == {p["name"] for p in C["planets"]}
    sun = K["planets"]["Sun"]
    assert sun["house"] == 12 and sun["star_lord"] == "Sun" and sun["sub_lord"] == "Jupiter"
    assert K["significators"][7]["d_owners"] == ["Mars"]
    from jyotish import report
    assert "कृष्णमूर्ति" in report.render(C)


def test_ruling_planets():
    from datetime import datetime, timezone
    from jyotish.ephemeris import AnalyticBackend
    rp = kp.ruling_planets(datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc), 23.18, 79.99, AnalyticBackend(), "Asia/Kolkata")
    assert rp["day_lord"] == "Sun"                                          # Sunday 8 Nov 2026, 17:30 IST
    for k in ("lagna_sign_lord", "lagna_star_lord", "lagna_sub_lord", "moon_sign_lord", "moon_star_lord", "moon_sub_lord"):
        assert rp[k] in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
    assert rp["ranked"][0] in rp.values() and "ruling_planets" in C["kp"]
