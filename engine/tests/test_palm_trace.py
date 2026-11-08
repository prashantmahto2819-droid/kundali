"""Palm photo tracing → measurements, implied choices, marks, extras."""
import pytest

from jyotish import handlers, palm, palm_trace as pt

LM = {"wrist": [300, 760], "index": [180, 260], "middle": [270, 230], "ring": [360, 240], "little": [440, 280], "thumb": [120, 480]}
WIDE = [[200, 300], [170, 400], [200, 520], [240, 640], [280, 720]]
NARROW = [[200, 300], [150, 400], [140, 520], [170, 640], [230, 720]]
SHORT = [[200, 300], [170, 400], [190, 480]]


def test_life_line_reach_and_sweep():
    m, c, _ = pt.measure(LM, {"life": WIDE})
    assert c["life_length"] == "long" and c["life_curve"] == "wide" and m["life_reach"] > 0.85
    _, c2, _ = pt.measure(LM, {"life": NARROW})
    assert c2["life_curve"] == "narrow"
    _, c3, _ = pt.measure(LM, {"life": SHORT})
    assert c3["life_length"] == "short"


def test_head_heart_fate_sun():
    lines = {"head": [[190, 330], [280, 350], [380, 380], [450, 430]], "heart": [[470, 330], [380, 300], [290, 290], [210, 300]],
             "fate": [[300, 720], [295, 560], [290, 400]], "sun": []}
    m, c, _ = pt.measure(LM, lines)
    assert c["head_length"] == "long" and c["head_slope"] == "sloping"
    assert c["heart_end"] == "between" and c["heart_shape"] == "straight"
    assert c["fate"] == "clear" and c["sun_line"] == "absent"
    _, c2, _ = pt.measure(LM, {"head": [[190, 330], [260, 335], [330, 338]], "heart": [[470, 330], [380, 250], [290, 250], [175, 290]]})
    assert c2["head_length"] == "short" and c2["head_slope"] == "straight" and c2["heart_end"] == "index" and c2["heart_shape"] == "curved"
    _, c3, _ = pt.measure(LM, {"heart": [[470, 330], [380, 300], [300, 300]]})
    assert c3["heart_end"] == "middle"


def test_trace_combines_implied_and_manual_choices():
    r = pt.trace({"landmarks": LM, "lines": {"life": WIDE}, "choices": {"life_depth": "deep", "mount_jupiter": "prominent"},
                  "marks": [{"line": "life", "type": "island", "x": 170, "y": 400}], "extras": {"union_lines": 2, "bracelets": 3, "travel_lines": 0}})
    assert r["choices"]["life_length"] == "long" and r["choices"]["life_depth"] == "deep"
    assert r["reading"]["count"] == 4 and "जीवन रेखा" in r["reading"]["groups"]
    assert r["marks"][0]["text_hi"].startswith("जीवन रेखा पर द्वीप") and r["marks"][0]["text_en"].startswith("Island on the life line")
    by = {x["key"]: x for x in r["extras"]}
    assert by["union_lines"]["count"] == 2 and "विवाहों की गिनती नहीं" in by["union_lines"]["text_hi"]
    assert by["bracelets"]["count"] == 3 and by["travel_lines"]["count"] == 0
    assert r["lines_traced"] == ["life"] and r["review_status"] == "draft" and r["trace_note_hi"]


def test_validation_and_safety():
    with pytest.raises(ValueError):
        pt.trace({"landmarks": {"wrist": [0, 0]}, "lines": {}})
    with pytest.raises(ValueError):
        pt.trace({"landmarks": LM, "lines": {"moon": [[1, 2]]}})
    with pytest.raises(ValueError):
        pt.trace({"landmarks": LM, "lines": {}, "marks": [{"line": "life", "type": "comet"}]})
    with pytest.raises(handlers.BadRequest):
        handlers.palm_trace_from_payload({"landmarks": LM, "lines": {}, "extras": {"wings": 1}})
    K = palm.knowledge()
    banned = ("मृत्यु", "मौत", "बीमारी", "रोग", "आयु", "death", "die", "illness", "disease", "lifespan")
    for m in K["marks"].values():
        for t in (m["hi_t"], m["en_t"]):
            assert not any(b in t.lower() for b in banned), t
    for x in K["extras"].values():
        for b in x["bands"]:
            assert not any(w in (b["hi"] + b["en"]).lower() for w in banned)
    html = handlers.palm_trace_report_from_payload({"landmarks": LM, "lines": {"life": WIDE}, "lang": "en"})
    assert "Palmistry" in html and "life line" in html.lower()
    cat = handlers.palm_trace_catalog()
    assert len(cat["landmarks"]) == 6 and "island" in cat["marks"] and "union_lines" in cat["extras"]
