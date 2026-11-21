from jyotish import handlers


def test_now_running_slots():
    # 21 Nov 2026 (Saturday) Delhi; 10:00 local
    r = handlers.now_from_query({"lat": 28.61, "lon": 77.2, "tz": "Asia/Kolkata", "at": "2026-11-21T10:00:00+05:30"})
    assert r["available"] and r["vara"]["index"] == 6
    c = r["choghadiya"]; h = r["hora"]
    assert c["name"] in ("Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog") and 0 < c["mins_left"] <= 100
    assert h["lord"] in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn") and 0 < h["mins_left"] <= 70
    nx = r["next_good_choghadiya"]
    assert nx is None or (nx["nature"] == "good" and nx["mins_to"] > 0)
    # Saturday Rahu kaal is 09:00-10:30 region in Delhi
    assert r["rahu_kaal_now"] is True
    # after midnight (before sunrise) the night slots of the previous day run
    n = handlers.now_from_query({"lat": 28.61, "lon": 77.2, "tz": "Asia/Kolkata", "at": "2026-11-22T02:00:00+05:30"})
    assert n["vara"]["index"] == 6 and n["choghadiya"] and n["hora"]["night"] is True
