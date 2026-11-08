"""Birth-time rectification aid."""
import pytest

from jyotish import handlers
from jyotish.rectify import EVENT_HOUSES, rectify

KORBA = dict(date="1991-04-09", time_hhmm="16:30", tz="Asia/Kolkata", lat=22.35, lon=82.68)


def test_windows_tile_the_range_and_exactly_one_contains_given_time():
    r = rectify(**KORBA, range_min=60, step_min=2)
    w = r["windows"]
    assert w[0]["from_offset_min"] == -60 and w[-1]["to_offset_min"] == 60
    for a, b in zip(w, w[1:]):
        assert b["from_offset_min"] == a["to_offset_min"] + 2          # consecutive, no gaps or overlaps
    assert sum(x["contains_given_time"] for x in w) == 1
    assert all(x["from"] <= x["to"] or x["from"] > "23" for x in w)  # local clock times
    assert r["ranked"] == [] and r["review_status"] == "draft"


def test_signature_changes_between_windows():
    r = rectify(**KORBA, range_min=90, step_min=2)
    sigs = [(x["lagna"], x["navamsa_lagna"], x["moon_nakshatra"]) for x in r["windows"]]
    assert all(a != b for a, b in zip(sigs, sigs[1:]))
    # the given time is in Kanya lagna with a Simha stretch earlier in the window (sign boundary ~25 min before)
    given = next(x for x in r["windows"] if x["contains_given_time"])
    assert given["lagna"] == "Kanya"
    assert any(x["lagna"] == "Simha" for x in r["windows"] if x["to_offset_min"] < given["from_offset_min"])
    assert given["from"] == "16:04" or given["from"] <= "16:30" <= given["to"]


def test_event_scoring_counts_and_ranks():
    events = [{"type": "marriage", "year": 2018}, {"type": "job", "year": 2014}]
    r = rectify(**KORBA, range_min=60, step_min=2, events=events)
    for x in r["windows"]:
        assert 0 <= x["event_hits"] <= 2 and len(x["event_detail"]) == 2
        for d in x["event_detail"]:
            assert d["type"] in EVENT_HOUSES and len(d["lords"]) == 2 and d["lords_hi"]
    hits = [x["event_hits"] for x in r["ranked"]]
    assert hits == sorted(hits, reverse=True) and len(r["ranked"]) <= 5
    assert r["ranked"][0]["event_hits"] == max(x["event_hits"] for x in r["windows"])


def test_handler_validation():
    base = {"date": "1991-04-09", "time": "16:30", "tz": "Asia/Kolkata", "lat": 22.35, "lon": 82.68}
    out = handlers.rectify_from_payload({**base, "range_min": 30, "step_min": 5, "events": [{"type": "marriage", "year": "2018"}]})
    assert out["range_min"] == 30 and out["step_min"] == 5 and out["events"][0]["month"] == 7
    with pytest.raises(handlers.BadRequest):
        handlers.rectify_from_payload({**base, "range_min": 2})
    with pytest.raises(handlers.BadRequest):
        handlers.rectify_from_payload({**base, "events": [{"type": "lottery", "year": 2018}]})
    with pytest.raises(handlers.BadRequest):
        handlers.rectify_from_payload({**base, "events": [{"type": "job", "year": "soon"}]})
    with pytest.raises(handlers.BadRequest):
        handlers.rectify_from_payload({"date": "1991-04-09"})
