"""Rashifal from the gochara rule library."""
import pytest

from jyotish import handlers, rashifal as rf


def test_rashifal_structure_and_periods():
    d = rf.rashifal("2026-11-09", "Asia/Kolkata", "daily")
    assert len(d["signs"]) == 12 and all(0 <= s["score"] <= 100 and s["summary_hi"] and s["planets"] for s in d["signs"])
    assert all(len(s["planets"]) == 9 for s in d["signs"]) and d["day_lord_hi"] == "चंद्र"          # Monday
    w = rf.rashifal("2026-11-09", "Asia/Kolkata", "weekly")
    assert w["span"] == {"from": "2026-11-09", "to": "2026-11-15"} and all(len(s["planets"]) == 8 for s in w["signs"])
    m = rf.rashifal("2026-11-09", "Asia/Kolkata", "monthly")
    assert m["span"] == {"from": "2026-11-01", "to": "2026-11-30"}
    for s in d["signs"]:
        for p in s["planets"]:
            assert p["house"] == (d["transits"][p["planet"]]["sign"] - s["sign"]) % 12 + 1
            assert "मृत्यु" not in p["text_hi"] and "death" not in p["text_en"].lower()


def test_handler_and_report():
    out = handlers.rashifal_from_query({"date": "2026-11-09", "period": "weekly"})
    assert out["period"] == "weekly"
    with pytest.raises(handlers.BadRequest):
        handlers.rashifal_from_query({"date": "2026-11-09", "period": "yearly"})
    html = handlers.rashifal_report_from_payload({"date": "2026-11-09", "period": "daily", "lang": "en"})
    assert "Rashifal" in html and "Mesha" in html
    from jyotish import calendar_design
    h = calendar_design.render_calendar(2026, [11], 22.35, 82.68, "Asia/Kolkata", {"template": "classic", "rashifal_page": True, "web_fonts": False}, "hi")
    assert h.count('class="page ') == 2 and "मासिक राशिफल" in h
