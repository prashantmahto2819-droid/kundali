import json
from pathlib import Path

from jyotish import compute_chart
from jyotish.rules import load_rules

FILE = Path(__file__).resolve().parents[2] / "data" / "rules" / "planet_in_house.json"


def test_library_is_complete_and_safe():
    rules = json.loads(FILE.read_text(encoding="utf-8"))["rules"]
    assert len(rules) == 108 and len({r["id"] for r in rules}) == 108
    pairs = {(r["when"]["planet"], r["when"]["house"]) for r in rules}
    assert len(pairs) == 108
    for r in rules:
        assert r["review_status"] == "draft" and r["source"]["text"] and r["text_hi"]
    blob = json.dumps(rules, ensure_ascii=False)
    for bad in ("मृत्यु", "बीमारी", "रोग", "कैंसर", "दरिद्र", "विनाश"):
        assert bad not in blob, bad
    assert "मंगल-दोष" in next(r for r in rules if r["id"] == "mars_in_7")["text_hi"]
    assert "मंगल-दोष" not in next(r for r in rules if r["id"] == "mars_in_3")["text_hi"]


def test_every_planet_gets_exactly_one_reading():
    c = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)
    house = [r for r in c["readings"] if r["category"] == "planet_in_house"]
    assert sorted(r["planet"] for r in house) == sorted(p["name"] for p in c["planets"])
    assert len(load_rules()) == 108 + 7 + 7 + 7 + 5


def test_dignity_and_retrograde_rules_fire_correctly():
    c = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)
    ids = {r["rule_id"] for r in c["readings"]}
    pl = {p["name"]: p for p in c["planets"]}
    assert pl["Venus"]["dignity"] == "exalted" and "venus_exalted" in ids
    assert pl["Saturn"]["dignity"] == "own" and "saturn_own_sign" in ids
    assert ("mercury_retrograde" in ids) == pl["Mercury"]["retrograde"]
    assert "sun_debilitated" not in ids
    blob = open(__import__("pathlib").Path(__file__).resolve().parents[2] / "data" / "rules" / "dignity_retrograde.json", encoding="utf-8").read()
    for bad in ("मृत्यु", "बीमारी", "रोग", "दरिद्र", "विनाश"):
        assert bad not in blob


def test_every_rule_has_english_text_in_tendency_language():
    from jyotish.rules import load_rules
    rules = load_rules()
    assert len(rules) == 134
    banned = ("death", "die ", "disease", "illness", "accident", "doom", "curse", "will lose", "will die")
    for r in rules:
        t = r["text_en"]
        assert t and len(t) > 40, r["id"]
        assert not any(b in t.lower() for b in banned), r["id"]
        assert "इंजन अभी उन्हें नहीं जाँचता" not in r["text_hi"]
    mars = next(r for r in rules if r["id"] == "mars_in_7")
    assert "Mangal Dosha" in mars["text_en"]


def test_knowledge_files_have_english_for_learn_panel():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "data" / "knowledge"
    n = json.loads((root / "nakshatras.json").read_text(encoding="utf-8"))["nakshatras"]
    s = json.loads((root / "signs.json").read_text(encoding="utf-8"))
    s = s["signs"] if isinstance(s, dict) else s
    assert len(n) == 27 and all(x["deity_en"] and x["symbol_en"] and len(x["traits_en"]) > 20 for x in n)
    assert len(s) == 12 and all(x["element_en"] in ("Fire", "Earth", "Air", "Water") and x["modality_en"] in ("movable", "fixed", "dual") and x["traits_en"] for x in s)
    from jyotish import vargas
    assert set(vargas.MEANING_EN) == set(vargas.MEANING_HI)
