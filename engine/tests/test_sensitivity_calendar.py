from datetime import datetime, timezone

from jyotish import compute_chart, sensitivity as S
from jyotish.transit import transit_calendar
from jyotish.ephemeris import AnalyticBackend


def test_sensitivity_flags_lagna_near_boundary():
    r = S.sensitivity("1991-11-10", "14:20", "Asia/Kolkata", 22.3667, 82.7667)   # Lagna Kumbha 28°41′
    lg = r["items"]["lagna_sign"]
    assert lg["minutes_later"] == 4 and not lg["stable_within_5_min"]
    assert any(w["what"] == "Lagna sign" and w["minutes"] == 4 for w in r["warnings"])
    assert r["items"]["moon_sign"]["margin_minutes"] is None               # Moon mid-sign: no change within 3 h
    r2 = S.sensitivity("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)
    assert r2["items"]["lagna_sign"]["margin_minutes"] == 38 and r2["items"]["lagna_sign"]["stable_within_15_min"]


def test_chart_adds_sensitivity_warnings_and_calendar():
    c = compute_chart("1991-11-10", "14:20", "Asia/Kolkata", 22.3667, 82.7667)
    assert any(w["code"] == "birth_time_sensitive" for w in c["input_warnings"])
    tc = c["transit_calendar"]
    assert len(tc["months"]) == 12 and all(len(m["planets"]) == 9 for m in tc["months"])
    assert all(1 <= v["house_from_moon"] <= 12 for m in tc["months"] for v in m["planets"].values())
    assert all(g["planet"] in ("Jupiter", "Saturn", "Rahu", "Ketu", "Mars") for g in tc["ingress"])


def test_calendar_ingress_known_event():
    """Rahu (mean node) moves from Kumbha to Makara in early December 2026; Jupiter re-enters Karka in Jan 2027 (retrograde)."""
    c = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)
    tc = transit_calendar(c, datetime(2026, 11, 8, tzinfo=timezone.utc), AnalyticBackend())
    rahu = next(g for g in tc["ingress"] if g["planet"] == "Rahu")
    assert rahu["to_sign"] == "Makara" and rahu["date"].startswith("2026-12")
    jup = [g for g in tc["ingress"] if g["planet"] == "Jupiter"]
    assert any(g["to_sign"] == "Karka" and g["date"].startswith("2027-01") for g in jup)


def test_life_transits_sade_sati_matches_known_dates():
    c = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)          # Moon in Makara
    L = c["life_transits"]
    w = next(x for x in L["sade_sati_windows"] if x["start"].startswith("2017"))
    assert w["start"][:7] == "2017-10" and w["end"][:7] == "2025-03"                # Saturn Dhanu Oct 2017 -> leaves Kumbha Mar 2025
    assert [p["phase"] for p in w["phases"]] == ["rising", "peak", "setting"] and w["status"] == "past"
    assert any(a["start"].startswith("2007") for a in L["ashtama_shani"])            # Saturn in Simha (8th from Makara) 2007-09
    assert all(1 <= j["house_from_moon"] <= 12 for j in L["jupiter_periods"]) and len(L["jupiter_periods"]) < 120
    from jyotish import report
    assert "साढ़ेसाती" in report.render(c)


def test_vedha_blocks_a_favourable_transit():
    from jyotish.transit import vedha_for, VEDHA
    hfm = {"Sun": 3, "Moon": 10, "Mars": 7, "Mercury": 10, "Jupiter": 8, "Venus": 9, "Saturn": 3, "Rahu": 2, "Ketu": 8}
    assert vedha_for("Mercury", 10, hfm) == ["Jupiter", "Ketu"]                    # Mercury's 10th is obstructed from the 8th
    base = {**hfm, "Venus": 11}
    assert vedha_for("Sun", 3, {**base, "Saturn": 9}) == []                          # Sun-Saturn never obstruct each other
    assert vedha_for("Sun", 3, {**base, "Mars": 9}) == ["Mars"]
    assert vedha_for("Mars", 7, hfm) == []                                           # not a favourable house: no vedha question
    assert all(set(v) <= set(range(1, 13)) for v in VEDHA.values())
    c = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)
    merc = next(r for r in c["gochara"]["planets"] if r["name"] == "Mercury")
    assert merc["favourable_from_moon"] and merc["vedha_by"] == ["Jupiter", "Ketu"] and merc["verdict"] == "mixed"
    assert c["gochara"]["vedha_applied"] is True
