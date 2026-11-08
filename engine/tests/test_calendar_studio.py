"""Monthly panchang and the printable calendar pages."""
import pytest

from jyotish import calendar_design, handlers, panchang_month


def test_month_rows():
    m = panchang_month.month(2026, 11, 28.61, 77.2, "Asia/Kolkata")
    assert len(m["days"]) == 30 and m["first_weekday"] == 0           # 1 Nov 2026 is a Sunday
    d8 = next(d for d in m["days"] if d["day"] == 8)
    assert d8["vara"] == "Ravivara" and d8["tithi"] == "Chaturdashi" and d8["paksha"] == "Krishna"
    assert any(e["key"] == "diwali" for e in d8["events"]) and d8["moonrise"] and d8["tithi_ends"]
    assert d8["yoga_ends"] and d8["karana_ends"] and d8["moon_sign"] == "Tula" and d8["disha_shool"] == "West" and d8["yamaganda"] and d8["good_choghadiya"]
    assert any(x["planet"] == "Sun" and x["sign"] == "Vrishchika" for x in m["ingress"]) and not any(x["planet"] == "Moon" for x in m["ingress"])
    assert m["muhurta"] and all(1 <= y["day"] <= 30 for x in m["muhurta"] for y in x["dates"])
    specials = {s["key"] for d in m["days"] for s in d["special"]}
    assert {"sarvartha_siddhi", "gand_mool", "panchak", "bhadra"} <= specials
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
    assert html.count('class="page ') == 1 and "Test Ad" in html and "Biz &lt;b&gt;" in html
    assert "javascript:alert" not in html and 'class="note"' in html and "holiday" in html
    assert "size: 297mm 210mm" in html and "#283593" in html
    for tpl in ("modern", "poster", "panchang", "compact"):
        h = calendar_design.render_calendar(2026, [11, 12], 28.61, 77.2, "Asia/Kolkata", {"template": tpl, "cover": True, "accent": "#0b7285", "background": "dark", "ad_side": {"enabled": True, "title": "Side"}, "web_fonts": False}, "hi")
        assert h.count('class="page ') == (2 if tpl == "compact" else 3) and "--accent:#0b7285" in h and "Side" in h and "fonts.googleapis" not in h
    pan = calendar_design.render_calendar(2026, [11], 28.61, 77.2, "Asia/Kolkata", {"template": "panchang"}, "hi")
    assert "शुभ मुहूर्त" in pan and "ग्रह गोचर" in pan and "सर्वार्थ सिद्धि" in pan and pan.count("<tr") >= 31
    en = calendar_design.render_calendar(2026, [1, 2], 28.61, 77.2, "Asia/Kolkata", {}, "en")
    assert en.count('class="page ') == 2 and "January" in en and "Vikram samvat" in en
    out = handlers.calendar_report_from_payload({"year": 2026, "month": "all", "lat": 22.35, "lon": 82.68, "tz": "Asia/Kolkata", "design": {}})
    assert out.count('class="page ') == 12
    with pytest.raises(handlers.BadRequest):
        handlers.calendar_report_from_payload({"year": 2026, "month": 13, "lat": 22.35, "lon": 82.68})
    with pytest.raises(handlers.BadRequest):
        handlers.calendar_report_from_payload({"year": 2026, "month": 1, "lat": 22.35, "lon": 82.68, "design": {"notes": "x"}})
    with pytest.raises(handlers.BadRequest):
        handlers.panchang_month_from_query({"year": "2026", "month": "0"})
