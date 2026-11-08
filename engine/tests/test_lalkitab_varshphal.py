import pytest

from jyotish import compute_chart, handlers, lalkitab

C = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)


def test_house_lookup_prefers_table_then_verified_column_then_rotation():
    data = {"table": {"1": [7] * 35}, "verified_columns": {"11": {"2": 12}}}
    assert lalkitab.varshphal_house(1, 3, data) == (7, "table")
    assert lalkitab.varshphal_house(2, 11, data) == (12, "verified_column")
    assert lalkitab.varshphal_house(2, 46, data) == (12, "verified_column")        # cycle wraps every 35 years
    assert lalkitab.varshphal_house(3, 2, data) == (4, "rotation") and lalkitab.varshphal_house(12, 2, data) == (1, "rotation")


def test_varshphal_uses_published_example_column():
    v = lalkitab.varshphal(C, 2000)                                            # 11th year of life
    assert v["year_of_life"] == 11 and v["cycle_year"] == 11 and v["method"] == "mixed"
    sun = next(p for p in v["planets"] if p["name"] == "Sun")
    assert sun["natal_house"] == 2 and sun["annual_house"] == 12                # verified column: house 2 -> 12
    assert "सत्यापित" in v["method_note_hi"]
    v2 = lalkitab.varshphal(C, 2026)
    assert v2["method"] == "rotation" and "मूल लाल किताब" in v2["method_note_hi"] and v2["review_status"] == "unverified"
    with pytest.raises(ValueError):
        lalkitab.varshphal(C, 1980)
    out = handlers.lalkitab_varshphal_from_payload({"date": "1990-05-17", "time": "06:45", "tz": "Asia/Kolkata", "lat": 23.18, "lon": 79.99, "year": 2000})
    assert out["cycle_year"] == 11
