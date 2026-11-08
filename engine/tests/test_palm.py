import json
import re
from pathlib import Path

import pytest

from jyotish import handlers, palm

K = json.loads((Path(__file__).resolve().parents[2] / "data" / "knowledge" / "palm.json").read_text(encoding="utf-8"))


def test_catalog_is_complete():
    keys = [f["key"] for f in K["features"]]
    assert len(keys) == len(set(keys)) == 16
    for f in K["features"]:
        assert f["where_hi"] and len(f["options"]) >= 2
        for o in f["options"].values():
            assert o["hi"] and o["meaning_hi"]
    assert sum(f["group"] == "पर्वत" for f in K["features"]) == 6


def test_no_lifespan_or_health_predictions():
    text = json.dumps(K, ensure_ascii=False)
    for bad in ("मृत्यु", "बीमारी", "रोग", "कैंसर", "अल्पायु", "दीर्घायु"):
        assert bad not in text, bad
    # the life line must say plainly that it is not about lifespan
    life = [o["meaning_hi"] for f in K["features"] if f["key"] == "life_length" for o in f["options"].values()]
    assert any("आयु" in m for m in life)


def test_read_orders_and_groups():
    r = palm.read({"mount_moon": "prominent", "life_length": "long", "hand_shape": "water"})
    assert [t["feature"] for t in r["traits"]] == ["hand_shape", "life_length", "mount_moon"]
    assert set(r["groups"]) == {"हाथ", "जीवन रेखा", "पर्वत"} and r["count"] == 3
    assert r["disclaimer_hi"]


def test_validation():
    for bad in (None, {}, {"nope": "x"}, {"life_length": "huge"}):
        with pytest.raises(handlers.BadRequest):
            handlers.palm_from_payload({"choices": bad})
    assert len(palm.catalog()["features"]) == 16
