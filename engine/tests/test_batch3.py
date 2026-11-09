"""Eclipse local circumstances + sutak, outer planets & true node, Nadi layer, regional term packs."""
from datetime import date

from jyotish import nadi, panchang_extra as px, regional
from jyotish.ephemeris import true_node, mean_node
from jyotish.handlers import chart_from_payload, eclipse_from_query, panchang_today_from_query

B = {"date": "1990-05-15", "time": "10:30", "tz": "Asia/Kolkata", "lat": 28.61, "lon": 77.2}


def test_eclipse_local_delhi_2025_09_07_total_lunar():
    ec = next(e for e in px.eclipses(2025, "Asia/Kolkata") if e["date"] == "2025-09-07")
    r = px.eclipse_local(ec, 28.61, 77.2, "Asia/Kolkata")
    assert r["type"] == "total" and r["visible"] and r["umbral_start"] == "21:58" and r["total_start"] == "23:01" and r["umbral_end"] == "01:26"
    assert 1.33 <= r["magnitude"] <= 1.40 and r["sutak"]["start"].endswith("12:58") and "सूतक" in r["sutak"]["text_hi"]


def test_eclipse_local_not_visible_and_solar_absent():
    ecs = px.eclipses(2025, "Asia/Kolkata")
    mar = px.eclipse_local(next(e for e in ecs if e["date"] == "2025-03-14"), 28.61, 77.2, "Asia/Kolkata")
    assert mar["type"] == "total" and mar["visible"] is False and "sutak" not in mar and "दिखाई नहीं" in mar["text_hi"]
    sol = px.eclipse_local(next(e for e in ecs if e["date"] == "2025-03-29"), 28.61, 77.2, "Asia/Kolkata")
    assert sol["occurs_here"] is False
    # the March 2025 solar eclipse was partial over Europe: Paris sees it
    paris = px.eclipse_local(next(e for e in ecs if e["date"] == "2025-03-29"), 48.85, 2.35, "Europe/Paris")
    assert paris["occurs_here"] and paris["visible"] and paris["type"] == "partial" and 0.2 <= paris["magnitude"] <= 0.4 and paris["maximum"] in ("12:01", "12:02", "12:03", "12:04")
    out = eclipse_from_query({"year": "2026", "lat": 28.61, "lon": 77.2, "tz": "Asia/Kolkata"})
    assert len(out["eclipses"]) == 4 and any(e.get("sutak") for e in out["eclipses"])


def test_outer_planets_and_true_node():
    ch = chart_from_payload(B)
    names = [o["name"] for o in ch["outer_planets"]]
    assert names == ["Uranus", "Neptune", "Pluto"] and ch["outer_planets"][0]["sign_name"] == "Dhanu" and ch["outer_planets"][2]["sign_name"] == "Tula"
    assert all(o["name"] not in {p["name"] for p in ch["planets"]} for o in ch["outer_planets"])
    jd = 2448026.7
    assert 0.5 < abs(((true_node(jd) - mean_node(jd) + 180) % 360) - 180) < 2.0
    ct = chart_from_payload({**B, "node_type": "true"})
    assert ct["input"]["node_type"] == "true" and ct["planets"][7]["dms"] != ch["planets"][7]["dms"]
    assert chart_from_payload({**B, "outer": False})["outer_planets"] == []


def test_nadi_layer():
    ch = chart_from_payload(B)
    n = ch["nadi"]
    assert n["system"] == "bhrigu_nandi_nadi" and n["nadi_kuta"]["name"] == "Antya" and 1 <= n["nadi_amsha"]["moon"] <= 150
    topics = {l["topic"] for l in n["lines"]}
    assert {"jeeva", "karma"} <= topics and all(l["hi"] and l["en"] for l in n["lines"])
    assert len(n["jupiter_clock"]) == 2 and n["jupiter_clock"][0]["year"] == date.today().year
    assert nadi.nadi_of_nakshatra(0) == "Adi" and nadi.nadi_of_nakshatra(2) == "Antya" and nadi.nadi_of_nakshatra(5) == "Adi"
    assert nadi.nadi_amsha(0.0) == 1 and nadi.nadi_amsha(29.99) == 150


def test_regional_packs_complete_and_localize():
    for lang in regional.LANGS:
        assert len(regional.SIGNS_L[lang]) == 12 and len(regional.VARA_L[lang]) == 7 and len(regional.TITHI_L[lang]) == 16
        assert len(regional.NAK_L[lang]) == 27 and len(regional.YOGA_L[lang]) == 27 and len(regional.KARANA_L[lang]) == 11 and len(regional.MASA_L[lang]) == 12
        assert set(regional.LABELS[lang]) == set(regional.LABELS["te"])
    r = panchang_today_from_query({"date": "2026-11-09", "lat": 17.38, "lon": 78.48, "tz": "Asia/Kolkata", "lang": "te"})
    assert r["vara_loc"] == "సోమవారం" and r["tithi_loc"] == "అమావాస్య" and r["nakshatra_loc"] == "స్వాతి" and r["masa_amanta_loc"] == "ఆశ్వయుజం" and r["labels"]["rahu_kaal"] == "రాహుకాలం"
    g = panchang_today_from_query({"date": "2026-11-09", "lat": 23.02, "lon": 72.57, "tz": "Asia/Kolkata", "lang": "gu"})
    assert g["paksha_loc"] == "વદ" and g["tithi_loc"] == "અમાસ" and g["masa_amanta_loc"] == "આસો"
    assert "vara_loc" not in panchang_today_from_query({"date": "2026-11-09", "lat": 23.02, "lon": 72.57, "tz": "Asia/Kolkata"})
