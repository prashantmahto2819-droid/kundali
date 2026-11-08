import json
from pathlib import Path

import pytest

from jyotish import compute_chart, handlers, lalkitab

C = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)
DATA = json.loads((Path(__file__).resolve().parents[2] / "data" / "lalkitab_varshphal.json").read_text(encoding="utf-8"))


def test_table_shape_and_published_example():
    rows = DATA["rows_by_year"]
    assert len(rows) == 120 and all(len(rows[str(y)]) == 12 for y in range(1, 121))
    # every row is a permutation of 1..12 except the two printed typos the source carries
    bad = [y for y in range(1, 121) if sorted(rows[str(y)]) != list(range(1, 13))]
    assert bad == [76, 96] and set(DATA["source_typos"]) == {"76", "96"}
    # the published worked example (46th year) matches the transcribed row exactly
    assert rows["46"] == [DATA["verified_against"]["46"][str(h)] for h in range(1, 13)]
    assert rows["1"] == [1, 9, 10, 3, 5, 2, 11, 7, 6, 12, 4, 8]


def test_house_lookup_and_wrap():
    assert lalkitab.varshphal_house(2, 46) == (12, "table") and lalkitab.varshphal_house(1, 1) == (1, "table")
    assert lalkitab.varshphal_house(2, 166) == (12, "table")                 # repeats after 120 (assumption)
    assert lalkitab.varshphal_house(3, 2, {"rows_by_year": {}}) == (4, "rotation")


def test_varshphal_for_a_chart():
    v = lalkitab.varshphal(C, 2035)                                           # 46th year of life
    assert v["year_of_life"] == 46 and v["method"] == "table" and v["review_status"] == "transcribed"
    sun = next(p for p in v["planets"] if p["name"] == "Sun")
    assert sun["natal_house"] == 2 and sun["annual_house"] == 12
    assert "120" in v["method_note_hi"] and v["source_typo"] is None
    assert lalkitab.varshphal(C, 2065)["source_typo"]                          # year 76 carries the source-typo note
    with pytest.raises(ValueError):
        lalkitab.varshphal(C, 1980)
    out = handlers.lalkitab_varshphal_from_payload({"date": "1990-05-17", "time": "06:45", "tz": "Asia/Kolkata", "lat": 23.18, "lon": 79.99, "year": 2035})
    assert out["year_of_life"] == 46
