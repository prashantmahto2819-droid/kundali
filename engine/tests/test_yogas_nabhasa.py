"""Pattern yogas: Mahapurusha, 32 Nabhasa, conjunction yogas."""
from jyotish import compute_chart, yogas_nabhasa as yn
from jyotish.ephemeris import AnalyticBackend

B = AnalyticBackend()


def _chart(houses: dict, signs: dict | None = None, lagna_sign: int = 0, nodes: dict | None = None):
    """Minimal chart-like dict: houses (1-12) and signs for the seven planets."""
    planets = []
    for n in yn.SEVEN:
        h = houses[n]
        s = (signs or {}).get(n, (lagna_sign + h - 1) % 12)
        planets.append({"name": n, "house": h, "sign": s})
    for n in ("Rahu", "Ketu"):
        if nodes and n in nodes:
            planets.append({"name": n, "house": nodes[n], "sign": (lagna_sign + nodes[n] - 1) % 12})
    return {"planets": planets, "lagna": {"sign": lagna_sign}}


def _by(out):
    return {y["id"]: y for y in out}


def test_catalogue_complete():
    out = yn.detect(_chart({n: 1 for n in yn.SEVEN}))
    ids = {y["id"] for y in out}
    assert len([i for i in ids if i in yn.NABHASA_TEXT]) == 32 and len(yn.MAHAPURUSHA) == 5
    assert all(y["name_hi"] and y["why_hi"] is not None and y["review_status"] == "draft" for y in out)


def test_mahapurusha():
    # Mars in Aries (own) in house 1 with Aries Lagna → Ruchaka
    out = _by(yn.detect(_chart({"Mars": 1, "Sun": 2, "Moon": 3, "Mercury": 5, "Jupiter": 6, "Venus": 8, "Saturn": 9}, lagna_sign=0)))
    assert out["ruchaka"]["present"] and not out["hamsa"]["present"]
    # Jupiter in Cancer (exalted) in house 4 with Aries Lagna → Hamsa
    out = _by(yn.detect(_chart({"Jupiter": 4, "Sun": 2, "Moon": 3, "Mercury": 5, "Mars": 6, "Venus": 8, "Saturn": 9}, lagna_sign=0)))
    assert out["hamsa"]["present"]
    # same Jupiter but in house 5 → no
    out = _by(yn.detect(_chart({"Jupiter": 5, "Sun": 2, "Moon": 3, "Mercury": 6, "Mars": 7, "Venus": 8, "Saturn": 9}, {"Jupiter": 3}, lagna_sign=0)))
    assert not out["hamsa"]["present"]


def test_nabhasa_patterns():
    kendras = {"Sun": 1, "Moon": 4, "Mars": 7, "Mercury": 10, "Jupiter": 1, "Venus": 4, "Saturn": 7}
    out = _by(yn.detect(_chart(kendras)))
    assert out["kamala"]["present"] and not out["gola"]["present"] and not out["veena"]["present"]   # Akriti beats Sankhya
    out = _by(yn.detect(_chart({n: 1 for n in yn.SEVEN})))
    assert out["gola"]["present"] and out["musala"]["present"] is False and out["rajju"]["present"]   # all in Aries: movable
    shakata = {"Sun": 1, "Moon": 1, "Mars": 7, "Mercury": 1, "Jupiter": 7, "Venus": 7, "Saturn": 1}
    out = _by(yn.detect(_chart(shakata)))
    assert out["shakata"]["present"] and not out["kamala"]["present"]
    nauka = dict(zip(yn.SEVEN, [1, 2, 3, 4, 5, 6, 7]))
    out = _by(yn.detect(_chart(nauka)))
    assert out["nauka"]["present"] and not out["ardha_chandra"]["present"] and not out["veena"]["present"]
    ardha = dict(zip(yn.SEVEN, [2, 3, 4, 5, 6, 7, 8]))
    assert _by(yn.detect(_chart(ardha)))["ardha_chandra"]["present"]
    spread = dict(zip(yn.SEVEN, [1, 2, 3, 5, 6, 8, 9]))         # no akriti shape → Sankhya by signs (7 signs) → Veena
    out = _by(yn.detect(_chart(spread)))
    assert out["veena"]["present"] and not any(out[k]["present"] for k in ("nauka", "kuta", "chhatra", "chapa", "chakra", "samudra"))
    mala = {"Jupiter": 1, "Venus": 4, "Mercury": 7, "Sun": 2, "Moon": 5, "Mars": 8, "Saturn": 11}
    assert _by(yn.detect(_chart(mala)))["mala"]["present"]
    vajra = {"Jupiter": 1, "Venus": 7, "Mercury": 1, "Sun": 4, "Moon": 10, "Mars": 10, "Saturn": 4}
    assert _by(yn.detect(_chart(vajra)))["vajra"]["present"]


def test_conjunction_yogas():
    out = _by(yn.detect(_chart({"Sun": 2, "Moon": 3, "Mars": 5, "Mercury": 2, "Jupiter": 6, "Venus": 8, "Saturn": 3}, nodes={"Rahu": 6, "Ketu": 12})))
    assert out["guru_chandala"]["present"] and out["vish"]["present"] and not out["angaraka"]["present"]
    assert out["shakata_moon"]["present"] is ((3 - 6) % 12 + 1 in (6, 8, 12))


def test_real_chart_carries_pattern_yogas():
    c = compute_chart("1991-04-09", "16:30", "Asia/Kolkata", 22.35, 82.68, backend=B)
    ids = {y["id"] for y in c["yogas"]}
    assert "ruchaka" in ids and "kamala" in ids and "guru_chandala" in ids and "gajakesari" in ids
    assert all("group" in y for y in c["yogas"])
    assert sum(1 for y in c["yogas"] if y["present"] and y["group"] == "nabhasa_sankhya") <= 1
