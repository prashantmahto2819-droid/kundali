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
