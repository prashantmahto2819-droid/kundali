"""Personal dashboard digest."""
from jyotish.handlers import dashboard_from_payload


def test_dashboard_digest():
    d = dashboard_from_payload({"name": "राम", "date": "1990-05-15", "time": "10:30", "tz": "Asia/Kolkata", "lat": 28.61, "lon": 77.2})
    assert d["identity"]["lagna_hi"] == "कर्क" and d["identity"]["moon_sign_hi"] == "धनु" and d["identity"]["name_syllable"] == "भे"
    assert [x["level"] for x in d["dasha"]] == [1, 2, 3] and all(0 <= x["percent"] <= 100 for x in d["dasha"])
    assert 0 <= d["today"]["rashifal"]["score"] <= 100 and d["today"]["personal"]["score"] >= 0
    assert 0 <= d["birthday"]["days"] <= 366 and d["birthday"]["date"].endswith("-05-15")
    assert set(d["doshas"]) == {"mangal", "kaal_sarp", "pitru"} and isinstance(d["upcoming"], list)
