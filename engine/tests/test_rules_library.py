import json
from pathlib import Path

from jyotish import compute_chart
from jyotish.rules import load_rules

FILE = Path(__file__).resolve().parents[2] / "data" / "rules" / "planet_in_house.json"


def test_library_is_complete_and_safe():
    rules = json.loads(FILE.read_text(encoding="utf-8"))["rules"]
    assert len(rules) == 108 and len({r["id"] for r in rules}) == 108
    pairs = {(r["when"]["planet"], r["when"]["house"]) for r in rules}
    assert len(pairs) == 108
    for r in rules:
        assert r["review_status"] == "draft" and r["source"]["text"] and r["text_hi"]
    blob = json.dumps(rules, ensure_ascii=False)
    for bad in ("मृत्यु", "बीमारी", "रोग", "कैंसर", "दरिद्र", "विनाश"):
        assert bad not in blob, bad
    assert "मंगल-दोष" in next(r for r in rules if r["id"] == "mars_in_7")["text_hi"]
    assert "मंगल-दोष" not in next(r for r in rules if r["id"] == "mars_in_3")["text_hi"]


def test_every_planet_gets_exactly_one_reading():
    c = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)
    assert len(c["readings"]) == 9
    assert sorted(r["planet"] for r in c["readings"]) == sorted(p["name"] for p in c["planets"])
    assert len(load_rules()) == 108
