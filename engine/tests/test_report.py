import pytest

from jyotish import compute_chart, handlers, report


def test_report_contains_all_sections_and_is_escaped():
    html = handlers.report_from_payload({"date": "1990-05-17", "time": "06:45", "tz": "Asia/Kolkata",
                                         "lat": 23.18, "lon": 79.99, "name": "<script>alert(1)</script>"})
    assert "<script>" not in html and "&lt;script&gt;" in html
    for needle in ("सारांश", "लग्न कुंडली (D1)", "नवांश (D9)", "ग्रह स्थिति", "पंचांग", "विंशोत्तरी दशा",
                   "अष्टकवर्ग", "गोचर", "योग और दोष", "ड्राफ़्ट"):
        assert needle in html, needle
    assert html.count("<svg") == 2 and html.count("<polygon") == 24
    assert "विकास-संस्करण" in html          # dev backend is flagged in the report


def test_north_chart_places_planets_in_houses():
    c = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)
    cells = report._d1_cells(c)
    assert len(cells) == 12 and sum(len(x["planets"]) for x in cells) == 9
    assert [x["sign"] for x in cells] == [h["sign"] for h in c["houses"]]


def test_bad_input_is_rejected():
    with pytest.raises(handlers.BadRequest):
        handlers.report_from_payload({"date": "nope"})
