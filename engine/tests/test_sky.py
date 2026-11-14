from jyotish import handlers
from jyotish.translit import roman


def test_sky_now_has_nine_grahas():
    d = handlers.sky_from_query({})
    names = [p["name"] for p in d["planets"]]
    assert len(names) == 9 and {"Sun", "Moon", "Rahu", "Ketu"} <= set(names)
    for p in d["planets"]:
        assert 0 <= p["longitude"] < 360 and 0 <= p["degree"] < 30 and p["sign_name_hi"] and p["nakshatra"]
    r = {p["name"]: p["longitude"] for p in d["planets"]}
    assert abs(((r["Rahu"] - r["Ketu"]) % 360) - 180) < 1e-6
    assert handlers.sky_from_query({}) is d                              # cached


def test_roman_names():
    assert [roman(w) for w in ("भोलानाथ", "जानकीनाथ", "कृष्ण", "आदित्य", "लक्ष्मी", "ज़ोया")] == ["Bholanath", "Janakinath", "Krishna", "Aditya", "Lakshmi", "Zoya"]
