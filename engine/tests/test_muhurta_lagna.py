"""Lagna table and lagna shuddhi."""
from datetime import date

import pytest

from jyotish import handlers, muhurta_lagna as ml


def test_lagna_table_covers_the_day():
    wins = ml.lagna_table(date(2026, 11, 26), 22.35, 82.68, "Asia/Kolkata")
    assert 12 <= len(wins) <= 14
    assert wins[0]["start"].strftime("%H:%M") == "00:00" and wins[-1]["end"].strftime("%H:%M") == "00:00"
    for a, b in zip(wins, wins[1:]):
        assert a["end"] == b["start"] and (b["sign"] - a["sign"]) % 12 == 1      # consecutive signs, no gaps
    assert all(45 <= (w["end"] - w["start"]).total_seconds() / 60 <= 200 for w in wins[1:-1])


def test_judge_rules():
    base = {"asc": 10.0, "lagna": 1, "lons": {}, "houses": {"Sun": 10, "Moon": 3, "Mars": 2, "Mercury": 10, "Jupiter": 5, "Venus": 9, "Saturn": 11, "Rahu": 4, "Ketu": 10}}
    j = ml.judge(base, "marriage")
    assert j["verdict"] == "shubh" and not j["doshas"] and any("केंद्र" in s["hi"] for s in j["strengths"])
    bad = {**base, "houses": {**base["houses"], "Saturn": 7, "Mars": 8, "Moon": 12}}
    jb = ml.judge(bad, "marriage")
    assert jb["verdict"] == "varjit" and {d["key"] for d in jb["doshas"]} >= {"jamitra", "ashtama", "mars_8", "moon"}
    jg = ml.judge(base, "marriage", groom_moon_sign=(1 - 7) % 12)          # lagna 8th from groom's Moon
    assert any(d["key"] == "groom_rashi" for d in jg["doshas"])


def test_lagna_muhurta_and_handler():
    r = ml.lagna_muhurta("2026-11-26", 22.35, 82.68, "Asia/Kolkata", "marriage", groom_moon_sign=3)
    assert len(r["lagnas"]) >= 12 and all(0 <= l["score"] <= 100 for l in r["lagnas"]) and r["abhijit"] and r["note_hi"]
    assert all(l["verdict"] != "varjit" for l in r["best"])
    out = handlers.muhurta_lagna_from_payload({"date": "2026-11-26", "lat": 22.35, "lon": 82.68, "tz": "Asia/Kolkata", "groom_moon_sign": "3", "bride_moon_sign": ""})
    assert out["date"] == "2026-11-26"
    with pytest.raises(handlers.BadRequest):
        handlers.muhurta_lagna_from_payload({"date": "26-11-2026", "lat": 22.35, "lon": 82.68})
    with pytest.raises(handlers.BadRequest):
        handlers.muhurta_lagna_from_payload({"date": "2026-11-26", "lat": 22.35, "lon": 82.68, "groom_moon_sign": 12})
