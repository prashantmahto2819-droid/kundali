import pytest

from jyotish import handlers, tarot


def test_deck_is_complete_and_unique():
    d = tarot.deck()
    assert len(d) == 78
    assert len({c["id"] for c in d}) == 78 and len({c["name"] for c in d}) == 78
    assert sum(c["arcana"] == "major" for c in d) == 22
    for suit in ("Wands", "Cups", "Swords", "Pentacles"):
        assert sum(c["suit"] == suit for c in d) == 14
    assert all(c["upright"] and c["reversed"] and c["upright_hi"] and c["reversed_hi"] for c in d)
    assert any(c["name"] == "Queen of Cups" for c in d) and any(c["name"] == "Ace of Pentacles" for c in d)


@pytest.mark.parametrize("spread,n", [("single", 1), ("three", 3), ("celtic", 10)])
def test_spread_sizes_and_no_repeats(spread, n):
    r = tarot.draw(spread, seed=1)
    ids = [c["card"]["id"] for c in r["cards"]]
    assert len(ids) == n and len(set(ids)) == n


def test_seed_is_deterministic_and_reversals_switch():
    a, b = tarot.draw("celtic", seed="x"), tarot.draw("celtic", seed="x")
    assert a["cards"] == b["cards"]
    assert tarot.draw("celtic", seed=2)["cards"] != a["cards"]
    assert not any(c["reversed"] for c in tarot.draw("celtic", seed=3, reversals=False)["cards"])
    r = tarot.draw("celtic", seed=4)
    for c in r["cards"]:
        full = next(x for x in tarot.deck() if x["id"] == c["card"]["id"])
        assert c["meaning"] == (full["reversed"] if c["reversed"] else full["upright"])


def test_reversals_are_roughly_balanced():
    flips = sum(c["reversed"] for s in range(200) for c in tarot.draw("three", seed=s)["cards"])
    assert 240 < flips < 360   # 600 cards, expect about 300


def test_handler_validation():
    assert len(handlers.tarot_from_payload({"spread": "three", "seed": 5})["cards"]) == 3
    with pytest.raises(handlers.BadRequest):
        handlers.tarot_from_payload({"spread": "nope"})
    with pytest.raises(handlers.BadRequest):
        handlers.tarot_from_payload({"question": "x" * 301})
    with pytest.raises(handlers.BadRequest):
        handlers.tarot_from_payload({"seed": [1]})
