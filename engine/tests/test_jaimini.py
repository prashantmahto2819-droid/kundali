from jyotish import compute_chart, jaimini

C = compute_chart("1990-05-17", "06:45", "Asia/Kolkata", 23.18, 79.99)


def test_chara_karakas_ranked_by_degree():
    ck = C["jaimini"]["chara_karakas"]
    degs = [k["degree_in_sign"] for k in ck["scheme7"]]
    assert degs == sorted(degs, reverse=True) and len(ck["scheme7"]) == 7 and len(ck["scheme8"]) == 8
    assert ck["scheme7"][0]["karaka"] == "Atmakaraka" and ck["scheme7"][-1]["karaka"] == "Darakaraka"
    assert "Rahu" in [k["planet"] for k in ck["scheme8"]] and "Rahu" not in [k["planet"] for k in ck["scheme7"]]
    ak = C["jaimini"]["atmakaraka"]
    assert ak == max((p for p in C["planets"] if p["name"] not in ("Rahu", "Ketu")), key=lambda p: p["degree_in_sign"])["name"]


def test_arudha_rule_and_exception():
    # synthetic: Lagna Mesha (0); Mars (lord of 1) in Karka (3): 4 signs away -> pada = Karka + 3 = Tula (6) ... 7th from house -> exception -> 10th from Tula = Karka
    planets = [{"name": n, "sign": s, "degree_in_sign": 10.0, "navamsa_sign": 0} for n, s in
               (("Sun", 1), ("Moon", 2), ("Mars", 3), ("Mercury", 4), ("Jupiter", 5), ("Venus", 7), ("Saturn", 8), ("Rahu", 9), ("Ketu", 3))]
    padas = jaimini.arudha_padas(0, planets)
    al = padas[0]
    assert al["lord"] == "Mars" and al["exception_applied"] and al["pada_sign_name"] == "Karka"
    # house 2 (Vrishabha, lord Venus in Vrishchika = 6 signs away) -> 6 more = Vrishabha itself -> exception -> 10th = Kumbha
    assert padas[1]["exception_applied"] and padas[1]["pada_sign_name"] == "Kumbha"
    # house 3 (Mithuna, lord Mercury in Simha, 2 away) -> Tula, no exception
    assert not padas[2]["exception_applied"] and padas[2]["pada_sign_name"] == "Tula"


def test_jaimini_in_chart_and_report():
    J = C["jaimini"]
    assert J["arudha_lagna"]["house"] == 1 and J["upapada"]["house"] == 12 and J["karakamsa"]["sign_name"] in jaimini.SIGNS
    from jyotish import report
    assert "जैमिनी" in report.render(C)
