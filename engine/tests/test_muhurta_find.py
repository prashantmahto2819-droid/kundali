import pytest

from jyotish import handlers, muhurta_find as M


def test_find_scores_and_rules():
    r = M.find("travel", 23.18, 79.99, "Asia/Kolkata", "2026-11-08", 30)
    assert len(r["all"]) == 30 and len(r["best"]) == 5 and r["best"] == sorted(r["all"], key=lambda x: (-x["score"], x["date"]))[:5]
    for d in r["all"]:
        assert 0 <= d["score"] <= 100 and d["rahu_kaal"] and d["sunrise"]
        if d["nakshatra"] in M.ACTIVITIES["travel"]["bad_nak"]:
            assert any("avoided" in w for w in d["reasons"])
        if d["tithi"] in ("Chaturthi", "Navami", "Chaturdashi"):
            assert any("rikta" in w for w in d["reasons"])
    with pytest.raises(ValueError):
        M.find("wedding-of-dragons", 23.18, 79.99, "Asia/Kolkata")


def test_tarabala_and_handler():
    r = M.find("business", 23.18, 79.99, "Asia/Kolkata", "2026-11-08", 10, birth_moon_lon=292.9)
    assert all(any("tarabala" in w for w in d["reasons"]) and any("chandrabala" in w for w in d["reasons"]) for d in r["all"])
    out = handlers.muhurta_from_payload({"activity": "general", "lat": 23.18, "lon": 79.99, "tz": "Asia/Kolkata", "start": "2026-11-08", "days": 5,
                                         "chart": {"date": "1990-05-17", "time": "06:45", "tz": "Asia/Kolkata", "lat": 23.18, "lon": 79.99}})
    assert out["days"] == 5 and any("tarabala" in w for w in out["all"][0]["reasons"])
    with pytest.raises(handlers.BadRequest):
        handlers.muhurta_from_payload({"activity": "general", "lat": "x", "lon": 1})
    with pytest.raises(handlers.BadRequest):
        handlers.muhurta_from_payload({"activity": "general", "lat": 1, "lon": 1, "start": "8-11-2026"})


def test_samskara_activities_and_period_blocks():
    from jyotish.muhurta_find import ACTIVITIES, find, month_flags
    from datetime import datetime, timezone
    assert {"marriage", "mundan", "namakaran", "annaprashan", "upanayana", "bhoomi_pujan", "property"} <= set(ACTIVITIES)
    # Kharmas: Sun in Dhanu from mid-December → marriage days score low
    r = find("marriage", 28.61, 77.2, "Asia/Kolkata", "2026-12-16", 20)
    assert all(x["score"] <= 40 for x in r["all"]) and any("खरमास" in " ".join(x["reasons_hi"]) for x in r["all"])
    # late November 2026: marriage dates exist
    r2 = find("marriage", 28.61, 77.2, "Asia/Kolkata", "2026-11-15", 25)
    assert any(x["score"] >= 65 for x in r2["all"])
    # chaturmas (amanta Shravana) blocks marriage, not property
    f = month_flags(datetime(2026, 8, 10, 1, 0, tzinfo=timezone.utc), 110.0, 20.0, 3, False, 5)
    assert any(x["key"] == "chaturmas" for x in f)
    r3 = find("property", 28.61, 77.2, "Asia/Kolkata", "2026-08-01", 15)
    assert any(x["score"] >= 60 for x in r3["all"])
