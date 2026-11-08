import pytest

from jyotish import compute_chart, relations as rel
from jyotish.constants import DEBILITATION, EXALTATION, PLANETS_HI, SIGNS_HI

LAGNA = 0  # Mesha


def mk(positions: dict, retro=()):
    """Synthetic chart: positions = {planet: (sign, degree)}; Mesha lagna, whole-sign houses."""
    planets = []
    for n, (sign, deg) in positions.items():
        dig = "debilitated" if sign == DEBILITATION.get(n) else "exalted" if sign == EXALTATION.get(n) else None
        planets.append({"name": n, "name_hi": PLANETS_HI[n], "sign": sign, "sign_name_hi": SIGNS_HI[sign],
                        "longitude": sign * 30 + deg, "house": (sign - LAGNA) % 12 + 1, "dignity": dig,
                        "retrograde": n in retro})
    return {"planets": planets}


BASE = {"Sun": (6, 10), "Moon": (7, 5), "Mars": (7, 20), "Mercury": (4, 3), "Jupiter": (2, 3),
        "Venus": (5, 3), "Saturn": (11, 3), "Rahu": (8, 3), "Ketu": (2, 13)}


def test_no_cancellation_when_nothing_applies():
    # Sun debilitated in Tula (house 7 = kendra itself). Venus (dispositor) in Kanya (house 6), Moon in Vrischika (8):
    # Venus is 11th from Moon? make sure no kendra from lagna or Moon, no aspect, navamsa not exalted.
    pos = dict(BASE)
    pos["Sun"] = (6, 25)                    # navamsa of 25 deg Libra is Taurus-ish, not Aries
    pos["Moon"] = (7, 5)
    pos["Mars"] = (2, 20)                   # exaltation lord of Sun's sign: house 3, 8th from Moon -> no kendra
    pos["Venus"] = (5, 3)                   # house 6 from lagna; from Moon (Vrischika, h8): 11th
    pos["Saturn"] = (11, 3)                 # exalted in Tula but sits in house 12; from Moon 5th
    r = rel.neecha_bhanga(mk(pos))
    sun = next(x for x in r if x["planet"] == "Sun")
    assert not sun["cancelled"] and sun["conditions"] == []


def test_dispositor_in_kendra_cancels():
    pos = dict(BASE)
    pos["Sun"] = (6, 25)
    pos["Venus"] = (3, 3)                   # Karka = house 4 = kendra from lagna
    sun = next(x for x in rel.neecha_bhanga(mk(pos)) if x["planet"] == "Sun")
    assert sun["cancelled"] and "dispositor_kendra" in [c["id"] for c in sun["conditions"]]


def test_raised_planet_in_kendra_and_exaltation_lord():
    pos = dict(BASE)
    pos["Sun"] = (6, 25)
    pos["Saturn"] = (9, 3)                  # Saturn (exalted in Tula) in Makara = house 10 = kendra
    ids = [c["id"] for c in next(x for x in rel.neecha_bhanga(mk(pos)) if x["planet"] == "Sun")["conditions"]]
    assert "raised_planet_kendra" in ids
    pos2 = dict(BASE)
    pos2["Sun"] = (6, 25)
    pos2["Mars"] = (0, 3)                   # Mars lords Mesha (Sun's exaltation sign): house 1 kendra
    ids2 = [c["id"] for c in next(x for x in rel.neecha_bhanga(mk(pos2)) if x["planet"] == "Sun")["conditions"]]
    assert "exaltation_lord_kendra" in ids2


def test_conjunction_with_dispositor_and_aspect():
    pos = dict(BASE)
    pos["Sun"] = (6, 25)
    pos["Venus"] = (6, 12)
    assert "conjunct_dispositor" in [c["id"] for c in next(x for x in rel.neecha_bhanga(mk(pos)) if x["planet"] == "Sun")["conditions"]]
    pos["Venus"] = (0, 12)                  # Venus in Mesha: 7th aspect falls on Tula
    ids = [c["id"] for c in next(x for x in rel.neecha_bhanga(mk(pos)) if x["planet"] == "Sun")["conditions"]]
    assert "aspected_by_dispositor" in ids


def test_navamsa_exaltation_condition():
    pos = dict(BASE)
    pos["Sun"] = (6, 22)                    # Tula 22 deg: 7th navamsa part -> Aries navamsa (exalted for Sun)
    ids = [c["id"] for c in next(x for x in rel.neecha_bhanga(mk(pos)) if x["planet"] == "Sun")["conditions"]]
    assert "exalted_in_navamsa" in ids


def test_combustion_orbs_and_retrograde():
    pos = dict(BASE)
    pos["Sun"] = (1, 10)
    pos["Mercury"] = (1, 22.5)              # 12.5 degrees from the Sun
    assert [c["planet"] for c in rel.combustion(mk(pos))] == ["Mercury"]
    assert rel.combustion(mk(pos, retro=("Mercury",))) == []      # retrograde orb is 12
    pos["Venus"] = (1, 18.5)                # 8.5 degrees
    assert "Venus" in [c["planet"] for c in rel.combustion(mk(pos))]
    assert "Venus" not in [c["planet"] for c in rel.combustion(mk(pos, retro=("Venus",)))]


def test_conjunctions_same_sign_only():
    pos = dict(BASE)
    pos.update({"Sun": (1, 29), "Mercury": (2, 1)})        # 2 degrees apart but different signs
    c = rel.conjunctions(mk(pos))
    assert all(set(x["planets"]) != {"Sun", "Mercury"} for x in c)
    pos["Mercury"] = (1, 25)
    c = rel.conjunctions(mk(pos))
    row = next(x for x in c if set(x["planets"]) == {"Sun", "Mercury"})
    assert row["orb"] == pytest.approx(4.0) and not row["close"]


def test_aspects_houses():
    a = rel.aspects(mk(BASE))
    mars = [r for r in a["planets"] if r["from"] == "Mars"]
    assert sorted(r["aspect"] for r in mars) == [4, 7, 8]
    assert mars[0]["to_house"] == (8 + 4 - 2) % 12 + 1               # Mars in Vrischika = house 8
    assert "Mars" in a["houses"][mars[0]["to_house"]]
    jup = sorted(r["to_house"] for r in a["planets"] if r["from"] == "Jupiter")
    assert jup == sorted(((3 + n - 2) % 12 + 1) for n in (5, 7, 9))


def test_chart_integration_has_relations():
    c = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)
    r = c["relations"]
    assert set(r) == {"neecha_bhanga", "conjunctions", "combustion", "aspects"}
    assert len(r["aspects"]["planets"]) >= 9 and set(r["aspects"]["houses"]) == set(range(1, 13))
