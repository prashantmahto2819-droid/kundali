import json
from pathlib import Path
from zoneinfo import ZoneInfo

from jyotish import compute_chart, handlers, places

DATA = json.loads((Path(__file__).resolve().parents[2] / "data" / "places.json").read_text(encoding="utf-8"))["places"]


def test_dataset_is_valid():
    names = [p["name"] for p in DATA]
    assert len(names) == len(set(names)) and len(DATA) >= 100
    for p in DATA:
        ZoneInfo(p["tz"])
        assert -90 <= p["lat"] <= 90 and -180 <= p["lon"] <= 180
        if p["tz"] == "Asia/Kolkata":     # every Indian place must be inside India's bounding box
            assert 6 < p["lat"] < 36 and 68 < p["lon"] < 98, p["name"]


def test_search_names_aliases_and_hindi():
    assert places.search("Jabalpur")[0]["name"] == "Jabalpur"
    assert places.search("jab")[0]["name"] == "Jabalpur"
    assert places.search("Bombay")[0]["name"] == "Mumbai"
    assert places.search("बनारस")[0]["name"] == "Varanasi"
    assert places.search("allahabad")[0]["name"] == "Prayagraj"
    assert places.search("zzzz") == [] and places.search("") == []
    assert len(places.search("a", limit=3)) == 3


def test_handler_and_every_place_computes_a_chart():
    assert handlers.places_from_query("delhi")["results"][0]["name"] == "Delhi"
    for p in DATA:
        c = compute_chart("1995-03-10", "10:30", p["tz"], p["lat"], p["lon"])
        assert 0 <= c["lagna"]["longitude"] < 360
