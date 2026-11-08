import json
from pathlib import Path

import pytest

from jyotish import handlers, vastu

K = json.loads((Path(__file__).resolve().parents[2] / "data" / "knowledge" / "vastu.json").read_text(encoding="utf-8"))


def test_data_is_consistent():
    dirs = set(K["directions"])
    assert dirs == {"N", "NE", "E", "SE", "S", "SW", "W", "NW", "C"}
    for key, r in K["rooms"].items():
        lists = [set(r["ideal"]), set(r["ok"]), set(r["avoid"])]
        assert all(l <= dirs for l in lists), key
        assert not (lists[0] & lists[1] or lists[0] & lists[2] or lists[1] & lists[2]), key
        assert r["ideal"] and r["avoid"] and r["why_hi"] and r["fix_hi"], key


def test_compass_degrees():
    assert [vastu.direction_from_degrees(d) for d in (0, 45, 90, 135, 180, 225, 270, 315, 359.9, 22.4, 22.6)] == \
           ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N", "N", "NE"]


def test_classic_cases():
    assert vastu.rate("kitchen", "SE") == "ideal" and vastu.rate("kitchen", "NE") == "avoid"
    assert vastu.rate("pooja", "NE") == "ideal" and vastu.rate("toilet", "NE") == "avoid"
    assert vastu.rate("master_bedroom", "SW") == "ideal" and vastu.rate("kitchen", "S") == "neutral"


def test_evaluate_scores_and_fix_only_for_avoid():
    r = vastu.evaluate([{"room": "kitchen", "direction": "SE"}, {"room": "toilet", "degrees": 45}])
    assert r["score"] == 2 - 2 and r["max"] == 4 and r["avoid_count"] == 1
    assert "fix_hi" not in r["items"][0] and "fix_hi" in r["items"][1]
    assert r["items"][1]["direction"] == "NE"


def test_handler_validation():
    assert handlers.vastu_from_payload({"items": [{"room": "pooja", "direction": "NE"}]})["score"] == 2
    for bad in ({}, {"items": []}, {"items": [{"room": "x", "direction": "N"}]},
                {"items": [{"room": "pooja", "direction": "Q"}]}, {"items": [{"room": "pooja"}]}):
        with pytest.raises(handlers.BadRequest):
            handlers.vastu_from_payload(bad)
    assert "kitchen" in handlers.vastu_catalog()["rooms"]
