"""Year overlay: dasha x Saturn/Jupiter double transit."""
from jyotish import compute_chart, timeline
from jyotish.ephemeris import AnalyticBackend

B = AnalyticBackend()


def test_influenced_houses():
    # Saturn in the Lagna sign influences 1, 3, 7, 10; Jupiter in the 5th influences 5, 9, 11, 1
    assert timeline._influenced(0, 0, timeline.SAT_ASPECTS) == {1, 3, 7, 10}
    assert timeline._influenced(4, 0, timeline.JUP_ASPECTS) == {5, 9, 11, 1}


def test_overlay_rows():
    c = compute_chart("1991-04-09", "16:30", "Asia/Kolkata", 22.35, 82.68, backend=B)
    ov = c["timeline"]["overlay"]
    rows = ov["rows"]
    assert rows[0]["year"] == 1991 and rows[0]["age"] == 0 and len(rows) >= 80
    assert all(r["age"] == r["year"] - 1991 for r in rows)
    r2022 = next(r for r in rows if r["year"] == 2022)
    assert r2022["mahadasha"] == "Jupiter" and r2022["antardasha"] == "Saturn" and r2022["sade_sati"] is True
    assert set(r2022["double_transit"]) == {7, 11} and 7 in r2022["key_houses"] and set(r2022["dasha_supports"]) <= set(r2022["key_houses"])
    for r in rows:
        assert set(r["double_transit"]) == timeline._influenced(r["saturn_sign"], c["lagna"]["sign"], timeline.SAT_ASPECTS) & timeline._influenced(r["jupiter_sign"], c["lagna"]["sign"], timeline.JUP_ASPECTS)
        assert 1 <= r["saturn_house"] <= 12 and 1 <= r["jupiter_house"] <= 12
    # Sade Sati flags agree with the lifetime windows
    windows = c["life_transits"]["sade_sati_windows"]
    for r in rows:
        inside = any(w["start"] <= f"{r['year']}-07-01" < w["end"] for w in windows)
        assert r["sade_sati"] == inside, r["year"]
    assert ov["note_hi"] and "7" in ov["key_houses"] or 7 in ov["key_houses"]
