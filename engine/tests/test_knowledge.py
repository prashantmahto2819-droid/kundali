import json
from pathlib import Path

from jyotish import constants as C
from jyotish import matching as M
from jyotish.core import nakshatra_of

K = Path(__file__).resolve().parents[2] / "data" / "knowledge"


def load(n):
    return json.loads((K / n).read_text(encoding="utf-8"))


def test_nakshatras_consistent_with_engine():
    naks = load("nakshatras.json")["nakshatras"]
    assert len(naks) == 27
    for i, n in enumerate(naks):
        mid = (i + 0.5) * 360 / 27
        eng = nakshatra_of(mid)
        assert n["name"] == eng["name"] == C.NAKSHATRAS[i]
        assert n["lord"] == eng["lord"], n["name"]
        assert n["gana"] == M._GANA[i]
        assert n["traits_hi"] and n["deity_hi"] and n["symbol_hi"]
    assert [n["lord"] for n in naks[:9]] == list(C.DASHA_ORDER)


def test_signs_consistent_with_engine():
    signs = load("signs.json")["signs"]
    assert [s["name"] for s in signs] == C.SIGNS and [s["lord"] for s in signs] == C.SIGN_LORDS
    for el in ("अग्नि", "पृथ्वी", "वायु", "जल"):
        assert sum(s["element_hi"] == el for s in signs) == 3
    for q in ("चर", "स्थिर", "द्विस्वभाव"):
        assert sum(s["modality_hi"] == q for s in signs) == 4
    # elements cycle fire, earth, air, water; modalities cycle movable, fixed, dual
    assert [s["element_hi"] for s in signs[:4]] == ["अग्नि", "पृथ्वी", "वायु", "जल"]


def test_planets_have_hindi_why():
    planets = load("planets.json")["planets"]
    assert set(planets) >= {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"}
    assert all(p.get("why_hi") and p.get("nature_hi") for p in planets.values())
