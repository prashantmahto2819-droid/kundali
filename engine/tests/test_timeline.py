import re
from datetime import datetime, timezone

from jyotish import compute_chart, timeline

WHEN = datetime(2026, 11, 8, tzinfo=timezone.utc)


def chart():
    return compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99, as_of=WHEN)


def test_phases_and_continuity():
    t = chart()["timeline"]
    ps = t["periods"]
    assert [p["phase"] for p in ps].count("running") == 1
    run = next(p for p in ps if p["phase"] == "running")
    assert run["lord"] == "Jupiter" and run["start"] < "2026-11-08" < run["end"]
    assert all(a["end"] == b["start"] for a, b in zip(ps, ps[1:]))
    order = {"past": 0, "running": 1, "future": 2}
    assert [order[p["phase"]] for p in ps] == sorted(order[p["phase"]] for p in ps)
    assert all(p["age_start"] <= timeline.MAX_START_AGE for p in ps)
    ads = run["antardashas"]
    assert ads and sum(a["phase"] == "running" for a in ads) == 1
    assert ads[0]["start"] == run["start"] and ads[-1]["end"] == run["end"]


def test_lord_profile_scoring_is_transparent():
    c = chart()
    for p in c["timeline"]["periods"]:
        pr = p["profile"]
        assert pr["tag"] in ("favourable", "mixed", "demanding")
        assert (pr["score"] >= 2) == (pr["tag"] == "favourable") and (pr["score"] <= -2) == (pr["tag"] == "demanding")
        if pr["lord"] in ("Rahu", "Ketu"):
            assert pr["owns"] == [] and pr["bindus"] is None
        else:
            assert pr["owns"], pr["lord"]
    # a lord owns 1 or 2 houses and every house has exactly one lord
    owned = [h for lord in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
             for h in timeline.lord_profile(c, lord)["owns"]]
    assert sorted(owned) == list(range(1, 13))


def test_text_is_hindi_and_free_of_fear_words():
    c = chart()
    for p in c["timeline"]["periods"]:
        assert re.search(r"[ऀ-ॿ]", p["text_hi"])
        for bad in ("आयु", "मृत्यु", "रोग", "बीमारी", "दुर्घटना", "शत्रु", "ऋण", "हानि"):
            assert bad not in p["text_hi"], (p["lord"], bad)
    assert "भविष्यवाणी नहीं" in c["timeline"]["note_hi"]
