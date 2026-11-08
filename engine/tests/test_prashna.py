from datetime import datetime, timezone

import pytest

from jyotish import handlers, prashna as P
from jyotish.ephemeris import AnalyticBackend

WHEN = datetime(2026, 11, 8, 12, 59, tzinfo=timezone.utc)


def test_kp_number_table():
    assert P.lagna_from_kp_number(1) == 0.0
    assert abs(P.lagna_from_kp_number(10) - 360 / 27) < 1e-9          # Bharani starts at number 10
    assert P.lagna_from_kp_number(249) > 359.0
    with pytest.raises(ValueError):
        P.lagna_from_kp_number(250)


def test_prashna_verdict_consistency():
    for topic in P.TOPICS:
        r = P.prashna(topic, WHEN, 23.18, 79.99, AnalyticBackend(), "Asia/Kolkata")
        fav, den = set(r["favour_hit"]), set(r["deny_hit"])
        assert fav <= set(P.TOPICS[topic]["favour"]) and den <= set(P.TOPICS[topic]["deny"])
        expect = "favourable" if fav and not den else "unfavourable" if den and not fav else "mixed" if fav and den else "unclear"
        assert r["verdict"] == expect and r["cusp_sub_lord"] in r["planets"] and len(r["cusps"]) == 12
        assert r["ruling_planets"]["ranked"] and r["disclaimer_hi"]
    n = P.prashna("job", WHEN, 23.18, 79.99, AnalyticBackend(), "Asia/Kolkata", kp_number=108)
    assert abs(n["cusps"][0]["degree_in_sign"] + n["cusps"][0]["sign"] * 30 - P.lagna_from_kp_number(108)) < 1e-6


def test_handler_validation():
    out = handlers.prashna_from_payload({"topic": "marriage", "lat": 23.18, "lon": 79.99, "tz": "Asia/Kolkata", "when": "2026-11-08 18:29", "kp_number": 7})
    assert out["kp_number"] == 7 and out["at"].startswith("2026-11-08T12:59")
    for bad in ({"topic": "x", "lat": 1, "lon": 1}, {"topic": "job", "lat": 1, "lon": 1, "kp_number": 300}, {"topic": "job", "lat": 1, "lon": 1, "when": "yesterday"}):
        with pytest.raises(handlers.BadRequest):
            handlers.prashna_from_payload(bad)


def test_prashna_and_muhurta_reports_render():
    import re
    from jyotish import i18n
    base = {"lat": 23.18, "lon": 79.99, "tz": "Asia/Kolkata"}
    h = handlers.prashna_report_from_payload({"topic": "job", "when": "2026-11-08 18:29", **base})
    assert "प्रश्न कुंडली" in h and "<table" in h
    en = handlers.prashna_report_from_payload({"topic": "job", "when": "2026-11-08 18:29", "lang": "en", **base})
    left = [t for t in re.findall(r">([^<>]+)<", en) if re.search(r"[ऀ-ॿ]", t)]
    assert '<html lang="en">' in en and left == [], left
    m = handlers.muhurta_report_from_payload({"activity": "travel", "start": "2026-11-08", "days": 7, **base})
    assert "मुहूर्त खोज" in m and m.count("<table") == 2
    men = handlers.muhurta_report_from_payload({"activity": "travel", "start": "2026-11-08", "days": 7, "lang": "en", **base})
    left = [t for t in re.findall(r">([^<>]+)<", men) if re.search(r"[ऀ-ॿ]", t)]
    assert left == [], left


def test_small_reports_render_in_both_languages():
    import re
    cases = [("numerology_report_from_payload", {"date": "1990-05-17", "name": "Prashant"}, "अंक ज्योतिष"),
             ("tarot_report_from_payload", {"spread": "three", "seed": 1, "question": "work"}, "टैरो पठन"),
             ("vastu_report_from_payload", {"items": [{"room": "kitchen", "direction": "SE"}, {"room": "pooja", "direction": "SW"}]}, "वास्तु जाँच"),
             ("palm_report_from_payload", {"choices": {"hand_shape": "earth", "life_length": "long"}}, "हस्तरेखा")]
    for fn, payload, title in cases:
        h = getattr(handlers, fn)(payload)
        assert title in h and "<table" in h, fn
        en = getattr(handlers, fn)({**payload, "lang": "en"})
        left = [t for t in re.findall(r">([^<>]+)<", en) if re.search(r"[ऀ-ॿ]", t) and len(t.strip()) > 2]
        assert '<html lang="en">' in en and left == [], (fn, left)
    assert set(handlers.REPORT_ROUTES) >= {"/v1/numerology/report", "/v1/tarot/report", "/v1/vastu/report", "/v1/palm/report"}
