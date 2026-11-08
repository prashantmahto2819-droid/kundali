from datetime import datetime, timezone

from jyotish import compute_chart, transit


def test_sade_sati_phases():
    moon = 3  # Karka
    assert transit.sade_sati(moon, 2)["phase"] == "rising"     # Mithuna: 12th from Moon
    assert transit.sade_sati(moon, 3)["phase"] == "peak"
    assert transit.sade_sati(moon, 4)["phase"] == "setting"
    assert not transit.sade_sati(moon, 5)["active"]
    assert transit.sade_sati(moon, 10)["ashtama"]              # Makara: 8th from Karka
    assert transit.sade_sati(0, 11)["phase"] == "rising"       # wraps around the zodiac


def test_favourable_tables_are_sane():
    for pl, houses in transit.FAVOURABLE_FROM_MOON.items():
        assert list(houses) == sorted(set(houses)) and all(1 <= h <= 12 for h in houses)
    assert 5 in transit.FAVOURABLE_FROM_MOON["Jupiter"] and 8 not in transit.FAVOURABLE_FROM_MOON["Saturn"]
    assert 11 in {h for hs in transit.FAVOURABLE_FROM_MOON.values() for h in hs}   # 11th is gain for all
    assert all(11 in hs for hs in transit.FAVOURABLE_FROM_MOON.values())


def test_known_sky_on_8_nov_2026():
    when = datetime(2026, 11, 8, 8, 0, tzinfo=timezone.utc)
    c = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99, as_of=when)
    g = {r["name"]: r for r in c["gochara"]["planets"]}
    assert g["Sun"]["sign_name"] == "Tula"          # the Sun enters Vrischika about 17 Nov
    assert g["Saturn"]["sign_name"] == "Meena" and g["Saturn"]["retrograde"]
    assert g["Rahu"]["sign_name"] == "Kumbha" and g["Ketu"]["sign_name"] == "Simha"
    assert g["Rahu"]["retrograde"] and "verdict" not in g["Rahu"]
    for n in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"):
        assert g[n]["verdict"] in ("supportive", "mixed", "challenging")
        assert 0 <= g[n]["bindus"] <= 8
        assert (g[n]["house_from_moon"] in transit.FAVOURABLE_FROM_MOON[n]) == g[n]["favourable_from_moon"]
    assert c["gochara"]["as_of"].startswith("2026-11-08")
