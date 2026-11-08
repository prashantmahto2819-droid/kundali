from jyotish import compute_chart
from jyotish.core import chalit_house, sripati_cusps


def test_sripati_cusps_geometry():
    c = sripati_cusps(51.05, 307.47)
    assert abs(c[0] - 51.05) < 1e-9 and abs(c[9] - 307.47) < 1e-9 and abs(c[6] - 231.05) < 1e-9 and abs(c[3] - 127.47) < 1e-9
    # quadrants trisected: equal steps inside each quadrant
    assert abs((c[1] - c[0]) - (c[2] - c[1])) < 1e-9 and abs((c[4] - c[3]) - (c[5] - c[4])) < 1e-9
    assert all(abs(((c[i + 6] - c[i]) % 360) - 180) < 1e-9 for i in range(6))


def test_chalit_house_membership():
    c = sripati_cusps(51.05, 307.47)
    assert chalit_house(51.05, c) == 1 and chalit_house(307.47, c) == 10
    assert chalit_house(32.18, c) == 12          # the Sun just risen (before the Lagna degree) is in the 12th
    assert chalit_house(63.0, c) == 1 and chalit_house(65.0, c) == 2
    assert all(1 <= chalit_house(x, c) <= 12 for x in range(0, 360, 7))


def test_chart_carries_chalit():
    c = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)
    ch = c["chalit"]
    assert ch["system"] == "sripati" and len(ch["cusps"]) == 12 and ch["mc_sign_name"] == "Kumbha"
    sun = next(p for p in c["planets"] if p["name"] == "Sun")
    assert sun["house"] == 1 and sun["house_chalit"] == 12
    assert {"planet": "Sun", "planet_hi": "सूर्य", "rasi_house": 1, "chalit_house": 12} in ch["moved"]
    from jyotish import report
    assert "भाव-चलित" in report.render(c)
