from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from jyotish import handlers
from jyotish.muhurta import day_table
from jyotish.numerology import analyse, name_value, reduce
from jyotish.sun import sun_times
from jyotish.vargas import all_vargas, varga_sign

IST = "Asia/Kolkata"
DELHI = (28.6139, 77.2090)


def minutes(dt):
    return dt.hour * 60 + dt.minute


# ---------------------------------------------------------------- sunrise
def test_sunrise_sunset_delhi_summer_solstice():
    t = sun_times(date(2026, 6, 21), *DELHI, IST)
    assert minutes(t["sunrise"]) == pytest.approx(5 * 60 + 23, abs=3)   # ~05:23
    assert minutes(t["sunset"]) == pytest.approx(19 * 60 + 22, abs=3)   # ~19:22


def test_equator_day_is_about_twelve_hours():
    t = sun_times(date(2026, 3, 20), -0.18, -78.47, "America/Guayaquil")
    hours = (t["sunset"] - t["sunrise"]).total_seconds() / 3600
    assert hours == pytest.approx(12.1, abs=0.15)


def test_polar_day_has_no_sunrise():
    assert sun_times(date(2026, 6, 21), 69.65, 18.96, "Europe/Oslo") is None


# ---------------------------------------------------------------- day table
def test_vara_before_sunrise_is_previous_day():
    # 2026-11-08 is a Sunday; before sunrise the Vedic day is still Saturday
    before = day_table(datetime(2026, 11, 8, 4, 30, tzinfo=ZoneInfo(IST)), 23.1815, 79.9864, IST)
    after = day_table(datetime(2026, 11, 8, 9, 0, tzinfo=ZoneInfo(IST)), 23.1815, 79.9864, IST)
    assert before["vedic_vara"]["name"] == "Shanivara" and before["vedic_vara"]["before_sunrise"]
    assert after["vedic_vara"]["name"] == "Ravivara" and not after["vedic_vara"]["before_sunrise"]


def test_rahu_kaal_sunday_is_last_eighth_and_abhijit_is_centred():
    d = day_table(datetime(2026, 11, 8, 9, 0, tzinfo=ZoneInfo(IST)), 23.1815, 79.9864, IST)
    assert d["rahu_kaal"]["end"] == d["sunset"]            # Sunday: 8th part ends at sunset

    def to_min(s):
        h, m = s.split(":")
        return int(h) * 60 + int(m)
    mid = (to_min(d["sunrise"]) + to_min(d["sunset"])) / 2
    ab = (to_min(d["abhijit"]["start"]) + to_min(d["abhijit"]["end"])) / 2
    assert ab == pytest.approx(mid, abs=1.5)
    assert len(d["choghadiya_day"]) == 8 and len(d["choghadiya_night"]) == 8
    assert d["choghadiya_day"][0]["name"] == "Udveg"        # Sunday day starts with Udveg


# ---------------------------------------------------------------- vargas
def test_varga_rules_on_known_points():
    taurus_2 = 32.0                        # 2 deg Taurus (even sign)
    assert varga_sign(taurus_2, "D9") == 9      # Makara
    assert varga_sign(taurus_2, "D2") == 3      # even sign, first half -> Moon's hora (Karka)
    assert varga_sign(taurus_2, "D3") == 1      # first third -> same sign
    assert varga_sign(taurus_2, "D7") == 7      # even sign starts from 7th (Vrishchika)
    assert varga_sign(taurus_2, "D10") == 9     # even sign starts from 9th (Makara)
    aries_20 = 20.0                        # 20 deg Mesha (odd sign)
    assert varga_sign(aries_20, "D2") == 3      # odd sign, second half -> Moon (Karka)
    assert varga_sign(aries_20, "D3") == 8      # third third -> 9th from Mesha = Dhanu
    assert varga_sign(aries_20, "D4") == 6      # third quarter (15-22.5 deg) -> 7th from Mesha = Tula


def test_all_vargas_shape():
    planets = [{"name": n, "longitude": 10.0 + 33.3 * i}
               for i, n in enumerate(["Sun", "Moon", "Mars", "Mercury", "Jupiter",
                                      "Venus", "Saturn", "Rahu", "Ketu"])]
    v = all_vargas(123.4, planets)
    assert set(v) == {"D1", "D2", "D3", "D4", "D7", "D9", "D10", "D12"}
    for chart in v.values():
        assert len(chart["houses"]) == 12
        assert sum(len(h["planets"]) for h in chart["houses"]) == 9
        assert chart["houses"][0]["sign"] == chart["lagna_sign"]


def test_boundaries_do_not_slip():
    assert varga_sign(30.0, "D9") == 9          # exactly 0 deg Taurus
    assert varga_sign(10.0, "D9") == 3          # 10 deg Mesha starts the 4th navamsha = Karka
    assert varga_sign(9.999999, "D9") == 2      # just before the edge is still the 3rd (Mithuna)
    assert varga_sign(359.9999999, "D12") in range(12)


# ---------------------------------------------------------------- numerology
def test_numerology_known_values():
    a = analyse(date(1990, 5, 17), "Prashant Mahto", date(2026, 11, 8))
    assert a["moolank"]["number"] == 8 and a["moolank"]["planet"] == "Saturn"
    assert a["bhagyank"]["number"] == 5            # (1+7)+5+(1+9+9+0) = 32 -> 5
    assert a["personal_year"]["number"] == 5       # 8 + 5 + (2+0+2+6) = 23 -> 5
    assert a["lo_shu"]["counts"][1] == 2 and a["lo_shu"]["counts"][9] == 2
    assert a["lo_shu"]["missing"] == [2, 3, 4, 6]


def test_reduce_and_name_values():
    assert reduce(29) == 2 and reduce(29, keep_master=True) == 11
    assert reduce(38) == 2 and reduce(9) == 9
    assert name_value("Cheiro")["compound"] == 23          # C3 H5 E5 I1 R2 O7
    assert name_value("A")["number"] == 1 and name_value("123")["number"] == 0


def test_numerology_handler_validation():
    ok = handlers.numerology_from_payload({"date": "2000-01-01", "name": "Test"})
    assert "namank" in ok
    with pytest.raises(handlers.BadRequest):
        handlers.numerology_from_payload({"date": "2000-02-31"})
    with pytest.raises(handlers.BadRequest):
        handlers.numerology_from_payload({})


def test_chart_now_contains_day_and_vargas():
    chart = handlers.chart_from_payload({"date": "1990-05-17", "time": "06:45", "tz": IST,
                                         "lat": 23.1815, "lon": 79.9864})
    assert chart["day"]["available"] and "D10" in chart["vargas"]
    assert chart["panchang"]["vara"]["name"] == "Guruvara"   # 1990-05-17 was a Thursday
