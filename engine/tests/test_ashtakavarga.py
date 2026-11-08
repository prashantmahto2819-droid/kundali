from jyotish import ashtakavarga as av
from jyotish import compute_chart


def test_table_totals_match_classical_counts():
    for pl, exp in av.EXPECTED_TOTALS.items():
        assert sum(len(h) for h in av.TABLES[pl].values()) == exp, pl
    assert sum(av.EXPECTED_TOTALS.values()) == 337
    for pl, rows in av.TABLES.items():
        assert set(rows) == {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Lagna"}
        for houses in rows.values():
            assert list(houses) == sorted(set(houses)) and all(1 <= h <= 12 for h in houses)


def test_every_chart_gives_337_and_per_planet_totals():
    for date, tm, lat, lon in [("1990-05-17", "06:45", 23.18, 79.99), ("1947-08-15", "00:00", 28.61, 77.21),
                               ("2001-12-31", "23:59", 19.08, 72.88)]:
        c = compute_chart(date, tm, "Asia/Kolkata", lat, lon)
        a = c["ashtakavarga"]
        assert a["sav"]["total"] == 337 and sum(a["sav"]["by_house"]) == 337
        for pl, exp in av.EXPECTED_TOTALS.items():
            assert a["bav"][pl]["total"] == exp
            assert max(a["bav"][pl]["by_sign"]) <= 8
        assert all(b in ("strong", "medium", "weak") for b in a["sav"]["bands"])


def test_known_hand_example():
    # every contributor in Aries, so house n from each contributor is sign n-1 (Aries = house 1)
    signs = {k: 0 for k in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Lagna")}
    row = av.bav("Sun", signs)
    assert row[0] == 3   # 1st house: Sun, Mars, Saturn
    assert row[2] == 3   # 3rd house: Moon, Mercury, Lagna
    assert row[5] == 5   # 6th house: Moon, Mercury, Jupiter, Venus, Lagna
    assert sum(row) == 48
    # a contributor further round the zodiac shifts its points: Lagna in Taurus moves its row by one sign
    moved = av.bav("Sun", {**signs, "Lagna": 1})
    assert moved[0] == row[0] + 1 and moved[2] == row[2] - 1   # Aries gains (12th from Taurus), Gemini loses
