import json

import pytest

from jyotish import compute_chart, lalkitab as lk

CH = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)


def test_tables_are_complete_and_consistent():
    kb = lk._kb()
    nine = {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"}
    assert set(kb["pakka_ghar"]) == nine == set(kb["upay_hi"])
    assert all(1 <= h <= 12 for h in kb["pakka_ghar"].values())
    assert set(kb["house_theme_hi"]) == {str(i) for i in range(1, 13)}
    for p, h in kb["exalt_house"].items():                    # opposite houses
        assert (h + 6 - 1) % 12 + 1 == kb["debil_house"][p]


def test_exalt_houses_match_zodiac_counting():
    from jyotish.constants import EXALTATION
    kb = lk._kb()
    for p, h in kb["exalt_house"].items():
        assert EXALTATION[p] + 1 == h


def test_chart_views():
    out = CH["lalkitab"]
    assert len(out["planets"]) == 9
    for r in out["planets"]:
        pl = next(p for p in CH["planets"] if p["name"] == r["name"])
        assert r["views"]["lagna"]["house"] == pl["house"]
        assert r["views"]["aries"]["house"] == pl["sign"] + 1
        assert r["views"]["lagna"]["status"] in ("pakka", "exalted", "debilitated", "other")
        assert r["upay_hi"].startswith("परंपरागत उपाय")


def test_status_rules():
    kb = lk._kb()
    assert lk._status(kb, "Sun", 1) == "pakka" and lk._status(kb, "Saturn", 7) == "exalted"
    assert lk._status(kb, "Saturn", 1) == "debilitated" and lk._status(kb, "Moon", 9) == "other"


def test_no_frightening_words_and_disclaimer():
    text = json.dumps(CH["lalkitab"], ensure_ascii=False)
    for bad in ("मृत्यु", "आयु", "रोग", "बीमारी", "दुर्घटना", "शाप", "श्राप", "ऋण", "बर्बाद", "तबाह"):
        assert bad not in text
    assert "वैज्ञानिक प्रमाण नहीं" in CH["lalkitab"]["disclaimer_hi"]
    assert CH["lalkitab"]["review_status"] == "draft"
