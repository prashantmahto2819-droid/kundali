from datetime import date

from jyotish import handlers, notify, regional


def test_tamil_malayalam_packs_complete():
    for lang in ("ta", "ml"):
        assert lang in regional.LANGS and lang in regional.REGIONAL
        assert len(regional.SIGNS_L[lang]) == 12 and len(regional.VARA_L[lang]) == 7 and len(regional.TITHI_L[lang]) == 16
        assert len(regional.NAK_L[lang]) == 27 and len(regional.YOGA_L[lang]) == 27 and len(regional.MASA_L[lang]) == 12
        assert set(regional.KARANA_L[lang]) == set(regional.KARANA_L["te"]) and set(regional.LABELS[lang]) == set(regional.LABELS["te"])


def test_tamil_malayalam_day_and_whatsapp():
    d = handlers.panchang_today_from_query({"date": "2026-11-20", "lat": 13.08, "lon": 80.27, "tz": "Asia/Kolkata", "lang": "ta"})
    assert d["lang"] == "ta" and d["labels"]["tithi"] == "திதி" and d["vara_loc"] == "வெள்ளி"
    m = handlers.panchang_today_from_query({"date": "2026-11-20", "lat": 9.93, "lon": 76.26, "tz": "Asia/Kolkata", "lang": "ml"})
    assert m["vara_loc"] == "വെള്ളി" and m["nakshatra_loc"] in regional.NAK_L["ml"]
    sub = {"lang": "ml", "tz": "Asia/Kolkata", "lat": 9.93, "lon": 76.26, "place": "Kochi", "vrat_kinds": "festival"}
    txt = notify.compose_daily(sub, date(2026, 11, 20))
    assert "പഞ്ചാംഗം" in txt and "തിഥി" in txt
