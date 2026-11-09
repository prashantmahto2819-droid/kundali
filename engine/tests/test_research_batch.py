"""Doshas/remedies, Yogini dasha, ayanamsa options, almanac extras (varjyam/amrit/dur muhurtam/anandadi/pushya), eclipses, name seeds."""
from datetime import date, datetime, timezone

import pytest

from jyotish import doshas, festivals, panchang_extra as px, panchang_month as pm, yogini
from jyotish.core import ayanamsa
from jyotish.handlers import BadRequest, chart_from_payload

B = {"date": "1990-05-15", "time": "10:30", "tz": "Asia/Kolkata", "lat": 28.61, "lon": 77.2}


def test_doshas_layer_and_remedies():
    ch = chart_from_payload(B)
    d = ch["doshas"]
    assert d["kaal_sarp"]["status"] in ("none", "partial", "full") and d["kaal_sarp"]["type_hi"] in (None, *doshas.KAAL_SARP_HI)
    assert d["mangal"]["houses"]["lagna"] == 8 and d["mangal"]["present"] and "गुरु" in " ".join(d["mangal"]["cancellations_hi"])
    assert d["pitru"]["present"] and "नवमेश" in d["pitru"]["text_hi"]
    r = d["remedies"]
    assert r["gemstones"][0]["planet"] == "Moon" and r["gemstones"][0]["gem_en"] == "Pearl" and r["rudraksha"]["mukhi"] == 2
    assert r["ishta_devata"]["devata_en"] and "Saturn" in r["avoid_planets"] or "Jupiter" in r["avoid_planets"]


def test_kaal_sarp_full_detection():
    # synthetic: Rahu 0°, Ketu 180°, all seven planets between 10° and 170° → full, Anant (Rahu in house 1)
    pl = [{"name": n, "longitude": lon, "sign": int(lon // 30), "house": int(lon // 30) + 1} for n, lon in
          (("Sun", 10), ("Moon", 40), ("Mars", 70), ("Mercury", 100), ("Jupiter", 130), ("Venus", 150), ("Saturn", 170), ("Rahu", 0), ("Ketu", 180))]
    ks = doshas.kaal_sarp({"planets": pl, "lagna": {"sign": 0}})
    assert ks["present"] and ks["type"] == "Anant" and ks["direction"] == "rahu_to_ketu"
    pl[6]["longitude"] = 200; pl[6]["sign"] = 6; pl[6]["house"] = 7
    ks = doshas.kaal_sarp({"planets": pl, "lagna": {"sign": 0}})
    assert ks["partial"] and not ks["present"] and ks["outside"] == ["Saturn"]


def test_yogini_dasha_cycle():
    y = yogini.yogini(266.6667, datetime(1990, 5, 15, 5, tzinfo=timezone.utc), datetime(2026, 11, 9, tzinfo=timezone.utc))   # Moon 266.67° = Uttara Ashadha start → (21+3)%8=0 Mangala
    assert y["periods"][0]["name"] == "Mangala" and y["periods"][0]["balance_years"] == 1.0
    assert [p["name"] for p in y["periods"][:8]] == ["Mangala", "Pingala", "Dhanya", "Bhramari", "Bhadrika", "Ulka", "Siddha", "Sankata"]
    assert y["periods"][8]["name"] == "Mangala"                       # 36-year cycle repeats
    assert y["running"]["mahadasha"]["name"] == "Mangala" and len(y["periods"][0]["antardashas"]) == 8
    ch = chart_from_payload(B)
    assert ch["yogini_dasha"]["running"]["mahadasha"]["name_hi"]


def test_ayanamsa_options():
    jd = 2451545.0
    assert abs(ayanamsa(jd, "lahiri") - 23.853) < 0.01 and abs(ayanamsa(jd, "raman") - 22.367) < 0.01 and abs(ayanamsa(jd, "kp") - 23.766) < 0.01
    with pytest.raises(ValueError):
        ayanamsa(jd, "fagan")
    ch = chart_from_payload({**B, "ayanamsa": "raman"})
    assert ch["input"]["ayanamsa"] == "raman" and ch["lagna"]["degree_in_sign"] > chart_from_payload(B)["lagna"]["degree_in_sign"]
    with pytest.raises(BadRequest):
        chart_from_payload({**B, "ayanamsa": "zzz"})


def test_panchang_extras_fields():
    d = pm.month(2026, 11, 28.61, 77.2, "Asia/Kolkata", only_day=9)["days"][0]
    assert d["varjyam"] == [{"start": "13:26", "end": "15:10"}] and d["amrit_kalam"]["start"] == "00:35"
    assert len(d["dur_muhurtam"]) == 2 and d["dur_muhurtam"][0]["start"] == "12:26"           # Monday: 9th and 12th muhurta
    assert d["anandadi_yoga"] == {"name": "Chhatra", "hi": "छत्र", "auspicious": True}
    assert px.special_yogas(4, "Pushya", 0, 7, 5)[0]["key"] == "guru_pushya"
    assert px.special_yogas(0, "Krittika", 0, 2, 2)[0]["key"] == "tripushkara" or any(x["key"] == "tripushkara" for x in px.special_yogas(0, "Krittika", 0, 2, 2))
    assert px.anandadi(0, 0)["name"] == "Ananda" and px.anandadi(6, 23)["name"] == "Ananda"


def test_eclipses_2025_known_dates():
    ec = px.eclipses(2025, "Asia/Kolkata")
    assert [(e["kind"], e["date"]) for e in ec] == [("lunar", "2025-03-14"), ("solar", "2025-03-29"), ("lunar", "2025-09-07"), ("solar", "2025-09-22")]
    assert all(e["certainty"] == "sure" for e in ec)
    cal = festivals.calendar(2026, 28.61, 77.2, "Asia/Kolkata")
    gr = [e for e in cal["events"] if e["kind"] == "grahan"]
    assert [e["date"] for e in gr] == ["2026-02-17", "2026-03-03", "2026-08-12", "2026-08-28"]


def test_name_suggestions():
    ch = chart_from_payload(B)
    ns = ch["patri"]["avakahada"]["name_syllable"]
    assert ns["pada"] == "भे" and ns["suggestions"]["boys"] and ns["suggestions"]["girls"]
