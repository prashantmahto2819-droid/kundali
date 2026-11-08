"""Monthly panchang and the printable calendar pages."""
import pytest

from jyotish import calendar_design, handlers, panchang_month


def test_month_rows():
    m = panchang_month.month(2026, 11, 28.61, 77.2, "Asia/Kolkata")
    assert len(m["days"]) == 30 and m["first_weekday"] == 0           # 1 Nov 2026 is a Sunday
    d8 = next(d for d in m["days"] if d["day"] == 8)
    assert d8["vara"] == "Ravivara" and d8["tithi"] == "Chaturdashi" and d8["paksha"] == "Krishna"
    assert any(e["key"] == "diwali" for e in d8["events"]) and d8["moonrise"] and d8["tithi_ends"]
    assert d8["masa_amanta"] == "Ashwina" and d8["masa_purnimanta"] == "Kartika" and d8["vikram_samvat"] == 2083
    # end times are later than sunrise and the next-day flag agrees with the clock
    for d in m["days"]:
        assert d["tithi_ends"] is None or d["tithi_ends_next_day"] or d["tithi_ends"] > d["sunrise"]
        assert d["nakshatra_ends"] is None or d["nakshatra_ends_next_day"] or d["nakshatra_ends"] > d["sunrise"]
    jan = panchang_month.month(2026, 1, 28.61, 77.2, "Asia/Kolkata")
    assert sum(1 for d in jan["days"] if d["sankranti"]) == 1 and next(d for d in jan["days"] if d["sankranti"])["day"] == 14
    assert jan["days"][0]["vikram_samvat"] == 2082


def test_calendar_pages_and_design_safety():
    design = {"theme": "indigo", "size": "A4-landscape", "ad_top": {"title": "Test Ad", "text": "line", "contact": "123"},
              "ad_bottom": {"image": "javascript:alert(1)"}, "logo": "data:image/png;base64,iVBORw0KGgo=",
              "business": {"name": "Biz <b>", "line": "L"}, "notes": [{"date": "2026-11-15", "text": "closed"}], "holidays": [{"date": "2026-11-26"}],
              "show": {"moonrise": True, "rahu_kaal": True}}
    html = calendar_design.render_calendar(2026, [11], 28.61, 77.2, "Asia/Kolkata", design, "hi")
    assert html.count('class="page"') == 1 and "Test Ad" in html and "Biz &lt;b&gt;" in html
    assert "javascript:alert" not in html and 'class="note"' in html and "holiday" in html
    assert "size: 297mm 210mm" in html and "#283593" in html
    en = calendar_design.render_calendar(2026, [1, 2], 28.61, 77.2, "Asia/Kolkata", {}, "en")
    assert en.count('class="page"') == 2 and "January" in en and "Vikram samvat" in en
    out = handlers.calendar_report_from_payload({"year": 2026, "month": "all", "lat": 22.35, "lon": 82.68, "tz": "Asia/Kolkata", "design": {}})
    assert out.count('class="page"') == 12
    with pytest.raises(handlers.BadRequest):
        handlers.calendar_report_from_payload({"year": 2026, "month": 13, "lat": 22.35, "lon": 82.68})
    with pytest.raises(handlers.BadRequest):
        handlers.calendar_report_from_payload({"year": 2026, "month": 1, "lat": 22.35, "lon": 82.68, "design": {"notes": "x"}})
    with pytest.raises(handlers.BadRequest):
        handlers.panchang_month_from_query({"year": "2026", "month": "0"})
